"""AI routes: candidate analysis and job matching with token management."""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import CurrentUser, get_current_user
from app.core.database import get_session
from app.models.ai_analysis import AIAnalysis
from app.models.enums import (
    AIAnalysisStatus,
    AIAnalysisType,
    JobStatus,
    UserRole,
)
from app.models.job import Job
from app.models.company import Company
from app.models.resume import Experience, Resume, Skill
from app.schemas.ai import (
    AnalyzeCandidatesRequest,
    AnalyzeCandidatesResponse,
    CandidateScoreResult,
    JobMatchingResponse,
    JobMatchResult,
)
from app.services.ai_service_client import (
    AIServiceError,
    AIServiceTimeoutError,
    AIServiceUnavailableError,
    CircuitBreakerOpenError,
    ai_service_client,
)
from app.services.wallet_service import WalletService
from app.services.payment_settings_service import PaymentSettingsService
from app.schemas.payment import ServicePaymentPurpose

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])

# Configurable token costs (can be overridden via TokenConfig in DB)
DEFAULT_COST_PER_CANDIDATE_ANALYSIS = 1  # 1 token per candidate analyzed
DEFAULT_COST_JOB_MATCHING = 1  # 1 token per job matching request


def _build_candidate_data(candidate_id: str, resume: Resume | None) -> dict[str, Any]:
    """Build the candidate payload expected by the AI service from a Resume.

    Returns the full resume profile (experiences, educations, skills, etc.)
    so the AI can score the candidate's adherence. If the candidate has no
    resume, returns an empty profile so the analysis still completes.
    """
    if resume is None:
        return {
            "candidate_id": candidate_id,
            "full_name": None,
            "location": None,
            "experiences": [],
            "educations": [],
            "skills": [],
            "certifications": [],
            "languages": [],
        }

    return {
        "candidate_id": candidate_id,
        "full_name": resume.full_name,
        "location": resume.location,
        "experiences": [
            {
                "company": exp.company,
                "position": exp.position,
                "start_date": str(exp.start_date) if exp.start_date else None,
                "end_date": str(exp.end_date) if exp.end_date else None,
                "description": exp.description,
            }
            for exp in (resume.experiences or [])
        ],
        "educations": [
            {
                "institution": edu.institution,
                "course": edu.course,
                "degree": edu.degree.value if edu.degree else None,
                "start_date": str(edu.start_date) if edu.start_date else None,
                "end_date": str(edu.end_date) if edu.end_date else None,
            }
            for edu in (resume.educations or [])
        ],
        "skills": [
            {
                "name": skill.name,
                "proficiency": skill.proficiency.value if skill.proficiency else None,
            }
            for skill in (resume.skills or [])
        ],
        "certifications": [
            {
                "name": cert.name,
                "issuer": cert.issuer,
                "obtained_at": str(cert.obtained_at) if cert.obtained_at else None,
            }
            for cert in (resume.certifications or [])
        ],
        "languages": [
            {
                "language": lang.language,
                "fluency": lang.fluency.value if lang.fluency else None,
            }
            for lang in (resume.languages or [])
        ],
    }


