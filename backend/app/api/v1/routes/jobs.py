"""Job management routes: CRUD, duplicate, status change, extend deadline, search."""

import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import CurrentUser, get_current_user
from app.core.cache import build_job_search_cache_key, cache_get, cache_invalidate, cache_set
from app.core.database import get_session
from app.models.company import Company
from app.models.enums import ContractType, JobModality
from app.schemas.job import (
    JobCreate,
    JobExtendDeadline,
    JobResponse,
    JobSearchFilters,
    JobSortField,
    JobStatusUpdate,
    JobUpdate,
    PaginatedResponse,
    SortOrder,
)
from app.services.job_service import JobService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])

# Cache invalidation pattern for all job search results
JOBS_CACHE_PATTERN = "jobs:search:*"


async def _get_employer_company(
    employer_id: UUID, session: AsyncSession
) -> Company:
    """Helper to get the employer's company."""
    result = await session.execute(
        select(Company).where(Company.owner_id == employer_id)
    )
    company = result.scalars().first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você precisa ter uma empresa cadastrada para gerenciar vagas",
        )
    if not company.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Empresa suspensa. Entre em contato com o suporte.")
    return company


def _require_employer(current_user: CurrentUser) -> None:
    """Ensure the current user is an employer."""
    if current_user.role != "employer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas empregadores podem realizar esta ação",
        )


@router.get(
    "",
    response_model=PaginatedResponse[JobResponse],
    summary="Listar e buscar vagas",
    description=(
        "Lista vagas ativas com paginação (20 itens/página), filtros combinados, "
        "busca textual e ordenação. Vagas em destaque aparecem primeiro. "
        "Endpoint público, não requer autenticação. Resultados são cacheados por 300s."
    ),
)
async def list_jobs(
    q: Optional[str] = Query(None, min_length=2, description="Busca textual (mín. 2 caracteres)"),
    modality: Optional[JobModality] = Query(None, description="Filtro por modalidade"),
    location: Optional[str] = Query(None, description="Filtro por localização"),
    salary_min: Optional[Decimal] = Query(None, ge=0, description="Salário mínimo da faixa"),
    salary_max: Optional[Decimal] = Query(None, description="Salário máximo da faixa"),
    contract_type: Optional[ContractType] = Query(None, description="Filtro por regime"),
    sort_by: JobSortField = Query(JobSortField.date, description="Campo de ordenação"),
    sort_order: SortOrder = Query(SortOrder.desc, description="Direção da ordenação"),
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[JobResponse]:
    """List active jobs with search, filters, pagination, and highlighting.

    Uses Redis cache with 300s TTL. Falls back to direct DB query if Redis
    is unavailable (Requirement 16.3, 16.6).
    """
    # Build cache key based on all search parameters
    cache_key = build_job_search_cache_key(
        q=q,
        modality=modality.value if modality else None,
        location=location,
        salary_min=salary_min,
        salary_max=salary_max,
        contract_type=contract_type.value if contract_type else None,
        sort_by=sort_by.value,
        sort_order=sort_order.value,
        page=page,
        page_size=page_size,
    )

    # Try to get from cache first
    cached_result = await cache_get(cache_key)
    if cached_result is not None:
        logger.debug("Cache hit for job search: %s", cache_key)
        return PaginatedResponse[JobResponse](**cached_result)

    # Cache miss - query the database
    logger.debug("Cache miss for job search: %s", cache_key)
    filters = JobSearchFilters(
        q=q,
        modality=modality,
        location=location,
        salary_min=salary_min,
        salary_max=salary_max,
        contract_type=contract_type,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )

    job_service = JobService(session)
    result = await job_service.search_jobs(filters)

    # Serialize items
    job_responses = [JobResponse.model_validate(job) for job in result.items]

    response = PaginatedResponse[JobResponse](
        items=job_responses,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )

    # Cache the result (TTL 300s). If Redis is down, this silently fails.
    await cache_set(cache_key, response.model_dump(mode="json"), ttl=300)

    return response


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar vaga",
    description="Cria uma nova vaga de emprego. Apenas empregadores autenticados.",
)
async def create_job(
    data: JobCreate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JobResponse:
    """Create a new job posting."""
    _require_employer(current_user)
    company = await _get_employer_company(current_user.id, session)

    job_service = JobService(session)
    job = await job_service.create_job(current_user.id, company.id, data)

    # Invalidate job search cache since listings have changed
    await cache_invalidate(JOBS_CACHE_PATTERN)

    return JobResponse.model_validate(job)


@router.put(
    "/{job_id}",
    response_model=JobResponse,
    summary="Atualizar vaga",
    description="Atualiza campos de uma vaga existente. Apenas o empregador dono.",
)
async def update_job(
    job_id: UUID,
    data: JobUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JobResponse:
    """Update an existing job posting."""
    _require_employer(current_user)

    job_service = JobService(session)
    job = await job_service.update_job(job_id, current_user.id, data)

    # Invalidate job search cache since job data has changed
    await cache_invalidate(JOBS_CACHE_PATTERN)

    return JobResponse.model_validate(job)


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Detalhe da vaga",
    description="Retorna os detalhes de uma vaga específica. Endpoint público.",
)
async def get_job(
    job_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> JobResponse:
    """Get a single job by ID (public)."""
    job_service = JobService(session)
    job = await job_service.get_job_by_id(job_id)
    return JobResponse.model_validate(job)


@router.post(
    "/{job_id}/duplicate",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Duplicar vaga",
    description="Duplica uma vaga existente com status rascunho e prazo em branco.",
)
async def duplicate_job(
    job_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JobResponse:
    """Duplicate an existing job posting."""
    _require_employer(current_user)

    job_service = JobService(session)
    job = await job_service.duplicate_job(job_id, current_user.id)
    return JobResponse.model_validate(job)


@router.patch(
    "/{job_id}/status",
    response_model=JobResponse,
    summary="Alterar status da vaga",
    description="Altera o status de uma vaga (ativar, inativar, encerrar).",
)
async def change_job_status(
    job_id: UUID,
    data: JobStatusUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JobResponse:
    """Change job status."""
    _require_employer(current_user)

    job_service = JobService(session)
    job = await job_service.change_status(job_id, current_user.id, data.status)

    # Invalidate job search cache since status change affects listings
    await cache_invalidate(JOBS_CACHE_PATTERN)

    return JobResponse.model_validate(job)


@router.patch(
    "/{job_id}/extend",
    response_model=JobResponse,
    summary="Prorrogar prazo da vaga",
    description="Prorroga o prazo de encerramento de uma vaga.",
)
async def extend_job_deadline(
    job_id: UUID,
    data: JobExtendDeadline,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> JobResponse:
    """Extend job deadline."""
    _require_employer(current_user)

    job_service = JobService(session)
    job = await job_service.extend_deadline(job_id, current_user.id, data)
    return JobResponse.model_validate(job)


@router.get(
    "/{job_id}/applications",
    summary="Listar candidaturas da vaga (empregador)",
    description=(
        "Lista as candidaturas recebidas para uma vaga específica. "
        "Apenas o empregador dono da vaga pode acessar."
    ),
)
async def list_job_applications(
    job_id: UUID,
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List applications for a specific job (employer view)."""
    _require_employer(current_user)

    from app.services.application_service import ApplicationService

    service = ApplicationService(session)
    return await service.get_job_applications(
        job_id, employer_id=current_user.id, page=page, page_size=page_size
    )
