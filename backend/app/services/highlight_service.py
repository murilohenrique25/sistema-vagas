"""Highlight service: activate, expire, list, and check highlights.

Implements requirements 12.1 through 12.4:
- 12.1: Activate highlight (token debit or Enterprise included), 7-day duration, max 20 simultaneous
- 12.2: Reject if no tokens and no Enterprise plan
- 12.3: Auto-expire after 7 days with notification
- 12.4: Visual indicator (is_active flag for frontend differentiation)
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    DeliveryStatus,
    JobStatus,
    NotificationChannel,
    SubscriptionPlan,
    SubscriptionStatus,
)
from app.models.job import Job
from app.models.job_highlight import JobHighlight
from app.models.company import Company
from app.models.notification import Notification
from app.models.subscription import Subscription
from app.services.token_service import TokenService

# Constants
HIGHLIGHT_DURATION_DAYS = 7
MAX_SIMULTANEOUS_HIGHLIGHTS = 20
HIGHLIGHT_TOKEN_COST = 1  # 1 token de destaque por ativação


class HighlightService:
    """Service handling job highlight business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def activate_highlight(self, user_id: UUID, job_id: UUID) -> JobHighlight:
        """Activate a 7-day highlight on a job (Req 12.1, 12.2).

        Validates:
        - Job exists and belongs to user
        - Job is active
        - Max 20 simultaneous highlighted jobs globally
        - User has Enterprise plan (free highlight) or tokens available
        """
        # Validate job exists and belongs to user
        job = await self._get_job_for_user(user_id, job_id)

        # Validate job is active
        if job.status != JobStatus.active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas vagas ativas podem ser destacadas.",
            )

        # Check if job already has an active highlight
        existing_highlight = await self._get_active_highlight_for_job(job_id)
        if existing_highlight:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta vaga já possui um destaque ativo.",
            )

        # Check global limit of 20 simultaneous highlights (Req 12.1)
        active_count = await self._count_active_highlights()
        if active_count >= MAX_SIMULTANEOUS_HIGHLIGHTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Limite de {MAX_SIMULTANEOUS_HIGHLIGHTS} vagas em destaque "
                    f"simultâneas atingido. Tente novamente mais tarde."
                ),
            )

        # Check if user has Enterprise plan (highlights included)
        is_enterprise = await self._is_enterprise_user(user_id)

        if not is_enterprise:
            # Debit token for highlight (Req 12.1)
            token_service = TokenService(self.session)
            await token_service.debit(
                user_id=user_id,
                amount=HIGHLIGHT_TOKEN_COST,
                reason="Destaque de vaga",
                reference_id=job_id,
            )

        # Create highlight with 7-day duration
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=HIGHLIGHT_DURATION_DAYS)

        highlight = JobHighlight(
            job_id=job_id,
            activated_at=now,
            expires_at=expires_at,
            is_active=True,
        )
        self.session.add(highlight)
        await self.session.flush()
        await self.session.refresh(highlight)

        return highlight

    async def deactivate_highlight(self, user_id: UUID, job_id: UUID) -> None:
        """Deactivate a highlight early (manual removal by employer)."""
        # Validate job belongs to user
        await self._get_job_for_user(user_id, job_id)

        highlight = await self._get_active_highlight_for_job(job_id)
        if not highlight:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nenhum destaque ativo encontrado para esta vaga.",
            )

        highlight.is_active = False
        await self.session.flush()

    async def expire_highlights(self) -> int:
        """Expire all highlights past their 7-day duration (Req 12.3).

        Returns the number of expired highlights.
        Sends notification to employer for each expired highlight.
        """
        now = datetime.now(timezone.utc)

        # Find active highlights that have expired
        result = await self.session.execute(
            select(JobHighlight).where(
                JobHighlight.is_active == True,  # noqa: E712
                JobHighlight.expires_at <= now,
            )
        )
        expired_highlights = result.scalars().all()

        for highlight in expired_highlights:
            highlight.is_active = False

            # Get job and company to find employer for notification
            job_result = await self.session.execute(
                select(Job).where(Job.id == highlight.job_id)
            )
            job = job_result.scalar_one_or_none()

            if job:
                company_result = await self.session.execute(
                    select(Company).where(Company.id == job.company_id)
                )
                company = company_result.scalar_one_or_none()

                if company:
                    # Send notification to employer (Req 12.3)
                    notification = Notification(
                        user_id=company.owner_id,
                        title="Destaque de vaga expirado",
                        message=(
                            f"O destaque da vaga '{job.title}' expirou após 7 dias. "
                            f"A vaga retornou ao posicionamento padrão na listagem."
                        ),
                        channel=NotificationChannel.both,
                        delivery_status=DeliveryStatus.pending,
                    )
                    self.session.add(notification)

        await self.session.flush()
        return len(expired_highlights)

    async def get_active_highlights(self) -> list[JobHighlight]:
        """Return all currently active highlighted jobs."""
        result = await self.session.execute(
            select(JobHighlight)
            .where(JobHighlight.is_active == True)  # noqa: E712
            .order_by(JobHighlight.activated_at.desc())
        )
        return list(result.scalars().all())

    async def is_highlighted(self, job_id: UUID) -> bool:
        """Check if a specific job currently has an active highlight."""
        highlight = await self._get_active_highlight_for_job(job_id)
        return highlight is not None

    # --- Private helpers ---

    async def _get_job_for_user(self, user_id: UUID, job_id: UUID) -> Job:
        """Get a job and validate it belongs to the given user (via company)."""
        result = await self.session.execute(
            select(Job).where(Job.id == job_id)
        )
        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vaga não encontrada.",
            )

        # Check that the job's company belongs to the user
        company_result = await self.session.execute(
            select(Company).where(
                Company.id == job.company_id,
                Company.owner_id == user_id,
            )
        )
        company = company_result.scalar_one_or_none()

        if not company:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para gerenciar esta vaga.",
            )

        return job

    async def _get_active_highlight_for_job(self, job_id: UUID) -> JobHighlight | None:
        """Get the active highlight for a specific job, if any."""
        result = await self.session.execute(
            select(JobHighlight).where(
                JobHighlight.job_id == job_id,
                JobHighlight.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def _count_active_highlights(self) -> int:
        """Count the total number of active highlights globally."""
        result = await self.session.execute(
            select(func.count(JobHighlight.id)).where(
                JobHighlight.is_active == True  # noqa: E712
            )
        )
        return int(result.scalar_one())

    async def _is_enterprise_user(self, user_id: UUID) -> bool:
        """Check if user has an active Enterprise subscription."""
        result = await self.session.execute(
            select(Subscription).where(
                Subscription.user_id == user_id,
                Subscription.plan == SubscriptionPlan.enterprise,
                Subscription.status == SubscriptionStatus.active,
            )
        )
        return result.scalar_one_or_none() is not None
