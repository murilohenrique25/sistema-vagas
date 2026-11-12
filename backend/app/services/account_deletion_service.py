"""Transactional, role-aware account erasure."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.account_action_token import AccountActionToken
from app.models.ai_analysis import AIAnalysis
from app.models.application import Application, ApplicationStatusHistory
from app.models.audit_log import AuditLog
from app.models.company import Company
from app.models.job import Job
from app.models.job_highlight import JobHighlight
from app.models.job_report import JobReport
from app.models.notification import Notification
from app.models.resume import Resume
from app.models.subscription import Payment, Subscription
from app.models.token import TokenTransaction
from app.models.user import User
from app.models.wallet import WalletTransaction


CONFIRMATION_PHRASE = "EXCLUIR MINHA CONTA"


class AccountDeletionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def delete_account(self, user_id: UUID, confirmation: str, password: str | None) -> None:
        if confirmation.strip().upper() != CONFIRMATION_PHRASE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Digite exatamente "{CONFIRMATION_PHRASE}" para confirmar',
            )

        user = (await self.session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Conta não encontrada")
        if user.role.value == "admin":
            raise HTTPException(status_code=403, detail="Contas administrativas não podem ser excluídas por este fluxo")
        if user.password_hash and (not password or not verify_password(password, user.password_hash)):
            raise HTTPException(status_code=401, detail="Senha incorreta")

        # Applications are removed both when owned by the candidate and when tied
        # to a job owned by an employer. Dependent history is deleted first.
        company_ids = select(Company.id).where(Company.owner_id == user_id)
        job_ids = select(Job.id).where(Job.company_id.in_(company_ids))
        application_ids = select(Application.id).where(
            (Application.candidate_id == user_id) | (Application.job_id.in_(job_ids))
        )

        await self.session.execute(
            delete(ApplicationStatusHistory).where(
                (ApplicationStatusHistory.application_id.in_(application_ids))
                | (ApplicationStatusHistory.changed_by == user_id)
            )
        )
        await self.session.execute(delete(JobReport).where((JobReport.reporter_id == user_id) | JobReport.job_id.in_(job_ids)))
        await self.session.execute(delete(AIAnalysis).where((AIAnalysis.requester_id == user_id) | AIAnalysis.job_id.in_(job_ids)))
        await self.session.execute(delete(JobHighlight).where(JobHighlight.job_id.in_(job_ids)))
        await self.session.execute(delete(Application).where(Application.id.in_(application_ids)))
        await self.session.execute(delete(Job).where(Job.id.in_(job_ids)))
        await self.session.execute(delete(Company).where(Company.owner_id == user_id))

        # Resume children use ON DELETE CASCADE in the database.
        await self.session.execute(delete(Resume).where(Resume.user_id == user_id))
        await self.session.execute(delete(Notification).where(Notification.user_id == user_id))
        await self.session.execute(delete(WalletTransaction).where(WalletTransaction.user_id == user_id))
        await self.session.execute(delete(TokenTransaction).where(TokenTransaction.user_id == user_id))
        await self.session.execute(delete(Subscription).where(Subscription.user_id == user_id))
        await self.session.execute(delete(Payment).where(Payment.user_id == user_id))
        await self.session.execute(delete(AccountActionToken).where(AccountActionToken.user_id == user_id))
        await self.session.execute(delete(AuditLog).where(AuditLog.admin_id == user_id))

        # This table is intentionally not modeled; nulling the optional audit FK
        # prevents a historical settings row from blocking erasure.
        await self.session.execute(
            text("UPDATE payment_settings SET updated_by = NULL WHERE updated_by = :user_id"),
            {"user_id": user_id},
        )
        await self.session.execute(delete(User).where(User.id == user_id))
        await self.session.flush()

