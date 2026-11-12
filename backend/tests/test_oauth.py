"""Tests for OAuth2 authentication service and routes."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import create_app
from app.services.oauth_service import OAuthService, OAUTH_PROVIDERS


@pytest.fixture
def app():
    """Create a test app instance."""
    return create_app()


@pytest.fixture
async def client(app):
    """Create an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestOAuthServiceAuthorizationUrl:
    """Tests for get_authorization_url method."""

    def test_google_authorization_url_contains_required_params(self):
        """Google authorization URL includes client_id, redirect_uri, scope."""
        service = OAuthService(db=None)
        url = service.get_authorization_url("google")

        assert "accounts.google.com" in url
        assert f"client_id={settings.google_client_id}" in url
        assert "response_type=code" in url
        assert "scope=" in url
        assert "access_type=offline" in url

    def test_linkedin_authorization_url_contains_required_params(self):
        """LinkedIn authorization URL includes client_id, redirect_uri, scope."""
        service = OAuthService(db=None)
        url = service.get_authorization_url("linkedin")

        assert "linkedin.com" in url
        assert f"client_id={settings.linkedin_client_id}" in url
        assert "response_type=code" in url
        assert "scope=" in url

    def test_unsupported_provider_raises_value_error(self):
        """Unsupported provider raises ValueError."""
        service = OAuthService(db=None)
        with pytest.raises(ValueError, match="Unsupported OAuth provider"):
            service.get_authorization_url("github")


class TestOAuthRoutes:
    """Tests for OAuth2 route endpoints."""

    async def test_oauth_redirect_google(self, client):
        """GET /v1/auth/oauth/google redirects to Google authorization page."""
        response = await client.get("/v1/auth/oauth/google", follow_redirects=False)
        assert response.status_code == 307
        location = response.headers["location"]
        assert "accounts.google.com" in location

    async def test_oauth_redirect_linkedin(self, client):
        """GET /v1/auth/oauth/linkedin redirects to LinkedIn authorization page."""
        response = await client.get("/v1/auth/oauth/linkedin", follow_redirects=False)
        assert response.status_code == 307
        location = response.headers["location"]
        assert "linkedin.com" in location

    async def test_oauth_redirect_unsupported_provider(self, client):
        """GET /v1/auth/oauth/github returns 400 for unsupported provider."""
        response = await client.get("/v1/auth/oauth/github")
        assert response.status_code == 400
        assert "Unsupported OAuth provider" in response.json()["detail"]

    async def test_oauth_callback_missing_code(self, client):
        """GET /v1/auth/oauth/google/callback without code returns 422."""
        response = await client.get("/v1/auth/oauth/google/callback")
        assert response.status_code == 422

    async def test_oauth_callback_unsupported_provider(self, client):
        """GET /v1/auth/oauth/github/callback returns 400 for unsupported provider."""
        response = await client.get("/v1/auth/oauth/github/callback?code=test_code")
        assert response.status_code == 400
        assert "Unsupported OAuth provider" in response.json()["detail"]


class TestOAuthProviderConfig:
    """Tests for OAuth provider configuration."""

    def test_google_provider_config_exists(self):
        """Google provider configuration exists with required fields."""
        assert "google" in OAUTH_PROVIDERS
        config = OAUTH_PROVIDERS["google"]
        assert "authorize_url" in config
        assert "token_url" in config
        assert "userinfo_url" in config
        assert "scopes" in config

    def test_linkedin_provider_config_exists(self):
        """LinkedIn provider configuration exists with required fields."""
        assert "linkedin" in OAUTH_PROVIDERS
        config = OAUTH_PROVIDERS["linkedin"]
        assert "authorize_url" in config
        assert "token_url" in config
        assert "userinfo_url" in config
        assert "scopes" in config

    def test_settings_have_oauth_fields(self):
        """Settings include OAuth2 configuration fields."""
        assert hasattr(settings, "google_client_id")
        assert hasattr(settings, "google_client_secret")
        assert hasattr(settings, "google_redirect_uri")
        assert hasattr(settings, "linkedin_client_id")
        assert hasattr(settings, "linkedin_client_secret")
        assert hasattr(settings, "linkedin_redirect_uri")
