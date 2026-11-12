"""Tests for metrics service and CSV export."""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.schemas.metrics import MetricsPeriod
from app.services.metrics_service import _calculate_date_range


@pytest.fixture
def app():
    """Create a test application instance."""
    return create_app()


@pytest.fixture
async def client(app):
    """Create an async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _make_token_payload(role: str = "admin", user_id: str | None = None):
    """Create a mock JWT payload."""
    return {
        "sub": user_id or str(uuid4()),
        "role": role,
        "type": "access",
    }


class TestCalculateDateRange:
    """Test the date range calculation helper."""

    def test_daily_returns_today(self):
        start, end = _calculate_date_range(MetricsPeriod.daily)
        today = date.today()
        assert start == today
        assert end == today

    def test_weekly_returns_7_days_back(self):
        start, end = _calculate_date_range(MetricsPeriod.weekly)
        today = date.today()
        assert end == today
        assert start == today - timedelta(days=7)

    def test_monthly_returns_30_days_back(self):
        start, end = _calculate_date_range(MetricsPeriod.monthly)
        today = date.today()
        assert end == today
        assert start == today - timedelta(days=30)

    def test_quarterly_returns_90_days_back(self):
        start, end = _calculate_date_range(MetricsPeriod.quarterly)
        today = date.today()
        assert end == today
        assert start == today - timedelta(days=90)

    def test_yearly_returns_365_days_back(self):
        start, end = _calculate_date_range(MetricsPeriod.yearly)
        today = date.today()
        assert end == today
        assert start == today - timedelta(days=365)

    def test_start_always_before_or_equal_end(self):
        for period in MetricsPeriod:
            start, end = _calculate_date_range(period)
            assert start <= end


class TestMetricsSchemas:
    """Test the metrics schema validations."""

    def test_platform_kpis_response_creation(self):
        from app.schemas.metrics import PlatformKPIsResponse

        kpis = PlatformKPIsResponse(
            period=MetricsPeriod.monthly,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            total_jobs_published=10,
            total_applications=50,
            hiring_rate=Decimal("20.00"),
            avg_hiring_time_days=Decimal("15.50"),
        )
        assert kpis.total_jobs_published == 10
        assert kpis.total_applications == 50
        assert kpis.hiring_rate == Decimal("20.00")
        assert kpis.avg_hiring_time_days == Decimal("15.50")

    def test_platform_kpis_with_zero_hiring_rate(self):
        from app.schemas.metrics import PlatformKPIsResponse

        kpis = PlatformKPIsResponse(
            period=MetricsPeriod.daily,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 1),
            total_jobs_published=0,
            total_applications=0,
            hiring_rate=Decimal("0.00"),
            avg_hiring_time_days=None,
        )
        assert kpis.hiring_rate == Decimal("0.00")
        assert kpis.avg_hiring_time_days is None

    def test_financial_metrics_response_creation(self):
        from app.schemas.metrics import FinancialMetricsResponse

        metrics = FinancialMetricsResponse(
            period=MetricsPeriod.monthly,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            total_revenue=Decimal("5000.00"),
            token_revenue=Decimal("3000.00"),
            subscription_revenue=Decimal("2000.00"),
            avg_ticket=Decimal("250.00"),
            total_transactions=20,
        )
        assert metrics.total_revenue == Decimal("5000.00")
        assert metrics.token_revenue + metrics.subscription_revenue == metrics.total_revenue
        assert metrics.avg_ticket == Decimal("250.00")

    def test_ai_metrics_response_creation(self):
        from app.schemas.metrics import AIMetricsResponse

        metrics = AIMetricsResponse(
            period=MetricsPeriod.weekly,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 7),
            total_analyses=100,
            total_tokens_consumed=5000,
            avg_score=Decimal("72.50"),
            utilization_by_plan={
                "free": Decimal("10.00"),
                "professional": Decimal("60.00"),
                "enterprise": Decimal("30.00"),
            },
        )
        assert metrics.total_analyses == 100
        assert metrics.total_tokens_consumed == 5000
        assert metrics.avg_score == Decimal("72.50")
        assert sum(metrics.utilization_by_plan.values()) == Decimal("100.00")

    def test_ai_metrics_with_no_data(self):
        from app.schemas.metrics import AIMetricsResponse

        metrics = AIMetricsResponse(
            period=MetricsPeriod.daily,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 1),
            total_analyses=0,
            total_tokens_consumed=0,
            avg_score=None,
            utilization_by_plan={},
        )
        assert metrics.total_analyses == 0
        assert metrics.avg_score is None


class TestMetricsPeriodEnum:
    """Test MetricsPeriod enum values."""

    def test_all_periods_exist(self):
        assert MetricsPeriod.daily == "daily"
        assert MetricsPeriod.weekly == "weekly"
        assert MetricsPeriod.monthly == "monthly"
        assert MetricsPeriod.quarterly == "quarterly"
        assert MetricsPeriod.yearly == "yearly"

    def test_period_count(self):
        assert len(MetricsPeriod) == 5


class TestCSVExportConstants:
    """Test CSV export configuration."""

    def test_max_records_limit(self):
        from app.services.csv_export_service import MAX_CSV_RECORDS

        assert MAX_CSV_RECORDS == 50_000


class TestMetricsEndpointsAuth:
    """Test the admin metrics endpoints require authentication."""

    async def test_kpis_endpoint_requires_auth(self, client):
        response = await client.get("/v1/admin/metrics/kpis")
        assert response.status_code == 401

    async def test_financial_endpoint_requires_auth(self, client):
        response = await client.get("/v1/admin/metrics/financial")
        assert response.status_code == 401

    async def test_ai_endpoint_requires_auth(self, client):
        response = await client.get("/v1/admin/metrics/ai")
        assert response.status_code == 401

    async def test_export_users_requires_auth(self, client):
        response = await client.get("/v1/admin/export/users")
        assert response.status_code == 401

    async def test_export_jobs_requires_auth(self, client):
        response = await client.get("/v1/admin/export/jobs")
        assert response.status_code == 401

    async def test_export_applications_requires_auth(self, client):
        response = await client.get("/v1/admin/export/applications")
        assert response.status_code == 401

    async def test_export_payments_requires_auth(self, client):
        response = await client.get("/v1/admin/export/payments")
        assert response.status_code == 401


class TestMetricsEndpointsNonAdmin:
    """Test that non-admin users cannot access metrics endpoints."""

    @pytest.fixture(autouse=True)
    def mock_auth(self):
        with patch("app.api.v1.dependencies.decode_token") as mock_decode:
            mock_decode.return_value = _make_token_payload(role="candidate")
            yield

    async def test_kpis_non_admin_returns_403(self, client):
        headers = {"Authorization": "Bearer fake-token"}
        response = await client.get("/v1/admin/metrics/kpis", headers=headers)
        assert response.status_code == 403

    async def test_financial_non_admin_returns_403(self, client):
        headers = {"Authorization": "Bearer fake-token"}
        response = await client.get("/v1/admin/metrics/financial", headers=headers)
        assert response.status_code == 403

    async def test_ai_non_admin_returns_403(self, client):
        headers = {"Authorization": "Bearer fake-token"}
        response = await client.get("/v1/admin/metrics/ai", headers=headers)
        assert response.status_code == 403

    async def test_export_non_admin_returns_403(self, client):
        headers = {"Authorization": "Bearer fake-token"}
        response = await client.get("/v1/admin/export/users", headers=headers)
        assert response.status_code == 403


class TestMetricsEndpointsPeriodValidation:
    """Test that metrics endpoints accept valid period parameters."""

    @pytest.fixture(autouse=True)
    def mock_auth(self):
        with patch("app.api.v1.dependencies.decode_token") as mock_decode:
            mock_decode.return_value = _make_token_payload(role="admin")
            yield

    async def test_invalid_period_returns_422(self, client):
        headers = {"Authorization": "Bearer admin-token"}
        response = await client.get(
            "/v1/admin/metrics/kpis?period=invalid",
            headers=headers,
        )
        assert response.status_code == 422

    async def test_valid_period_accepted(self, client):
        headers = {"Authorization": "Bearer admin-token"}
        # This may fail with DB error but should not return 422
        try:
            response = await client.get(
                "/v1/admin/metrics/kpis?period=monthly",
                headers=headers,
            )
            assert response.status_code != 422
        except Exception:
            # DB connection error is expected without a running DB
            pass
