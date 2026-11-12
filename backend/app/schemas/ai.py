"""AI-related schemas for candidate analysis and job matching endpoints."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import BaseSchema


# --- Candidate Analysis (Employer) ---


class CandidateData(BaseModel):
    """Candidate resume data for analysis."""

    candidate_id: str = Field(..., description="ID do candidato")
    full_name: str | None = Field(None, description="Nome completo")
    location: str | None = Field(None, description="Localização")
    experiences: list[dict[str, Any]] = Field(default_factory=list)
    educations: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[dict[str, Any]] = Field(default_factory=list)
    certifications: list[dict[str, Any]] = Field(default_factory=list)
    languages: list[dict[str, Any]] = Field(default_factory=list)


class AnalyzeCandidatesRequest(BaseModel):
    """Request body for POST /v1/ai/analyze-candidates."""

    job_id: UUID = Field(..., description="ID da vaga para análise")
    candidate_ids: list[UUID] | None = Field(
        None,
        description="IDs dos candidatos (busca do backend)",
        max_length=200,
    )
    job_requirements: dict[str, Any] | None = Field(
        None, description="Requisitos da vaga (fornecidos diretamente)"
    )
    candidates: list[CandidateData] | None = Field(
        None,
        description="Dados dos candidatos (fornecidos diretamente, max 200)",
        max_length=200,
    )


class CandidateScoreResult(BaseSchema):
    """Single candidate score in the analysis response."""

    candidate_id: str
    candidate_name: str | None = None
    score: int = Field(ge=0, le=100)
    strengths: list[str] = Field(description="Pontos fortes (1-5)")
    concerns: list[str] = Field(description="Pontos de atenção (1-5)")
    justification: str = Field(description="Justificativa (max 500 chars)")


class AnalyzeCandidatesResponse(BaseSchema):
    """Response body for POST /v1/ai/analyze-candidates."""

    job_id: str
    total_candidates: int
    results: list[CandidateScoreResult]
    tokens_consumed: int


# --- Job Matching (Candidate) ---


class JobMatchingRequest(BaseModel):
    """Request body for POST /v1/ai/job-matching."""

    # No body fields needed - uses authenticated candidate's resume
    pass


class JobMatchResult(BaseSchema):
    """Single job match result."""

    job_id: str
    job_title: str | None = None
    company_name: str | None = None
    compatibility_percentage: int = Field(ge=0, le=100)
    justifications: list[str] = Field(description="Justificativas de compatibilidade")
    improvement_suggestions: list[str] = Field(
        description="Sugestões de melhoria (max 5)"
    )


class JobMatchingResponse(BaseSchema):
    """Response body for POST /v1/ai/job-matching."""

    candidate_id: str
    matches: list[JobMatchResult]
    tokens_consumed: int
    message: str | None = None
