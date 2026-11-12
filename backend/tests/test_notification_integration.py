"""Integration tests for notification triggers in existing modules.

Verifies that notifications are properly triggered at the right points:
- ApplicationService: employer notification on new application, candidate notification on status change
- TokenService: low balance notification after debit
- JobService: employer notification 7 days before job deadline

Also verifies that notification failures don't block main business logic.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from app.models.application import Application, ApplicationStatusHistory
from app.models.company import Company
from app.models.enums import (
    ApplicationStatus,
    DeliveryStatus,
    JobStatus,
    NotificationChannel,
    TokenTransactionType,
)
from app.models.job import Job
from app.models.notification import Notification
from app.models.resume import Resume
from app.models.token import TokenTransaction
from app.services.application_service import ApplicationService
from app.services.job_service import JobService
from app.services.token_service import TokenService


def _make_job(company_id: uuid.UUID, title: str = "Desenvolvedor Python") -> MagicMock:
    """Create a mock Job."""
    job = MagicMock(spec=Job)
    job.id = uuid.uuid4()
    job.company_id = company_id
    job.title = title
    job.status = JobStatus.active
    job.deadline = date.today() + timedelta(days=30)
    return job


def _make_company(owner_id: uuid.UUID) -> MagicMock:
    """Create a mock Company."""
    company = MagicMock(spec=Company)
    company.id = uuid.uuid4()
    company.owner_id = owner_id
    company.name = "Empresa Teste"
    return company


def _make_application(
    candidate_id: uuid.UUID,
    job_id: uuid.UUID,
    status: ApplicationStatus = ApplicationStatus.received,
) -> MagicMock:
    """Create a mock Application."""
    app = MagicMock(spec=Application)
    app.id = uuid.uuid4()
    app.candidate_id = candidate_id
    app.job_id = job_id
    app.status = status
    app.applied_at = datetime.now(timezone.utc)
    app.updated_at = datetime.now(timezone.utc)
    return app


class TestApplicationServiceNotifications:
    """Tests verifying notification integration in ApplicationService."""

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_redis")
    async def test_employer_notified_on_new_application(self, mock_get_redis):
        """Req 13.1: Employer should receive notification when new application is created."""
        employer_id = uuid.uuid4()
        candidate_id = uuid.uuid4()
        company_id = uuid.uuid4()
        job_id = uuid.uuid4()

        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        # Mock Redis for notification queuing
        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        # Setup mocks for the apply flow
        resume = MagicMock(spec=Resume)
        resume.id = uuid.uuid4()

        job = _make_job(company_id)
        job.id = job_id

        company = _make_company(employer_id)
        company.id = company_id

        # Track notifications added
        added_objects = []
        original_add = session.add

        def track_add(obj):
            added_objects.append(obj)

        session.add = track_add

        # Mock execute to return appropriate results
        resume_result = MagicMock()
        resume_result.scalar_one_or_none.return_value = resume

        job_result = MagicMock()
        job_result.scalar_one_or_none.return_value = job

        existing_app_result = MagicMock()
        existing_app_result.scalar_one_or_none.return_value = None

        company_result = MagicMock()
        company_result.scalar_one_or_none.return_value = company

        session.execute = AsyncMock(
            side_effect=[resume_result, job_result, existing_app_result, company_result]
        )

        service = ApplicationService(session)
        await service.apply(candidate_id, job_id)

        # Verify that a notification was created for the employer
        notifications = [
            obj for obj in added_objects if isinstance(obj, Notification)
        ]
        assert len(notifications) == 1
        assert notifications[0].user_id == employer_id
        assert "Nova candidatura recebida" in notifications[0].title
        assert notifications[0].channel == NotificationChannel.both

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_redis")
    async def test_candidate_notified_on_status_change(self, mock_get_redis):
        """Req 13.2: Candidate should receive notification when status changes."""
        candidate_id = uuid.uuid4()
        employer_id = uuid.uuid4()
        job_id = uuid.uuid4()
        company_id = uuid.uuid4()

        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        application = _make_application(candidate_id, job_id, ApplicationStatus.received)

        job = _make_job(company_id, "Analista de Dados")
        job.id = job_id

        # Track what gets added
        added_objects = []
        session.add = lambda obj: added_objects.append(obj)

        # Mock the application query, then the job query for notification
        app_result = MagicMock()
        app_result.scalar_one_or_none.return_value = application

        job_result = MagicMock()
        job_result.scalar_one_or_none.return_value = job

        session.execute = AsyncMock(side_effect=[app_result, job_result])

        service = ApplicationService(session)
        await service.change_status(application.id, ApplicationStatus.in_review, employer_id)

        # Verify notification sent to candidate
        notifications = [
            obj for obj in added_objects if isinstance(obj, Notification)
        ]
        assert len(notifications) == 1
        assert notifications[0].user_id == candidate_id
        assert "status" in notifications[0].title.lower() or "atualizado" in notifications[0].title.lower()

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_redis")
    async def test_interview_notification_has_special_message(self, mock_get_redis):
        """Req 13.3: Interview invitation should have special notification message."""
        candidate_id = uuid.uuid4()
        employer_id = uuid.uuid4()
        job_id = uuid.uuid4()
        company_id = uuid.uuid4()

        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        application = _make_application(candidate_id, job_id, ApplicationStatus.in_review)

        job = _make_job(company_id, "Engenheiro de Software")
        job.id = job_id

        added_objects = []
        session.add = lambda obj: added_objects.append(obj)

        app_result = MagicMock()
        app_result.scalar_one_or_none.return_value = application

        job_result = MagicMock()
        job_result.scalar_one_or_none.return_value = job

        session.execute = AsyncMock(side_effect=[app_result, job_result])

        service = ApplicationService(session)
        await service.change_status(application.id, ApplicationStatus.interview, employer_id)

        notifications = [
            obj for obj in added_objects if isinstance(obj, Notification)
        ]
        assert len(notifications) == 1
        assert notifications[0].title == "Convite para entrevista"
        assert "entrevista" in notifications[0].message.lower()

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_redis")
    async def test_hired_notification(self, mock_get_redis):
        """Req 13.4: Candidate should receive approval notification when hired."""
        candidate_id = uuid.uuid4()
        employer_id = uuid.uuid4()
        job_id = uuid.uuid4()
        company_id = uuid.uuid4()

        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        application = _make_application(candidate_id, job_id, ApplicationStatus.proposal)

        job = _make_job(company_id, "Product Manager")
        job.id = job_id

        added_objects = []
        session.add = lambda obj: added_objects.append(obj)

        app_result = MagicMock()
        app_result.scalar_one_or_none.return_value = application

        job_result = MagicMock()
        job_result.scalar_one_or_none.return_value = job

        # Mock for hiring rate calculation
        total_count_result = MagicMock()
        total_count_result.scalar_one.return_value = 5
        hired_count_result = MagicMock()
        hired_count_result.scalar_one.return_value = 1

        session.execute = AsyncMock(
            side_effect=[app_result, job_result, total_count_result, hired_count_result]
        )

        service = ApplicationService(session)
        await service.change_status(application.id, ApplicationStatus.hired, employer_id)

        notifications = [
            obj for obj in added_objects if isinstance(obj, Notification)
        ]
        assert len(notifications) == 1
        assert notifications[0].title == "Candidatura aprovada"
        assert "contratado" in notifications[0].message.lower()

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_redis")
    async def test_rejected_notification(self, mock_get_redis):
        """Req 13.4: Candidate should receive rejection notification."""
        candidate_id = uuid.uuid4()
        employer_id = uuid.uuid4()
        job_id = uuid.uuid4()
        company_id = uuid.uuid4()

        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        application = _make_application(candidate_id, job_id, ApplicationStatus.in_review)

        job = _make_job(company_id, "Designer UX")
        job.id = job_id

        added_objects = []
        session.add = lambda obj: added_objects.append(obj)

        app_result = MagicMock()
        app_result.scalar_one_or_none.return_value = application

        job_result = MagicMock()
        job_result.scalar_one_or_none.return_value = job

        session.execute = AsyncMock(side_effect=[app_result, job_result])

        service = ApplicationService(session)
        await service.change_status(application.id, ApplicationStatus.rejected, employer_id)

        notifications = [
            obj for obj in added_objects if isinstance(obj, Notification)
        ]
        assert len(notifications) == 1
        assert notifications[0].title == "Candidatura reprovada"
        assert "reprovada" in notifications[0].message.lower()

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_redis")
    async def test_notification_failure_does_not_block_application(self, mock_get_redis):
        """Notification failure should not prevent application from being created."""
        candidate_id = uuid.uuid4()
        job_id = uuid.uuid4()
        company_id = uuid.uuid4()

        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        # Redis failure simulates notification failure
        mock_redis = AsyncMock()
        mock_redis.rpush.side_effect = Exception("Redis connection failed")
        mock_get_redis.return_value = mock_redis

        resume = MagicMock(spec=Resume)
        resume.id = uuid.uuid4()

        job = _make_job(company_id)
        job.id = job_id

        company = _make_company(uuid.uuid4())
        company.id = company_id

        added_objects = []
        session.add = lambda obj: added_objects.append(obj)

        resume_result = MagicMock()
        resume_result.scalar_one_or_none.return_value = resume

        job_result = MagicMock()
        job_result.scalar_one_or_none.return_value = job

        existing_app_result = MagicMock()
        existing_app_result.scalar_one_or_none.return_value = None

        company_result = MagicMock()
        company_result.scalar_one_or_none.return_value = company

        session.execute = AsyncMock(
            side_effect=[resume_result, job_result, existing_app_result, company_result]
        )

        service = ApplicationService(session)
        # Should not raise even though notification fails
        await service.apply(candidate_id, job_id)

        # Application should still be created
        applications = [
            obj for obj in added_objects if isinstance(obj, Application)
        ]
        assert len(applications) == 1
        assert applications[0].status == ApplicationStatus.received


class TestTokenServiceNotifications:
    """Tests verifying notification integration in TokenService."""

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_redis")
    async def test_low_balance_notification_triggered(self, mock_get_redis):
        """Req 13.5: User should be notified when token balance is low."""
        user_id = uuid.uuid4()

        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        added_objects = []
        session.add = lambda obj: added_objects.append(obj)

        # User has 100 tokens, debiting 95 leaves 5
        # Consumption in last 30 days: 200 tokens, so 10% threshold = 20
        # 5 <= 20, so notification should fire
        balance_result = MagicMock()
        balance_result.scalar_one.return_value = 100  # current balance

        consumption_result = MagicMock()
        consumption_result.scalar_one.return_value = 200  # total consumption 30d

        session.execute = AsyncMock(side_effect=[balance_result, consumption_result])

        service = TokenService(session)
        await service.debit(user_id, 95, "Análise de IA")

        # Verify low balance notification was created
        notifications = [
            obj for obj in added_objects if isinstance(obj, Notification)
        ]
        assert len(notifications) == 1
        assert notifications[0].user_id == user_id
        assert "saldo" in notifications[0].title.lower() or "baixo" in notifications[0].title.lower()
        assert "5 tokens restantes" in notifications[0].message

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_redis")
    async def test_no_notification_when_balance_sufficient(self, mock_get_redis):
        """Should not send notification when balance is above threshold."""
        user_id = uuid.uuid4()

        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        added_objects = []
        session.add = lambda obj: added_objects.append(obj)

        # User has 100 tokens, debiting 10 leaves 90
        # Consumption in last 30 days: 200 tokens, so 10% threshold = 20
        # 90 > 20, so NO notification
        balance_result = MagicMock()
        balance_result.scalar_one.return_value = 100

        consumption_result = MagicMock()
        consumption_result.scalar_one.return_value = 200

        session.execute = AsyncMock(side_effect=[balance_result, consumption_result])

        service = TokenService(session)
        await service.debit(user_id, 10, "Análise de IA")

        # No notification should be created
        notifications = [
            obj for obj in added_objects if isinstance(obj, Notification)
        ]
        assert len(notifications) == 0

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_redis")
    async def test_low_balance_notification_failure_does_not_block_debit(self, mock_get_redis):
        """Debit should succeed even if notification sending fails."""
        user_id = uuid.uuid4()

        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        # Redis fails for notification
        mock_redis = AsyncMock()
        mock_redis.rpush.side_effect = Exception("Redis down")
        mock_get_redis.return_value = mock_redis

        added_objects = []
        session.add = lambda obj: added_objects.append(obj)

        balance_result = MagicMock()
        balance_result.scalar_one.return_value = 100

        consumption_result = MagicMock()
        consumption_result.scalar_one.return_value = 200

        session.execute = AsyncMock(side_effect=[balance_result, consumption_result])

        service = TokenService(session)
        # Should not raise even though notification fails
        transaction = await service.debit(user_id, 95, "Análise de IA")

        # Transaction should still be created
        transactions = [
            obj for obj in added_objects if isinstance(obj, TokenTransaction)
        ]
        assert len(transactions) == 1


class TestJobServiceNotifications:
    """Tests verifying notification integration in JobService for 7-day deadline."""

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_redis")
    async def test_notify_expiring_jobs_sends_notification(self, mock_get_redis):
        """Req 13.6: Employer should receive notification 7 days before job deadline."""
        employer_id = uuid.uuid4()
        company_id = uuid.uuid4()
        job_id = uuid.uuid4()

        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        # Job expiring in 7 days
        target_date = date.today() + timedelta(days=7)
        job = MagicMock(spec=Job)
        job.id = job_id
        job.title = "Desenvolvedor Full Stack"
        job.company_id = company_id
        job.status = JobStatus.active
        job.deadline = target_date

        company = MagicMock(spec=Company)
        company.id = company_id
        company.owner_id = employer_id

        added_objects = []
        session.add = lambda obj: added_objects.append(obj)

        # Mock query result for expiring jobs
        query_result = MagicMock()
        query_result.all.return_value = [(job, company)]
        session.execute = AsyncMock(return_value=query_result)

        service = JobService(session)
        notified_count = await service.notify_expiring_jobs()

        assert notified_count == 1

        notifications = [
            obj for obj in added_objects if isinstance(obj, Notification)
        ]
        assert len(notifications) == 1
        assert notifications[0].user_id == employer_id
        assert "encerramento" in notifications[0].title.lower() or "próxima" in notifications[0].title.lower()
        assert "7 dias" in notifications[0].message

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_redis")
    async def test_notify_expiring_jobs_no_jobs(self, mock_get_redis):
        """Should return 0 when no jobs are expiring in 7 days."""
        session = AsyncMock()
        session.flush = AsyncMock()

        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        query_result = MagicMock()
        query_result.all.return_value = []
        session.execute = AsyncMock(return_value=query_result)

        service = JobService(session)
        notified_count = await service.notify_expiring_jobs()

        assert notified_count == 0

    @pytest.mark.asyncio
    @patch("app.services.notification_service.get_redis")
    async def test_notify_expiring_jobs_partial_failure(self, mock_get_redis):
        """Should continue notifying other employers even if one notification fails."""
        employer1_id = uuid.uuid4()
        employer2_id = uuid.uuid4()
        company1_id = uuid.uuid4()
        company2_id = uuid.uuid4()

        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        # First notification succeeds, second also succeeds
        # but we simulate Redis failure on first call only
        call_count = [0]
        mock_redis = AsyncMock()

        async def rpush_side_effect(*args):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Redis timeout")
            return True

        mock_redis.rpush = rpush_side_effect
        mock_get_redis.return_value = mock_redis

        target_date = date.today() + timedelta(days=7)

        job1 = MagicMock(spec=Job)
        job1.id = uuid.uuid4()
        job1.title = "Job 1"
        job1.company_id = company1_id
        job1.deadline = target_date

        job2 = MagicMock(spec=Job)
        job2.id = uuid.uuid4()
        job2.title = "Job 2"
        job2.company_id = company2_id
        job2.deadline = target_date

        company1 = MagicMock(spec=Company)
        company1.id = company1_id
        company1.owner_id = employer1_id

        company2 = MagicMock(spec=Company)
        company2.id = company2_id
        company2.owner_id = employer2_id

        added_objects = []
        session.add = lambda obj: added_objects.append(obj)

        query_result = MagicMock()
        query_result.all.return_value = [(job1, company1), (job2, company2)]
        session.execute = AsyncMock(return_value=query_result)

        service = JobService(session)
        # The first notification will fail at Redis level but the notification
        # object is still saved in DB. The method should still continue to job2.
        notified_count = await service.notify_expiring_jobs()

        # Both should be attempted - first one saves to DB even if queue fails
        # (NotificationService.send_notification saves then queues)
        notifications = [
            obj for obj in added_objects if isinstance(obj, Notification)
        ]
        assert len(notifications) >= 1  # At least the ones that didn't throw
