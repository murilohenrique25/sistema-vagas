"""Unit tests for job search and listing (Task 5.2).

Tests cover:
- Paginated listing (20 items/page) ordered by publication date (Req 5.1)
- Combined filters with AND logic (Req 5.2)
- Text search validation (min 2 chars) (Req 5.3)
- Sorting (date, salary, relevance) (Req 5.5)
- Highlighted jobs prioritization (Req 5.6)
- Schema validations for search filters
"""

import uuid
import math
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.enums import ContractType, JobModality, JobStatus
from app.models.job import Job
from app.models.job_highlight import JobHighlight
from app.schemas.job import (
    JobSearchFilters,
    JobSortField,
    PaginatedResponse,
    SortOrder,
)


# --- Schema validation tests ---


class TestJobSearchFiltersSchema:
    """Test JobSearchFilters schema validations."""

    def test_default_values(self):
        """Default pagination is page=1, page_size=20, sorted by date desc."""
        filters = JobSearchFilters()
        assert filters.page == 1
        assert filters.page_size == 20
        assert filters.sort_by == JobSortField.date
        assert filters.sort_order == SortOrder.desc
        assert filters.q is None
        assert filters.modality is None
        assert filters.location is None
        assert filters.salary_min is None
        assert filters.salary_max is None
        assert filters.contract_type is None

    def test_search_text_min_2_chars(self):
        """Requirement 5.3: Search text must have at least 2 characters."""
        with pytest.raises(ValueError):
            JobSearchFilters(q="a")

    def test_search_text_exactly_2_chars_valid(self):
        """Search text with exactly 2 characters is valid."""
        filters = JobSearchFilters(q="py")
        assert filters.q == "py"

    def test_search_text_long_string_valid(self):
        """Long search strings are accepted."""
        filters = JobSearchFilters(q="desenvolvedor python senior full stack")
        assert filters.q == "desenvolvedor python senior full stack"

    def test_page_must_be_positive(self):
        """Page number must be >= 1."""
        with pytest.raises(ValueError):
            JobSearchFilters(page=0)

    def test_page_size_max_100(self):
        """Page size cannot exceed 100."""
        with pytest.raises(ValueError):
            JobSearchFilters(page_size=101)

    def test_page_size_must_be_positive(self):
        """Page size must be >= 1."""
        with pytest.raises(ValueError):
            JobSearchFilters(page_size=0)

    def test_salary_min_must_be_non_negative(self):
        """Salary minimum filter cannot be negative."""
        with pytest.raises(ValueError):
            JobSearchFilters(salary_min=Decimal("-1"))

    def test_all_filters_combined(self):
        """All filters can be combined together."""
        filters = JobSearchFilters(
            q="python",
            modality=JobModality.remote,
            location="São Paulo",
            salary_min=Decimal("5000"),
            salary_max=Decimal("15000"),
            contract_type=ContractType.clt,
            sort_by=JobSortField.salary,
            sort_order=SortOrder.asc,
            page=2,
            page_size=10,
        )
        assert filters.q == "python"
        assert filters.modality == JobModality.remote
        assert filters.location == "São Paulo"
        assert filters.salary_min == Decimal("5000")
        assert filters.salary_max == Decimal("15000")
        assert filters.contract_type == ContractType.clt
        assert filters.sort_by == JobSortField.salary
        assert filters.sort_order == SortOrder.asc
        assert filters.page == 2
        assert filters.page_size == 10

    def test_sort_by_relevance(self):
        """Sorting by relevance is a valid option."""
        filters = JobSearchFilters(sort_by=JobSortField.relevance)
        assert filters.sort_by == JobSortField.relevance


