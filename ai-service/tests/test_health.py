import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint_returns_healthy_status():
    """Test that the health check endpoint returns expected structure."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert data["service"] == "ai-recruitment-service"
    assert data["version"] == "0.1.0"
    assert "openai_model" in data
    assert "openai_configured" in data
    assert "backend_url" in data
    assert "backend_configured" in data
    assert "dependencies" in data


@pytest.mark.asyncio
async def test_health_endpoint_shows_degraded_when_openai_not_configured():
    """Test that health check shows degraded status when OpenAI key is empty."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    data = response.json()
    # In test environment without OPENAI_API_KEY, should be degraded
    if not data["openai_configured"]:
        assert data["status"] == "degraded"


@pytest.mark.asyncio
async def test_health_endpoint_does_not_expose_api_key():
    """Test that the health check does not expose the OpenAI API key."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    data = response.json()
    assert "openai_api_key" not in data
    assert "api_key" not in data
    # Check nested dependencies don't contain the key
    assert "openai_api_key" not in data.get("dependencies", {})


@pytest.mark.asyncio
async def test_health_endpoint_includes_dependencies():
    """Test that health check includes dependency status."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    data = response.json()
    deps = data["dependencies"]
    assert "openai" in deps
    assert "backend" in deps
    assert isinstance(deps["openai"], bool)
    assert isinstance(deps["backend"], bool)


@pytest.mark.asyncio
async def test_extract_pdf_rejects_non_pdf():
    """Test that extract-pdf rejects non-PDF files."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/extract-pdf",
            files={"file": ("resume.txt", b"some content", "text/plain")},
        )

    assert response.status_code == 422
    assert "PDF" in response.json()["detail"]


@pytest.mark.asyncio
async def test_analyze_candidates_rejects_empty_list():
    """Test that analyze-candidates rejects empty candidate list."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/analyze-candidates",
            json={"job_id": "job-123", "candidate_ids": []},
        )

    assert response.status_code == 400
    assert "At least one candidate" in response.json()["detail"]


@pytest.mark.asyncio
async def test_analyze_candidates_rejects_over_200():
    """Test that analyze-candidates rejects more than 200 candidates."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/analyze-candidates",
            json={"job_id": "job-123", "candidate_ids": [f"c-{i}" for i in range(201)]},
        )

    assert response.status_code == 400
    assert "200" in response.json()["detail"]


@pytest.mark.asyncio
async def test_match_jobs_requires_candidate_id():
    """Test that match-jobs validates candidate_id presence."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/match-jobs",
            json={"candidate_id": ""},
        )

    assert response.status_code == 400
    assert "Candidate ID" in response.json()["detail"]


@pytest.mark.asyncio
async def test_all_ai_endpoints_registered():
    """Test that all AI endpoints are registered in the app."""
    routes = [route.path for route in app.routes]
    assert "/health" in routes
    assert "/extract-pdf" in routes
    assert "/analyze-candidates" in routes
    assert "/match-jobs" in routes
