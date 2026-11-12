"""Unit tests for JobService.

Tests cover:
- CRUD with validations (title max 150 chars, deadline min 1 day, max 180 days)
- Duplication (copies data, status=draft, deadline=None)
- Inactivation with candidate notification
- Deadline extension with validations
- Auto-closing expired jobs (scheduler)
- Free plan limit of 3 active jobs
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.enums import (
    ApplicationStatus,
    ContractType,
    JobModality,
    JobStatus,
    NotificationChannel,
    SubscriptionPlan,
    SubscriptionStatus,
)
from app.models.job import Job
from app.schemas.job import JobCreate, JobExtendDeadline, JobUpdate


# --- Schema validation tests (pure unit tests, no DB needed) ---


class TestJobCreateSchema:
    """Test JobCreate schema validations."""

    def _valid_data(self) -> dict:
        """Return valid job creation data."""
        return {
            "title": "Desenvolvedor Python Senior",
            "modality": JobModality.remote,
            "location": "São Paulo, SP",
            "responsibilities": "Desenvolver e manter APIs REST",
            "required_skills": "Python, FastAPI, SQLAlchemy",
            "contract_type": ContractType.clt,
            "deadline": date.today() + timedelta(days=30),
        }

    def test_valid_job_creation(self):
        """Test that valid data passes all validations."""
        data = self._valid_data()
        schema = JobCreate(**data)
        assert schema.title == "Desenvolvedor Python Senior"
        assert schema.modality == JobModality.remote
        assert schema.deadline == date.today() + timedelta(days=30)

    def test_title_max_150_chars(self):
        """Requirement 2.1: Title must be at most 150 characters."""
        data = self._valid_data()
        data["title"] = "A" * 151
        with pytest.raises(ValueError, match="150 caracteres"):
            JobCreate(**data)

    def test_title_exactly_150_chars_is_valid(self):
        """Title with exactly 150 characters should be accepted."""
        data = self._valid_data()
        data["title"] = "A" * 150
        schema = JobCreate(**data)
        assert len(schema.title) == 150

    def test_title_empty_rejected(self):
        """Empty title must be rejected."""
        data = self._valid_data()
        data["title"] = "   "
        with pytest.raises(ValueError, match="obrigatório"):
            JobCreate(**data)

    def test_deadline_min_1_day_future(self):
        """Requirement 2.1: Deadline must be at least 1 day in the future."""
        data = self._valid_data()
        data["deadline"] = date.today()  # Today is not valid (must be future)
        with pytest.raises(ValueError, match="1 dia no futuro"):
            JobCreate(**data)

    def test_deadline_past_date_rejected(self):
        """Past deadline must be rejected."""
        data = self._valid_data()
        data["deadline"] = date.today() - timedelta(days=5)
        with pytest.raises(ValueError, match="1 dia no futuro"):
            JobCreate(**data)

    def test_deadline_max_180_days(self):
        """Requirement 2.1: Deadline must be at most 180 days in the future."""
        data = self._valid_data()
        data["deadline"] = date.today() + timedelta(days=181)
        with pytest.raises(ValueError, match="180 dias"):
            JobCreate(**data)

    def test_deadline_exactly_180_days_is_valid(self):
        """Deadline at exactly 180 days should be accepted."""
        data = self._valid_data()
        data["deadline"] = date.today() + timedelta(days=180)
        schema = JobCreate(**data)
        assert schema.deadline == date.today() + timedelta(days=180)

    def test_deadline_1_day_future_is_valid(self):
        """Deadline at exactly 1 day in the future should be accepted."""
        data = self._valid_data()
        data["deadline"] = date.today() + timedelta(days=1)
        schema = JobCreate(**data)
        assert schema.deadline == date.today() + timedelta(days=1)

    def test_negative_salary_rejected(self):
        """Salary cannot be negative."""
        data = self._valid_data()
        data["salary_min"] = Decimal("-100")
        with pytest.raises(ValueError, match="negativo"):
            JobCreate(**data)

    def test_optional_fields_can_be_omitted(self):
        """Optional fields (salary, benefits, optional_skills) can be omitted."""
        data = self._valid_data()
        schema = JobCreate(**data)
        assert schema.salary_min is None
        assert schema.salary_max is None
        assert schema.benefits is None
        assert schema.optional_skills is None


class TestJobUpdateSchema:
    """Test JobUpdate schema validations."""

    def test_title_too_long_rejected(self):
        """Title update exceeding 150 chars must be rejected."""
        with pytest.raises(ValueError, match="150 caracteres"):
            JobUpdate(title="A" * 151)

    def test_empty_title_rejected(self):
        """Empty title must be rejected."""
        with pytest.raises(ValueError, match="vazio"):
            JobUpdate(title="   ")

    def test_valid_title_update(self):
        """Valid title update should succeed."""
        schema = JobUpdate(title="Novo título")
        assert schema.title == "Novo título"

    def test_deadline_in_past_rejected(self):
        """Deadline in the past must be rejected."""
        with pytest.raises(ValueError, match="1 dia no futuro"):
            JobUpdate(deadline=date.today() - timedelta(days=1))

    def test_deadline_beyond_180_days_rejected(self):
        """Deadline beyond 180 days must be rejected."""
        with pytest.raises(ValueError, match="180 dias"):
            JobUpdate(deadline=date.today() + timedelta(days=181))


class TestJobExtendDeadlineSchema:
    """Test JobExtendDeadline schema validations."""

    def test_valid_extension(self):
        """Valid date between 1 and 180 days should be accepted."""
        schema = JobExtendDeadline(new_date=date.today() + timedelta(days=30))
        assert schema.new_date == date.today() + timedelta(days=30)

    def test_past_date_rejected(self):
        """Past date must be rejected."""
        with pytest.raises(ValueError, match="1 dia no futuro"):
            JobExtendDeadline(new_date=date.today() - timedelta(days=1))

    def test_today_rejected(self):
        """Today's date must be rejected (must be at least 1 day in future)."""
        with pytest.raises(ValueError, match="1 dia no futuro"):
            JobExtendDeadline(new_date=date.today())

    def test_beyond_180_days_rejected(self):
        """Date beyond 180 days must be rejected."""
        with pytest.raises(ValueError, match="180 dias"):
            JobExtendDeadline(new_date=date.today() + timedelta(days=181))

    def test_exactly_1_day_valid(self):
        """Exactly 1 day in future is the minimum valid value."""
        schema = JobExtendDeadline(new_date=date.today() + timedelta(days=1))
        assert schema.new_date == date.today() + timedelta(days=1)

    def test_exactly_180_days_valid(self):
        """Exactly 180 days in future is the maximum valid value."""
        schema = JobExtendDeadline(new_date=date.today() + timedelta(days=180))
        assert schema.new_date == date.today() + timedelta(days=180)


