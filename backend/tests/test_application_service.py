"""Unit tests for ApplicationService.

Tests cover:
- Candidatura com validações (currículo obrigatório, vaga ativa, sem duplicata)
- Listagem paginada de candidaturas do candidato (20 itens/página)
- Cancelamento com validação de status final
- Alteração automática de status quando vaga é encerrada

Requirements: 6.1, 6.2, 6.4, 6.5, 6.6, 6.7, 6.8
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.models.application import Application
from app.models.enums import ApplicationStatus, JobStatus
from app.models.job import Job
from app.models.resume import Resume


# --- Test helpers ---


def _mock_session():
    """Create a mock AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


def _mock_execute_result(scalar_value=None, scalars_value=None, all_value=None):
    """Create a mock execute result."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=scalar_value)
    mock_result.scalar_one = MagicMock(return_value=scalar_value if scalar_value is not None else 0)
    if scalars_value is not None:
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=scalars_value)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
    else:
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result.scalars = MagicMock(return_value=mock_scalars)
    if all_value is not None:
        mock_result.all = MagicMock(return_value=all_value)
    else:
        mock_result.all = MagicMock(return_value=[])
    return mock_result


def _make_resume(user_id: uuid.UUID) -> MagicMock:
    """Create a mock Resume."""
    resume = MagicMock(spec=Resume)
    resume.id = uuid.uuid4()
    resume.user_id = user_id
    resume.full_name = "João Silva"
    return resume


def _make_job(
    job_id: uuid.UUID | None = None,
    status: JobStatus = JobStatus.active,
    company_id: uuid.UUID | None = None,
) -> MagicMock:
    """Create a mock Job."""
    job = MagicMock(spec=Job)
    job.id = job_id or uuid.uuid4()
    job.company_id = company_id or uuid.uuid4()
    job.title = "Desenvolvedor Python"
    job.status = status
    return job


def _make_application(
    application_id: uuid.UUID | None = None,
    candidate_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    status: ApplicationStatus = ApplicationStatus.received,
) -> MagicMock:
    """Create a mock Application."""
    app = MagicMock(spec=Application)
    app.id = application_id or uuid.uuid4()
    app.candidate_id = candidate_id or uuid.uuid4()
    app.job_id = job_id or uuid.uuid4()
    app.status = status
    app.applied_at = datetime.now(timezone.utc)
    app.updated_at = None
    return app


# --- Test: Application creation (apply) ---


class TestApplicationServiceApply:
    """Test ApplicationService.apply with validations."""

    @pytest.mark.asyncio
    async def test_apply_success(self):
        """Requirement 6.1: Candidate with resume can apply to active job."""
        from app.services.application_service import ApplicationService

        session = _mock_session()
        candidate_id = uuid.uuid4()
        job_id = uuid.uuid4()

        resume = _make_resume(candidate_id)
        job = _make_job(job_id=job_id)
        company_mock = MagicMock()
        company_mock.owner_id = uuid.uuid4()

        # Mock execute calls:
        # 1. get_candidate_resume -> resume exists
        # 2. get_job -> job exists and is active
        # 3. get_existing_application -> no duplicate
        # 4. notify employer (get company)
        resume_result = _mock_execute_result(scalar_value=resume)
        job_result = _mock_execute_result(scalar_value=job)
        no_existing_app = _mock_execute_result(scalar_value=None)
        company_result = _mock_execute_result(scalar_value=company_mock)

        session.execute = AsyncMock(
            side_effect=[resume_result, job_result, no_existing_app, company_result]
        )

        service = ApplicationService(session)
        application = await service.apply(candidate_id, job_id)

        # Verify application was added to session
        add_calls = session.add.call_args_list
        assert len(add_calls) >= 1  # Application + history + notification

    @pytest.mark.asyncio
    async def test_apply_without_resume_rejected(self):
        """Requirement 6.6: Candidate without resume cannot apply."""
        from app.services.application_service import ApplicationService

        session = _mock_session()
        candidate_id = uuid.uuid4()
        job_id = uuid.uuid4()

        # No resume found
        no_resume = _mock_execute_result(scalar_value=None)
        session.execute = AsyncMock(return_value=no_resume)

        service = ApplicationService(session)
        with pytest.raises(HTTPException) as exc_info:
            await service.apply(candidate_id, job_id)

        assert exc_info.value.status_code == 400
        assert "currículo" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_apply_to_inactive_job_rejected(self):
        """Requirement 6.1: Can only apply to active jobs."""
        from app.services.application_service import ApplicationService

        session = _mock_session()
        candidate_id = uuid.uuid4()
        job_id = uuid.uuid4()

        resume = _make_resume(candidate_id)
        job = _make_job(job_id=job_id, status=JobStatus.closed)

        resume_result = _mock_execute_result(scalar_value=resume)
        job_result = _mock_execute_result(scalar_value=job)

        session.execute = AsyncMock(side_effect=[resume_result, job_result])

        service = ApplicationService(session)
        with pytest.raises(HTTPException) as exc_info:
            await service.apply(candidate_id, job_id)

        assert exc_info.value.status_code == 400
        assert "ativa" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_apply_to_nonexistent_job_rejected(self):
        """Job must exist to apply."""
        from app.services.application_service import ApplicationService

        session = _mock_session()
        candidate_id = uuid.uuid4()
        job_id = uuid.uuid4()

        resume = _make_resume(candidate_id)

        resume_result = _mock_execute_result(scalar_value=resume)
        no_job = _mock_execute_result(scalar_value=None)

        session.execute = AsyncMock(side_effect=[resume_result, no_job])

        service = ApplicationService(session)
        with pytest.raises(HTTPException) as exc_info:
            await service.apply(candidate_id, job_id)

        assert exc_info.value.status_code == 404
        assert "não encontrada" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_apply_duplicate_rejected(self):
        """Requirement 6.5: Duplicate application for same job is blocked."""
        from app.services.application_service import ApplicationService

        session = _mock_session()
        candidate_id = uuid.uuid4()
        job_id = uuid.uuid4()

        resume = _make_resume(candidate_id)
        job = _make_job(job_id=job_id)
        existing_app = _make_application(candidate_id=candidate_id, job_id=job_id)

        resume_result = _mock_execute_result(scalar_value=resume)
        job_result = _mock_execute_result(scalar_value=job)
        existing_app_result = _mock_execute_result(scalar_value=existing_app)

        session.execute = AsyncMock(
            side_effect=[resume_result, job_result, existing_app_result]
        )

        service = ApplicationService(session)
        with pytest.raises(HTTPException) as exc_info:
            await service.apply(candidate_id, job_id)

        assert exc_info.value.status_code == 409
        assert "já possui" in exc_info.value.detail.lower()


# --- Test: Candidate application listing ---


class TestApplicationServiceListCandidateApplications:
    """Test ApplicationService.get_candidate_applications."""

    @pytest.mark.asyncio
    async def test_list_applications_paginated(self):
        """Requirement 6.2: List applications with 20 items/page, ordered by date desc."""
        from app.services.application_service import ApplicationService

        session = _mock_session()
        candidate_id = uuid.uuid4()

        # Mock total count
        count_result = _mock_execute_result(scalar_value=5)

        # Mock paginated results (application, job_title, company_name)
        mock_rows = []
        for i in range(5):
            app = _make_application(candidate_id=candidate_id)
            mock_rows.append((app, f"Vaga {i}", f"Empresa {i}"))

        list_result = MagicMock()
        list_result.all = MagicMock(return_value=mock_rows)

        session.execute = AsyncMock(side_effect=[count_result, list_result])

        service = ApplicationService(session)
        result = await service.get_candidate_applications(candidate_id, page=1, page_size=20)

        assert result.total == 5
        assert result.page == 1
        assert result.page_size == 20
        assert len(result.items) == 5
        assert result.items[0].job_title == "Vaga 0"
        assert result.items[0].company_name == "Empresa 0"

    @pytest.mark.asyncio
    async def test_list_applications_empty(self):
        """Empty result returns zero items and total."""
        from app.services.application_service import ApplicationService

        session = _mock_session()
        candidate_id = uuid.uuid4()

        count_result = _mock_execute_result(scalar_value=0)
        list_result = MagicMock()
        list_result.all = MagicMock(return_value=[])

        session.execute = AsyncMock(side_effect=[count_result, list_result])

        service = ApplicationService(session)
        result = await service.get_candidate_applications(candidate_id, page=1)

        assert result.total == 0
        assert len(result.items) == 0
        assert result.total_pages == 0

    @pytest.mark.asyncio
    async def test_list_applications_pagination_calculation(self):
        """Total pages calculated correctly for pagination."""
        from app.services.application_service import ApplicationService

        session = _mock_session()
        candidate_id = uuid.uuid4()

        # 45 total items, 20 per page = 3 pages
        count_result = _mock_execute_result(scalar_value=45)
        list_result = MagicMock()
        list_result.all = MagicMock(return_value=[])

        session.execute = AsyncMock(side_effect=[count_result, list_result])

        service = ApplicationService(session)
        result = await service.get_candidate_applications(candidate_id, page=1, page_size=20)

        assert result.total == 45
        assert result.total_pages == 3


# --- Test: Cancellation ---


class TestApplicationServiceCancel:
    """Test ApplicationService.cancel with status validation."""

    @pytest.mark.asyncio
    async def test_cancel_received_application(self):
        """Requirement 6.4: Can cancel application with status 'received'."""
        from app.services.application_service import ApplicationService

        session = _mock_session()
        candidate_id = uuid.uuid4()
        app = _make_application(
            candidate_id=candidate_id,
            status=ApplicationStatus.received,
        )

        app_result = _mock_execute_result(scalar_value=app)
        session.execute = AsyncMock(return_value=app_result)

        service = ApplicationService(session)
        result = await service.cancel(app.id, candidate_id)

        assert app.status == ApplicationStatus.cancelled

    @pytest.mark.asyncio
    async def test_cancel_in_review_application(self):
        """Can cancel application with status 'in_review'."""
        from app.services.application_service import ApplicationService

        session = _mock_session()
        candidate_id = uuid.uuid4()
        app = _make_application(
            candidate_id=candidate_id,
            status=ApplicationStatus.in_review,
        )

        app_result = _mock_execute_result(scalar_value=app)
        session.execute = AsyncMock(return_value=app_result)

        service = ApplicationService(session)
        result = await service.cancel(app.id, candidate_id)

        assert app.status == ApplicationStatus.cancelled

    @pytest.mark.asyncio
    async def test_cancel_hired_application_rejected(self):
        """Requirement 6.7: Cannot cancel application with status 'hired'."""
        from app.services.application_service import ApplicationService

        session = _mock_session()
        candidate_id = uuid.uuid4()
        app = _make_application(
            candidate_id=candidate_id,
            status=ApplicationStatus.hired,
        )

        app_result = _mock_execute_result(scalar_value=app)
        session.execute = AsyncMock(return_value=app_result)

        service = ApplicationService(session)
        with pytest.raises(HTTPException) as exc_info:
            await service.cancel(app.id, candidate_id)

        assert exc_info.value.status_code == 400
        assert "status final" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_cancel_rejected_application_rejected(self):
        """Requirement 6.7: Cannot cancel application with status 'rejected'."""
        from app.services.application_service import ApplicationService

        session = _mock_session()
        candidate_id = uuid.uuid4()
        app = _make_application(
            candidate_id=candidate_id,
            status=ApplicationStatus.rejected,
        )

        app_result = _mock_execute_result(scalar_value=app)
        session.execute = AsyncMock(return_value=app_result)

        service = ApplicationService(session)
        with pytest.raises(HTTPException) as exc_info:
            await service.cancel(app.id, candidate_id)

        assert exc_info.value.status_code == 400
        assert "status final" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_cancel_already_cancelled_rejected(self):
        """Cannot cancel an already cancelled application."""
        from app.services.application_service import ApplicationService

        session = _mock_session()
        candidate_id = uuid.uuid4()
        app = _make_application(
            candidate_id=candidate_id,
            status=ApplicationStatus.cancelled,
        )

        app_result = _mock_execute_result(scalar_value=app)
        session.execute = AsyncMock(return_value=app_result)

        service = ApplicationService(session)
        with pytest.raises(HTTPException) as exc_info:
            await service.cancel(app.id, candidate_id)

        assert exc_info.value.status_code == 400
        assert "já está cancelada" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_cancel_other_users_application_rejected(self):
        """Cannot cancel another user's application."""
        from app.services.application_service import ApplicationService

        session = _mock_session()
        candidate_id = uuid.uuid4()
        other_candidate_id = uuid.uuid4()
        app = _make_application(
            candidate_id=other_candidate_id,
            status=ApplicationStatus.received,
        )

        app_result = _mock_execute_result(scalar_value=app)
        session.execute = AsyncMock(return_value=app_result)

        service = ApplicationService(session)
        with pytest.raises(HTTPException) as exc_info:
            await service.cancel(app.id, candidate_id)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_application_rejected(self):
        """Cannot cancel a non-existent application."""
        from app.services.application_service import ApplicationService

        session = _mock_session()
        candidate_id = uuid.uuid4()

        no_app = _mock_execute_result(scalar_value=None)
        session.execute = AsyncMock(return_value=no_app)

        service = ApplicationService(session)
        with pytest.raises(HTTPException) as exc_info:
            await service.cancel(uuid.uuid4(), candidate_id)

        assert exc_info.value.status_code == 404


