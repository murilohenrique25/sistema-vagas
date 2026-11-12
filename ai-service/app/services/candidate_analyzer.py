"""Service for analyzing candidates against job requirements using LangChain/OpenAI.

This module implements the core AI logic for comparing candidate resumes
against job requirements and generating adherence scores.
"""

import asyncio
import logging
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.config import settings
from app.services.llm import get_structured_llm

logger = logging.getLogger(__name__)


# --- Structured Output Models for LangChain ---


class CandidateAnalysisResult(BaseModel):
    """Structured output from LLM for a single candidate analysis."""

    score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Score de Aderência (0-100) indicating how well the candidate matches the job requirements",
    )
    strengths: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="1 to 5 key strengths of the candidate relative to the job",
    )
    concerns: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="1 to 5 areas of concern or missing qualifications",
    )
    justification: str = Field(
        ...,
        max_length=500,
        description="Brief explanation of the score (max 500 characters)",
    )


# --- Prompt Template ---

ANALYSIS_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Você é um especialista em recrutamento e seleção. Sua tarefa é analisar
a aderência de um candidato a uma vaga de emprego com base no currículo fornecido
e nos requisitos da vaga.

Gere uma análise estruturada contendo:
- Score de Aderência (0-100): nota geral de compatibilidade
- Pontos Fortes (1-5 itens): aspectos do candidato que se destacam para a vaga
- Pontos de Atenção (1-5 itens): lacunas ou áreas de preocupação
- Justificativa (máximo 500 caracteres): explicação breve da pontuação

Seja objetivo e baseie sua análise exclusivamente nas informações fornecidas.
Não invente informações que não estejam no currículo ou nos requisitos.""",
        ),
        (
            "human",
            """## Requisitos da Vaga

Título: {job_title}
Modalidade: {job_modality}
Localização: {job_location}
Responsabilidades: {job_responsibilities}
Requisitos Obrigatórios: {job_required_skills}
Requisitos Desejáveis: {job_optional_skills}
Regime: {job_contract_type}

## Currículo do Candidato

Nome: {candidate_name}
Localização: {candidate_location}
Experiências: {candidate_experiences}
Formação: {candidate_educations}
Habilidades: {candidate_skills}
Certificações: {candidate_certifications}
Idiomas: {candidate_languages}