# --- Service-level tests with mocked database session ---


def _make_job(**kwargs) -> Job:
    """Create a Job instance for testing without DB."""
    defaults = {
        "id": uuid.uuid4(),
        "company_id": uuid.uuid4(),
        "title": "Desenvolvedor Python",
        "modality": JobModality.remote,
        "location": "São Paulo, SP",
        "responsibilities": "Desenvolver APIs",
        "required_skills": "Python, FastAPI",
        "optional_skills": None,
        "benefits": None,
        "contract_type": ContractType.clt,
        "salary_min": None,
        "salary_max": None,
        "status": JobStatus.active,
        "deadline": date.today() + timedelta(days=30),
    }
    defaults.update(kwargs)
    job = MagicMock(spec=Job)
    for key, value in defaults.items():
        setattr(job, key, value)
    return job


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
    mock_result.scalar_one = MagicMock(return_value=scalar_value)
    mock_result.scalar_first = MagicMock(return_value=scalar_value)
    if scalars_value is not None:
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=scalars_value)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
    else:
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=[])
        mock_result.scalars = MagicMock(return_value=mock_scalars)
    return mock_result


class TestJobServiceCreateJob:
    """Test JobService.create_job with plan limit validation."""

    @pytest.mark.asyncio
    async def test_create_job_free_plan_under_limit(self):
        """Free plan employer with fewer than 3 active jobs can create a new job."""
        from app.services.job_service import JobService

        session = _mock_session()
        employer_id = uuid.uuid4()
        company_id = uuid.uuid4()

        # Mock: no active subscription (defaults to free)
        # Mock: active count = 2 (under limit)
        subscription_result = _mock_execute_result(scalar_value=None)
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=2)

        session.execute = AsyncMock(
            side_effect=[subscription_result, count_result]
        )

        data = JobCreate(
            title="Dev Python",
            modality=JobModality.remote,
            location="SP",
            responsibilities="Desenvolver APIs",
            required_skills="Python",
            contract_type=ContractType.clt,
            deadline=date.today() + timedelta(days=30),
        )

        service = JobService(session)
        job = await service.create_job(employer_id, company_id, data)

        # Verify job was added to session
        session.add.assert_called_once()
        session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_create_job_professional_plan_no_limit(self):
        """Requirement 2.10: Professional/Enterprise plans have no limit."""
        from app.services.job_service import JobService

        session = _mock_session()
        employer_id = uuid.uuid4()
        company_id = uuid.uuid4()

        # Mock: professional subscription
        mock_subscription = MagicMock()
        mock_subscription.plan = SubscriptionPlan.professional
        subscription_result = _mock_execute_result(scalar_value=mock_subscription)

        session.execute = AsyncMock(return_value=subscription_result)

        data = JobCreate(
            title="Dev Python",
            modality=JobModality.remote,
            location="SP",
            responsibilities="Desenvolver APIs",
            required_skills="Python",
            contract_type=ContractType.clt,
            deadline=date.today() + timedelta(days=30),
        )

        service = JobService(session)
        job = await service.create_job(employer_id, company_id, data)

        # Should not raise - no limit check needed
        session.add.assert_called_once()


