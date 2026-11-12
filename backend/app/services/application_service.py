"""Application service with candidature logic, validation, and status management."""

import logging
import math
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationStatusHistory
from app.models.enums import (
    ApplicationStatus,
    DeliveryStatus,
    JobStatus,
    NotificationChannel,
)
from app.models.job import Job
from app.models.notification import Notification
from app.models.resume import Resume
from app.schemas.application import (
    ApplicationListResponse,
    ApplicationResponse,
    PaginatedApplicationsResponse,
)

logger = logging.getLogger(__name__)

# Final statuses that cannot be cancelled
FINAL_STATUSES = {ApplicationStatus.hired, ApplicationStatus.rejected}

# Statuses affected when a job is closed/inactivated
PENDING_STATUSES = {ApplicationStatus.received, ApplicationStatus.in_review}

# Default page size for application listing
DEFAULT_PAGE_SIZE = 20

# Valid progressive transitions in the candidature workflow (Req 7.1)
# Recebida → Em análise → Entrevista → Teste técnico → Proposta → Contratado
PROGRESSIVE_TRANSITIONS: dict[ApplicationStatus, ApplicationStatus] = {
    ApplicationStatus.received: ApplicationStatus.in_review,
    ApplicationStatus.in_review: ApplicationStatus.interview,
    ApplicationStatus.interview: ApplicationStatus.technical_test,
    ApplicationStatus.technical_test: ApplicationStatus.proposal,
    ApplicationStatus.proposal: ApplicationStatus.hired,
}

# Statuses from which transition to "Reprovado" is NOT allowed
CANNOT_REJECT_FROM = {ApplicationStatus.hired, ApplicationStatus.cancelled}

# Statuses from which transition to "Cancelado" is NOT allowed
CANNOT_CANCEL_FROM = {ApplicationStatus.hired}