Analise a aderência deste candidato à vaga acima.""",
        ),
    ]
)


class CandidateAnalyzer:
    """Analyzes candidates against job requirements using LangChain with structured output.

    Uses OpenAI's structured output via LangChain to ensure consistent
    JSON responses for each candidate analysis.
    """

    def __init__(self) -> None:
        self._timeout = settings.candidate_analysis_timeout

    def _get_chain(self):
        """Create the analysis chain with structured output."""
        structured_llm = get_structured_llm(CandidateAnalysisResult, temperature=0.1)
        return ANALYSIS_PROMPT | structured_llm

    def _format_job_data(self, job: dict) -> dict[str, str]:
        """Format job data for the prompt template."""
        return {
            "job_title": job.get("title", "N/A"),
            "job_modality": job.get("modality", "N/A"),
            "job_location": job.get("location", "N/A"),
            "job_responsibilities": job.get("responsibilities", "N/A"),
            "job_required_skills": job.get("required_skills", "N/A"),
            "job_optional_skills": job.get("optional_skills", "N/A"),
            "job_contract_type": job.get("contract_type", "N/A"),
        }

    def _format_candidate_data(self, candidate: dict) -> dict[str, str]:
        """Format candidate resume data for the prompt template."""
        resume = candidate.get("resume", candidate)

        experiences = resume.get("experiences", [])
        experiences_text = "; ".join(
            f"{exp.get('position', 'N/A')} em {exp.get('company', 'N/A')} "
            f"({exp.get('start_date', '?')} - {exp.get('end_date', 'atual')}): "
            f"{exp.get('description', 'N/A')}"
            for exp in experiences
        ) or "Nenhuma experiência informada"

        educations = resume.get("educations", [])
        educations_text = "; ".join(
            f"{edu.get('degree', 'N/A')} em {edu.get('course', 'N/A')} - "
            f"{edu.get('institution', 'N/A')} ({edu.get('start_date', '?')} - {edu.get('end_date', '?')})"
            for edu in educations
        ) or "Nenhuma formação informada"

        skills = resume.get("skills", [])
        skills_text = ", ".join(
            f"{skill.get('name', 'N/A')} ({skill.get('proficiency', 'N/A')})"
            for skill in skills
        ) or "Nenhuma habilidade informada"

        certifications = resume.get("certifications", [])
        certifications_text = ", ".join(
            f"{cert.get('name', 'N/A')} ({cert.get('issuer', 'N/A')})"
            for cert in certifications
        ) or "Nenhuma certificação informada"

        languages = resume.get("languages", [])
        languages_text = ", ".join(
            f"{lang.get('language', 'N/A')} ({lang.get('fluency', 'N/A')})"
            for lang in languages
        ) or "Nenhum idioma informado"

        personal = resume.get("personal_data", {})
        candidate_name = personal.get("full_name") or resume.get("full_name", "N/A")
        candidate_location = personal.get("location") or resume.get("location", "N/A")

        return {
            "candidate_name": candidate_name,
            "candidate_location": candidate_location,
            "candidate_experiences": experiences_text,
            "candidate_educations": educations_text,
            "candidate_skills": skills_text,
            "candidate_certifications": certifications_text,
            "candidate_languages": languages_text,
        }

    async def analyze_single_candidate(
        self,
        job: dict,
        candidate: dict,
    ) -> CandidateAnalysisResult | None:
        """Analyze a single candidate against job requirements with timeout.

        Args:
            job: Job details dictionary with requirements.
            candidate: Candidate resume data dictionary.

        Returns:
            CandidateAnalysisResult on success, None on timeout or error.
        """
        chain = self._get_chain()
        job_data = self._format_job_data(job)
        candidate_data = self._format_candidate_data(candidate)

        prompt_input = {**job_data, **candidate_data}

        try:
            result = await asyncio.wait_for(
                chain.ainvoke(prompt_input),
                timeout=self._timeout,
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(
                "Timeout analyzing candidate (exceeded %ds)", self._timeout
            )
            return None
        except Exception as e:
            logger.error("Error analyzing candidate: %s", str(e))
            return None

    async def analyze_candidates(
        self,
        job: dict,
        candidates: list[dict],
    ) -> list[dict[str, Any]]:
        """Analyze multiple candidates against job requirements.

        Processes each candidate sequentially with a per-candidate timeout.
        Results are sorted by score descending.

        Args:
            job: Job details dictionary with requirements.
            candidates: List of candidate data dictionaries.
                Each must include a 'candidate_id' field.

        Returns:
            List of analysis results sorted by score descending.
            Each result contains candidate_id, score, strengths, concerns,
            justification, and a status field ('completed' or 'timeout').
        """
        results: list[dict[str, Any]] = []

        for candidate in candidates:
            candidate_id = candidate.get("candidate_id", "unknown")
            analysis = await self.analyze_single_candidate(job, candidate)

            if analysis is not None:
                results.append(
                    {
                        "candidate_id": candidate_id,
                        "score": analysis.score,
                        "strengths": analysis.strengths,
                        "concerns": analysis.concerns,
                        "justification": analysis.justification,
                        "status": "completed",
                    }
                )
            else:
                results.append(
                    {
                        "candidate_id": candidate_id,
                        "score": 0,
                        "strengths": [],
                        "concerns": ["Análise não pôde ser concluída"],
                        "justification": "Timeout ou erro durante a análise do candidato.",
                        "status": "timeout",
                    }
                )

        # Sort by score descending
        results.sort(key=lambda r: r["score"], reverse=True)
        return results


# Module-level instance
candidate_analyzer = CandidateAnalyzer()
