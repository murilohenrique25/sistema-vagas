"""Tests for application initialization and configuration."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app


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


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    async def test_root_health(self, client):
        """Root health endpoint returns healthy status."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "app" in data
        assert "version" in data

    async def test_v1_health(self, client):
        """V1 health endpoint returns healthy status."""
        response = await client.get("/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1"


class TestOpenAPIDocs:
    """Tests for OpenAPI documentation availability."""

    async def test_openapi_json_available(self, client):
        """OpenAPI JSON schema is served at configured URL."""
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert data["info"]["title"] == "Sistema Vagas API"

    async def test_swagger_docs_available(self, client):
        """Swagger UI is available at /docs."""
        response = await client.get("/docs")
        assert response.status_code == 200

    async def test_redoc_available(self, client):
        """ReDoc is available at /redoc."""
        response = await client.get("/redoc")
        assert response.status_code == 200


class TestSettings:
    """Tests for application settings."""

    def test_default_settings(self):
        """Settings load with expected defaults."""
        s = Settings()
        assert s.app_name == "Sistema Vagas API"
        assert s.redis_url == "redis://localhost:6379/0"
        assert s.redis_max_connections == 20
        assert s.redis_cache_ttl == 300
        assert s.jwt_algorithm == "HS256"
        assert s.openapi_url == "/openapi.json"

    def test_cors_origins_default(self):
        """CORS origins include localhost for development."""
        s = Settings()
        assert "http://localhost:5173" in s.cors_origins


class TestCleanArchitectureImports:
    """Tests that Clean Architecture layers are properly structured."""

    def test_schemas_importable(self):
        """Schemas package is importable."""
        from app.schemas.base import (  # noqa: F401
            BaseSchema,
            ErrorResponse,
            MessageResponse,
            PaginatedResponse,
            PaginationParams,
        )

    def test_repositories_importable(self):
        """Repository base class is importable."""
        from app.repositories.base import BaseRepository  # noqa: F401

    def test_models_importable(self):
        """Model mixins are importable."""
        from app.models.base import TimestampMixin, UUIDMixin  # noqa: F401

    def test_redis_importable(self):
        """Redis module is importable."""
        from app.core.redis import (  # noqa: F401
            close_redis_pool,
            get_redis,
            init_redis_pool,
        )

    def test_database_importable(self):
        """Database module is importable."""
        from app.core.database import Base, get_session  # noqa: F401