# --- Test: Auto-reject when job is closed ---


class TestApplicationServiceRejectPending:
    """Test ApplicationService.reject_pending_applications_for_job."""

    @pytest.mark.asyncio
    async def test_reject_pending_applications(self):
        """Requirement 6.8: Pending applications are rejected when job is closed."""
        from app.services.application_service import ApplicationService

        session = _mock_session()
        job_id = uuid.uuid4()
        job = _make_job(job_id=job_id)

        # Two pending applications
        app1 = _make_application(job_id=job_id, status=ApplicationStatus.received)
        app2 = _make_application(job_id=job_id, status=ApplicationStatus.in_review)

        apps_result = _mock_execute_result(scalars_value=[app1, app2])
        job_result = _mock_execute_result(scalar_value=job)

        session.execute = AsyncMock(side_effect=[apps_result, job_result])

        service = ApplicationService(session)
        count = await service.reject_pending_applications_for_job(job_id)

        assert count == 2
        assert app1.status == ApplicationStatus.rejected
        assert app2.status == ApplicationStatus.rejected

    @pytest.mark.asyncio
    async def test_reject_no_pending_applications(self):
        """No applications are rejected when there are no pending ones."""
        from app.services.application_service import ApplicationService

        session = _mock_session()
        job_id = uuid.uuid4()

        # No pending applications
        apps_result = _mock_execute_result(scalars_value=[])

        session.execute = AsyncMock(return_value=apps_result)

        service = ApplicationService(session)
        count = await service.reject_pending_applications_for_job(job_id)

        assert count == 0
        session.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_reject_sends_notifications(self):
        """Requirement 6.8: Candidates are notified when applications are auto-rejected."""
        from app.services.application_service import ApplicationService

        session = _mock_session()
        job_id = uuid.uuid4()
        job = _make_job(job_id=job_id)

        app1 = _make_application(job_id=job_id, status=ApplicationStatus.received)

        apps_result = _mock_execute_result(scalars_value=[app1])
        job_result = _mock_execute_result(scalar_value=job)

        session.execute = AsyncMock(side_effect=[apps_result, job_result])

        service = ApplicationService(session)
        await service.reject_pending_applications_for_job(job_id)

        # Verify notifications were added (history + notification per application)
        add_calls = session.add.call_args_list
        assert len(add_calls) >= 2  # At least history + notification
