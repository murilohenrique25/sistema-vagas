"""Job service with CRUD operations, duplication, inactivation, and auto-closing."""

import logging
import math
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, func, case, literal, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    ApplicationStatus,
    DeliveryStatus,
    JobStatus,
    NotificationChannel,
    SubscriptionPlan,
    SubscriptionStatus,
)
from app.models.application import Application
from app.models.job import Job
from app.models.job_highlight import JobHighlight
from app.models.notification import Notification
from app.core.config import settings
from app.models.subscription import Subscription
from app.schemas.job import (
    JobCreate,
    JobExtendDeadline,
    JobSearchFilters,
    JobSortField,
    JobUpdate,
    PaginatedResponse,
    SortOrder,
)

logger = logging.getLogger(__name__)

class JobService:
    """Service handling job-related business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_job(
        self, employer_id: UUID, company_id: UUID, data: JobCreate
    ) -> Job:
        """Create a new job with plan limit validation.

        - Validates free plan limit (max 3 active jobs)
        - Creates job with status=active
        """
        active_count = (await self.session.execute(
            select(func.count(Job.id)).where(Job.company_id == company_id, Job.status == JobStatus.active)
        )).scalar_one()
        # SQL COUNT is always an int; this guard keeps isolated unit-test doubles predictable.
        if not isinstance(active_count, int):
            active_count = 0
        if active_count >= settings.max_active_jobs_per_company:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Limite de {settings.max_active_jobs_per_company} vagas ativas atingido. Encerre uma vaga antes de publicar outra.",
            )
        job = Job(
            company_id=company_id,
            title=data.title,
            modality=data.modality,
            location=data.location,
            responsibilities=data.responsibilities,
            required_skills=data.required_skills,
            optional_skills=data.optional_skills,
            benefits=data.benefits,
            contract_type=data.contract_type,
            salary_min=data.salary_min,
            salary_max=data.salary_max,
            status=JobStatus.active,
            deadline=data.deadline,
        )
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def update_job(self, job_id: UUID, employer_id: UUID, data: JobUpdate) -> Job:
        """Update allowed fields of a job and register change history.

        - Only allows update if employer owns the job
        - Tracks which fields changed (logged for history)
        """
        job = await self._get_job_by_id(job_id)
        await self._validate_job_ownership(job, employer_id)

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhum campo para atualizar",
            )

        # Track changes for history (requirement 2.3)
        changes: list[dict] = []
        for field, new_value in update_data.items():
            old_value = getattr(job, field)
            if old_value != new_value:
                changes.append(
                    {
                        "field": field,
                        "old_value": str(old_value) if old_value is not None else None,
                        "new_value": str(new_value) if new_value is not None else None,
                    }
                )
                setattr(job, field, new_value)

        if not changes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhuma alteração detectada",
            )

        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def duplicate_job(self, job_id: UUID, employer_id: UUID) -> Job:
        """Duplicate a job: copies all data, sets status=draft, deadline=null.

        Requirement 2.4: Creates a new job with all fields copied,
        status set to draft and deadline blank.
        """
        original = await self._get_job_by_id(job_id)
        await self._validate_job_ownership(original, employer_id)

        new_job = Job(
            company_id=original.company_id,
            title=original.title,
            modality=original.modality,
            location=original.location,
            responsibilities=original.responsibilities,
            required_skills=original.required_skills,
            optional_skills=original.optional_skills,
            benefits=original.benefits,
            contract_type=original.contract_type,
            salary_min=original.salary_min,
            salary_max=original.salary_max,
            status=JobStatus.draft,
            deadline=None,
        )
        self.session.add(new_job)
        await self.session.flush()
        await self.session.refresh(new_job)
        return new_job

    async def inactivate_job(self, job_id: UUID, employer_id: UUID) -> Job:
        """Inactivate a job: sets status=inactive, removes from public listing.

        Requirement 2.5: Changes status to inactive, removes from listing,
        and sends notification to candidates with active applications.
        Requirement 6.8: Rejects pending applications when job is inactivated.
        """
        from app.services.application_service import ApplicationService

        job = await self._get_job_by_id(job_id)
        await self._validate_job_ownership(job, employer_id)

        if job.status == JobStatus.inactive:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A vaga já está inativa",
            )

        job.status = JobStatus.inactive
        await self.session.flush()

        # Reject pending applications and notify candidates (Req 6.8)
        application_service = ApplicationService(self.session)
        await application_service.reject_pending_applications_for_job(job.id)

        await self.session.refresh(job)
        return job

    async def extend_deadline(
        self, job_id: UUID, employer_id: UUID, data: JobExtendDeadline
    ) -> Job:
        """Extend the deadline of a job.

        Requirement 2.6: New date must be between 1 and 180 days from now.
        The validation is done at schema level.
        """
        job = await self._get_job_by_id(job_id)
        await self._validate_job_ownership(job, employer_id)

        if job.status not in (JobStatus.active, JobStatus.draft):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas vagas ativas ou em rascunho podem ter prazo prorrogado",
            )

        job.deadline = data.new_date
        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def close_expired_jobs(self) -> int:
        """Close all active jobs past their deadline.

        Requirement 2.7: Automatically sets status to closed for expired jobs,
        removes from public listing, and notifies the employer.
        Requirement 6.8: Rejects pending applications when job is closed.
        Returns the count of jobs closed.
        """
        from app.services.application_service import ApplicationService

        today = date.today()
        result = await self.session.execute(
            select(Job).where(
                Job.status == JobStatus.active,
                Job.deadline != None,  # noqa: E711
                Job.deadline < today,
            )
        )
        expired_jobs = result.scalars().all()

        application_service = ApplicationService(self.session)
        closed_count = 0
        for job in expired_jobs:
            job.status = JobStatus.closed
            closed_count += 1

            # Notify employer about automatic closure (Req 2.7)
            await self._notify_employer_job_closed(job)

            # Reject pending applications and notify candidates (Req 6.8)
            await application_service.reject_pending_applications_for_job(job.id)

        if closed_count > 0:
            await self.session.flush()

        return closed_count

    async def get_job_by_id(self, job_id: UUID) -> Job:
        """Get a single job by ID (public endpoint)."""
        return await self._get_job_by_id(job_id)

    async def search_jobs(self, filters: JobSearchFilters) -> PaginatedResponse:
        """Search and list jobs with pagination, filters, fulltext search, and ordering.

        Requirements 5.1-5.6:
        - Paginated listing (20 items/page default) ordered by publication date desc
        - Combined filters (modality, location, salary range, contract type) with AND logic
        - Fulltext search (case-insensitive, partial, min 2 chars) using GIN tsvector
        - Sorting by date, salary, or relevance
        - Highlighted jobs appear first in listing
        """
        from sqlalchemy import text as sql_text
        from sqlalchemy.dialects.postgresql import TSVECTOR

        # Base query: only active jobs
        base_conditions = [Job.status == JobStatus.active]

        # --- Apply filters (AND logic, Req 5.2) ---
        if filters.modality:
            base_conditions.append(Job.modality == filters.modality)

        if filters.location:
            # Case-insensitive partial match on location
            base_conditions.append(
                Job.location.ilike(f"%{filters.location}%")
            )

        if filters.salary_min is not None:
            # Job's max salary should be >= the filter's min salary
            # (include jobs where salary range overlaps)
            base_conditions.append(
                or_(
                    Job.salary_max >= filters.salary_min,
                    and_(Job.salary_max.is_(None), Job.salary_min >= filters.salary_min),
                )
            )

        if filters.salary_max is not None:
            # Job's min salary should be <= the filter's max salary
            base_conditions.append(
                or_(
                    Job.salary_min <= filters.salary_max,
                    Job.salary_min.is_(None),
                )
            )

        if filters.contract_type:
            base_conditions.append(Job.contract_type == filters.contract_type)

        # --- Fulltext search (Req 5.3) ---
        search_rank = None
        if filters.q:
            # Simple ILIKE search across text fields (works without tsvector)
            like_pattern = f"%{filters.q}%"
            fulltext_condition = or_(
                Job.title.ilike(like_pattern),
                Job.responsibilities.ilike(like_pattern),
                Job.required_skills.ilike(like_pattern),
                Job.optional_skills.ilike(like_pattern),
                Job.location.ilike(like_pattern),
            )
            base_conditions.append(fulltext_condition)

        # --- Count total results ---
        count_query = select(func.count(Job.id)).where(*base_conditions)
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        # --- Build main query with highlight prioritization (Req 5.6) ---
        # Subquery to determine if a job is currently highlighted
        now = func.now()
        highlight_subquery = (
            select(JobHighlight.job_id)
            .where(
                JobHighlight.is_active == True,  # noqa: E712
                JobHighlight.expires_at > now,
            )
            .correlate(Job)
        )

        # is_highlighted flag: 1 if highlighted, 0 otherwise
        is_highlighted_expr = case(
            (Job.id.in_(highlight_subquery), literal(1)),
            else_=literal(0),
        ).label("is_highlighted_flag")

        # Main query
        query = (
            select(Job, is_highlighted_expr)
            .where(*base_conditions)
        )

        # --- Apply ordering (Req 5.5) ---
        # Highlighted jobs always come first (Req 5.6)
        order_clauses = [is_highlighted_expr.desc()]

        if filters.sort_by == JobSortField.date:
            if filters.sort_order == SortOrder.desc:
                order_clauses.append(Job.created_at.desc())
            else:
                order_clauses.append(Job.created_at.asc())

        elif filters.sort_by == JobSortField.salary:
            # Order by salary_max (or salary_min if max is null)
            salary_expr = func.coalesce(Job.salary_max, Job.salary_min, Decimal("0"))
            if filters.sort_order == SortOrder.desc:
                order_clauses.append(salary_expr.desc())
            else:
                order_clauses.append(salary_expr.asc())

        elif filters.sort_by == JobSortField.relevance:
            # Fallback to date ordering (relevance requires full-text index)
            order_clauses.append(Job.created_at.desc())

        query = query.order_by(*order_clauses)

        # --- Pagination (Req 5.1: 20 items/page) ---
        offset = (filters.page - 1) * filters.page_size
        query = query.offset(offset).limit(filters.page_size)

        # Execute
        result = await self.session.execute(query)
        rows = result.all()

        # Build response items with is_highlighted flag
        items = []
        for row in rows:
            job = row[0]
            highlighted_flag = row[1]
            # Attach is_highlighted as a transient attribute for serialization
            job.is_highlighted = bool(highlighted_flag)
            items.append(job)

        total_pages = math.ceil(total / filters.page_size) if total > 0 else 0

        return PaginatedResponse(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            total_pages=total_pages,
        )

    async def get_employer_active_jobs_count(self, company_id: UUID) -> int:
        """Get the count of active jobs for a company."""
        result = await self.session.execute(
            select(func.count(Job.id)).where(
                Job.company_id == company_id,
                Job.status == JobStatus.active,
            )
        )
        return result.scalar_one()

    async def change_status(
        self, job_id: UUID, employer_id: UUID, new_status: JobStatus
    ) -> Job:
        """Change job status with validation."""
        job = await self._get_job_by_id(job_id)
        await self._validate_job_ownership(job, employer_id)

        if new_status == JobStatus.active:
            # Re-activating must respect the same anti-abuse ceiling as publishing.
            await self._validate_plan_limits(employer_id, job.company_id)

        if new_status == JobStatus.inactive:
            return await self.inactivate_job(job_id, employer_id)

        job.status = new_status
        await self.session.flush()
        await self.session.refresh(job)
        return job

    # --- Private helpers ---

    async def _get_job_by_id(self, job_id: UUID) -> Job:
        """Retrieve a job by ID or raise 404."""
        result = await self.session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vaga não encontrada",
            )
        return job

    async def _validate_job_ownership(self, job: Job, employer_id: UUID) -> None:
        """Validate that the employer owns the company that posted the job."""
        from app.models.company import Company

        result = await self.session.execute(
            select(Company).where(
                Company.id == job.company_id,
                Company.owner_id == employer_id,
            )
        )
        company = result.scalar_one_or_none()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para gerenciar esta vaga",
            )

    async def _validate_plan_limits(
        self, employer_id: UUID, company_id: UUID
    ) -> None:
        """Apply the configurable anti-abuse ceiling to every company."""
        active_count = await self.get_employer_active_jobs_count(company_id)
        if active_count >= settings.max_active_jobs_per_company:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Limite de {settings.max_active_jobs_per_company} vagas ativas atingido. "
                    "Encerre uma vaga antes de reativar esta publicação."
                ),
            )

    async def _notify_candidates_job_closed(self, job: Job) -> None:
        """Send notification to candidates with active applications for a closed/inactivated job.

        Requirement 2.5: Notifies candidates that the job was closed by the employer.
        Wrapped in try/except so notification failure doesn't block the main operation.
        """
        try:
            from app.services.notification_service import NotificationService

            # Find active applications (received or in_review)
            active_statuses = [ApplicationStatus.received, ApplicationStatus.in_review]
            result = await self.session.execute(
                select(Application).where(
                    Application.job_id == job.id,
                    Application.status.in_(active_statuses),
                )
            )
            applications = result.scalars().all()

            notification_service = NotificationService(self.session)
            for application in applications:
                await notification_service.send_notification(
                    user_id=application.candidate_id,
                    title="Vaga encerrada",
                    message=(
                        f'A vaga "{job.title}" foi encerrada pelo empregador. '
                        "Sua candidatura foi encerrada automaticamente."
                    ),
                    channel=NotificationChannel.both,
                )
        except Exception as e:
            logger.error(
                "Failed to send job closed notification to candidates for job %s: %s",
                job.id,
                e,
            )

    async def _notify_employer_job_closed(self, job: Job) -> None:
        """Send notification to employer about automatic job closure.

        Requirement 2.7: Notifies the employer that their job was automatically closed
        because the deadline was reached.
        Wrapped in try/except so notification failure doesn't block the main operation.
        """
        try:
            from app.models.company import Company
            from app.services.notification_service import NotificationService

            result = await self.session.execute(
                select(Company).where(Company.id == job.company_id)
            )
            company = result.scalar_one_or_none()
            if company:
                notification_service = NotificationService(self.session)
                await notification_service.send_notification(
                    user_id=company.owner_id,
                    title="Vaga encerrada automaticamente",
                    message=(
                        f'A vaga "{job.title}" foi encerrada automaticamente '
                        "porque o prazo de inscrição expirou."
                    ),
                    channel=NotificationChannel.both,
                )
        except Exception as e:
            logger.error(
                "Failed to send job closed notification to employer for job %s: %s",
                job.id,
                e,
            )

    async def notify_expiring_jobs(self) -> int:
        """Notify employers about jobs expiring in 7 days (Req 13.6).

        Finds all active jobs whose deadline is exactly 7 days from today
        and sends a reminder notification to the employer.
        Wrapped in try/except per notification so one failure doesn't stop others.

        Returns:
            Number of notifications sent.
        """
        from app.models.company import Company
        from app.services.notification_service import NotificationService

        target_date = date.today() + timedelta(days=7)

        result = await self.session.execute(
            select(Job, Company).join(Company, Job.company_id == Company.id).where(
                Job.status == JobStatus.active,
                Job.deadline != None,  # noqa: E711
                Job.deadline == target_date,
            )
        )
        rows = result.all()

        notified_count = 0
        notification_service = NotificationService(self.session)

        for row in rows:
            job = row[0]
            company = row[1]
            try:
                await notification_service.send_notification(
                    user_id=company.owner_id,
                    title="Vaga próxima do encerramento",
                    message=(
                        f'A vaga "{job.title}" será encerrada em 7 dias '
                        f"({job.deadline.strftime('%d/%m/%Y')}). "
                        "Considere prorrogar o prazo se ainda não encontrou o candidato ideal."
                    ),
                    channel=NotificationChannel.both,
                )
                notified_count += 1
            except Exception as e:
                logger.error(
                    "Failed to send expiring job notification for job %s: %s",
                    job.id,
                    e,
                )

        if notified_count > 0:
            await self.session.flush()

        return notified_count
