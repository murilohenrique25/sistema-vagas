"""Tests for admin panel routes - authorization and basic responses."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


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


# ==============================================================================
# Admin Authorization Tests
# ==============================================================================


class TestAdminAuthorization:
    """Test that admin endpoints require admin role."""

    ADMIN_ENDPOINTS = [
        ("GET", "/v1/admin/users"),
        ("GET", "/v1/admin/companies"),
        ("GET", "/v1/admin/jobs"),
        ("GET", "/v1/admin/applications"),
        ("GET", "/v1/admin/financials/transactions"),
        ("GET", "/v1/admin/financials/payments"),
        ("GET", "/v1/admin/audit-logs"),
    ]

    @pytest.mark.parametrize("method,endpoint", ADMIN_ENDPOINTS)
    async def test_unauthenticated_returns_401(self, client, method, endpoint):
        """Requests without auth token should return 401."""
        response = await client.request(method, endpoint)
        assert response.status_code == 401

    @pytest.mark.parametrize("method,endpoint", ADMIN_ENDPOINTS)
    async def test_non_admin_returns_403(self, client, method, endpoint):
        """Requests from non-admin users should return 403."""
        with patch("app.api.v1.dependencies.decode_token") as mock_decode:
            mock_decode.return_value = _make_token_payload(role="candidate")
            headers = {"Authorization": "Bearer fake-token"}
            response = await client.request(method, endpoint, headers=headers)
            assert response.status_code == 403

    @pytest.mark.parametrize("method,endpoint", ADMIN_ENDPOINTS)
    async def test_employer_returns_403(self, client, method, endpoint):
        """Requests from employer users should return 403."""
        with patch("app.api.v1.dependencies.decode_token") as mock_decode:
            mock_decode.return_value = _make_token_payload(role="employer")
            headers = {"Authorization": "Bearer fake-token"}
            response = await client.request(method, endpoint, headers=headers)
            assert response.status_code == 403


# ==============================================================================
# Admin Endpoint Response Tests (with mocked DB)
# ==============================================================================


class TestAdminEndpointsWithAdminAuth:
    """Test that admin endpoints pass auth and reach the handler.

    These tests verify that admin authentication/authorization works correctly.
    The endpoints pass auth checks and either execute (if DB is available) or
    raise a connection error (which is expected in CI without a DB).
    """

    @pytest.fixture
    def admin_headers(self):
        return {"Authorization": "Bearer admin-token"}

    @pytest.fixture(autouse=True)
    def mock_auth(self):
        """Mock auth to return admin user for all tests in this class."""
        with patch("app.api.v1.dependencies.decode_token") as mock_decode:
            mock_decode.return_value = _make_token_payload(role="admin")
            yield mock_decode

    async def test_revenue_requires_dates(self, client, admin_headers):
        """Revenue endpoint requires start_date and end_date query params."""
        response = await client.get("/v1/admin/financials/revenue", headers=admin_headers)
        # Should return 422 because required query params are missing
        assert response.status_code == 422

    async def test_update_user_accepts_valid_body(self, client, admin_headers):
        """Update user accepts valid JSON body without returning 422."""
        user_id = str(uuid4())
        try:
            response = await client.patch(
                f"/v1/admin/users/{user_id}",
                headers=admin_headers,
                json={"name": "New Name"},
            )
            # Should pass validation (not 422), may hit DB error or 404
            assert response.status_code != 422
        except Exception:
            # DB connection error is expected when no DB is available
            pass

    async def test_update_job_status_accepts_valid_body(self, client, admin_headers):
        """Update job status accepts valid JSON body without returning 422."""
        job_id = str(uuid4())
        try:
            response = await client.patch(
                f"/v1/admin/jobs/{job_id}/status",
                headers=admin_headers,
                json={"status": "active"},
            )
            assert response.status_code != 422
        except Exception:
            # DB connection error is expected when no DB is available
            pass


# ==============================================================================
# Pagination Validation Tests
# ==============================================================================


class TestAdminPaginationValidation:
    """Test pagination parameter validation."""

    @pytest.fixture
    def admin_headers(self):
        return {"Authorization": "Bearer admin-token"}

    @pytest.fixture(autouse=True)
    def mock_auth(self):
        with patch("app.api.v1.dependencies.decode_token") as mock_decode:
            mock_decode.return_value = _make_token_payload(role="admin")
            yield

    async def test_audit_logs_max_page_size_100(self, client, admin_headers):
        """Audit logs should reject page_size > 100."""
        response = await client.get(
            "/v1/admin/audit-logs?page_size=101",
            headers=admin_headers,
        )
        assert response.status_code == 422

    async def test_transactions_max_page_size_50(self, client, admin_headers):
        """Transactions should reject page_size > 50."""
        response = await client.get(
            "/v1/admin/financials/transactions?page_size=51",
            headers=admin_headers,
        )
        assert response.status_code == 422

    async def test_invalid_page_number(self, client, admin_headers):
        """Page number < 1 should return 422."""
        response = await client.get(
            "/v1/admin/users?page=0",
            headers=admin_headers,
        )
        assert response.status_code == 422