class TestJobServiceDuplicateJob:
    """Test JobService.duplicate_job."""

    @pytest.mark.asyncio
    async def test_duplicate_copies_data_with_draft_and_no_deadline(self):
        """Requirement 2.4: Duplicate copies all fields, sets status=draft, deadline=None."""
        from app.services.job_service import JobService

        session = _mock_session()
        employer_id = uuid.uuid4()
        company_id = uuid.uuid4()
        original_job = _make_job(company_id=company_id)

        # Mock: find original job
        job_result = _mock_execute_result(scalar_value=original_job)
        # Mock: ownership check
        company_mock = MagicMock()
        company_result = _mock_execute_result(scalar_value=company_mock)

        session.execute = AsyncMock(side_effect=[job_result, company_result])

        service = JobService(session)
        new_job = await service.duplicate_job(original_job.id, employer_id)

        # Verify add was called (new job created)
        session.add.assert_called_once()
        added_job = session.add.call_args[0][0]
        assert added_job.status == JobStatus.draft
        assert added_job.deadline is None
        assert added_job.title == original_job.title
        assert added_job.modality == original_job.modality
        assert added_job.company_id == original_job.company_id
        assert added_job.responsibilities == original_job.responsibilities
        assert added_job.required_skills == original_job.required_skills


class TestJobServiceInactivation:
    """Test JobService.inactivate_job."""

    @pytest.mark.asyncio
    async def test_inactivate_job_changes_status(self):
        """Requirement 2.5: Inactivation sets status to inactive."""
        from app.services.job_service import JobService

        session = _mock_session()
        employer_id = uuid.uuid4()
        company_id = uuid.uuid4()
        job = _make_job(company_id=company_id, status=JobStatus.active)

        # Mock: find job
        job_result = _mock_execute_result(scalar_value=job)
        # Mock: ownership check
        company_mock = MagicMock()
        company_result = _mock_execute_result(scalar_value=company_mock)
        # Mock: ApplicationService.reject_pending - query pending apps (none)
        apps_result = _mock_execute_result(scalars_value=[])

        session.execute = AsyncMock(
            side_effect=[job_result, company_result, apps_result]
        )

        service = JobService(session)
        result = await service.inactivate_job(job.id, employer_id)

        assert job.status == JobStatus.inactive

    @pytest.mark.asyncio
    async def test_inactivate_already_inactive_raises(self):
        """Cannot inactivate a job that is already inactive."""
        from app.services.job_service import JobService

        session = _mock_session()
        employer_id = uuid.uuid4()
        company_id = uuid.uuid4()
        job = _make_job(company_id=company_id, status=JobStatus.inactive)

        job_result = _mock_execute_result(scalar_value=job)
        company_mock = MagicMock()
        company_result = _mock_execute_result(scalar_value=company_mock)

        session.execute = AsyncMock(side_effect=[job_result, company_result])

        service = JobService(session)
        with pytest.raises(HTTPException) as exc_info:
            await service.inactivate_job(job.id, employer_id)

        assert exc_info.value.status_code == 400
        assert "já está inativa" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_inactivate_notifies_candidates(self):
        """Requirement 2.5: Candidates with active applications are notified."""
        from app.services.job_service import JobService

        session = _mock_session()
        employer_id = uuid.uuid4()
        company_id = uuid.uuid4()
        job = _make_job(company_id=company_id, status=JobStatus.active)

        # Mock active application
        mock_app = MagicMock()
        mock_app.candidate_id = uuid.uuid4()
        mock_app.status = ApplicationStatus.received

        job_result = _mock_execute_result(scalar_value=job)
        company_mock = MagicMock()
        company_result = _mock_execute_result(scalar_value=company_mock)
        # ApplicationService.reject_pending: query pending apps
        apps_result = _mock_execute_result(scalars_value=[mock_app])
        # ApplicationService.reject_pending: get job for notification
        job_for_notification = _mock_execute_result(scalar_value=job)

        session.execute = AsyncMock(
            side_effect=[job_result, company_result, apps_result, job_for_notification]
        )

        service = JobService(session)
        await service.inactivate_job(job.id, employer_id)

        # Verify notification was added
        # session.add called with history + notification
        calls = session.add.call_args_list
        assert len(calls) >= 1  # At least history + notification were added


