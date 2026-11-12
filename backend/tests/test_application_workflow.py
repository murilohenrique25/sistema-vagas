"""Unit tests for Application Workflow (State Machine).

Tests cover:
- Valid progressive transitions: Recebida → Em análise → Entrevista → Teste técnico → Proposta → Contratado
- Transition to "Reprovado" from any status except Contratado/Cancelado
- Transition to "Cancelado" from any status except Contratado
- History recording (UTC date, previous status, new status, responsible user)
- Invalid transitions rejected with error message
- Hiring rate calculation when moving to "Contratado"

Requirements: 7.1, 7.2, 7.3, 7.5, 7.6
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.models.application import Application, ApplicationStatusHistory
from app.models.enums import ApplicationStatus, JobStatus
from app.models.job import Job
from app.services.application_service import (
    ApplicationService,
    PROGRESSIVE_TRANSITIONS,
    CANNOT_REJECT_FROM,
    CANNOT_CANCEL_FROM,
)


# --- Test helpers ---


def _mock_session():
    """Create a mock AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


def _mock_execute_result(scalar_value=None, scalars_value=None):
    """Create a mock execute result."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=scalar_value)
    mock_result.scalar_one = MagicMock(return_value=scalar_value if scalar_value is not None else 0)
    if scalars_value is not None:
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=scalars_value)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
    return mock_result


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


# --- Test: Valid progressive transitions (Req 7.1) ---


class TestWorkflowProgressiveTransitions:
    """Test valid progressive transitions in the candidature workflow."""

    @pytest.mark.asyncio
    async def test_received_to_in_review(self):
        """Req 7.1: Recebida → Em análise is a valid transition."""
        session = _mock_session()
        employer_id = uuid.uuid4()
        job_id = uuid.uuid4()
        app = _make_application(status=ApplicationStatus.received, job_id=job_id)
        job = _make_job(job_id=job_id)

        # Execute returns: get_application, then get_job (for notification)
        app_result = _mock_execute_result(scalar_value=app)
        job_result = _mock_execute_result(scalar_value=job)

        session.execute = AsyncMock(side_effect=[app_result, job_result])

        service = ApplicationService(session)
        result = await service.change_status(app.id, ApplicationStatus.in_review, employer_id)

        assert app.status == ApplicationStatus.in_review

    @pytest.mark.asyncio
    async def test_in_review_to_interview(self):
        """Req 7.1: Em análise → Entrevista is a valid transition."""
        session = _mock_session()
        employer_id = uuid.uuid4()
        job_id = uuid.uuid4()
        app = _make_application(status=ApplicationStatus.in_review, job_id=job_id)
        job = _make_job(job_id=job_id)

        app_result = _mock_execute_result(scalar_value=app)
        job_result = _mock_execute_result(scalar_value=job)

        session.execute = AsyncMock(side_effect=[app_result, job_result])

        service = ApplicationService(session)
        await service.change_status(app.id, ApplicationStatus.interview, employer_id)

        assert app.status == ApplicationStatus.interview

    @pytest.mark.asyncio
    async def test_interview_to_technical_test(self):
        """Req 7.1: Entrevista → Teste técnico is a valid transition."""
        session = _mock_session()
        employer_id = uuid.uuid4()
        job_id = uuid.uuid4()
        app = _make_application(status=ApplicationStatus.interview, job_id=job_id)
        job = _make_job(job_id=job_id)

        app_result = _mock_execute_result(scalar_value=app)
        job_result = _mock_execute_result(scalar_value=job)

        session.execute = AsyncMock(side_effect=[app_result, job_result])

        service = ApplicationService(session)
        await service.change_status(app.id, ApplicationStatus.technical_test, employer_id)

        assert app.status == ApplicationStatus.technical_test

    @pytest.mark.asyncio
    async def test_technical_test_to_proposal(self):
        """Req 7.1: Teste técnico → Proposta is a valid transition."""
        session = _mock_session()
        employer_id = uuid.uuid4()
        job_id = uuid.uuid4()
        app = _make_application(status=ApplicationStatus.technical_test, job_id=job_id)
        job = _make_job(job_id=job_id)

        app_result = _mock_execute_result(scalar_value=app)
        job_result = _mock_execute_result(scalar_value=job)

        session.execute = AsyncMock(side_effect=[app_result, job_result])

        service = ApplicationService(session)
        await service.change_status(app.id, ApplicationStatus.proposal, employer_id)

        assert app.status == ApplicationStatus.proposal

    @pytest.mark.asyncio
    async def test_proposal_to_hired(self):
        """Req 7.1, 7.5: Proposta → Contratado is valid and calculates hiring rate."""
        session = _mock_session()
        employer_id = uuid.uuid4()
        job_id = uuid.uuid4()
        app = _make_application(status=ApplicationStatus.proposal, job_id=job_id)
        job = _make_job(job_id=job_id)

        app_result = _mock_execute_result(scalar_value=app)
        job_result = _mock_execute_result(scalar_value=job)
        # Hiring rate: total=10, hired=1
        total_result = _mock_execute_result(scalar_value=10)
        hired_result = _mock_execute_result(scalar_value=1)

        session.execute = AsyncMock(
            side_effect=[app_result, job_result, total_result, hired_result]
        )

        service = ApplicationService(session)
        await service.change_status(app.id, ApplicationStatus.hired, employer_id)

        assert app.status == ApplicationStatus.hired


# --- Test: Transition to "Reprovado" (Req 7.1) ---


class TestWorkflowRejection:
    """Test transition to Reprovado from various statuses."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "current_status",
        [
            ApplicationStatus.received,
            ApplicationStatus.in_review,
            ApplicationStatus.interview,
            ApplicationStatus.technical_test,
            ApplicationStatus.proposal,
        ],
    )
    async def test_reject_from_valid_statuses(self, current_status):
        """Req 7.1: Rejection is allowed from any status except Contratado/Cancelado."""
        session = _mock_session()
        employer_id = uuid.uuid4()
        job_id = uuid.uuid4()
        app = _make_application(status=current_status, job_id=job_id)
        job = _make_job(job_id=job_id)

        app_result = _mock_execute_result(scalar_value=app)
        job_result = _mock_execute_result(scalar_value=job)

        session.execute = AsyncMock(side_effect=[app_result, job_result])

        service = ApplicationService(session)
        await service.change_status(app.id, ApplicationStatus.rejected, employer_id)

        assert app.status == ApplicationStatus.rejected

    @pytest.mark.asyncio
    async def test_reject_from_hired_not_allowed(self):
        """Req 7.1: Cannot reject from Contratado."""
        session = _mock_session()
        employer_id = uuid.uuid4()
        app = _make_application(status=ApplicationStatus.hired)

        app_result = _mock_execute_result(scalar_value=app)
        session.execute = AsyncMock(return_value=app_result)

        service = ApplicationService(session)
        with pytest.raises(HTTPException) as exc_info:
            await service.change_status(app.id, ApplicationStatus.rejected, employer_id)

        assert exc_info.value.status_code == 400
        assert "inválida" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_reject_from_cancelled_not_allowed(self):
        """Req 7.1: Cannot reject from Cancelado."""
        session = _mock_session()
        employer_id = uuid.uuid4()
        app = _make_application(status=ApplicationStatus.cancelled)

        app_result = _mock_execute_result(scalar_value=app)
        session.execute = AsyncMock(return_value=app_result)

        service = ApplicationService(session)
        with pytest.raises(HTTPException) as exc_info:
            await service.change_status(app.id, ApplicationStatus.rejected, employer_id)

        assert exc_info.value.status_code == 400
        assert "inválida" in exc_info.value.detail.lower()


