"""AI router for candidate analysis and job matching endpoints."""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.backend_client import BackendClientError, backend_client
from app.services.candidate_analyzer import candidate_analyzer
from app.services.job_matcher import match_candidate_to_jobs

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Request/Response schemas ---


class CandidateResume(BaseModel):
    """Candidate resume data included in the analysis request."""

    candidate_id: str = Field(..., description="Unique identifier of the candidate")
    full_name: str | None = Field(None, description="Candidate full name")
    location: str | None = Field(None, description="Candidate location")
    experiences: list[dict] = Field(default_factory=list, description="Professional experiences")
    educations: list[dict] = Field(default_factory=list, description="Education entries")
    skills: list[dict] = Field(default_factory=list, description="Technical skills")
    certifications: list[dict] = Field(default_factory=list, description="Certifications")
    languages: list[dict] = Field(default_factory=list, description="Languages")


class CandidateAnalysisRequest(BaseModel):
    """Request body for candidate analysis.

    Accepts either:
    - job_id + candidate_ids: fetches data from backend
    - job_requirements + candidates: uses provided data directly
    """

    job_id: str | None = Field(None, description="Job ID to fetch requirements from backend")
    candidate_ids: list[str] | None = Field(
        None, description="Candidate IDs to fetch from backend (max 200)"
    )
    job_requirements: dict | None = Field(
        None, description="Job requirements provided directly"
    )
    candidates: list[CandidateResume] | None = Field(
        None, description="Candidate data provided directly (max 200)"
    )


class CandidateScore(BaseModel):
    """Individual candidate score result."""

    candidate_id: str = Field(..., description="Unique identifier of the candidate")
    score: int = Field(..., ge=0, le=100, description="Score de Aderência (0-100)")
    strengths: list[str] = Field(
        ..., description="Pontos fortes (1-5 items)"
    )
    concerns: list[str] = Field(
        ..., description="Pontos de atenção (1-5 items)"
    )
    justification: str = Field(
        ..., description="Justificativa da pontuação (max 500 chars)"
    )
    status: str = Field(
        default="completed",
        description="Analysis status: 'completed' or 'timeout'",
    )


class CandidateAnalysisResponse(BaseModel):
    """Response body for candidate analysis."""

    job_id: str = Field(..., description="ID of the analyzed job")
    total_candidates: int = Field(..., description="Total number of candidates analyzed")
    results: list[CandidateScore] = Field(
        ..., description="Analysis results sorted by score descending"
    )


class ResumeMatchData(BaseModel):
    """Candidate resume data for job matching."""

    personal_data: dict[str, Any] | None = Field(
        default=None,
        description="Personal information (full_name, contact_email, phone, location)",
    )
    experiences: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Professional experiences (company, position, start_date, end_date, description)",
    )
    educations: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Education entries (institution, course, degree, start_date, end_date)",
    )
    skills: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Skills (name, proficiency)",
    )
    certifications: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Certifications (name, issuer, obtained_at)",
    )
    languages: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Languages (language, fluency)",
    )


class JobMatchData(BaseModel):
    """Active job data for matching."""

    id: str = Field(description="Unique job identifier")
    title: str = Field(description="Job title")
    modality: str | None = Field(default=None, description="Work modality (remote, hybrid, onsite)")
    location: str | None = Field(default=None, description="Job location")
    responsibilities: str | None = Field(default=None, description="Job responsibilities")
    required_skills: str | None = Field(default=None, description="Required skills/qualifications")
    optional_skills: str | None = Field(default=None, description="Optional/desired skills")
    contract_type: str | None = Field(
        default=None, description="Contract type (clt, pj, temporary, internship)"
    )
    salary_min: float | None = Field(default=None, description="Minimum salary")
    salary_max: float | None = Field(default=None, description="Maximum salary")


class JobMatchRequest(BaseModel):
    """Request body for job matching.

    Accepts candidate resume data and a list of active jobs to compare against.
    """

    candidate_id: str = Field(description="Candidate identifier")
    resume: ResumeMatchData | None = Field(
        default=None, description="Candidate's resume data (provide directly)"
    )
    active_jobs: list[JobMatchData] | None = Field(
        default=None, description="List of active jobs to evaluate compatibility"
    )


class JobMatch(BaseModel):
    """Individual job match result."""

    job_id: str = Field(description="ID of the matched job")
    compatibility_percentage: int = Field(
        ge=0, le=100, description="Compatibility percentage (0-100)"
    )
    justifications: list[str] = Field(
        min_length=1, max_length=5, description="Reasons for the compatibility score"
    )
    improvement_suggestions: list[str] = Field(
        max_length=5, description="Suggestions for candidate to improve fit (max 5)"
    )


class JobMatchResponse(BaseModel):
    """Response body for job matching.

    Results are sorted by compatibility_percentage descending.
    Only jobs with compatibility >= 10% are included.
    """

    candidate_id: str = Field(description="ID of the candidate analyzed")
    matches: list[JobMatch] = Field(description="Job matches sorted by compatibility descending")


# --- Endpoints ---


