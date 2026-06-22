import os
import json
import uuid
import asyncio
from datetime import datetime, timezone
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# ─── Client Setup with Multi-Key Fallback ────────────────────────────────────

# Priority-ordered list of (api_key, base_url, model) to try
API_CONFIGS = [
    {
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1"),
        "model": os.getenv("LLM_MODEL", "deepseek-chat"),
    },
    {
        "api_key": os.getenv("DEEPSEEK_API_KEY_1", ""),
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    },
    {
        "api_key": os.getenv("GEMINI_API_KEY_1", ""),
        "base_url": "https://openrouter.ai/api/v1",
        "model": "google/gemini-2.5-flash",
    }
]

def _clean_json(content: str) -> str:
    """Strip markdown code fences from LLM output."""
    content = content.strip()
    for prefix in ("```json", "```"):
        if content.startswith(prefix):
            content = content[len(prefix):]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()

async def _chat(prompt: str, system: str = "You are an expert AI assistant. Return ONLY valid JSON, no markdown, no backticks.") -> dict:
    """
    Try each API config in order until one succeeds.
    Returns a dict. On total failure, returns {"_error": "...", "_raw": "..."}.
    """
    last_error = None
    for cfg in API_CONFIGS:
        key = cfg.get("api_key", "").strip()
        if not key or key == "sk-ant-xxxxxxxxxxxxxxxxxxxxx":
            continue
        try:
            client = AsyncOpenAI(api_key=key, base_url=cfg["base_url"])
            response = await client.chat.completions.create(
                model=cfg["model"],
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                timeout=30,
            )
            raw = response.choices[0].message.content or ""
            cleaned = _clean_json(raw)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                # LLM returned text but not JSON — wrap it
                return {"_raw_text": raw}
        except Exception as e:
            last_error = str(e)
            # Suppress individual connection error prints to prevent terminal spam during permutation checking
            continue

    return {"_error": last_error or "All API configs failed"}

# ─── Module 1: Resume Text Extraction (NO LLM needed) ────────────────────────