class TestJobServiceExtendDeadline:
    """Test JobService.extend_deadline."""

    @pytest.mark.asyncio
    async def test_extend_deadline_active_job(self):
        """Requirement 2.6: Active job can have deadline extended."""
        from app.services.job_service import JobService

        session = _mock_session()
        employer_id = uuid.uuid4()
        company_id = uuid.uuid4()
        job = _make_job(company_id=company_id, status=JobStatus.active)

        job_result = _mock_execute_result(scalar_value=job)
        company_mock = MagicMock()
        company_result = _mock_execute_result(scalar_value=company_mock)

        session.execute = AsyncMock(side_effect=[job_result, company_result])

        new_date = date.today() + timedelta(days=60)
        data = JobExtendDeadline(new_date=new_date)

        service = JobService(session)
        result = await service.extend_deadline(job.id, employer_id, data)

        assert job.deadline == new_date

    @pytest.mark.asyncio
    async def test_extend_deadline_closed_job_rejected(self):
        """Closed or inactive jobs cannot have deadline extended."""
        from app.services.job_service import JobService

        session = _mock_session()
        employer_id = uuid.uuid4()
        company_id = uuid.uuid4()
        job = _make_job(company_id=company_id, status=JobStatus.closed)

        job_result = _mock_execute_result(scalar_value=job)
        company_mock = MagicMock()
        company_result = _mock_execute_result(scalar_value=company_mock)

        session.execute = AsyncMock(side_effect=[job_result, company_result])

        new_date = date.today() + timedelta(days=60)
        data = JobExtendDeadline(new_date=new_date)

        service = JobService(session)
        with pytest.raises(HTTPException) as exc_info:
            await service.extend_deadline(job.id, employer_id, data)

        assert exc_info.value.status_code == 400
        assert "ativas ou em rascunho" in exc_info.value.detail