@router.post("/analyze-candidates", response_model=CandidateAnalysisResponse)
async def analyze_candidates(request: CandidateAnalysisRequest) -> CandidateAnalysisResponse:
    """Analyze candidates' fit for a specific job.

    Compares each candidate's resume against job requirements using
    LangChain/OpenAI and generates an adherence score (0-100) with
    strengths, concerns, and justification for each candidate.

    Limits:
    - Maximum 200 candidates per request
    - 60-second timeout per candidate analysis

    Results are sorted by score descending (ranking).
    """
    # Determine candidate count and validate limit
    candidate_count = 0
    if request.candidates:
        candidate_count = len(request.candidates)
    elif request.candidate_ids:
        candidate_count = len(request.candidate_ids)

    if candidate_count == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one candidate is required. Provide either 'candidates' or 'candidate_ids'.",
        )

    if candidate_count > 200:
        raise HTTPException(
            status_code=400,
            detail="Maximum 200 candidates per request. "
            f"Received: {candidate_count}.",
        )

    # Resolve job requirements
    job_data: dict = {}
    job_id: str = ""

    if request.job_requirements:
        job_data = request.job_requirements
        job_id = request.job_id or "provided"
    elif request.job_id:
        job_id = request.job_id
        try:
            job_data = await backend_client.get_job(request.job_id)
        except BackendClientError as e:
            logger.error("Failed to fetch job %s: %s", request.job_id, str(e))
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch job requirements: {str(e)}",
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Either 'job_id' or 'job_requirements' must be provided.",
        )

    # Resolve candidate data
    candidates_data: list[dict] = []

    if request.candidates:
        candidates_data = [
            {
                "candidate_id": c.candidate_id,
                "full_name": c.full_name,
                "location": c.location,
                "experiences": c.experiences,
                "educations": c.educations,
                "skills": c.skills,
                "certifications": c.certifications,
                "languages": c.languages,
            }
            for c in request.candidates
        ]
    elif request.candidate_ids:
        try:
            fetched = await backend_client.get_candidates_for_job(
                request.job_id or "", request.candidate_ids
            )
            candidates_data = fetched
        except BackendClientError as e:
            logger.error("Failed to fetch candidates: %s", str(e))
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch candidate data: {str(e)}",
            )

    # Run analysis
    results = await candidate_analyzer.analyze_candidates(job_data, candidates_data)

    # Convert to response model
    scored_results = [
        CandidateScore(
            candidate_id=r["candidate_id"],
            score=r["score"],
            strengths=r["strengths"] if r["strengths"] else ["N/A"],
            concerns=r["concerns"] if r["concerns"] else ["N/A"],
            justification=r["justification"],
            status=r["status"],
        )
        for r in results
    ]

    return CandidateAnalysisResponse(
        job_id=job_id,
        total_candidates=len(scored_results),
        results=scored_results,
    )


@router.post("/match-jobs", response_model=JobMatchResponse)
async def match_jobs(request: JobMatchRequest) -> JobMatchResponse:
    """Find compatible jobs for a candidate's profile.

    Compares the candidate's resume against active jobs using LangChain/OpenAI
    and returns compatibility percentages with justifications and improvement
    suggestions.

    Features:
    - Generates compatibility percentage (0-100%) per job
    - Generates up to 5 improvement suggestions per job for identified gaps
    - Implements 30-second overall timeout
    - Returns results sorted by compatibility percentage descending
    - Only returns jobs with compatibility >= 10%

    Raises:
        400: If candidate_id is empty or no resume/jobs provided
        408: If analysis exceeds 30-second timeout
        500: If LLM analysis fails
        502: If backend communication fails when fetching data
    """
    if not request.candidate_id:
        raise HTTPException(status_code=400, detail="Candidate ID is required")

    # Resolve resume data
    resume_data: dict[str, Any] = {}
    if request.resume:
        resume_data = request.resume.model_dump()
    else:
        # Fetch from backend
        try:
            resume_data = await backend_client.get_resume(request.candidate_id)
        except BackendClientError as e:
            logger.error(
                "Failed to fetch resume for candidate %s: %s",
                request.candidate_id,
                str(e),
            )
            raise HTTPException(
                status_code=502,
                detail=f"Falha ao buscar currículo do candidato: {str(e)}",
            )

    # Resolve active jobs
    jobs_data: list[dict[str, Any]] = []
    if request.active_jobs is not None:
        jobs_data = [job.model_dump() for job in request.active_jobs]
    else:
        # Fetch from backend
        try:
            jobs_data = await backend_client.get_active_jobs()
        except BackendClientError as e:
            logger.error("Failed to fetch active jobs: %s", str(e))
            raise HTTPException(
                status_code=502,
                detail=f"Falha ao buscar vagas ativas: {str(e)}",
            )

    if not jobs_data:
        raise HTTPException(
            status_code=400,
            detail="Nenhuma vaga ativa disponível para análise de compatibilidade.",
        )

    # Run the matching analysis with 30-second timeout
    try:
        matches = await match_candidate_to_jobs(
            candidate_resume=resume_data,
            active_jobs=jobs_data,
        )

        return JobMatchResponse(
            candidate_id=request.candidate_id,
            matches=[JobMatch(**m) for m in matches],
        )

    except asyncio.TimeoutError:
        logger.error(
            "Job matching timed out for candidate %s with %d jobs",
            request.candidate_id,
            len(jobs_data),
        )
        raise HTTPException(
            status_code=408,
            detail="Análise de compatibilidade excedeu o tempo limite de 30 segundos. "
            "Tente novamente.",
        )
    except Exception as e:
        logger.error(
            "Job matching failed for candidate %s: %s",
            request.candidate_id,
            str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Falha na análise de compatibilidade: {str(e)}",
        )
