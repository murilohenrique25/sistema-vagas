"""Tests for PDF import endpoint (task 6.2).

Tests cover:
- File validation (extension, header, size, pages)
- AI service client communication
- Timeout fallback to manual filling
- Form pre-fill with extracted data
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies import CurrentUser
from app.main import create_app
from app.schemas.resume import PDFImportResponse
from app.services.ai_service_client import (
    AIServiceClient,
    AIServiceError,
    AIServiceTimeoutError,
    AIServiceUnavailableError,
)


# Minimal valid PDF content (magic bytes + minimal structure)
VALID_PDF_HEADER = b"%PDF-1.4\n"
MINIMAL_PDF = VALID_PDF_HEADER + b"1 0 obj\n<< /Type /Page >>\nendobj\n" + b"\n%%EOF"


def _make_candidate():
    """Create a mock candidate user."""
    return CurrentUser(user_id=uuid.uuid4(), role="candidate")


def _make_employer():
    """Create a mock employer user."""
    return CurrentUser(user_id=uuid.uuid4(), role="employer")


def _override_auth(user: CurrentUser):
    """Create a dependency override for authentication."""
    async def _override():
        return user
    return _override


@pytest.fixture
def app():
    """Create a test application instance."""
    return create_app()


@pytest.fixture
def candidate():
    """Create a candidate user."""
    return _make_candidate()


@pytest.fixture
async def client(app, candidate):
    """Create an async HTTP test client with candidate auth."""
    from app.api.v1.dependencies import get_current_user
    app.dependency_overrides[get_current_user] = _override_auth(candidate)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def employer_client(app):
    """Create an async HTTP test client with employer auth."""
    from app.api.v1.dependencies import get_current_user
    employer = _make_employer()
    app.dependency_overrides[get_current_user] = _override_auth(employer)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestPDFImportValidation:
    """Tests for PDF file validation in import-pdf endpoint."""

    async def test_rejects_non_pdf_extension(self, client):
        """Files without .pdf extension are rejected."""
        response = await client.post(
            "/v1/resumes/import-pdf",
            files={"file": ("resume.docx", MINIMAL_PDF, "application/pdf")},
        )
        assert response.status_code == 400
        assert "extensão .pdf" in response.json()["detail"]

    async def test_rejects_no_extension(self, client):
        """Files without any extension are rejected."""
        response = await client.post(
            "/v1/resumes/import-pdf",
            files={"file": ("resume", MINIMAL_PDF, "application/pdf")},
        )
        assert response.status_code == 400
        assert "extensão .pdf" in response.json()["detail"]

    async def test_rejects_file_exceeding_5mb(self, client):
        """Files larger than 5MB are rejected."""
        large_content = VALID_PDF_HEADER + b"x" * (5 * 1024 * 1024 + 1)
        response = await client.post(
            "/v1/resumes/import-pdf",
            files={"file": ("resume.pdf", large_content, "application/pdf")},
        )
        assert response.status_code == 400
        assert "5 MB" in response.json()["detail"]

    async def test_rejects_invalid_pdf_header(self, client):
        """Files without valid PDF magic bytes are rejected."""
        fake_pdf = b"NOT-A-PDF-FILE-CONTENT"
        response = await client.post(
            "/v1/resumes/import-pdf",
            files={"file": ("resume.pdf", fake_pdf, "application/pdf")},
        )
        assert response.status_code == 400
        assert "PDF válido" in response.json()["detail"]

    async def test_rejects_file_exceeding_10_pages(self, client):
        """PDFs with more than 10 pages are rejected."""
        # Create a PDF-like content with 11 /Type /Page entries
        content = VALID_PDF_HEADER
        for i in range(11):
            content += f"{i+1} 0 obj\n<< /Type /Page >>\nendobj\n".encode()
        content += b"\n%%EOF"

        response = await client.post(
            "/v1/resumes/import-pdf",
            files={"file": ("resume.pdf", content, "application/pdf")},
        )
        assert response.status_code == 400
        assert "10 páginas" in response.json()["detail"]

    async def test_accepts_file_with_exactly_10_pages(self, client):
        """PDFs with exactly 10 pages pass validation (AI call may still fail)."""
        content = VALID_PDF_HEADER
        for i in range(10):
            content += f"{i+1} 0 obj\n<< /Type /Page >>\nendobj\n".encode()
        content += b"\n%%EOF"

        # Mock the AI service call to succeed
        mock_result = {
            "personal_data": {"full_name": "Test", "contact_email": None, "phone": None, "location": None},
            "experiences": [],
            "educations": [],
            "skills": [],
            "certifications": [],
            "languages": [],
        }
        with patch.object(AIServiceClient, "extract_pdf", new_callable=AsyncMock, return_value=mock_result):
            response = await client.post(
                "/v1/resumes/import-pdf",
                files={"file": ("resume.pdf", content, "application/pdf")},
            )
        assert response.status_code == 200

    async def test_accepts_file_exactly_5mb(self, client):
        """Files with exactly 5MB pass size validation."""
        # Create content that is exactly 5MB
        padding_size = 5 * 1024 * 1024 - len(VALID_PDF_HEADER) - len(b"\n%%EOF") - len(b"1 0 obj\n<< /Type /Page >>\nendobj\n")
        content = VALID_PDF_HEADER + b"1 0 obj\n<< /Type /Page >>\nendobj\n" + b"x" * padding_size + b"\n%%EOF"
        # Trim to exactly 5MB
        content = content[:5 * 1024 * 1024]
        # Make sure it still has PDF header
        assert content.startswith(VALID_PDF_HEADER)

        mock_result = {
            "personal_data": {"full_name": "Test", "contact_email": None, "phone": None, "location": None},
            "experiences": [],
            "educations": [],
            "skills": [],
            "certifications": [],
            "languages": [],
        }
        with patch.object(AIServiceClient, "extract_pdf", new_callable=AsyncMock, return_value=mock_result):
            response = await client.post(
                "/v1/resumes/import-pdf",
                files={"file": ("resume.pdf", content, "application/pdf")},
            )
        assert response.status_code == 200

    async def test_employer_cannot_import_pdf(self, employer_client):
        """Employers are forbidden from using the PDF import endpoint."""
        response = await employer_client.post(
            "/v1/resumes/import-pdf",
            files={"file": ("resume.pdf", MINIMAL_PDF, "application/pdf")},
        )
        assert response.status_code == 403


class TestPDFImportAIServiceCall:
    """Tests for AI service integration in PDF import."""

    async def test_successful_extraction_returns_data(self, client):
        """Successful AI extraction returns structured resume data."""
        mock_result = {
            "personal_data": {
                "full_name": "João Silva",
                "contact_email": "joao@example.com",
                "phone": "+5511999999999",
                "location": "São Paulo, SP",
            },
            "experiences": [
                {
                    "company": "Acme Corp",
                    "position": "Desenvolvedor",
                    "start_date": "2020-01",
                    "end_date": "2023-06",
                    "description": "Desenvolveu sistemas web",
                }
            ],
            "educations": [
                {
                    "institution": "Universidade ABC",
                    "course": "Ciência da Computação",
                    "degree": "bachelor",
                    "start_date": "2016-02",
                    "end_date": "2020-12",
                }
            ],
            "skills": [
                {"name": "Python", "proficiency": "advanced"},
                {"name": "JavaScript", "proficiency": "intermediate"},
            ],
            "certifications": [
                {"name": "AWS Solutions Architect", "issuer": "Amazon", "obtained_at": "2022-05"}
            ],
            "languages": [
                {"language": "Inglês", "fluency": "advanced"},
                {"language": "Português", "fluency": "native"},
            ],
        }

        with patch.object(AIServiceClient, "extract_pdf", new_callable=AsyncMock, return_value=mock_result):
            response = await client.post(
                "/v1/resumes/import-pdf",
                files={"file": ("resume.pdf", MINIMAL_PDF, "application/pdf")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["extraction_complete"] is True
        assert data["personal_data"]["full_name"] == "João Silva"
        assert data["personal_data"]["contact_email"] == "joao@example.com"
        assert data["personal_data"]["phone"] == "+5511999999999"
        assert data["personal_data"]["location"] == "São Paulo, SP"
        assert len(data["experiences"]) == 1
        assert data["experiences"][0]["company"] == "Acme Corp"
        assert len(data["educations"]) == 1
        assert data["educations"][0]["institution"] == "Universidade ABC"
        assert len(data["skills"]) == 2
        assert len(data["certifications"]) == 1
        assert len(data["languages"]) == 2

    async def test_partial_extraction_returns_nulls(self, client):
        """When AI can't extract some fields, they are returned as null."""
        mock_result = {
            "personal_data": {
                "full_name": "Maria Santos",
                "contact_email": None,
                "phone": None,
                "location": None,
            },
            "experiences": [
                {
                    "company": "Tech Inc",
                    "position": None,
                    "start_date": "2019-03",
                    "end_date": None,
                    "description": None,
                }
            ],
            "educations": [],
            "skills": [],
            "certifications": [],
            "languages": [],
        }

        with patch.object(AIServiceClient, "extract_pdf", new_callable=AsyncMock, return_value=mock_result):
            response = await client.post(
                "/v1/resumes/import-pdf",
                files={"file": ("resume.pdf", MINIMAL_PDF, "application/pdf")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["extraction_complete"] is True
        assert data["personal_data"]["full_name"] == "Maria Santos"
        assert data["personal_data"]["contact_email"] is None
        assert data["personal_data"]["phone"] is None
        assert data["experiences"][0]["position"] is None
        assert data["experiences"][0]["description"] is None


class TestPDFImportTimeout:
    """Tests for timeout handling in PDF import."""

    async def test_timeout_returns_fallback_response(self, client):
        """When AI service times out, returns response for manual filling."""
        with patch.object(
            AIServiceClient, "extract_pdf", new_callable=AsyncMock, side_effect=AIServiceTimeoutError()
        ):
            response = await client.post(
                "/v1/resumes/import-pdf",
                files={"file": ("resume.pdf", MINIMAL_PDF, "application/pdf")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["extraction_complete"] is False
        assert "60 segundos" in data["message"]
        assert "manualmente" in data["message"]

    async def test_unavailable_returns_fallback_response(self, client):
        """When AI service is unavailable, returns response for manual filling."""
        with patch.object(
            AIServiceClient, "extract_pdf", new_callable=AsyncMock, side_effect=AIServiceUnavailableError()
        ):
            response = await client.post(
                "/v1/resumes/import-pdf",
                files={"file": ("resume.pdf", MINIMAL_PDF, "application/pdf")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["extraction_complete"] is False
        assert "indisponível" in data["message"]
        assert "manualmente" in data["message"]

    async def test_ai_error_returns_502(self, client):
        """When AI service returns an error, returns 502."""
        with patch.object(
            AIServiceClient,
            "extract_pdf",
            new_callable=AsyncMock,
            side_effect=AIServiceError("Internal processing error", status_code=500),
        ):
            response = await client.post(
                "/v1/resumes/import-pdf",
                files={"file": ("resume.pdf", MINIMAL_PDF, "application/pdf")},
            )

        assert response.status_code == 502
        assert "serviço de extração" in response.json()["detail"]


class TestAIServiceClient:
    """Tests for the AIServiceClient class."""

    async def test_extract_pdf_sends_correct_request(self):
        """extract_pdf sends multipart form data with file."""
        import httpx

        mock_response = httpx.Response(
            200,
            json={
                "personal_data": {"full_name": "Test"},
                "experiences": [],
                "educations": [],
                "skills": [],
                "certifications": [],
                "languages": [],
            },
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as mock_post:
            client = AIServiceClient()
            result = await client.extract_pdf(b"%PDF-1.4 content", "test.pdf")

        assert result["personal_data"]["full_name"] == "Test"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "files" in call_kwargs.kwargs

    async def test_extract_pdf_timeout_raises_error(self):
        """extract_pdf raises AIServiceTimeoutError on timeout."""
        import httpx

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=httpx.TimeoutException("timeout")):
            client = AIServiceClient()
            with pytest.raises(AIServiceTimeoutError):
                await client.extract_pdf(b"%PDF-1.4 content", "test.pdf")

    async def test_extract_pdf_connect_error_raises_unavailable(self):
        """extract_pdf raises AIServiceUnavailableError on connection failure."""
        import httpx

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=httpx.ConnectError("refused")):
            client = AIServiceClient()
            with pytest.raises(AIServiceUnavailableError):
                await client.extract_pdf(b"%PDF-1.4 content", "test.pdf")

    async def test_extract_pdf_non_200_raises_error(self):
        """extract_pdf raises AIServiceError for non-200 responses."""
        import httpx

        mock_response = httpx.Response(
            422,
            json={"detail": "Invalid PDF content"},
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            client = AIServiceClient()
            with pytest.raises(AIServiceError) as exc_info:
                await client.extract_pdf(b"%PDF-1.4 content", "test.pdf")
            assert exc_info.value.status_code == 422
            assert "Invalid PDF content" in exc_info.value.message
