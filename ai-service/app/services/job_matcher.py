"""Job matching service using LangChain/OpenAI for candidate-job compatibility analysis.

Compares a candidate's resume against active jobs using structured output
to generate compatibility percentages and improvement suggestions.
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


class JobMatchResult(BaseModel):
    """Structured output for a single job match analysis."""

    job_id: str = Field(description="The ID of the job being evaluated")
    compatibility_percentage: int = Field(
        description="Compatibility percentage (0-100) between candidate and job",
        ge=0,
        le=100,
    )
    justifications: list[str] = Field(
        description="List of reasons explaining the compatibility score (1-5 items)",
        min_length=1,
        max_length=5,
    )
    improvement_suggestions: list[str] = Field(
        description="Suggestions for the candidate to improve fit for this job (0-5 items)",
        max_length=5,
    )


class JobMatchAnalysis(BaseModel):
    """Structured output for the complete job matching analysis."""

    matches: list[JobMatchResult] = Field(
        description="List of job match results with compatibility scores"
    )


# --- Prompt Template ---

JOB_MATCHING_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Você é um especialista em recrutamento e seleção. Sua tarefa é analisar
a compatibilidade entre o perfil de um candidato e vagas de emprego ativas.

Para cada vaga, você deve:
1. Avaliar o percentual de compatibilidade (0-100%) baseado em:
   - Correspondência entre habilidades do candidato e requisitos da vaga
   - Experiência profissional relevante
   - Formação acadêmica compatível
   - Certificações e idiomas relevantes
   - Adequação do nível de senioridade

2. Fornecer justificativas (1 a 5) explicando o percentual atribuído:
   - Pontos fortes do candidato em relação à vaga
   - Áreas de convergência entre perfil e requisitos

3. Gerar sugestões de melhoria (máximo 5 por vaga) para lacunas identificadas:
   - Habilidades específicas a desenvolver
   - Certificações recomendadas
   - Experiências a buscar
   - Exemplos: "Obter certificação em AWS", "Adicionar experiência com Python ao currículo"

Seja objetivo e preciso. Avalie de forma justa sem inflar percentuais.
Candidatos sem nenhuma relevância para a vaga devem receber percentual baixo (0-10%).
""",
        ),
        (
            "human",
            """## Perfil do Candidato

{candidate_profile}

## Vagas Ativas para Avaliação

{jobs_data}

Analise a compatibilidade do candidato com cada vaga listada acima.
Retorne os resultados para TODAS as vagas fornecidas.""",
        ),
    ]
)


def _format_candidate_profile(resume: dict[str, Any]) -> str:
    """Format candidate resume data into a readable string for the LLM."""
    parts = []

    # Personal data
    personal = resume.get("personal_data") or {}
    if personal.get("full_name"):
        parts.append(f"**Nome:** {personal['full_name']}")
    if personal.get("location"):
        parts.append(f"**Localização:** {personal['location']}")

    # Experiences
    experiences = resume.get("experiences") or []
    if experiences:
        parts.append("\n**Experiência Profissional:**")
        for exp in experiences:
            line = f"- {exp.get('position', 'N/A')} em {exp.get('company', 'N/A')}"
            if exp.get("start_date"):
                line += f" ({exp['start_date']} - {exp.get('end_date', 'Atual')})"
            if exp.get("description"):
                line += f"\n  {exp['description'][:200]}"
            parts.append(line)

    # Education
    educations = resume.get("educations") or []
    if educations:
        parts.append("\n**Formação Acadêmica:**")
        for edu in educations:
            line = f"- {edu.get('degree', 'N/A')} em {edu.get('course', 'N/A')}"
            if edu.get("institution"):
                line += f" - {edu['institution']}"
            parts.append(line)

    # Skills
    skills = resume.get("skills") or []
    if skills:
        parts.append("\n**Habilidades:**")
        skill_items = [
            f"{s.get('name', 'N/A')} ({s.get('proficiency', 'N/A')})" for s in skills
        ]
        parts.append(", ".join(skill_items))

    # Certifications
    certifications = resume.get("certifications") or []
    if certifications:
        parts.append("\n**Certificações:**")
        for cert in certifications:
            line = f"- {cert.get('name', 'N/A')}"
            if cert.get("issuer"):
                line += f" ({cert['issuer']})"
            parts.append(line)

    # Languages
    languages = resume.get("languages") or []
    if languages:
        parts.append("\n**Idiomas:**")
        for lang in languages:
            parts.append(f"- {lang.get('language', 'N/A')}: {lang.get('fluency', 'N/A')}")

    return "\n".join(parts) if parts else "Perfil sem dados cadastrados"


