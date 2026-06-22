from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# ─── Job Models ─────────────────────────────────────────────────────────────

class JobRequirements(BaseModel):
    title: str
    description: str
    required_skills: List[str] = []
    years_experience_min: Optional[int] = 0
    years_experience_preferred: Optional[int] = 0
    seniority_level: Optional[str] = "mid"
    domain: Optional[str] = None

class JobParseRequest(BaseModel):
    job_description: str

class JobParseResponse(BaseModel):
    role_title: str
    core_competencies: List[str]
    critical_requirements: List[str]
    years_experience: Dict[str, int]
    domain: str
    seniority_level: str
    tech_stack: List[str]

# ─── Resume Models ───────────────────────────────────────────────────────────

class ExtractedProject(BaseModel):
    name: str
    description: str
    tech_stack: List[str]

class ExtractedExperience(BaseModel):
    company: str
    role: str
    duration_months: int
    highlights: List[str]

class CandidateProfile(BaseModel):
    name: str
    email: Optional[str] = ""
    resume_text: Optional[str] = ""
    skills: List[str] = []
    years_experience: Optional[int] = 0
    github_commits_30d: Optional[int] = 0
    learning_engagement: Optional[float] = 0.0

class ExtractedCandidateProfile(BaseModel):
    name: str
    email: str
    core_skills: List[str]
    years_experience: int
    projects: List[ExtractedProject]
    experience_history: List[ExtractedExperience]
    education: str
    raw_text: str

# ─── Assessment Models ───────────────────────────────────────────────────────

class AssessmentQuestion(BaseModel):
    question_id: str
    type: str  # scenario_coding | architectural_tradeoff | debug_challenge
    prompt: str
    evaluation_criteria: str
    difficulty: str  # easy | medium | hard

class GeneratedAssessment(BaseModel):
    assessment_id: str
    application_id: str
    candidate_name: str
    role: str
    generated_at: str
    questions: List[AssessmentQuestion]

class QuestionAnswer(BaseModel):
    question_id: str
    answer: str

class AssessmentSubmission(BaseModel):
    assessment_id: str
    application_id: str
    answers: List[QuestionAnswer]

class ScoredAnswer(BaseModel):
    question_id: str
    score: float  # 0-10
    max_score: float
    feedback: str
    demonstrated_skills: List[str]

class AssessmentResult(BaseModel):
    assessment_id: str
    application_id: str
    candidate_name: str
    total_score: float
    max_total: float
    percentage: float
    scored_answers: List[ScoredAnswer]
    summary: str

# ─── Ranking Models ──────────────────────────────────────────────────────────

class RoleCapabilityMap(BaseModel):
    skill: str
    level: str  # Expert | Advanced | Intermediate | Beginner
    verified_by: str  # Resume | Assessment | Both

class RankingRequest(BaseModel):
    job: JobRequirements
    candidates: List[CandidateProfile]

class TalentRankCandidate(BaseModel):
    rank: int
    name: str
    email: str
    composite_score: float
    resume_semantic_match: float
    ai_test_score: float
    career_velocity: float
    role_capability_map: List[RoleCapabilityMap]
    recommendation: str  # STRONG HIRE | CONSIDER | PASS
    system_recommendation: str

class RecruiterDashboard(BaseModel):
    job_id: str
    role_title: str
    evaluated_candidates_count: int
    processing_time_ms: int
    ranked_shortlist: List[TalentRankCandidate]

class RankedCandidate(BaseModel):
    name: str
    overall_score: float
    semantic_match: float
    career_trajectory: float
    behavioral_signals: float
    cultural_fit: float
    recommendation: str
    reasoning: str

class RankingResponse(BaseModel):
    ranked_candidates: List[RankedCandidate]
    processing_time_ms: int

# ─── Application Flow ────────────────────────────────────────────────────────

class ApplicationRequest(BaseModel):
    application_id: str
    candidate_info: ExtractedCandidateProfile
    job_profile: JobParseResponse

class GenerateAssessmentRequest(BaseModel):
    application_id: str
    candidate_name: str
    candidate_email: str
    core_skills: List[str]
    projects: List[ExtractedProject]
    job_id: str
    role: str
    critical_requirements: List[str]

# ─── AI Interview System ──────────────────────────────────────────────────────

class InterviewStartRequest(BaseModel):
    resume_text: str
    job_description: str
    candidate_name: Optional[str] = "Candidate"
    candidate_email: Optional[str] = ""

class CandidateAnalysis(BaseModel):
    candidate_name: str
    education: List[str]
    skills: List[str]
    projects: List[str]
    certifications: List[str]
    experience: List[str]
    technical_strengths: List[str]
    weak_areas: List[str]
    profile_summary: str

class JobAnalysis(BaseModel):
    required_skills: List[str]
    preferred_skills: List[str]
    experience_requirements: str
    responsibilities: List[str]
    important_technologies: List[str]
    match_percentage: float
    skill_gap: List[str]
    strength_analysis: str

class InterviewQuestion(BaseModel):
    question_id: str
    section: str        # A | B | C | D
    section_name: str
    category: Optional[str] = ""
    difficulty: Optional[str] = "medium"
    question: str

class InterviewSession(BaseModel):
    session_id: str
    candidate_name: str
    candidate_email: str
    resume_text: str
    job_description: str
    candidate_analysis: CandidateAnalysis
    job_analysis: JobAnalysis
    questions: List[InterviewQuestion]
    created_at: str

class AnswerEvaluationRequest(BaseModel):
    session_id: str
    question_id: str
    question: str
    answer: str
    section: str

class AnswerEvaluation(BaseModel):
    question_id: str
    question: str
    answer: str
    technical_accuracy: float
    communication: float
    problem_solving: float
    confidence: float
    strengths: List[str]
    weaknesses: List[str]
    suggested_improvement: str
    overall_question_score: float

class FinalReportRequest(BaseModel):
    session_id: str
    evaluations: List[AnswerEvaluation]

class FinalInterviewReport(BaseModel):
    session_id: str
    candidate_name: str
    candidate_email: str
    candidate_summary: str
    skill_assessment: Dict[str, str]
    technical_score: float
    communication_score: float
    problem_solving_score: float
    overall_score: float
    job_match_percentage: float
    key_strengths: List[str]
    areas_of_improvement: List[str]
    final_recommendation: str   # HIRE | MAYBE HIRE | REJECT
    recommendation_reasoning: str
    section_scores: Dict[str, float]
    generated_at: str