def extract_text_from_pdf(content: bytes) -> str:
    import fitz  # PyMuPDF
    doc = fitz.open(stream=content, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text

def extract_text_from_docx(content: bytes) -> str:
    import io
    from docx import Document
    doc = Document(io.BytesIO(content))
    return "\n".join(para.text for para in doc.paragraphs)

# ─── Module 2: LLM Resume Profile Extraction ─────────────────────────────────

async def extract_resume_profile(raw_text: str) -> dict:
    """
    Extract a structured candidate profile from raw resume text using LLM.
    Falls back to basic heuristic extraction if LLM fails.
    """
    prompt = f"""Extract a structured candidate profile from this resume text.
Return ONLY a valid JSON object (no markdown, no backticks) with these exact keys:
{{
  "name": "Full Name",
  "email": "email@domain.com",
  "core_skills": ["skill1", "skill2"],
  "years_experience": 5,
  "projects": [
    {{"name": "Project Name", "description": "What it does", "tech_stack": ["Python"]}}
  ],
  "experience_history": [
    {{"company": "Company", "role": "Role Title", "duration_months": 18, "highlights": ["achievement1"]}}
  ],
  "education": "B.Tech Computer Science, IIT Delhi (2019)"
}}

Resume Text:
{raw_text[:5000]}"""

    result = await _chat(prompt)

    # If LLM failed or returned error, do basic heuristic fallback
    if "_error" in result or "_raw_text" in result:
        result = _heuristic_profile(raw_text)

    result["raw_text"] = raw_text
    return result

def _heuristic_profile(text: str) -> dict:
    """Basic heuristic extraction when LLM is unavailable."""
    import re
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # Extract email
    email_match = re.search(r'[\w.-]+@[\w.-]+\.\w+', text)
    email = email_match.group(0) if email_match else ""

    # First non-empty line is likely the name
    name = lines[0] if lines else "Unknown Candidate"

    # Common tech skills to scan for
    common_skills = [
        "Python","JavaScript","TypeScript","React","Node.js","FastAPI","Django","Flask",
        "Java","C++","C#","Go","Rust","Ruby","PHP","SQL","PostgreSQL","MySQL","MongoDB",
        "Redis","Docker","Kubernetes","AWS","GCP","Azure","Git","Linux","REST","GraphQL",
        "Machine Learning","Deep Learning","TensorFlow","PyTorch","Pandas","NumPy"
    ]
    found_skills = [s for s in common_skills if s.lower() in text.lower()]

    # Rough year count
    year_matches = re.findall(r'(\d{4})\s*[-–]\s*(\d{4}|present|current)', text, re.IGNORECASE)
    years_exp = 0
    for start, end in year_matches:
        end_yr = 2026 if end.lower() in ('present', 'current') else int(end)
        years_exp = max(years_exp, end_yr - int(start))

    return {
        "name": name,
        "email": email,
        "core_skills": found_skills[:10],
        "years_experience": years_exp or 2,
        "projects": [
            {"name": "Project (auto-detected)", "description": "See resume for details", "tech_stack": found_skills[:3]}
        ],
        "experience_history": [],
        "education": "See resume"
    }

# ─── Module 3: Job Description Parsing ───────────────────────────────────────

async def parse_job_description(job_desc: str) -> dict:
    prompt = f"""You are an expert HR intelligence system. Analyze this job description and extract structured information.
Return ONLY a valid JSON object (no markdown, no backticks):
{{
  "role_title": "Senior Backend Engineer",
  "core_competencies": ["Competency 1", "Competency 2"],
  "critical_requirements": ["Must-have 1", "Must-have 2"],
  "years_experience": {{"min": 3, "preferred": 5}},
  "domain": "FinTech",
  "seniority_level": "senior",
  "tech_stack": ["Python", "FastAPI", "PostgreSQL"]
}}

Job Description:
{job_desc}"""

    result = await _chat(prompt)

    if "_error" in result or "_raw_text" in result:
        # Fallback: return a basic parsed structure
        words = job_desc.split()
        return {
            "role_title": "Software Engineer",
            "core_competencies": ["Software Development", "Problem Solving"],
            "critical_requirements": ["Experience with relevant technologies"],
            "years_experience": {"min": 2, "preferred": 5},
            "domain": "Technology",
            "seniority_level": "mid",
            "tech_stack": []
        }

    return result

# ─── Module 4: Assessment Generation ─────────────────────────────────────────

async def generate_assessment(
    candidate_name: str,
    core_skills: list,
    projects: list,
    role: str,
    critical_requirements: list
) -> dict:
    projects_str = json.dumps(projects[:3], indent=2)
    skills_str = ", ".join(core_skills[:8])
    reqs_str = ", ".join(critical_requirements[:5])

    prompt = f"""You are an elite technical interviewer. Generate 5 unique, scenario-based technical assessment questions.

Candidate: {candidate_name}
Their Skills: {skills_str}
Their Projects: {projects_str}
Role: {role}
Critical Requirements: {reqs_str}

Requirements for questions:
1. Reference the candidate's ACTUAL projects and skills specifically
2. Focus on architectural decisions, tradeoffs, and debugging — NOT syntax recall
3. Make them hard to Google directly
4. Cover critical requirements of the role

Return ONLY a JSON object (no markdown, no backticks):
{{
  "questions": [
    {{
      "question_id": "q_01",
      "type": "scenario_coding",
      "prompt": "Specific question referencing their actual project...",
      "evaluation_criteria": "What a perfect answer looks like...",
      "difficulty": "hard"
    }}
  ]
}}

Types: scenario_coding, architectural_tradeoff, debug_challenge, system_design, concept_depth"""

    result = await _chat(prompt, system="You are an elite technical interviewer. Return ONLY valid JSON.")

    questions = result.get("questions", [])

    # Fallback: generate generic questions if LLM failed
    if not questions or "_error" in result:
        questions = _fallback_questions(role, core_skills, critical_requirements)

    assessment_id = f"test_{uuid.uuid4().hex[:8]}"
    application_id = f"app_{uuid.uuid4().hex[:8]}"

    return {
        "assessment_id": assessment_id,
        "application_id": application_id,
        "candidate_name": candidate_name,
        "role": role,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "questions": questions
    }

def _fallback_questions(role: str, skills: list, requirements: list) -> list:
    """Generate reasonable fallback questions when LLM is unavailable."""
    skill_str = skills[0] if skills else "your primary technology"
    req_str = requirements[0] if requirements else "system performance"
    return [
        {
            "question_id": "q_01",
            "type": "scenario_coding",
            "prompt": f"You are building a high-traffic API using {skill_str}. The system starts experiencing timeouts under 10,000 concurrent requests. Walk through your debugging process and the architectural changes you would make.",
            "evaluation_criteria": "Understanding of concurrency, connection pooling, async patterns, and systematic debugging.",
            "difficulty": "hard"
        },
        {
            "question_id": "q_02",
            "type": "architectural_tradeoff",
            "prompt": f"For a system requiring {req_str}, compare using a SQL database vs. a NoSQL database. What factors would drive your decision and what are the key tradeoffs?",
            "evaluation_criteria": "Understanding of CAP theorem, data consistency, query patterns, scalability tradeoffs.",
            "difficulty": "medium"
        },
        {
            "question_id": "q_03",
            "type": "system_design",
            "prompt": f"Design a {role}-level system that can handle 1 million events per day with sub-100ms response time. Describe your architecture, the key components, and how you ensure reliability.",
            "evaluation_criteria": "Load balancing, caching strategy, database choice, monitoring and alerting.",
            "difficulty": "hard"
        },
        {
            "question_id": "q_04",
            "type": "debug_challenge",
            "prompt": "A production service was working fine but suddenly memory usage climbs 10% every hour. After 12 hours it crashes. You have access to logs, metrics, and a profiler. Walk through your exact investigation process.",
            "evaluation_criteria": "Systematic debugging methodology, understanding of memory leaks, use of profiling tools.",
            "difficulty": "medium"
        },
        {
            "question_id": "q_05",
            "type": "concept_depth",
            "prompt": f"Explain how you would implement a rate limiter for a public API using {skill_str}. What algorithm would you use, and how would it behave under distributed deployment across 5 servers?",
            "evaluation_criteria": "Token bucket vs sliding window algorithms, distributed state management, Redis usage.",
            "difficulty": "medium"
        }
    ]

# ─── Module 5: Assessment Scoring ────────────────────────────────────────────

async def score_single_answer(question: dict, answer: str, role: str) -> dict:
    if not answer or not answer.strip():
        return {
            "question_id": question.get("question_id", "q_??"),
            "score": 0.0,
            "max_score": 10.0,
            "feedback": "No answer was provided.",
            "demonstrated_skills": []
        }

    prompt = f"""Score this technical assessment answer strictly and objectively.

Role: {role}
Question Type: {question.get("type")}
Question: {question.get("prompt")}
Evaluation Criteria: {question.get("evaluation_criteria")}
Difficulty: {question.get("difficulty", "medium")}

Candidate Answer: {answer[:2000]}

Return ONLY a JSON object (no markdown, no backticks):
{{
  "score": 7.5,
  "max_score": 10.0,
  "feedback": "Concise expert feedback on what was good and what was missing...",
  "demonstrated_skills": ["skill1", "skill2"]
}}

Scoring: 9-10=Expert, 7-8=Advanced, 5-6=Intermediate, 3-4=Basic, 0-2=Poor/No answer."""

    result = await _chat(prompt, system="You are a strict technical evaluator. Return ONLY valid JSON.")

    if "_error" in result or "_raw_text" in result:
        # Heuristic scoring fallback
        word_count = len(answer.split())
        score = min(max(word_count / 30, 1.0), 7.0)
        result = {
            "score": round(score, 1),
            "max_score": 10.0,
            "feedback": "Answer received. AI scoring temporarily unavailable — scored by answer depth heuristic.",
            "demonstrated_skills": []
        }

    result["question_id"] = question.get("question_id", "q_??")
    return result

async def score_full_assessment(questions: list, answers: list, role: str, candidate_name: str) -> dict:
    answer_map = {a["question_id"]: a["answer"] for a in answers}
    tasks = [score_single_answer(q, answer_map.get(q["question_id"], ""), role) for q in questions]
    scored = list(await asyncio.gather(*tasks))

    total = sum(float(s.get("score", 0)) for s in scored)
    max_total = sum(float(s.get("max_score", 10)) for s in scored)
    percentage = round((total / max_total) * 100, 1) if max_total > 0 else 0.0

    summary_prompt = f"""Write a 2-sentence recruiter summary for this candidate's assessment.
Candidate: {candidate_name}, Role: {role}, Score: {percentage}%
Feedback highlights: {'; '.join(s.get('feedback','')[:100] for s in scored[:3])}

Return ONLY JSON: {{"summary": "Two sentence summary..."}}"""

    summary_result = await _chat(summary_prompt)
    summary = summary_result.get("summary", f"{candidate_name} scored {percentage}% on the technical assessment.")

    return {
        "candidate_name": candidate_name,
        "total_score": round(total, 2),
        "max_total": round(max_total, 2),
        "percentage": percentage,
        "scored_answers": scored,
        "summary": summary
    }

# ─── Module 6: Composite Candidate Evaluation ────────────────────────────────

async def evaluate_candidate_full(candidate_profile: dict, job_profile: dict, assessment_percentage: float = 0.0) -> dict:
    profile_str = json.dumps({
        "name": candidate_profile.get("name"),
        "skills": candidate_profile.get("core_skills", candidate_profile.get("skills", [])),
        "years_experience": candidate_profile.get("years_experience", 0),
        "projects": candidate_profile.get("projects", [])[:3],
    }, indent=2)

    job_str = json.dumps({
        "role": job_profile.get("role_title", job_profile.get("title", "Unknown Role")),
        "requirements": job_profile.get("critical_requirements", job_profile.get("required_skills", []))[:5],
        "tech_stack": job_profile.get("tech_stack", [])[:8],
        "seniority": job_profile.get("seniority_level", "mid")
    }, indent=2)

    prompt = f"""You are an elite AI Recruiter. Generate a full talent evaluation.

Job Profile:
{job_str}

Candidate Profile:
{profile_str}

Assessment Score: {assessment_percentage}% (pre-computed, do NOT change this)

Return ONLY a JSON object (no markdown, no backticks):
{{
  "resume_semantic_match": 85.5,
  "career_velocity": 78.0,
  "role_capability_map": [
    {{"skill": "Database Optimization", "level": "Expert", "verified_by": "Resume"}},
    {{"skill": "Async Programming", "level": "Advanced", "verified_by": "Both"}}
  ],
  "system_recommendation": "One paragraph explaining hire decision with specific evidence from their background..."
}}

resume_semantic_match (0-100): How well background/skills semantically align with role requirements
career_velocity (0-100): Career progression speed and growth trajectory
role_capability_map: List 4-6 key skills for this role. Levels: Expert/Advanced/Intermediate/Beginner. verified_by: Resume/Assessment/Both"""

    result = await _chat(prompt, system="You are an elite AI Recruiter. Return ONLY valid JSON.")

    if "_error" in result or "_raw_text" in result:
        # Heuristic fallback scoring
        candidate_skills = set(s.lower() for s in candidate_profile.get("core_skills", candidate_profile.get("skills", [])))
        job_skills = set(s.lower() for s in job_profile.get("tech_stack", []) + job_profile.get("critical_requirements", []))
        if job_skills:
            overlap = len(candidate_skills & job_skills) / len(job_skills)
            sem_fit = min(overlap * 100 + 20, 95)
        else:
            sem_fit = 60.0
        years = candidate_profile.get("years_experience", 0)
        velocity = min(50 + years * 5, 90)

        result = {
            "resume_semantic_match": round(sem_fit, 1),
            "career_velocity": round(velocity, 1),
            "role_capability_map": [
                {"skill": s.title(), "level": "Intermediate", "verified_by": "Resume"}
                for s in list(candidate_skills & job_skills)[:4]
            ],
            "system_recommendation": f"Candidate has {years} years of experience with relevant skills. Assessment score: {assessment_percentage}%. Full AI analysis temporarily unavailable."
        }

    sem_fit = float(result.get("resume_semantic_match", 50.0))
    career_vel = float(result.get("career_velocity", 50.0))
    test_score = float(assessment_percentage)

    # TalentRank Formula: 40% Resume + 45% Assessment + 15% Career Velocity
    composite = (0.40 * sem_fit) + (0.45 * test_score) + (0.15 * career_vel)

    result["composite_score"] = round(composite, 1)
    result["ai_test_score"] = round(test_score, 1)
    result["name"] = candidate_profile.get("name", "Unknown")
    result["email"] = candidate_profile.get("email", "")

    return result

# ─── Legacy async wrapper ─────────────────────────────────────────────────────

async def evaluate_candidate_async(job_reqs_json: str, candidate_json: str) -> dict:
    """Legacy wrapper used by old ranker."""
    try:
        job = json.loads(job_reqs_json)
        cand = json.loads(candidate_json)
        result = await evaluate_candidate_full(cand, job, 0.0)
        sem = result.get("resume_semantic_match", 50.0) / 10.0
        vel = result.get("career_velocity", 50.0) / 10.0
        return {
            "semantic_match": round(min(sem, 10.0), 2),
            "career_trajectory": round(min(vel, 10.0), 2),
            "behavioral_signals": round(min(vel * 0.9, 10.0), 2),
            "cultural_fit": round(min(sem * 0.85, 10.0), 2),
            "reasoning": result.get("system_recommendation", "Evaluation complete.")[:200]
        }
    except Exception as e:
        return {
            "semantic_match": 5.0, "career_trajectory": 5.0,
            "behavioral_signals": 5.0, "cultural_fit": 5.0,
            "reasoning": f"Evaluation error: {e}"
        }


# =============================================================================
#  AI INTERVIEW ENGINE — 5 PHASES
# =============================================================================

# ─── Phase 1: Resume Analysis ─────────────────────────────────────────────────

async def analyze_resume(resume_text: str) -> dict:
    """Extract structured candidate info from resume text."""
    prompt = f"""You are an expert HR Analyst. Analyze this resume and extract structured information.
Return ONLY a JSON object (no markdown, no backticks):
{{
  "candidate_name": "Full Name",
  "education": ["B.Tech Computer Science, IIT Delhi (2019)", "Coursera ML Certificate"],
  "skills": ["Python", "Machine Learning", "SQL", "Docker"],
  "projects": ["E-commerce Recommendation Engine using collaborative filtering", "Real-time fraud detection pipeline"],
  "certifications": ["AWS Solutions Architect", "Google Data Analytics"],
  "experience": ["2 years at Infosys as Data Engineer", "6 months internship at Flipkart"],
  "technical_strengths": ["Strong Python & ML fundamentals", "Good grasp of SQL optimization"],
  "weak_areas": ["Limited cloud deployment experience", "No production ML system ownership"],
  "profile_summary": "A 2-sentence professional summary of this candidate."
}}

Resume Text:
{resume_text[:6000]}"""

    result = await _chat(prompt, system="You are an expert HR Analyst. Return ONLY valid JSON.")

    if "_error" in result or "_raw_text" in result:
        # Heuristic fallback
        import re
        lines = [l.strip() for l in resume_text.split('\n') if l.strip()]
        email_match = re.search(r'[\w.-]+@[\w.-]+\.\w+', resume_text)
        common_skills = ["Python","JavaScript","SQL","Machine Learning","React","Node.js",
                         "Docker","Kubernetes","AWS","GCP","Azure","TensorFlow","PyTorch",
                         "FastAPI","Django","PostgreSQL","MongoDB","Redis","Java","C++","Go"]
        found = [s for s in common_skills if s.lower() in resume_text.lower()]
        result = {
            "candidate_name": lines[0] if lines else "Unknown",
            "education": [l for l in lines if any(w in l.lower() for w in ["b.tech","m.tech","bsc","msc","bachelor","master","phd","degree","university","college","coursera","udemy"])][:3],
            "skills": found[:10],
            "projects": [l for l in lines if any(w in l.lower() for w in ["project","built","developed","created","implemented"])][:4],
            "certifications": [l for l in lines if any(w in l.lower() for w in ["certified","certification","certificate","aws","google","microsoft","oracle"])][:3],
            "experience": [l for l in lines if any(w in l.lower() for w in ["engineer","analyst","developer","intern","manager","lead","years"])][:4],
            "technical_strengths": [f"Proficient in {s}" for s in found[:3]],
            "weak_areas": ["Details need manual review"],
            "profile_summary": f"Candidate with skills in {', '.join(found[:4])}. Profile extracted from resume."
        }

    return result


# ─── Phase 2: JD Analysis + Match ────────────────────────────────────────────

async def analyze_job_description(job_desc: str, candidate_analysis: dict) -> dict:
    """Analyze JD and compute match against candidate profile."""
    candidate_skills = candidate_analysis.get("skills", [])

    prompt = f"""You are an expert HR Intelligence System. Analyze this job description and compute candidate match.

Candidate Skills: {json.dumps(candidate_skills)}

Job Description:
{job_desc[:4000]}

Return ONLY a JSON object (no markdown, no backticks):
{{
  "required_skills": ["Python", "SQL", "Machine Learning"],
  "preferred_skills": ["Kubernetes", "Spark"],
  "experience_requirements": "3-5 years in data engineering or ML",
  "responsibilities": ["Build ML pipelines", "Optimize SQL queries", "Deploy models to production"],
  "important_technologies": ["Python", "TensorFlow", "PostgreSQL", "Docker"],
  "match_percentage": 73.5,
  "skill_gap": ["No Kubernetes experience", "Missing Spark knowledge"],
  "strength_analysis": "Strong Python and ML background aligns well with core requirements. SQL skills cover 80% of data requirements."
}}

match_percentage: Honest 0-100 score based on skill overlap, experience fit, and domain match."""

    result = await _chat(prompt, system="You are an expert HR Intelligence System. Return ONLY valid JSON.")

    if "_error" in result or "_raw_text" in result:
        # Heuristic fallback
        common_tech = ["python","sql","machine learning","data science","javascript","react",
                       "node","docker","kubernetes","aws","tensorflow","pytorch"]
        jd_lower = job_desc.lower()
        required = [t for t in common_tech if t in jd_lower]
        cand_lower = [s.lower() for s in candidate_skills]
        overlap = [r for r in required if r in cand_lower]
        match_pct = (len(overlap) / len(required) * 100) if required else 50.0
        gaps = [r for r in required if r not in cand_lower]

        result = {
            "required_skills": [t.title() for t in required],
            "preferred_skills": [],
            "experience_requirements": "See job description",
            "responsibilities": ["Role responsibilities extracted from JD"],
            "important_technologies": [t.title() for t in required[:5]],
            "match_percentage": round(min(match_pct, 95.0), 1),
            "skill_gap": [f"Missing: {g.title()}" for g in gaps[:4]],
            "strength_analysis": f"Candidate matches {len(overlap)}/{len(required)} detected required skills."
        }

    return result


# ─── Phase 3: Interview Question Generation ───────────────────────────────────

async def generate_interview_questions(
    candidate_analysis: dict,
    job_analysis: dict,
    resume_text: str
) -> list:
    """Generate 15-20 interview questions across 4 sections (A, B, C, D)."""

    name = candidate_analysis.get("candidate_name", "Candidate")
    skills = candidate_analysis.get("skills", [])
    projects = candidate_analysis.get("projects", [])
    certs = candidate_analysis.get("certifications", [])
    required_skills = job_analysis.get("required_skills", [])
    tech_stack = job_analysis.get("important_technologies", [])

    prompt = f"""You are an expert technical interviewer. Generate a comprehensive, realistic interview question set.

Candidate: {name}
Skills: {json.dumps(skills[:8])}
Projects: {json.dumps(projects[:3])}
Certifications: {json.dumps(certs[:3])}
Job Required Skills: {json.dumps(required_skills[:8])}
Key Technologies: {json.dumps(tech_stack[:6])}

Generate questions across 4 sections. Return ONLY a JSON array (no markdown, no backticks):
[
  {{
    "question_id": "A1",
    "section": "A",
    "section_name": "Resume-Based Questions",
    "category": "Project Deep-Dive",
    "difficulty": "medium",
    "question": "In your [specific project from resume], you mentioned using [technology]. What was the most complex challenge you faced and how did you resolve it?"
  }},
  {{
    "question_id": "B1",
    "section": "B",
    "section_name": "Technical Questions",
    "category": "Python - Intermediate",
    "difficulty": "medium",
    "question": "Explain the difference between a generator and an iterator in Python. When would you use one over the other?"
  }},
  {{
    "question_id": "C1",
    "section": "C",
    "section_name": "Scenario-Based Questions",
    "category": "System Design",
    "difficulty": "hard",
    "question": "You are given a slow-running SQL query on a table with 50 million rows. Walk me through your optimization process step by step."
  }},
  {{
    "question_id": "D1",
    "section": "D",
    "section_name": "Behavioral Questions",
    "category": "Leadership & Teamwork",
    "difficulty": "easy",
    "question": "Tell me about a time when you had a technical disagreement with a teammate. How did you handle it and what was the outcome?"
  }}
]

Rules:
- Section A (4-5 questions): Reference SPECIFIC projects, technologies, certifications from the resume
- Section B (5-6 questions): Mix of beginner/intermediate/advanced; cover Python, SQL, ML, Data Science, AI, Cloud, Cyber Security, or Web Dev — only what's relevant to candidate skills and job
- Section C (3-4 questions): Realistic workplace scenarios directly relevant to job role
- Section D (3 questions): Behavioral STAR-format questions
- Make questions SPECIFIC and PERSONALIZED to this candidate's profile, not generic"""

    result = await _chat(prompt, system="You are an expert technical interviewer. Return ONLY a valid JSON array.")

    # Handle both list and dict response
    if isinstance(result, list):
        questions = result
    elif isinstance(result, dict):
        questions = result.get("questions", [])
    else:
        questions = []

    if not questions or (isinstance(result, dict) and "_error" in result):
        questions = _fallback_interview_questions(name, skills, projects, required_skills)

    return questions


def _fallback_interview_questions(name: str, skills: list, projects: list, required: list) -> list:
    """Fallback interview questions when LLM unavailable."""
    skill = skills[0] if skills else "Python"
    proj = projects[0] if projects else "your main project"
    req = required[0] if required else "system performance"

    return [
        # Section A
        {"question_id": "A1", "section": "A", "section_name": "Resume-Based Questions",
         "category": "Project Deep-Dive", "difficulty": "medium",
         "question": f"You mentioned '{proj}'. What was the most significant technical challenge you encountered and how did you overcome it?"},
        {"question_id": "A2", "section": "A", "section_name": "Resume-Based Questions",
         "category": "Technology Choice", "difficulty": "medium",
         "question": f"Why did you choose {skill} for this project? What alternatives did you consider?"},
        {"question_id": "A3", "section": "A", "section_name": "Resume-Based Questions",
         "category": "Impact & Results", "difficulty": "easy",
         "question": "What was the measurable impact of your most significant project? How did you quantify success?"},
        {"question_id": "A4", "section": "A", "section_name": "Resume-Based Questions",
         "category": "Learning", "difficulty": "easy",
         "question": "What is the most important technical skill you have taught yourself outside of formal education?"},
        # Section B
        {"question_id": "B1", "section": "B", "section_name": "Technical Questions",
         "category": "Beginner", "difficulty": "easy",
         "question": f"Explain the concept of OOP with a real-world example relevant to {skill}."},
        {"question_id": "B2", "section": "B", "section_name": "Technical Questions",
         "category": "Intermediate", "difficulty": "medium",
         "question": "What is the difference between a LEFT JOIN and an INNER JOIN in SQL? Give a use case for each."},
        {"question_id": "B3", "section": "B", "section_name": "Technical Questions",
         "category": "Intermediate", "difficulty": "medium",
         "question": "Explain how a REST API works. What are the key HTTP methods and when do you use each?"},
        {"question_id": "B4", "section": "B", "section_name": "Technical Questions",
         "category": "Advanced", "difficulty": "hard",
         "question": "Explain the bias-variance tradeoff in machine learning. How do you detect and mitigate each in practice?"},
        {"question_id": "B5", "section": "B", "section_name": "Technical Questions",
         "category": "Advanced", "difficulty": "hard",
         "question": f"How would you design a system to handle {req} at scale? Describe your architecture choices."},
        # Section C
        {"question_id": "C1", "section": "C", "section_name": "Scenario-Based Questions",
         "category": "Database Optimization", "difficulty": "hard",
         "question": "A production query that ran in 200ms now takes 45 seconds after a data load. How do you diagnose and fix this?"},
        {"question_id": "C2", "section": "C", "section_name": "Scenario-Based Questions",
         "category": "Security", "difficulty": "medium",
         "question": "How would you secure a web application from the top 5 OWASP vulnerabilities? Walk me through each one."},
        {"question_id": "C3", "section": "C", "section_name": "Scenario-Based Questions",
         "category": "System Failure", "difficulty": "hard",
         "question": "Your machine learning model's accuracy drops from 94% to 71% in production. No code changed. What do you investigate first?"},
        # Section D
        {"question_id": "D1", "section": "D", "section_name": "Behavioral Questions",
         "category": "Conflict Resolution", "difficulty": "easy",
         "question": "Describe a situation where you disagreed with your team's technical decision. What did you do?"},
        {"question_id": "D2", "section": "D", "section_name": "Behavioral Questions",
         "category": "Deadline Management", "difficulty": "easy",
         "question": "Tell me about a time you were under extreme deadline pressure. How did you manage it?"},
        {"question_id": "D3", "section": "D", "section_name": "Behavioral Questions",
         "category": "Growth Mindset", "difficulty": "easy",
         "question": "What is the biggest technical mistake you have made, and what did you learn from it?"},
    ]


# ─── Phase 4: Answer Evaluation ──────────────────────────────────────────────

async def evaluate_interview_answer(
    question: dict,
    answer: str,
    section: str,
    candidate_name: str,
) -> dict:
    """Evaluate a single interview answer across 4 dimensions."""

    if not answer or not answer.strip():
        return {
            "question_id": question.get("question_id", "?"),
            "question": question.get("question", ""),
            "answer": "",
            "technical_accuracy": 0.0,
            "communication": 0.0,
            "problem_solving": 0.0,
            "confidence": 0.0,
            "strengths": [],
            "weaknesses": ["No answer provided"],
            "suggested_improvement": "Please attempt the question even if unsure — partial answers show reasoning ability.",
            "overall_question_score": 0.0
        }

    prompt = f"""You are a strict but fair technical interviewer evaluating an interview answer.

Section: {question.get("section_name", section)}
Category: {question.get("category", "")}
Difficulty: {question.get("difficulty", "medium")}
Question: {question.get("question", "")}

Candidate Answer: {answer[:2500]}

Evaluate on 4 dimensions (each 0-10):
- technical_accuracy: Is the answer factually correct and complete?
- communication: Is the answer clear, structured, and easy to follow?
- problem_solving: Does the answer show analytical thinking and approach?
- confidence: Does the answer sound decisive and backed by knowledge?

Return ONLY a JSON object (no markdown, no backticks):
{{
  "technical_accuracy": 7.5,
  "communication": 8.0,
  "problem_solving": 6.5,
  "confidence": 7.0,
  "strengths": ["Correctly identified the core issue", "Good use of specific examples"],
  "weaknesses": ["Did not mention edge cases", "Missing mention of monitoring strategy"],
  "suggested_improvement": "Specific, actionable advice on what would make this answer expert-level..."
}}

For Section D (behavioral), focus on: STAR format (Situation/Task/Action/Result), specificity, and self-awareness instead of technical accuracy."""

    result = await _chat(prompt, system="You are a strict technical interviewer. Return ONLY valid JSON.")

    if "_error" in result or "_raw_text" in result:
        word_count = len(answer.split())
        base = min(max(word_count / 25, 2.0), 7.5)
        result = {
            "technical_accuracy": round(base, 1),
            "communication": round(base + 0.5, 1),
            "problem_solving": round(base - 0.5, 1),
            "confidence": round(base, 1),
            "strengths": ["Answer provided"],
            "weaknesses": ["AI evaluation temporarily unavailable"],
            "suggested_improvement": "Review the topic area and practice with concrete examples."
        }

    ta = float(result.get("technical_accuracy", 5.0))
    comm = float(result.get("communication", 5.0))
    ps = float(result.get("problem_solving", 5.0))
    conf = float(result.get("confidence", 5.0))

    # Section-weighted overall score
    if section in ("A", "B"):
        overall = (ta * 0.45) + (ps * 0.30) + (comm * 0.15) + (conf * 0.10)
    elif section == "C":
        overall = (ps * 0.40) + (ta * 0.35) + (comm * 0.15) + (conf * 0.10)
    else:  # D - Behavioral
        overall = (comm * 0.40) + (conf * 0.30) + (ps * 0.20) + (ta * 0.10)

    return {
        "question_id": question.get("question_id", "?"),
        "question": question.get("question", ""),
        "answer": answer[:500] + ("..." if len(answer) > 500 else ""),
        "technical_accuracy": round(ta, 1),
        "communication": round(comm, 1),
        "problem_solving": round(ps, 1),
        "confidence": round(conf, 1),
        "strengths": result.get("strengths", []),
        "weaknesses": result.get("weaknesses", []),
        "suggested_improvement": result.get("suggested_improvement", ""),
        "overall_question_score": round(overall, 2)
    }


async def evaluate_all_answers(questions: list, answers: dict, candidate_name: str) -> list:
    """Evaluate all interview answers concurrently."""
    tasks = []
    for q in questions:
        qid = q.get("question_id", q.get("id", "?"))
        section = q.get("section", "B")
        answer = answers.get(qid, "")
        tasks.append(evaluate_interview_answer(q, answer, section, candidate_name))

    return list(await asyncio.gather(*tasks))


# ─── Phase 5: Final HR Report ─────────────────────────────────────────────────

async def generate_final_interview_report(
    session_id: str,
    candidate_name: str,
    candidate_email: str,
    candidate_analysis: dict,
    job_analysis: dict,
    evaluations: list,
) -> dict:
    """Generate the final professional HR report with HIRE/MAYBE HIRE/REJECT decision."""

    # Compute section scores
    section_buckets: dict = {"A": [], "B": [], "C": [], "D": []}
    for ev in evaluations:
        qid = ev.get("question_id", "")
        section = qid[0] if qid else "B"
        if section in section_buckets:
            section_buckets[section].append(ev.get("overall_question_score", 5.0))

    section_scores = {
        s: round(sum(v) / len(v) * 10, 1) if v else 0.0
        for s, v in section_buckets.items()
    }

    # Overall dimension averages
    technical_score = round(
        sum(e.get("technical_accuracy", 5.0) for e in evaluations) / max(len(evaluations), 1) * 10, 1)
    communication_score = round(
        sum(e.get("communication", 5.0) for e in evaluations) / max(len(evaluations), 1) * 10, 1)
    problem_solving_score = round(
        sum(e.get("problem_solving", 5.0) for e in evaluations) / max(len(evaluations), 1) * 10, 1)

    all_scores = [e.get("overall_question_score", 5.0) for e in evaluations]
    raw_overall = sum(all_scores) / max(len(all_scores), 1)
    overall_score = round(raw_overall * 10, 1)

    job_match = float(job_analysis.get("match_percentage", 50.0))

    # Final recommendation
    if overall_score >= 80:
        recommendation = "HIRE"
    elif overall_score >= 60:
        recommendation = "MAYBE HIRE"
    else:
        recommendation = "REJECT"

    # All strengths and weaknesses
    all_strengths = []
    all_weaknesses = []
    for ev in evaluations:
        all_strengths.extend(ev.get("strengths", []))
        all_weaknesses.extend(ev.get("weaknesses", []))

    # Deduplicate
    seen_s, seen_w = set(), set()
    unique_strengths = [s for s in all_strengths if s not in seen_s and not seen_s.add(s)][:6]
    unique_weaknesses = [w for w in all_weaknesses if w not in seen_w and not seen_w.add(w)][:5]

    # Ask LLM for narrative summary + reasoning
    eval_summary = json.dumps([{
        "q": e.get("question", "")[:80],
        "score": e.get("overall_question_score"),
        "strengths": e.get("strengths", [])[:2],
        "weaknesses": e.get("weaknesses", [])[:2]
    } for e in evaluations[:6]], indent=1)

    prompt = f"""You are a senior HR Director writing a professional interview evaluation report.

Candidate: {candidate_name}
Overall Score: {overall_score}/100
Technical Score: {technical_score}/100
Communication Score: {communication_score}/100
Problem Solving Score: {problem_solving_score}/100
Job Match: {job_match}%
Recommendation: {recommendation}

Key Evaluation Points:
{eval_summary}

Skill Gap: {json.dumps(job_analysis.get("skill_gap", [])[:4])}

Return ONLY a JSON object (no markdown, no backticks):
{{
  "candidate_summary": "3-4 sentence professional summary of the candidate's profile and interview performance...",
  "skill_assessment": {{
    "Python": "Advanced",
    "SQL": "Intermediate",
    "Machine Learning": "Beginner"
  }},
  "recommendation_reasoning": "3-4 sentence professional justification for the HIRE/MAYBE HIRE/REJECT decision with specific evidence from the interview..."
}}"""

    narrative = await _chat(prompt, system="You are a senior HR Director. Return ONLY valid JSON.")

    if "_error" in narrative or "_raw_text" in narrative:
        narrative = {
            "candidate_summary": f"{candidate_name} completed the interview with an overall score of {overall_score}/100. Technical skills showed {'strong' if technical_score >= 70 else 'moderate'} performance.",
            "skill_assessment": {s: "Assessed" for s in candidate_analysis.get("skills", [])[:5]},
            "recommendation_reasoning": f"Based on interview performance (score: {overall_score}/100) and job match ({job_match}%), the recommendation is {recommendation}."
        }

    return {
        "session_id": session_id,
        "candidate_name": candidate_name,
        "candidate_email": candidate_email,
        "candidate_summary": narrative.get("candidate_summary", ""),
        "skill_assessment": narrative.get("skill_assessment", {}),
        "technical_score": technical_score,
        "communication_score": communication_score,
        "problem_solving_score": problem_solving_score,
        "overall_score": overall_score,
        "job_match_percentage": job_match,
        "key_strengths": unique_strengths,
        "areas_of_improvement": unique_weaknesses,
        "final_recommendation": recommendation,
        "recommendation_reasoning": narrative.get("recommendation_reasoning", ""),
        "section_scores": section_scores,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

