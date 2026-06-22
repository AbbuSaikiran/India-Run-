import uuid
import io
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import Optional

from src.api.schemas import (
    RankingRequest, RankingResponse,
    JobParseRequest, JobParseResponse,
    GenerateAssessmentRequest, GeneratedAssessment,
    AssessmentSubmission, AssessmentResult,
)
from src.ranking.ranker import CandidateRanker
from src.llm_client import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_resume_profile,
    parse_job_description,
    generate_assessment,
    score_full_assessment,
    # Interview Engine
    analyze_resume,
    analyze_job_description,
    generate_interview_questions,
    evaluate_interview_answer,
    evaluate_all_answers,
    generate_final_interview_report,
)

router = APIRouter()
ranker = CandidateRanker()

# In-memory store for hackathon demo (replace with DB in production)
_assessments: dict = {}
_profiles: dict = {}
_results: dict = {}

# ─── Status ──────────────────────────────────────────────────────────────────

@router.get("/status")
async def status():
    return {"status": "operational", "api_version": "v2", "model": "TalentRank AI"}

# ─── Job Parsing ─────────────────────────────────────────────────────────────

@router.post("/parse-job")
async def parse_job(request: JobParseRequest):
    try:
        parsed = await parse_job_description(request.job_description)
        return parsed
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── Resume Upload & Extraction ───────────────────────────────────────────────

@router.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """
    Accept PDF or DOCX resume, extract text, return structured profile.
    """
    filename = file.filename or ""
    content = await file.read()
    raw_text = ""

    try:
        if filename.lower().endswith(".pdf"):
            raw_text = extract_text_from_pdf(content)
        elif filename.lower().endswith(".docx"):
            raw_text = extract_text_from_docx(content)
        elif filename.lower().endswith(".txt"):
            raw_text = content.decode("utf-8", errors="ignore")
        else:
            raw_text = content.decode("utf-8", errors="ignore")

        if not raw_text.strip():
            raise ValueError("No text could be extracted from the uploaded file.")

        profile = await extract_resume_profile(raw_text)
        profile_id = f"profile_{uuid.uuid4().hex[:8]}"
        _profiles[profile_id] = profile
        profile["profile_id"] = profile_id
        return profile

    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Resume extraction failed: {str(e)}")

# ─── Assessment Generation ────────────────────────────────────────────────────

@router.post("/generate-assessment")
async def generate_assessment_endpoint(request: GenerateAssessmentRequest):
    """
    Generate a unique, personalized AI assessment based on candidate + job.
    """
    try:
        projects = [p.model_dump() for p in request.projects]
        assessment = await generate_assessment(
            candidate_name=request.candidate_name,
            core_skills=request.core_skills,
            projects=projects,
            role=request.role,
            critical_requirements=request.critical_requirements
        )
        assessment["application_id"] = request.application_id or f"app_{uuid.uuid4().hex[:8]}"
        _assessments[assessment["assessment_id"]] = assessment
        return assessment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── Assessment Submission & Scoring ─────────────────────────────────────────

@router.post("/submit-assessment")
async def submit_assessment(submission: AssessmentSubmission):
    """
    Accept candidate answers and score them with the LLM.
    """
    assessment = _assessments.get(submission.assessment_id)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found.")
    
    try:
        answers = [a.model_dump() for a in submission.answers]
        result = await score_full_assessment(
            questions=assessment["questions"],
            answers=answers,
            role=assessment.get("role", "Unknown Role"),
            candidate_name=assessment.get("candidate_name", "Candidate")
        )
        result["assessment_id"] = submission.assessment_id
        result["application_id"] = submission.application_id
        _results[submission.assessment_id] = result
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── Legacy Ranking ───────────────────────────────────────────────────────────

@router.post("/rank", response_model=RankingResponse)
async def rank_candidates(request: RankingRequest):
    result = await ranker.rank_candidates(request.job, request.candidates)
    return result

# ─── Full Recruiter Dashboard ─────────────────────────────────────────────────