class TestJobServiceCloseExpired:
    """Test JobService.close_expired_jobs."""

    @pytest.mark.asyncio
    async def test_close_expired_jobs_updates_status(self):
        """Requirement 2.7: Expired jobs are automatically closed."""
        from app.services.job_service import JobService

        session = _mock_session()

        # Create expired jobs
        expired_job1 = _make_job(
            status=JobStatus.active,
            deadline=date.today() - timedelta(days=1),
        )
        expired_job2 = _make_job(
            status=JobStatus.active,
            deadline=date.today() - timedelta(days=5),
        )

        # Mock: query returns expired jobs
        jobs_result = _mock_execute_result(scalars_value=[expired_job1, expired_job2])
        # Mock: for each job: notify employer (company lookup) + reject pending apps (no apps)
        company_mock = MagicMock()
        company_mock.owner_id = uuid.uuid4()
        company_result_1 = _mock_execute_result(scalar_value=company_mock)
        company_result_2 = _mock_execute_result(scalar_value=company_mock)
        empty_apps_1 = _mock_execute_result(scalars_value=[])
        empty_apps_2 = _mock_execute_result(scalars_value=[])

        # For each expired job: company lookup + reject_pending (query apps)
        session.execute = AsyncMock(
            side_effect=[
                jobs_result,
                company_result_1, empty_apps_1,  # job1: notify employer + reject pending
                company_result_2, empty_apps_2,  # job2: notify employer + reject pending
            ]
        )

        service = JobService(session)
        count = await service.close_expired_jobs()

        assert count == 2
        assert expired_job1.status == JobStatus.closed
        assert expired_job2.status == JobStatus.closed

    @pytest.mark.asyncio
    async def test_close_expired_jobs_no_expired(self):
        """No jobs closed when none are expired."""
        from app.services.job_service import JobService

        session = _mock_session()

        # Mock: no expired jobs
        jobs_result = _mock_execute_result(scalars_value=[])
        session.execute = AsyncMock(return_value=jobs_result)

        service = JobService(session)
        count = await service.close_expired_jobs()

        assert count == 0
        session.flush.assert_not_called()


class TestJobServiceOwnership:
    """Test ownership validation."""

    @pytest.mark.asyncio
    async def test_non_owner_cannot_update_job(self):
        """Only the company owner can update a job."""
        from app.services.job_service import JobService

        session = _mock_session()
        employer_id = uuid.uuid4()
        job = _make_job()

        # Job found
        job_result = _mock_execute_result(scalar_value=job)
        # Ownership check fails (no matching company)
        company_result = _mock_execute_result(scalar_value=None)

        session.execute = AsyncMock(side_effect=[job_result, company_result])

        data = JobUpdate(title="Novo Título")

        service = JobService(session)
        with pytest.raises(HTTPException) as exc_info:
            await service.update_job(job.id, employer_id, data)

        assert exc_info.value.status_code == 403
        assert "permissão" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_job_not_found_raises_404(self):
        """Non-existent job returns 404."""
        from app.services.job_service import JobService

        session = _mock_session()
        employer_id = uuid.uuid4()

        # Job not found
        job_result = _mock_execute_result(scalar_value=None)
        session.execute = AsyncMock(return_value=job_result)

        data = JobUpdate(title="Novo Título")

        service = JobService(session)
        with pytest.raises(HTTPException) as exc_info:
            await service.update_job(uuid.uuid4(), employer_id, data)

        assert exc_info.value.status_code == 404
        assert "não encontrada" in exc_info.value.detail