@router.post(
    "/analyze-candidates",
    response_model=AnalyzeCandidatesResponse,
    summary="Análise de candidatos por IA",
    description=(
        "Analisa a aderência de candidatos a uma vaga utilizando IA. "
        "Requer saldo de tokens suficiente. "
        "Custo: 1 token por candidato analisado. "
        "Limite: 200 candidatos por solicitação."
    ),
)
async def analyze_candidates(
    request: AnalyzeCandidatesRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AnalyzeCandidatesResponse:
    """Analyze candidates for a job position using AI.

    Flow:
    1. Validate user is employer
    2. Determine candidate count and calculate token cost
    3. Validate token balance
    4. Debit tokens BEFORE AI call
    5. Call AI service
    6. On success: persist results and return
    7. On failure: refund tokens and raise error
    """
    # 1. Validate role
    if current_user.role != UserRole.employer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas empregadores podem realizar análise de candidatos",
        )

    # 2. Determine candidate count - auto-fetch from job applications if none provided
    candidate_count = 0
    if request.candidates:
        candidate_count = len(request.candidates)
    elif request.candidate_ids:
        candidate_count = len(request.candidate_ids)
    else:
        # Auto-fetch candidates who applied to this job
        from app.models.application import Application
        from app.models.resume import Resume
        app_result = await session.execute(
            select(Application.candidate_id).where(
                Application.job_id == request.job_id
            )
        )
        candidate_ids_from_db = [row[0] for row in app_result.all()]
        if candidate_ids_from_db:
            request.candidate_ids = candidate_ids_from_db
            candidate_count = len(candidate_ids_from_db)

    if candidate_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum candidato encontrado para esta vaga. Aguarde candidaturas antes de analisar.",
        )

    if candidate_count > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Limite máximo de 200 candidatos por solicitação. Recebido: {candidate_count}",
        )

    owned_job_result = await session.execute(
        select(Job.id).join(Company).where(
            Job.id == request.job_id, Company.owner_id == current_user.id
        )
    )
    if owned_job_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Você não pode analisar candidatos desta vaga.")

    wallet_service = WalletService(session)
    analysis_price = await PaymentSettingsService(session).get_price(ServicePaymentPurpose.resume_analysis)
    await wallet_service.debit(
        current_user.id, analysis_price, reason="Análise de currículos por IA",
        reference_id=request.job_id,
        operation_id=f"{current_user.id}:resume-analysis:{idempotency_key}" if idempotency_key else None,
    )
    await session.commit()
    total_cost = 0

    # 5. Call AI service
    try:
        # Prepare job requirements
        job_requirements = request.job_requirements
        if not job_requirements:
            # Fetch job from database
            result = await session.execute(
                select(Job).where(Job.id == request.job_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Vaga não encontrada",
                )
            job_requirements = {
                "id": str(job.id),
                "title": job.title,
                "modality": job.modality.value if job.modality else None,
                "location": job.location,
                "responsibilities": job.responsibilities,
                "required_skills": job.required_skills,
                "optional_skills": job.optional_skills,
                "contract_type": job.contract_type.value if job.contract_type else None,
            }

        # Prepare candidates data - fetch full resume profiles from the DB
        candidates_data: list[dict[str, Any]] = []
        candidate_names: dict[str, str | None] = {}
        if request.candidates:
            candidates_data = [c.model_dump() for c in request.candidates]
            for c in request.candidates:
                candidate_names[str(c.candidate_id)] = c.full_name
        elif request.candidate_ids:
            # Load each candidate's resume (with experiences, skills, etc.)
            resumes_result = await session.execute(
                select(Resume).where(Resume.user_id.in_(request.candidate_ids))
            )
            resumes_by_user = {
                r.user_id: r for r in resumes_result.scalars().all()
            }
            for cid in request.candidate_ids:
                resume = resumes_by_user.get(cid)
                candidates_data.append(_build_candidate_data(str(cid), resume))
                candidate_names[str(cid)] = resume.full_name if resume else None

        # Call AI microservice
        ai_result = await ai_service_client.analyze_candidates(
            job_requirements=job_requirements,
            candidates=candidates_data,
        )

        # 6. Persist analysis record
        analysis = AIAnalysis(
            requester_id=current_user.id,
            job_id=request.job_id,
            type=AIAnalysisType.candidate_analysis,
            result=ai_result,
            tokens_consumed=total_cost,
            status=AIAnalysisStatus.completed,
            completed_at=datetime.now(timezone.utc),
        )
        session.add(analysis)
        await session.commit()

        # Build response
        results = []
        for r in ai_result.get("results", []):
            results.append(
                CandidateScoreResult(
                    candidate_id=r["candidate_id"],
                    candidate_name=candidate_names.get(str(r["candidate_id"])),
                    score=r["score"],
                    strengths=r.get("strengths", []),
                    concerns=r.get("concerns", []),
                    justification=r.get("justification", ""),
                )
            )

        return AnalyzeCandidatesResponse(
            job_id=ai_result.get("job_id", str(request.job_id)),
            total_candidates=ai_result.get("total_candidates", len(results)),
            results=results,
            tokens_consumed=total_cost,
        )

    except (AIServiceTimeoutError, AIServiceUnavailableError, CircuitBreakerOpenError, AIServiceError) as e:
        logger.error("AI service error during candidate analysis: %s", str(e))
        await wallet_service.credit(current_user.id, analysis_price, reason="Estorno: falha na análise de currículos", reference_id=request.job_id)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha no serviço de IA. O pagamento pode ser reutilizado. Detalhes: {e.message}",
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Unexpected error in analyze_candidates")
        await session.rollback()
        await wallet_service.credit(current_user.id, analysis_price)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno. O pagamento não foi consumido.",
        )