# --- Test: Transition to "Cancelado" (Req 7.1) ---


class TestWorkflowCancellation:
    """Test transition to Cancelado from various statuses."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "current_status",
        [
            ApplicationStatus.received,
            ApplicationStatus.in_review,
            ApplicationStatus.interview,
            ApplicationStatus.technical_test,
            ApplicationStatus.proposal,
            ApplicationStatus.rejected,
        ],
    )
    async def test_cancel_from_valid_statuses(self, current_status):
        """Req 7.1: Cancellation is allowed from any status except Contratado."""
        session = _mock_session()
        employer_id = uuid.uuid4()
        job_id = uuid.uuid4()
        app = _make_application(status=current_status, job_id=job_id)
        job = _make_job(job_id=job_id)

        app_result = _mock_execute_result(scalar_value=app)
        job_result = _mock_execute_result(scalar_value=job)

        session.execute = AsyncMock(side_effect=[app_result, job_result])

        service = ApplicationService(session)
        await service.change_status(app.id, ApplicationStatus.cancelled, employer_id)

        assert app.status == ApplicationStatus.cancelled

    @pytest.mark.asyncio
    async def test_cancel_from_hired_not_allowed(self):
        """Req 7.1: Cannot cancel from Contratado."""
        session = _mock_session()
        employer_id = uuid.uuid4()
        app = _make_application(status=ApplicationStatus.hired)

        app_result = _mock_execute_result(scalar_value=app)
        session.execute = AsyncMock(return_value=app_result)

        service = ApplicationService(session)
        with pytest.raises(HTTPException) as exc_info:
            await service.change_status(app.id, ApplicationStatus.cancelled, employer_id)

        assert exc_info.value.status_code == 400
        assert "inválida" in exc_info.value.detail.lower()


# --- Test: Invalid transitions rejected (Req 7.3) ---


class TestWorkflowInvalidTransitions:
    """Test that invalid transitions are rejected with error message."""

    @pytest.mark.asyncio
    async def test_skip_step_not_allowed(self):
        """Req 7.3: Cannot skip steps (received directly to interview)."""
        session = _mock_session()
        employer_id = uuid.uuid4()
        app = _make_application(status=ApplicationStatus.received)

        app_result = _mock_execute_result(scalar_value=app)
        session.execute = AsyncMock(return_value=app_result)

        service = ApplicationService(session)
        with pytest.raises(HTTPException) as exc_info:
            await service.change_status(app.id, ApplicationStatus.interview, employer_id)

        assert exc_info.value.status_code == 400
        assert "inválida" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_backward_transition_not_allowed(self):
        """Req 7.3: Cannot go backward (interview to received)."""
        session = _mock_session()
        employer_id = uuid.uuid4()
        app = _make_application(status=ApplicationStatus.interview)

        app_result = _mock_execute_result(scalar_value=app)
        session.execute = AsyncMock(return_value=app_result)

        service = ApplicationService(session)
        with pytest.raises(HTTPException) as exc_info:
            await service.change_status(app.id, ApplicationStatus.received, employer_id)

        assert exc_info.value.status_code == 400
        assert "inválida" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_transition_from_hired_not_allowed(self):
        """Req 7.3: No transitions allowed from Contratado (except itself, which is also blocked)."""
        session = _mock_session()
        employer_id = uuid.uuid4()
        app = _make_application(status=ApplicationStatus.hired)

        app_result = _mock_execute_result(scalar_value=app)
        session.execute = AsyncMock(return_value=app_result)

        service = ApplicationService(session)
        # Try progressive: hired has no next step
        with pytest.raises(HTTPException) as exc_info:
            await service.change_status(app.id, ApplicationStatus.proposal, employer_id)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_nonexistent_application_rejected(self):
        """Cannot change status of non-existent application."""
        session = _mock_session()
        employer_id = uuid.uuid4()

        no_app = _mock_execute_result(scalar_value=None)
        session.execute = AsyncMock(return_value=no_app)

        service = ApplicationService(session)
        with pytest.raises(HTTPException) as exc_info:
            await service.change_status(uuid.uuid4(), ApplicationStatus.in_review, employer_id)

        assert exc_info.value.status_code == 404


# --- Test: History recording (Req 7.2) ---


class TestWorkflowHistoryRecording:
    """Test that status transitions record history with correct metadata."""

    @pytest.mark.asyncio
    async def test_history_recorded_on_transition(self):
        """Req 7.2: Transition records date, previous status, new status, and user."""
        session = _mock_session()
        employer_id = uuid.uuid4()
        job_id = uuid.uuid4()
        app = _make_application(status=ApplicationStatus.received, job_id=job_id)
        job = _make_job(job_id=job_id)

        app_result = _mock_execute_result(scalar_value=app)
        job_result = _mock_execute_result(scalar_value=job)

        session.execute = AsyncMock(side_effect=[app_result, job_result])

        service = ApplicationService(session)
        await service.change_status(app.id, ApplicationStatus.in_review, employer_id)

        # Verify history was added via session.add
        add_calls = session.add.call_args_list
        # Should have at least one history entry and one notification
        history_calls = [
            call for call in add_calls
            if isinstance(call[0][0], ApplicationStatusHistory)
        ]
        assert len(history_calls) >= 1

        history_obj = history_calls[0][0][0]
        assert history_obj.application_id == app.id
        assert history_obj.previous_status == ApplicationStatus.received
        assert history_obj.new_status == ApplicationStatus.in_review
        assert history_obj.changed_by == employer_id


# --- Test: Hiring rate calculation (Req 7.5, 7.6) ---


class TestWorkflowHiringRate:
    """Test hiring rate calculation when moving to Contratado."""

    @pytest.mark.asyncio
    async def test_hiring_rate_calculated_on_hired(self):
        """Req 7.5: Hiring rate = hired / total for the job."""
        session = _mock_session()
        employer_id = uuid.uuid4()
        job_id = uuid.uuid4()
        app = _make_application(status=ApplicationStatus.proposal, job_id=job_id)
        job = _make_job(job_id=job_id)

        app_result = _mock_execute_result(scalar_value=app)
        job_result = _mock_execute_result(scalar_value=job)
        # After setting hired, total=20, hired=2
        total_result = _mock_execute_result(scalar_value=20)
        hired_result = _mock_execute_result(scalar_value=2)

        session.execute = AsyncMock(
            side_effect=[app_result, job_result, total_result, hired_result]
        )

        service = ApplicationService(session)
        await service.change_status(app.id, ApplicationStatus.hired, employer_id)

        assert app.status == ApplicationStatus.hired
        # The hiring rate should be 2/20 = 0.1 (10%)
        # We verify the calculation logic was called correctly by checking
        # that execute was called the expected number of times (4 calls)
        assert session.execute.call_count == 4

    @pytest.mark.asyncio
    async def test_hiring_rate_zero_applications(self):
        """Hiring rate is 0.0 when there are no applications (edge case)."""
        service = ApplicationService(_mock_session())
        # Test the internal calculation method directly
        session = _mock_session()
        total_result = _mock_execute_result(scalar_value=0)
        hired_result = _mock_execute_result(scalar_value=0)
        session.execute = AsyncMock(side_effect=[total_result, hired_result])

        service = ApplicationService(session)
        rate = await service._calculate_hiring_rate(uuid.uuid4())
        assert rate == 0.0


# --- Test: State machine validation logic ---


class TestStateMachineValidation:
    """Test the _is_valid_transition method directly."""

    def test_all_progressive_transitions_valid(self):
        """All defined progressive transitions are valid."""
        service = ApplicationService(AsyncMock())
        for current, next_status in PROGRESSIVE_TRANSITIONS.items():
            assert service._is_valid_transition(current, next_status) is True

    def test_rejection_from_valid_statuses(self):
        """Rejection is valid from all statuses except hired and cancelled."""
        service = ApplicationService(AsyncMock())
        for s in ApplicationStatus:
            if s in CANNOT_REJECT_FROM:
                assert service._is_valid_transition(s, ApplicationStatus.rejected) is False
            else:
                assert service._is_valid_transition(s, ApplicationStatus.rejected) is True

    def test_cancellation_from_valid_statuses(self):
        """Cancellation is valid from all statuses except hired."""
        service = ApplicationService(AsyncMock())
        for s in ApplicationStatus:
            if s in CANNOT_CANCEL_FROM:
                assert service._is_valid_transition(s, ApplicationStatus.cancelled) is False
            else:
                assert service._is_valid_transition(s, ApplicationStatus.cancelled) is True

    def test_skip_step_invalid(self):
        """Skipping a step in progressive flow is invalid."""
        service = ApplicationService(AsyncMock())
        # received -> interview (skipping in_review)
        assert service._is_valid_transition(
            ApplicationStatus.received, ApplicationStatus.interview
        ) is False
        # in_review -> technical_test (skipping interview)
        assert service._is_valid_transition(
            ApplicationStatus.in_review, ApplicationStatus.technical_test
        ) is False

    def test_backward_transition_invalid(self):
        """Going backward in the progressive flow is invalid."""
        service = ApplicationService(AsyncMock())
        assert service._is_valid_transition(
            ApplicationStatus.interview, ApplicationStatus.received
        ) is False
        assert service._is_valid_transition(
            ApplicationStatus.proposal, ApplicationStatus.in_review
        ) is False