def _format_jobs_data(jobs: list[dict[str, Any]]) -> str:
    """Format list of jobs into a readable string for the LLM."""
    parts = []

    for job in jobs:
        job_section = [f"### Vaga ID: {job.get('id', 'N/A')}"]
        if job.get("title"):
            job_section.append(f"**Título:** {job['title']}")
        if job.get("modality"):
            job_section.append(f"**Modalidade:** {job['modality']}")
        if job.get("location"):
            job_section.append(f"**Localização:** {job['location']}")
        if job.get("contract_type"):
            job_section.append(f"**Regime:** {job['contract_type']}")
        if job.get("responsibilities"):
            job_section.append(f"**Responsabilidades:** {job['responsibilities'][:300]}")
        if job.get("required_skills"):
            job_section.append(f"**Requisitos Obrigatórios:** {job['required_skills'][:300]}")
        if job.get("optional_skills"):
            job_section.append(f"**Requisitos Desejáveis:** {job['optional_skills'][:200]}")
        if job.get("salary_min") or job.get("salary_max"):
            salary = ""
            if job.get("salary_min"):
                salary += f"R${job['salary_min']}"
            if job.get("salary_max"):
                salary += f" - R${job['salary_max']}"
            job_section.append(f"**Faixa Salarial:** {salary}")

        parts.append("\n".join(job_section))

    return "\n\n---\n\n".join(parts)


async def match_candidate_to_jobs(
    candidate_resume: dict[str, Any],
    active_jobs: list[dict[str, Any]],
    timeout_seconds: int | None = None,
) -> list[dict[str, Any]]:
    """Analyze compatibility between a candidate and active jobs using LLM.

    Args:
        candidate_resume: Candidate's resume data (structured as ExtractedResume schema).
        active_jobs: List of active job postings to compare against.
        timeout_seconds: Overall timeout in seconds. Defaults to config value (30s).

    Returns:
        List of job match results sorted by compatibility percentage descending,
        filtered to only include jobs with compatibility >= 10%.

    Raises:
        asyncio.TimeoutError: If analysis exceeds the timeout.
        Exception: If LLM call fails.
    """
    if timeout_seconds is None:
        timeout_seconds = settings.job_matching_timeout

    if not active_jobs:
        return []

    # Format data for the prompt
    candidate_text = _format_candidate_profile(candidate_resume)
    jobs_text = _format_jobs_data(active_jobs)

    # Get LLM with structured output
    structured_llm = get_structured_llm(JobMatchAnalysis, temperature=0.1)

    # Build the chain
    chain = JOB_MATCHING_PROMPT | structured_llm

    # Execute with timeout
    result: JobMatchAnalysis = await asyncio.wait_for(
        chain.ainvoke({
            "candidate_profile": candidate_text,
            "jobs_data": jobs_text,
        }),
        timeout=timeout_seconds,
    )

    # Filter results: only jobs with compatibility >= 10%
    filtered_matches = [
        {
            "job_id": match.job_id,
            "compatibility_percentage": match.compatibility_percentage,
            "justifications": match.justifications,
            "improvement_suggestions": match.improvement_suggestions,
        }
        for match in result.matches
        if match.compatibility_percentage >= 10
    ]

    # Sort by compatibility percentage descending
    filtered_matches.sort(key=lambda x: x["compatibility_percentage"], reverse=True)

    return filtered_matches
