"""Admin panel routes for platform management."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import CurrentUser, require_admin
from app.core.database import get_session
from app.models.application import Application
from app.models.audit_log import AuditLog
from app.models.company import Company
from app.models.job import Job
from app.models.subscription import Payment
from app.models.token import TokenTransaction
from app.models.user import User
from app.models.job_report import JobReport
from app.schemas.report import JobReportResponse, JobReportStatusUpdate
from app.schemas.admin import (
    AdminApplicationResponse,
    AdminAuditLogResponse,
    AdminCompanyResponse,
    AdminCompanyUpdate,
    AdminJobResponse,
    AdminJobStatusUpdate,
    AdminPaymentResponse,
    AdminRevenueResponse,
    AdminTransactionResponse,
    AdminUserResponse,
    AdminUserUpdate,
    AdminPaymentSettingsUpdate,
)
from app.schemas.base import PaginatedResponse
from app.schemas.metrics import (
    AIMetricsResponse,
    FinancialMetricsResponse,
    MetricsPeriod,
    PlatformKPIsResponse,
)
from app.services import csv_export_service, metrics_service

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/job-reports", response_model=list[JobReportResponse])
async def list_job_reports(admin: CurrentUser = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    return list((await session.execute(select(JobReport).order_by(JobReport.created_at.desc()).limit(500))).scalars().all())

@router.patch("/job-reports/{report_id}", response_model=JobReportResponse)
async def moderate_job_report(report_id: UUID, data: JobReportStatusUpdate, admin: CurrentUser = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    report = await session.get(JobReport, report_id)
    if not report: raise HTTPException(status_code=404, detail="Denúncia não encontrada")
    previous={"status":report.status}; report.status=data.status
    await _create_audit_log(session,admin.id,"moderate_job_report","job_report",report.id,previous,{"status":report.status})
    return report


# ==============================================================================
# Helper: Create audit log entry
# ==============================================================================


async def _create_audit_log(
    session: AsyncSession,
    admin_id: UUID,
    action: str,
    entity_type: str,
    entity_id: UUID,
    previous_value: dict | None = None,
    new_value: dict | None = None,
) -> None:
    """Create an audit log entry for an admin action."""
    log = AuditLog(
        admin_id=admin_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        previous_value=previous_value,
        new_value=new_value,
    )
    session.add(log)


# ==============================================================================
# User Management
# ==============================================================================


@router.get(
    "/users",
    response_model=PaginatedResponse[AdminUserResponse],
    summary="Listar todos os usuários",
)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: str | None = Query(None, description="Filtrar por role"),
    is_active: bool | None = Query(None, description="Filtrar por status ativo"),
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[AdminUserResponse]:
    """List all users with optional filters."""
    query = select(User)

    if role is not None:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(User.created_at.desc())
    result = await session.execute(query)
    users = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=[AdminUserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.patch(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="Editar usuário",
)
async def update_user(
    user_id: UUID,
    data: AdminUserUpdate,
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> AdminUserResponse:
    """Edit user name, role, or status."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
    if user.id == admin.id and (data.role not in (None, "admin") or data.is_active is False):
        raise HTTPException(status_code=400, detail="Administrador não pode remover o próprio acesso")

    previous_value = {"name": user.name, "role": user.role.value if hasattr(user.role, 'value') else user.role, "is_active": user.is_active}

    if data.name is not None:
        user.name = data.name
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active

    new_value = {"name": user.name, "role": user.role.value if hasattr(user.role, 'value') else user.role, "is_active": user.is_active}

    await _create_audit_log(session, admin.id, "update_user", "user", user_id, previous_value, new_value)

    return AdminUserResponse.model_validate(user)