@router.post("/recruiter-dashboard")
async def recruiter_dashboard(payload: dict):
    """
    Build the full recruiter dashboard.
    Expects: { job_id, role_title, job_profile, candidates: [{name, email, profile, assessment_percentage}] }
    """
    try:
        result = await ranker.build_recruiter_dashboard(
            job_id=payload.get("job_id", "job_001"),
            role_title=payload.get("role_title", "Unknown Role"),
            candidates=payload.get("candidates", []),
            job_profile=payload.get("job_profile", {})
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  AI INTERVIEW ENGINE ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

# In-memory interview session store
_interview_sessions: dict = {}

@router.post("/interview/start")
async def start_interview(request: dict):
    """
    Phase 1+2+3: Analyze resume, analyze JD, generate full interview question set.
    Expects: { resume_text, job_description, candidate_name?, candidate_email? }
    """
    try:
        resume_text = request.get("resume_text", "")
        job_desc = request.get("job_description", "")
        candidate_email = request.get("candidate_email", "")

        if not resume_text.strip():
            raise HTTPException(status_code=400, detail="resume_text is required.")
        if not job_desc.strip():
            raise HTTPException(status_code=400, detail="job_description is required.")

        # Run Phase 1 (Resume Analysis) first, then Phase 2 + 3 concurrently
        candidate_analysis = await analyze_resume(resume_text)
        candidate_name = request.get("candidate_name", "") or candidate_analysis.get("candidate_name", "Candidate")

        # Phase 2 + 3 in parallel
        job_analysis, questions = await asyncio.gather(
            analyze_job_description(job_desc, candidate_analysis),
            generate_interview_questions(candidate_analysis, {}, resume_text)
        )

        session_id = f"iv_{uuid.uuid4().hex[:10]}"
        session = {
            "session_id": session_id,
            "candidate_name": candidate_name,
            "candidate_email": candidate_email,
            "resume_text": resume_text,
            "job_description": job_desc,
            "candidate_analysis": candidate_analysis,
            "job_analysis": job_analysis,
            "questions": questions,
            "created_at": __import__("datetime").datetime.utcnow().isoformat(),
        }
        _interview_sessions[session_id] = session

        return session

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interview/evaluate-answer")
async def evaluate_answer(request: dict):
    """
    Phase 4: Evaluate a single interview answer in real-time.
    Expects: { session_id, question_id, question, answer, section }
    """
    try:
        session_id = request.get("session_id", "")
        question = {
            "question_id": request.get("question_id", "?"),
            "question": request.get("question", ""),
            "section_name": request.get("section_name", ""),
            "category": request.get("category", ""),
            "difficulty": request.get("difficulty", "medium"),
        }
        answer = request.get("answer", "")
        section = request.get("section", "B")
        session = _interview_sessions.get(session_id, {})
        candidate_name = session.get("candidate_name", "Candidate")

        result = await evaluate_interview_answer(question, answer, section, candidate_name)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interview/submit-all")
async def submit_all_answers(request: dict):
    """
    Phase 4 (batch): Evaluate all answers at once.
    Expects: { session_id, answers: { "A1": "...", "B2": "..." } }
    """
    try:
        session_id = request.get("session_id", "")
        answers_map = request.get("answers", {})

        session = _interview_sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Interview session not found.")

        questions = session.get("questions", [])
        candidate_name = session.get("candidate_name", "Candidate")

        evaluations = await evaluate_all_answers(questions, answers_map, candidate_name)

        # Store evaluations in session
        _interview_sessions[session_id]["evaluations"] = evaluations

        return {"session_id": session_id, "evaluations": evaluations, "total_questions": len(questions)}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/interview/final-report")
async def generate_report(request: dict):
    """
    Phase 5: Generate the final professional HR report.
    Expects: { session_id, evaluations? } — evaluations optional if submit-all was called.
    """
    try:
        session_id = request.get("session_id", "")
        session = _interview_sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Interview session not found.")

        evaluations = request.get("evaluations") or session.get("evaluations", [])
        if not evaluations:
            raise HTTPException(status_code=400, detail="No evaluations found. Submit answers first.")

        report = await generate_final_interview_report(
            session_id=session_id,
            candidate_name=session.get("candidate_name", "Candidate"),
            candidate_email=session.get("candidate_email", ""),
            candidate_analysis=session.get("candidate_analysis", {}),
            job_analysis=session.get("job_analysis", {}),
            evaluations=evaluations,
        )

        _interview_sessions[session_id]["final_report"] = report
        return report

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/interview/session/{session_id}")
async def get_session(session_id: str):
    session = _interview_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session


import asyncio