@router.post(
    "/job-matching",
    response_model=JobMatchingResponse,
    summary="Compatibilidade de vagas por IA",
    description=(
        "Analisa a compatibilidade do candidato com vagas ativas usando IA. "
        "Requer currículo com ao menos 1 experiência ou 1 habilidade. "
        "Requer saldo de tokens suficiente. "
        "Custo: 1 token por análise."
    ),
)
async def job_matching(
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JobMatchingResponse:
    """Find compatible jobs for a candidate using AI.

    Flow:
    1. Validate user is candidate
    2. Validate resume exists with minimum data (1 experience OR 1 skill)
    3. Validate token balance and debit
    4. Fetch active jobs
    5. Call AI service
    6. On success: return results (filter ≥10% compatibility)
    7. On failure: refund tokens and raise error
    8. Handle no matches scenario
    """
    # 1. Validate role
    if current_user.role != UserRole.candidate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas candidatos podem utilizar a análise de compatibilidade",
        )

    # 2. Validate resume exists with minimum data
    result = await session.execute(
        select(Resume).where(Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="É necessário ter um currículo cadastrado para utilizar a análise de compatibilidade",
        )

    # Check minimum: at least 1 experience OR 1 skill
    has_experiences = len(resume.experiences) > 0 if resume.experiences else False
    has_skills = len(resume.skills) > 0 if resume.skills else False

    if not has_experiences and not has_skills:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Seu currículo precisa ter ao menos 1 experiência profissional ou "
                "1 habilidade cadastrada para utilizar a análise de compatibilidade"
            ),
        )

    wallet_service = WalletService(session)
    compatibility_price = await PaymentSettingsService(session).get_price(ServicePaymentPurpose.job_compatibility)
    await wallet_service.debit(
        current_user.id, compatibility_price, reason="Busca de compatibilidade por IA",
        operation_id=f"{current_user.id}:job-match:{idempotency_key}" if idempotency_key else None,
    )
    await session.commit()

    # 4. Fetch active jobs
    jobs_result = await session.execute(
        select(Job).where(Job.status == JobStatus.active)
    )
    active_jobs = jobs_result.scalars().all()

    if not active_jobs:
        await wallet_service.credit(current_user.id, compatibility_price)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma vaga ativa disponível para análise de compatibilidade",
        )

    # Build lookups to enrich the response with job title and company name
    from app.models.company import Company

    jobs_by_id = {str(job.id): job for job in active_jobs}
    company_ids = {job.company_id for job in active_jobs}
    companies_result = await session.execute(
        select(Company.id, Company.name).where(Company.id.in_(company_ids))
    )
    company_names = {cid: name for cid, name in companies_result.all()}

    # Prepare resume data for AI service
    resume_data: dict[str, Any] = {
        "personal_data": {
            "full_name": resume.full_name,
            "contact_email": resume.contact_email,
            "phone": resume.phone,
            "location": resume.location,
        },
        "experiences": [
            {
                "company": exp.company,
                "position": exp.position,
                "start_date": str(exp.start_date) if exp.start_date else None,
                "end_date": str(exp.end_date) if exp.end_date else None,
                "description": exp.description,
            }
            for exp in (resume.experiences or [])
        ],
        "educations": [
            {
                "institution": edu.institution,
                "course": edu.course,
                "degree": edu.degree.value if edu.degree else None,
                "start_date": str(edu.start_date) if edu.start_date else None,
                "end_date": str(edu.end_date) if edu.end_date else None,
            }
            for edu in (resume.educations or [])
        ],
        "skills": [
            {
                "name": skill.name,
                "proficiency": skill.proficiency.value if skill.proficiency else None,
            }
            for skill in (resume.skills or [])
        ],
        "certifications": [
            {
                "name": cert.name,
                "issuer": cert.issuer,
                "obtained_at": str(cert.obtained_at) if cert.obtained_at else None,
            }
            for cert in (resume.certifications or [])
        ],
        "languages": [
            {
                "language": lang.language,
                "fluency": lang.fluency.value if lang.fluency else None,
            }
            for lang in (resume.languages or [])
        ],
    }

    # Prepare jobs data for AI service
    jobs_data: list[dict[str, Any]] = [
        {
            "id": str(job.id),
            "title": job.title,
            "modality": job.modality.value if job.modality else None,
            "location": job.location,
            "responsibilities": job.responsibilities,
            "required_skills": job.required_skills,
            "optional_skills": job.optional_skills,
            "contract_type": job.contract_type.value if job.contract_type else None,
            "salary_min": float(job.salary_min) if job.salary_min else None,
            "salary_max": float(job.salary_max) if job.salary_max else None,
        }
        for job in active_jobs
    ]

    # 5. Call AI service
    try:
        ai_result = await ai_service_client.match_jobs(
            candidate_id=str(current_user.id),
            resume=resume_data,
            active_jobs=jobs_data,
        )

        # 6. Process results - filter matches with ≥10% compatibility
        matches = ai_result.get("matches", [])
        filtered_matches = [
            m for m in matches if m.get("compatibility_percentage", 0) >= 10
        ]

        # Persist analysis record
        analysis = AIAnalysis(
            requester_id=current_user.id,
            type=AIAnalysisType.job_matching,
            result=ai_result,
            tokens_consumed=0,
            status=AIAnalysisStatus.completed,
            completed_at=datetime.now(timezone.utc),
        )
        session.add(analysis)
        await session.commit()

        # 8. Handle no matches scenario
        message = None
        if not filtered_matches:
            message = (
                "Não foram encontradas vagas com aderência relevante ao seu perfil (≥10%). "
                "Considere atualizar seu currículo com mais experiências e habilidades."
            )

        # Build response
        match_results = []
        for m in filtered_matches[:5]:  # Top 5 matches
            job = jobs_by_id.get(m["job_id"])
            match_results.append(
                JobMatchResult(
                    job_id=m["job_id"],
                    job_title=job.title if job else None,
                    company_name=company_names.get(job.company_id) if job else None,
                    compatibility_percentage=m["compatibility_percentage"],
                    justifications=m.get("justifications", []),
                    improvement_suggestions=m.get("improvement_suggestions", []),
                )
            )

        return JobMatchingResponse(
            candidate_id=str(current_user.id),
            matches=match_results,
            tokens_consumed=0,
            message=message,
        )

    except (AIServiceTimeoutError, AIServiceUnavailableError, CircuitBreakerOpenError, AIServiceError) as e:
        logger.error("AI service error during job matching: %s", str(e))
        await wallet_service.credit(current_user.id, compatibility_price)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Falha no serviço de IA. O pagamento pode ser reutilizado. Detalhes: {e.message}",
        )

    except HTTPException:
        raise

    except Exception as e:
        logger.exception("Unexpected error in job_matching")
        await session.rollback()
        await wallet_service.credit(current_user.id, compatibility_price)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno. O pagamento não foi consumido.",
        )