@router.post(
    "/users/{user_id}/activate",
    response_model=AdminUserResponse,
    summary="Ativar usuário",
)
async def activate_user(
    user_id: UUID,
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> AdminUserResponse:
    """Activate a user account."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    previous_value = {"is_active": user.is_active}
    user.is_active = True
    new_value = {"is_active": True}

    await _create_audit_log(session, admin.id, "activate_user", "user", user_id, previous_value, new_value)

    return AdminUserResponse.model_validate(user)


@router.post(
    "/users/{user_id}/deactivate",
    response_model=AdminUserResponse,
    summary="Desativar usuário",
)
async def deactivate_user(
    user_id: UUID,
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> AdminUserResponse:
    """Deactivate a user account."""
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Administrador não pode desativar a própria conta")
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    previous_value = {"is_active": user.is_active}
    user.is_active = False
    new_value = {"is_active": False}

    await _create_audit_log(session, admin.id, "deactivate_user", "user", user_id, previous_value, new_value)

    return AdminUserResponse.model_validate(user)


# ==============================================================================
# Company Management
# ==============================================================================


@router.get(
    "/companies",
    response_model=PaginatedResponse[AdminCompanyResponse],
    summary="Listar todas as empresas",
)
async def list_companies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[AdminCompanyResponse]:
    """List all companies."""
    query = select(Company)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Company.created_at.desc())
    result = await session.execute(query)
    companies = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=[AdminCompanyResponse.model_validate(c) for c in companies],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.patch(
    "/companies/{company_id}",
    response_model=AdminCompanyResponse,
    summary="Editar empresa",
)
async def update_company(
    company_id: UUID,
    data: AdminCompanyUpdate,
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> AdminCompanyResponse:
    """Edit company details."""
    result = await session.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa não encontrada")

    previous_value = {"name": company.name, "description": company.description, "website": company.website, "is_active": company.is_active}

    if data.name is not None:
        company.name = data.name
    if data.description is not None:
        company.description = data.description
    if data.website is not None:
        company.website = data.website
    if data.is_active is not None:
        company.is_active = data.is_active

    new_value = {"name": company.name, "description": company.description, "website": company.website, "is_active": company.is_active}

    await _create_audit_log(session, admin.id, "update_company", "company", company_id, previous_value, new_value)

    return AdminCompanyResponse.model_validate(company)


# ==============================================================================
# Job Management
# ==============================================================================


@router.get(
    "/jobs",
    response_model=PaginatedResponse[AdminJobResponse],
    summary="Listar todas as vagas",
)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    job_status: str | None = Query(None, alias="status", description="Filtrar por status"),
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[AdminJobResponse]:
    """List all jobs with optional status filter."""
    query = select(Job)

    if job_status is not None:
        query = query.where(Job.status == job_status)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Job.created_at.desc())
    result = await session.execute(query)
    jobs = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=[AdminJobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.patch(
    "/jobs/{job_id}/status",
    response_model=AdminJobResponse,
    summary="Alterar status da vaga",
)
async def update_job_status(
    job_id: UUID,
    data: AdminJobStatusUpdate,
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> AdminJobResponse:
    """Change job status."""
    result = await session.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaga não encontrada")

    previous_value = {"status": job.status.value if hasattr(job.status, 'value') else job.status}
    job.status = data.status
    new_value = {"status": data.status}

    await _create_audit_log(session, admin.id, "update_job_status", "job", job_id, previous_value, new_value)

    return AdminJobResponse.model_validate(job)


# ==============================================================================
# Application Management
# ==============================================================================


@router.get(
    "/applications",
    response_model=PaginatedResponse[AdminApplicationResponse],
    summary="Listar todas as candidaturas",
)
async def list_applications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[AdminApplicationResponse]:
    """List all applications."""
    query = select(Application)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Application.applied_at.desc())
    result = await session.execute(query)
    applications = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=[AdminApplicationResponse.model_validate(a) for a in applications],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ==============================================================================
# Financial Management
# ==============================================================================


@router.get(
    "/financials/transactions",
    response_model=PaginatedResponse[AdminTransactionResponse],
    summary="Listar transações de tokens",
)
async def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[AdminTransactionResponse]:
    """List all token transactions (paginated, max 50 per page)."""
    query = select(TokenTransaction)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(TokenTransaction.created_at.desc())
    result = await session.execute(query)
    transactions = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=[AdminTransactionResponse.model_validate(t) for t in transactions],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/financials/payments",
    response_model=PaginatedResponse[AdminPaymentResponse],
    summary="Listar pagamentos",
)
async def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[AdminPaymentResponse]:
    """List all payments."""
    query = select(Payment)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(Payment.created_at.desc())
    result = await session.execute(query)
    payments = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=[AdminPaymentResponse.model_validate(p) for p in payments],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/financials/revenue",
    response_model=AdminRevenueResponse,
    summary="Receita por período",
)
async def get_revenue(
    start_date: date = Query(..., description="Data inicial"),
    end_date: date = Query(..., description="Data final"),
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> AdminRevenueResponse:
    """Get revenue summary for a given period."""
    query = select(
        func.coalesce(func.sum(Payment.amount), Decimal("0.00")).label("total_revenue"),
        func.count(Payment.id).label("total_transactions"),
    ).where(
        Payment.status == "confirmed",
        func.date(Payment.created_at) >= start_date,
        func.date(Payment.created_at) <= end_date,
    )

    result = await session.execute(query)
    row = result.one()

    return AdminRevenueResponse(
        start_date=start_date,
        end_date=end_date,
        total_revenue=row.total_revenue,
        total_transactions=row.total_transactions,
    )


# ==============================================================================
# Audit Log
# ==============================================================================


@router.get(
    "/audit-logs",
    response_model=PaginatedResponse[AdminAuditLogResponse],
    summary="Listar logs de auditoria",
)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[AdminAuditLogResponse]:
    """List audit logs (paginated, max 100/page, last 365 days)."""
    # Filter to last 365 days
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=365)

    query = select(AuditLog).where(AuditLog.created_at >= cutoff_date)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_query)).scalar_one()

    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size).order_by(AuditLog.created_at.desc())
    result = await session.execute(query)
    logs = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse(
        items=[AdminAuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ==============================================================================
# Metrics and KPIs
# ==============================================================================


@router.get(
    "/metrics/kpis",
    response_model=PlatformKPIsResponse,
    summary="KPIs da plataforma",
)
async def get_platform_kpis(
    period: MetricsPeriod = Query(MetricsPeriod.monthly, description="Período de análise"),
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> PlatformKPIsResponse:
    """Get platform KPIs: vagas publicadas, candidaturas, taxa de contratação, tempo médio."""
    return await metrics_service.get_platform_kpis(session, period)


@router.get(
    "/metrics/financial",
    response_model=FinancialMetricsResponse,
    summary="Métricas financeiras",
)
async def get_financial_metrics(
    period: MetricsPeriod = Query(MetricsPeriod.monthly, description="Período de análise"),
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> FinancialMetricsResponse:
    """Get financial metrics: receita tokens, assinaturas, ticket médio."""
    return await metrics_service.get_financial_metrics(session, period)


@router.get(
    "/metrics/ai",
    response_model=AIMetricsResponse,
    summary="Métricas de IA",
)
async def get_ai_metrics(
    period: MetricsPeriod = Query(MetricsPeriod.monthly, description="Período de análise"),
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> AIMetricsResponse:
    """Get AI metrics: total análises, consumo tokens, média score, utilização por plano."""
    return await metrics_service.get_ai_metrics(session, period)


# ==============================================================================
# CSV Export
# ==============================================================================


@router.get(
    "/export/users",
    summary="Exportar usuários em CSV",
)
async def export_users_csv(
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Export users data as CSV file (max 50,000 records)."""
    return StreamingResponse(
        csv_export_service.export_users_csv(session),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=users_export.csv"},
    )


@router.get(
    "/export/jobs",
    summary="Exportar vagas em CSV",
)
async def export_jobs_csv(
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Export jobs data as CSV file (max 50,000 records)."""
    return StreamingResponse(
        csv_export_service.export_jobs_csv(session),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=jobs_export.csv"},
    )


@router.get(
    "/export/applications",
    summary="Exportar candidaturas em CSV",
)
async def export_applications_csv(
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Export applications data as CSV file (max 50,000 records)."""
    return StreamingResponse(
        csv_export_service.export_applications_csv(session),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=applications_export.csv"},
    )


@router.get(
    "/export/payments",
    summary="Exportar pagamentos em CSV",
)
async def export_payments_csv(
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Export payments data as CSV file (max 50,000 records)."""
    return StreamingResponse(
        csv_export_service.export_payments_csv(session),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=payments_export.csv"},
    )


# ==============================================================================
# Payment Settings
# ==============================================================================


@router.get(
    "/payment-settings",
    summary="Obter configurações de pagamento",
)
async def get_payment_settings(
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Get current payment settings."""
    from sqlalchemy import text
    result = await session.execute(text("SELECT * FROM payment_settings LIMIT 1"))
    row = result.mappings().first()
    if not row:
        return {"exists": False}
    return {
        "exists": True,
        "pix_key_type": row.get("pix_key_type"),
        "pix_key": row.get("pix_key"),
        "pix_beneficiary_name": row.get("pix_beneficiary_name"),
        "gateway_provider": row.get("gateway_provider"),
        "gateway_api_key": "***" if row.get("gateway_api_key") else None,
        "gateway_secret_key": "***" if row.get("gateway_secret_key") else None,
        "gateway_webhook_url": row.get("gateway_webhook_url"),
        "bank_name": row.get("bank_name"),
        "bank_agency": row.get("bank_agency"),
        "bank_account": row.get("bank_account"),
        "bank_account_type": row.get("bank_account_type"),
        "resume_analysis_price": row.get("resume_analysis_price", Decimal("5.00")),
        "job_compatibility_price": row.get("job_compatibility_price", Decimal("5.00")),
        "minimum_wallet_topup": row.get("minimum_wallet_topup", Decimal("1.00")),
        "is_active": row.get("is_active"),
        "updated_at": str(row.get("updated_at")) if row.get("updated_at") else None,
    }


@router.put(
    "/payment-settings",
    summary="Atualizar configurações de pagamento",
)
async def update_payment_settings(
    data: AdminPaymentSettingsUpdate,
    admin: CurrentUser = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    """Create or update payment settings."""
    from sqlalchemy import text

    values = data.model_dump()
    from app.core.secrets import encrypt_secret

    for field in ("gateway_api_key", "gateway_secret_key"):
        if values[field] and values[field] != "***":
            values[field] = encrypt_secret(values[field])

    # Check if exists
    result = await session.execute(text("SELECT id FROM payment_settings LIMIT 1"))
    existing = result.scalar_one_or_none()

    if existing:
        await session.execute(text("""
            UPDATE payment_settings SET
                pix_key_type = :pix_key_type,
                pix_key = :pix_key,
                pix_beneficiary_name = :pix_beneficiary_name,
                gateway_provider = :gateway_provider,
                gateway_api_key = CASE WHEN :gateway_api_key = '***' THEN gateway_api_key ELSE :gateway_api_key END,
                gateway_secret_key = CASE WHEN :gateway_secret_key = '***' THEN gateway_secret_key ELSE :gateway_secret_key END,
                gateway_webhook_url = :gateway_webhook_url,
                bank_name = :bank_name,
                bank_agency = :bank_agency,
                bank_account = :bank_account,
                bank_account_type = :bank_account_type,
                resume_analysis_price = :resume_analysis_price,
                job_compatibility_price = :job_compatibility_price,
                minimum_wallet_topup = :minimum_wallet_topup,
                is_active = :is_active,
                updated_at = now(),
                updated_by = :admin_id
            WHERE id = :id
        """), {
            "id": str(existing),
            **values,
            "admin_id": str(admin.id),
        })
    else:
        await session.execute(text("""
            INSERT INTO payment_settings (pix_key_type, pix_key, pix_beneficiary_name, gateway_provider, gateway_api_key, gateway_secret_key, gateway_webhook_url, bank_name, bank_agency, bank_account, bank_account_type, resume_analysis_price, job_compatibility_price, minimum_wallet_topup, is_active, updated_by)
            VALUES (:pix_key_type, :pix_key, :pix_beneficiary_name, :gateway_provider, :gateway_api_key, :gateway_secret_key, :gateway_webhook_url, :bank_name, :bank_agency, :bank_account, :bank_account_type, :resume_analysis_price, :job_compatibility_price, :minimum_wallet_topup, :is_active, :admin_id)
        """), {
            **values,
            "admin_id": str(admin.id),
        })

    await session.commit()
    return {"message": "Configurações de pagamento atualizadas com sucesso"}