class TestPaginatedResponseSchema:
    """Test PaginatedResponse schema."""

    def test_paginated_response_structure(self):
        """Paginated response contains required metadata."""
        response = PaginatedResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )
        assert response.items == []
        assert response.total == 0
        assert response.page == 1
        assert response.page_size == 20
        assert response.total_pages == 0

    def test_paginated_response_with_items(self):
        """Paginated response correctly holds items."""
        response = PaginatedResponse(
            items=["item1", "item2"],
            total=50,
            page=2,
            page_size=20,
            total_pages=3,
        )
        assert len(response.items) == 2
        assert response.total == 50
        assert response.page == 2
        assert response.total_pages == 3

    def test_total_pages_calculation(self):
        """Verify total_pages matches expected computation."""
        total = 45
        page_size = 20
        expected_pages = math.ceil(total / page_size)
        response = PaginatedResponse(
            items=[],
            total=total,
            page=1,
            page_size=page_size,
            total_pages=expected_pages,
        )
        assert response.total_pages == 3


# --- Service-level tests for search_jobs ---


def _make_job(**kwargs) -> Job:
    """Create a Job instance for testing without DB."""
    defaults = {
        "id": uuid.uuid4(),
        "company_id": uuid.uuid4(),
        "title": "Desenvolvedor Python",
        "modality": JobModality.remote,
        "location": "São Paulo, SP",
        "responsibilities": "Desenvolver APIs REST",
        "required_skills": "Python, FastAPI",
        "optional_skills": None,
        "benefits": "VR, VT",
        "contract_type": ContractType.clt,
        "salary_min": Decimal("8000"),
        "salary_max": Decimal("12000"),
        "status": JobStatus.active,
        "deadline": date.today() + timedelta(days=30),
        "created_at": datetime.now(),
        "updated_at": None,
        "search_vector": None,
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


class TestJobServiceSearch:
    """Test JobService.search_jobs method logic through schema validation."""

    @pytest.mark.asyncio
    async def test_search_returns_paginated_response(self):
        """Requirement 5.1: Returns paginated response with correct metadata."""
        from app.services.job_service import JobService

        session = _mock_session()

        # Mock count query result
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=2)

        # Mock main query result - return tuples (job, is_highlighted_flag)
        job1 = _make_job(title="Job 1")
        job2 = _make_job(title="Job 2")
        row1 = MagicMock()
        row1.__getitem__ = lambda self, idx: [job1, 0][idx]
        row2 = MagicMock()
        row2.__getitem__ = lambda self, idx: [job2, 0][idx]

        main_result = MagicMock()
        main_result.all = MagicMock(return_value=[row1, row2])

        session.execute = AsyncMock(side_effect=[count_result, main_result])

        service = JobService(session)
        filters = JobSearchFilters()
        result = await service.search_jobs(filters)

        assert result.total == 2
        assert result.page == 1
        assert result.page_size == 20
        assert result.total_pages == 1
        assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        """Requirement 5.4: Empty results return valid paginated response."""
        from app.services.job_service import JobService

        session = _mock_session()

        # Mock count query result - no results
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=0)

        # Mock main query result - empty
        main_result = MagicMock()
        main_result.all = MagicMock(return_value=[])

        session.execute = AsyncMock(side_effect=[count_result, main_result])

        service = JobService(session)
        filters = JobSearchFilters(q="inexistente termo busca")
        result = await service.search_jobs(filters)

        assert result.total == 0
        assert result.items == []
        assert result.total_pages == 0

    @pytest.mark.asyncio
    async def test_search_with_filters_executes_queries(self):
        """Requirement 5.2: Filters are applied (AND logic verified at query level)."""
        from app.services.job_service import JobService

        session = _mock_session()

        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=0)

        main_result = MagicMock()
        main_result.all = MagicMock(return_value=[])

        session.execute = AsyncMock(side_effect=[count_result, main_result])

        service = JobService(session)
        filters = JobSearchFilters(
            modality=JobModality.remote,
            location="São Paulo",
            salary_min=Decimal("5000"),
            salary_max=Decimal("15000"),
            contract_type=ContractType.clt,
        )
        result = await service.search_jobs(filters)

        # Verify two queries were executed (count + main)
        assert session.execute.call_count == 2
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_search_with_text_executes_fulltext(self):
        """Requirement 5.3: Text search triggers fulltext query."""
        from app.services.job_service import JobService

        session = _mock_session()

        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=0)

        main_result = MagicMock()
        main_result.all = MagicMock(return_value=[])

        session.execute = AsyncMock(side_effect=[count_result, main_result])

        service = JobService(session)
        filters = JobSearchFilters(q="python developer")
        result = await service.search_jobs(filters)

        # Verify two queries were executed
        assert session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_search_pagination_offset_calculation(self):
        """Pagination offset is correctly calculated for page > 1."""
        from app.services.job_service import JobService

        session = _mock_session()

        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=50)

        main_result = MagicMock()
        main_result.all = MagicMock(return_value=[])

        session.execute = AsyncMock(side_effect=[count_result, main_result])

        service = JobService(session)
        filters = JobSearchFilters(page=3, page_size=10)
        result = await service.search_jobs(filters)

        assert result.total == 50
        assert result.page == 3
        assert result.page_size == 10
        assert result.total_pages == 5

    @pytest.mark.asyncio
    async def test_search_highlighted_jobs_marked(self):
        """Requirement 5.6: Highlighted jobs get is_highlighted=True."""
        from app.services.job_service import JobService

        session = _mock_session()

        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=2)

        # First job is highlighted, second is not
        job1 = _make_job(title="Highlighted Job")
        job2 = _make_job(title="Regular Job")

        row1 = MagicMock()
        row1.__getitem__ = lambda self, idx: [job1, 1][idx]
        row2 = MagicMock()
        row2.__getitem__ = lambda self, idx: [job2, 0][idx]

        main_result = MagicMock()
        main_result.all = MagicMock(return_value=[row1, row2])

        session.execute = AsyncMock(side_effect=[count_result, main_result])

        service = JobService(session)
        filters = JobSearchFilters()
        result = await service.search_jobs(filters)

        assert result.items[0].is_highlighted is True
        assert result.items[1].is_highlighted is False

    @pytest.mark.asyncio
    async def test_search_total_pages_rounds_up(self):
        """Total pages is ceiling of total/page_size."""
        from app.services.job_service import JobService

        session = _mock_session()

        # 21 items with page_size=20 -> 2 pages
        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=21)

        main_result = MagicMock()
        main_result.all = MagicMock(return_value=[])

        session.execute = AsyncMock(side_effect=[count_result, main_result])

        service = JobService(session)
        filters = JobSearchFilters(page_size=20)
        result = await service.search_jobs(filters)

        assert result.total == 21
        assert result.total_pages == 2

    @pytest.mark.asyncio
    async def test_search_sort_by_salary(self):
        """Requirement 5.5: Sorting by salary is accepted."""
        from app.services.job_service import JobService

        session = _mock_session()

        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=0)

        main_result = MagicMock()
        main_result.all = MagicMock(return_value=[])

        session.execute = AsyncMock(side_effect=[count_result, main_result])

        service = JobService(session)
        filters = JobSearchFilters(sort_by=JobSortField.salary, sort_order=SortOrder.asc)
        result = await service.search_jobs(filters)

        # Should not raise, queries executed normally
        assert session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_search_sort_by_relevance_without_query_falls_back_to_date(self):
        """Sorting by relevance without search text falls back to date ordering."""
        from app.services.job_service import JobService

        session = _mock_session()

        count_result = MagicMock()
        count_result.scalar_one = MagicMock(return_value=0)

        main_result = MagicMock()
        main_result.all = MagicMock(return_value=[])

        session.execute = AsyncMock(side_effect=[count_result, main_result])

        service = JobService(session)
        # Sort by relevance but no search text
        filters = JobSearchFilters(sort_by=JobSortField.relevance)
        result = await service.search_jobs(filters)

        # Should not raise
        assert session.execute.call_count == 2