class ApplicationService:
    """Service handling application-related business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def apply(self, candidate_id: UUID, job_id: UUID) -> Application:
        """Register a new application (candidate applies to a job).

        Validates:
        - Candidate has a resume (Req 6.6)
        - Job exists and is active (Req 6.1)
        - No duplicate application for same job (Req 6.5)

        Creates application with status "Recebida" and notifies the employer.
        """
        # 1. Validate candidate has a resume
        resume = await self._get_candidate_resume(candidate_id)
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Você precisa ter um currículo cadastrado para se candidatar",
            )

        # 2. Validate job exists and is active
        job = await self._get_job(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vaga não encontrada",
            )
        if job.status != JobStatus.active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não é possível se candidatar a uma vaga que não está ativa",
            )

        # 3. Check for duplicate application
        existing = await self._get_existing_application(candidate_id, job_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Você já possui uma candidatura para esta vaga",
            )

        # 4. Create application with status "received"
        application = Application(
            job_id=job_id,
            candidate_id=candidate_id,
            status=ApplicationStatus.received,
        )
        self.session.add(application)
        await self.session.flush()

        # 5. Record initial status in history
        history = ApplicationStatusHistory(
            application_id=application.id,
            previous_status=None,
            new_status=ApplicationStatus.received,
            changed_by=candidate_id,
        )
        self.session.add(history)

        # 6. Notify employer (Req 6.1)
        await self._notify_employer_new_application(job, candidate_id)

        await self.session.flush()
        await self.session.refresh(application)
        return application

    async def get_candidate_applications(
        self, candidate_id: UUID, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE
    ) -> PaginatedApplicationsResponse:
        """List paginated applications for a candidate (Req 6.2).

        Returns applications ordered by applied_at descending, 20 items/page,
        with job title and company name.
        """
        from app.models.company import Company

        # Count total
        count_query = select(func.count(Application.id)).where(
            Application.candidate_id == candidate_id
        )
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        # Fetch paginated applications with job and company info
        offset = (page - 1) * page_size
        query = (
            select(Application, Job.title, Company.name)
            .join(Job, Application.job_id == Job.id)
            .join(Company, Job.company_id == Company.id)
            .where(Application.candidate_id == candidate_id)
            .order_by(Application.applied_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(query)
        rows = result.all()

        items = []
        for row in rows:
            application = row[0]
            job_title = row[1]
            company_name = row[2]
            items.append(
                ApplicationListResponse(
                    id=application.id,
                    job_id=application.job_id,
                    candidate_id=application.candidate_id,
                    status=application.status,
                    applied_at=application.applied_at,
                    updated_at=application.updated_at,
                    job_title=job_title,
                    company_name=company_name,
                )
            )

        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return PaginatedApplicationsResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def change_status(
        self, application_id: UUID, new_status: ApplicationStatus, changed_by: UUID
    ) -> Application:
        """Change application status following the state machine rules (Req 7.1, 7.2, 7.3, 7.5, 7.6).

        Valid transitions:
        - Progressive: Recebida → Em análise → Entrevista → Teste técnico → Proposta → Contratado
        - Rejected: from any status except Contratado and Cancelado
        - Cancelled: from any status except Contratado

        Records transition history with UTC timestamp, previous/new status, and user ID.
        Calculates hiring rate when moving to "Contratado".
        """
        application = await self._get_application(application_id)
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidatura não encontrada",
            )

        current_status = application.status

        # Validate the transition
        if not self._is_valid_transition(current_status, new_status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Transição de status inválida: "
                    f"não é possível mudar de '{current_status.value}' para '{new_status.value}'"
                ),
            )

        # Apply the transition
        previous_status = application.status
        application.status = new_status
        await self.session.flush()

        # Record history (Req 7.2)
        history = ApplicationStatusHistory(
            application_id=application.id,
            previous_status=previous_status,
            new_status=new_status,
            changed_by=changed_by,
        )
        self.session.add(history)

        # Send notification on status change (Req 7.4, 7.5, 7.6)
        await self._notify_candidate_status_change(application, previous_status, new_status)

        # Calculate hiring rate when moving to "Contratado" (Req 7.5)
        hiring_rate = None
        if new_status == ApplicationStatus.hired:
            hiring_rate = await self._calculate_hiring_rate(application.job_id)

        await self.session.flush()
        await self.session.refresh(application)
        return application

    def _is_valid_transition(
        self, current_status: ApplicationStatus, new_status: ApplicationStatus
    ) -> bool:
        """Check if a status transition is valid per the state machine rules (Req 7.1).

        Rules:
        - Progressive: each status can only move to its immediate successor
        - Rejected: allowed from any status except Contratado and Cancelado
        - Cancelled: allowed from any status except Contratado
        """
        # Transition to "rejected"
        if new_status == ApplicationStatus.rejected:
            return current_status not in CANNOT_REJECT_FROM

        # Transition to "cancelled"
        if new_status == ApplicationStatus.cancelled:
            return current_status not in CANNOT_CANCEL_FROM

        # Progressive transition
        expected_next = PROGRESSIVE_TRANSITIONS.get(current_status)
        return expected_next == new_status

    async def _calculate_hiring_rate(self, job_id: UUID) -> float:
        """Calculate hiring rate for a job (Req 7.5).

        hiring_rate = hired_count / total_applications
        """
        # Total applications for the job
        total_result = await self.session.execute(
            select(func.count(Application.id)).where(Application.job_id == job_id)
        )
        total = total_result.scalar_one()

        # Hired applications for the job
        hired_result = await self.session.execute(
            select(func.count(Application.id)).where(
                Application.job_id == job_id,
                Application.status == ApplicationStatus.hired,
            )
        )
        hired = hired_result.scalar_one()

        if total == 0:
            return 0.0

        return hired / total

    async def _notify_candidate_status_change(
        self,
        application: Application,
        previous_status: ApplicationStatus,
        new_status: ApplicationStatus,
    ) -> None:
        """Send notification to candidate on status change (Req 13.2, 13.3, 13.4).

        - Req 13.2: Notify on any status change
        - Req 13.3: Special interview invitation notification
        - Req 13.4: Approval/rejection notification

        Uses NotificationService for proper queuing and retry.
        Wrapped in try/except so notification failure doesn't block the main operation.
        """
        try:
            from app.services.notification_service import NotificationService

            job = await self._get_job(application.job_id)
            job_title = job.title if job else "Vaga"

            if new_status == ApplicationStatus.interview:
                # Req 13.3: Interview invitation
                title = "Convite para entrevista"
                message = (
                    f'Parabéns! Você foi convidado para entrevista na vaga "{job_title}". '
                    "Aguarde informações adicionais do empregador sobre data, horário e local."
                )
            elif new_status == ApplicationStatus.hired:
                # Req 13.4: Approval notification
                title = "Candidatura aprovada"
                message = f'Parabéns! Você foi contratado para a vaga "{job_title}".'
            elif new_status == ApplicationStatus.rejected:
                # Req 13.4: Rejection notification
                title = "Candidatura reprovada"
                message = f'Sua candidatura para a vaga "{job_title}" foi reprovada.'
            else:
                # Req 13.2: General status change
                status_labels = {
                    "received": "Recebida",
                    "in_review": "Em Análise",
                    "interview": "Entrevista",
                    "technical_test": "Teste Técnico",
                    "proposal": "Proposta",
                    "hired": "Contratado",
                    "rejected": "Reprovado",
                    "cancelled": "Cancelado",
                }
                status_label = status_labels.get(new_status.value, new_status.value)
                title = "Status da candidatura atualizado"
                message = (
                    f'O status da sua candidatura para a vaga "{job_title}" '
                    f'foi alterado para "{status_label}".'
                )

            notification_service = NotificationService(self.session)
            await notification_service.send_notification(
                user_id=application.candidate_id,
                title=title,
                message=message,
                channel=NotificationChannel.both,
            )
        except Exception as e:
            logger.error(
                "Failed to send status change notification for application %s: %s",
                application.id,
                e,
            )

    async def get_job_applications(
        self, job_id: UUID, employer_id: UUID, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE
    ) -> PaginatedApplicationsResponse:
        """List applications for a specific job (employer view).

        Validates that the employer owns the company that posted the job.
        Returns paginated applications ordered by applied_at descending.
        """
        from app.models.company import Company

        # Get the job to validate it exists
        job = await self._get_job(job_id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vaga não encontrada",
            )

        # Validate ownership: employer must own the company that posted the job
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
                detail="Você não tem permissão para visualizar as candidaturas desta vaga",
            )

        # Count total applications for this job
        count_result = await self.session.execute(
            select(func.count(Application.id)).where(Application.job_id == job_id)
        )
        total = count_result.scalar_one()

        # Fetch paginated applications
        offset = (page - 1) * page_size
        from app.models.user import User

        query = (
            select(Application, User.name)
            .join(User, Application.candidate_id == User.id)
            .where(Application.job_id == job_id)
            .order_by(Application.applied_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        rows_result = await self.session.execute(query)
        rows = rows_result.all()

        items = []
        for row in rows:
            application = row[0]
            candidate_name = row[1]
            items.append(
                ApplicationListResponse(
                    id=application.id,
                    job_id=application.job_id,
                    candidate_id=application.candidate_id,
                    status=application.status,
                    applied_at=application.applied_at,
                    updated_at=application.updated_at,
                    job_title=job.title,
                    company_name=company.name,
                    candidate_name=candidate_name,
                )
            )

        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return PaginatedApplicationsResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def cancel(self, application_id: UUID, candidate_id: UUID) -> Application:
        """Cancel an application by the candidate (Req 6.4, 6.7).

        Validates:
        - Application exists and belongs to the candidate
        - Application is not in a final status (hired or rejected)
        """
        application = await self._get_application(application_id)
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidatura não encontrada",
            )

        # Validate ownership
        if application.candidate_id != candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para cancelar esta candidatura",
            )

        # Validate not in final status (Req 6.7)
        if application.status in FINAL_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Candidaturas com status final (Contratado ou Reprovado) não podem ser canceladas",
            )

        # Already cancelled
        if application.status == ApplicationStatus.cancelled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta candidatura já está cancelada",
            )

        # Perform cancellation
        previous_status = application.status
        application.status = ApplicationStatus.cancelled
        await self.session.flush()

        # Record status change in history
        history = ApplicationStatusHistory(
            application_id=application.id,
            previous_status=previous_status,
            new_status=ApplicationStatus.cancelled,
            changed_by=candidate_id,
        )
        self.session.add(history)

        await self.session.flush()
        await self.session.refresh(application)
        return application

    async def reject_pending_applications_for_job(self, job_id: UUID) -> int:
        """Reject all pending applications when a job is closed/inactivated (Req 6.8).

        Changes status to "rejected" for applications with status "received" or "in_review",
        and sends notifications to affected candidates.

        Returns the count of applications rejected.
        """
        result = await self.session.execute(
            select(Application).where(
                Application.job_id == job_id,
                Application.status.in_(PENDING_STATUSES),
            )
        )
        applications = result.scalars().all()

        if not applications:
            return 0

        # Get job info for notification message
        job = await self._get_job(job_id)

        rejected_count = 0
        for application in applications:
            previous_status = application.status
            application.status = ApplicationStatus.rejected
            rejected_count += 1

            # Record status change in history
            history = ApplicationStatusHistory(
                application_id=application.id,
                previous_status=previous_status,
                new_status=ApplicationStatus.rejected,
                changed_by=application.candidate_id,  # System-initiated
            )
            self.session.add(history)

            # Notify candidate (Req 6.8) - wrapped in try/except
            if job:
                try:
                    from app.services.notification_service import NotificationService

                    notification_service = NotificationService(self.session)
                    await notification_service.send_notification(
                        user_id=application.candidate_id,
                        title="Candidatura encerrada",
                        message=(
                            f'A vaga "{job.title}" foi encerrada. '
                            "Sua candidatura foi automaticamente marcada como reprovada."
                        ),
                        channel=NotificationChannel.both,
                    )
                except Exception as e:
                    logger.error(
                        "Failed to send job closure notification to candidate %s: %s",
                        application.candidate_id,
                        e,
                    )

        await self.session.flush()

        return rejected_count

    # --- Private helpers ---

    async def _get_candidate_resume(self, candidate_id: UUID) -> Resume | None:
        """Check if candidate has a resume."""
        result = await self.session.execute(
            select(Resume).where(Resume.user_id == candidate_id)
        )
        return result.scalar_one_or_none()

    async def _get_job(self, job_id: UUID) -> Job | None:
        """Get a job by ID."""
        result = await self.session.execute(
            select(Job).where(Job.id == job_id)
        )
        return result.scalar_one_or_none()

    async def _get_existing_application(
        self, candidate_id: UUID, job_id: UUID
    ) -> Application | None:
        """Check if candidate already has an application for this job."""
        result = await self.session.execute(
            select(Application).where(
                Application.candidate_id == candidate_id,
                Application.job_id == job_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_application(self, application_id: UUID) -> Application | None:
        """Get an application by ID."""
        result = await self.session.execute(
            select(Application).where(Application.id == application_id)
        )
        return result.scalar_one_or_none()

    async def _notify_employer_new_application(
        self, job: Job, candidate_id: UUID
    ) -> None:
        """Send notification to employer when a new application is received (Req 13.1).

        Requirement: Notification sent within 5 minutes of application.
        Uses NotificationService for proper queuing and retry.
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
                    title="Nova candidatura recebida",
                    message=(
                        f'Uma nova candidatura foi recebida para a vaga "{job.title}".'
                    ),
                    channel=NotificationChannel.both,
                )
        except Exception as e:
            logger.error(
                "Failed to send new application notification for job %s: %s",
                job.id,
                e,
            )
