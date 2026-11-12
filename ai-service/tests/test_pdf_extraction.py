"""Tests for PDF extraction endpoint and service."""

import io
import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.resume import (
    CertificationData,
    EducationData,
    ExperienceData,
    ExtractedResume,
    LanguageData,
    PersonalData,
    SkillData,
)
from app.services.pdf_extractor import _parse_llm_response, extract_text_from_pdf


client = TestClient(app)


# --- Schema Tests ---


class TestResumeSchemas:
    """Test Pydantic schemas for resume extraction."""

    def test_personal_data_all_none(self):
        data = PersonalData()
        assert data.full_name is None
        assert data.contact_email is None
        assert data.phone is None
        assert data.location is None

    def test_personal_data_with_values(self):
        data = PersonalData(
            full_name="John Doe",
            contact_email="john@example.com",
            phone="+55 11 99999-0000",
            location="São Paulo, SP",
        )
        assert data.full_name == "John Doe"
        assert data.contact_email == "john@example.com"

    def test_extracted_resume_empty(self):
        resume = ExtractedResume()
        assert resume.personal_data.full_name is None
        assert resume.experiences == []
        assert resume.educations == []
        assert resume.skills == []
        assert resume.certifications == []
        assert resume.languages == []

    def test_extracted_resume_with_data(self):
        resume = ExtractedResume(
            personal_data=PersonalData(full_name="Ana Silva"),
            experiences=[ExperienceData(company="ACME", position="Developer")],
            educations=[EducationData(institution="USP", course="Computer Science")],
            skills=[SkillData(name="Python", proficiency="advanced")],
            certifications=[CertificationData(name="AWS SAA", issuer="Amazon")],
            languages=[LanguageData(language="English", fluency="advanced")],
        )
        assert resume.personal_data.full_name == "Ana Silva"
        assert len(resume.experiences) == 1
        assert resume.experiences[0].company == "ACME"
        assert len(resume.skills) == 1
        assert resume.skills[0].name == "Python"


# --- LLM Response Parsing Tests ---


class TestParseLLMResponse:
    """Test the LLM response parser."""

    def test_parse_valid_json(self):
        response = json.dumps({
            "personal_data": {
                "full_name": "Maria Costa",
                "contact_email": "maria@email.com",
                "phone": "+55 21 98888-0000",
                "location": "Rio de Janeiro, RJ",
            },
            "experiences": [
                {
                    "company": "Tech Corp",
                    "position": "Backend Developer",
                    "start_date": "2020-01",
                    "end_date": None,
                    "description": "Developed APIs",
                }
            ],
            "educations": [
                {
                    "institution": "UFRJ",
                    "course": "Engenharia de Software",
                    "degree": "bachelor",
                    "start_date": "2016-03",
                    "end_date": "2020-12",
                }
            ],
            "skills": [{"name": "Python", "proficiency": "advanced"}],
            "certifications": [{"name": "AWS SAA", "issuer": "Amazon", "obtained_at": "2023-06"}],
            "languages": [{"language": "English", "fluency": "advanced"}],
        })

        result = _parse_llm_response(response)
        assert result.personal_data.full_name == "Maria Costa"
        assert result.personal_data.contact_email == "maria@email.com"
        assert len(result.experiences) == 1
        assert result.experiences[0].company == "Tech Corp"
        assert result.experiences[0].end_date is None
        assert len(result.educations) == 1
        assert result.educations[0].degree == "bachelor"
        assert len(result.skills) == 1
        assert len(result.certifications) == 1
        assert len(result.languages) == 1

    def test_parse_json_with_markdown_code_block(self):
        response = '```json\n{"personal_data": {"full_name": "Test"}, "experiences": [], "educations": [], "skills": [], "certifications": [], "languages": []}\n```'

        result = _parse_llm_response(response)
        assert result.personal_data.full_name == "Test"

    def test_parse_invalid_json_returns_empty(self):
        result = _parse_llm_response("this is not json at all")
        assert result.personal_data.full_name is None
        assert result.experiences == []

    def test_parse_empty_sections(self):
        response = json.dumps({
            "personal_data": {"full_name": "Empty Resume"},
            "experiences": [],
            "educations": [],
            "skills": [],
            "certifications": [],
            "languages": [],
        })

        result = _parse_llm_response(response)
        assert result.personal_data.full_name == "Empty Resume"
        assert result.experiences == []

    def test_parse_null_fields(self):
        response = json.dumps({
            "personal_data": {
                "full_name": "Partial Data",
                "contact_email": None,
                "phone": None,
                "location": None,
            },
            "experiences": [{"company": "ACME", "position": None, "start_date": None, "end_date": None, "description": None}],
            "educations": [],
            "skills": [],
            "certifications": [],
            "languages": [],
        })

        result = _parse_llm_response(response)
        assert result.personal_data.full_name == "Partial Data"
        assert result.personal_data.contact_email is None
        assert result.experiences[0].company == "ACME"
        assert result.experiences[0].position is None

    def test_parse_missing_sections_default_empty(self):
        response = json.dumps({"personal_data": {"full_name": "Minimal"}})
        result = _parse_llm_response(response)
        assert result.personal_data.full_name == "Minimal"
        assert result.experiences == []
        assert result.educations == []


# --- PDF Text Extraction Tests ---


class TestExtractTextFromPDF:
    """Test PDF text extraction with pdfplumber."""

    def test_invalid_bytes_raises_value_error(self):
        with pytest.raises(ValueError, match="Failed to read PDF"):
            extract_text_from_pdf(b"not a pdf file at all")

    def test_valid_pdf_with_text(self):
        """Test extracting text from a minimal valid PDF."""
        import pdfplumber
        from reportlab.pdfgen import canvas as _  # noqa: F401
        # Create a simple PDF in memory
        from io import BytesIO
        from reportlab.pdfgen import canvas

        buffer = BytesIO()
        c = canvas.Canvas(buffer)
        c.drawString(100, 750, "John Doe - Software Engineer")
        c.drawString(100, 730, "john@example.com")
        c.showPage()
        c.save()
        pdf_bytes = buffer.getvalue()

        text, num_pages = extract_text_from_pdf(pdf_bytes)
        assert num_pages == 1
        assert "John Doe" in text


# --- Router Endpoint Tests ---


class TestExtractPDFEndpoint:
    """Test the POST /extract-pdf endpoint."""

    def test_reject_non_pdf_extension(self):
        response = client.post(
            "/extract-pdf",
            files={"file": ("resume.txt", b"some text content", "text/plain")},
        )
        assert response.status_code == 422
        assert "PDF" in response.json()["detail"]

    def test_reject_file_too_large(self):
        # Create content larger than 5MB with PDF magic bytes
        large_content = b"%PDF-1.4" + b"\x00" * (6 * 1024 * 1024)
        response = client.post(
            "/extract-pdf",
            files={"file": ("resume.pdf", large_content, "application/pdf")},
        )
        assert response.status_code == 413
        assert "5 MB" in response.json()["detail"]

    def test_reject_invalid_pdf_content(self):
        response = client.post(
            "/extract-pdf",
            files={"file": ("resume.pdf", b"not a real pdf", "application/pdf")},
        )
        assert response.status_code == 422
        assert "valid PDF" in response.json()["detail"]

    def test_reject_too_many_pages(self):
        """Test that PDFs with >10 pages are rejected."""
        # Create a multi-page PDF
        try:
            from reportlab.pdfgen import canvas as rc
        except ImportError:
            pytest.skip("reportlab not installed")

        buffer = io.BytesIO()
        c = rc.Canvas(buffer)
        for i in range(11):
            c.drawString(100, 750, f"Page {i + 1}")
            c.showPage()
        c.save()
        pdf_bytes = buffer.getvalue()

        response = client.post(
            "/extract-pdf",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 422
        assert "10 pages" in response.json()["detail"]

    @patch("app.routers.pdf.extract_from_pdf")
    def test_successful_extraction(self, mock_extract):
        """Test successful PDF extraction with mocked LLM."""
        mock_extract.return_value = ExtractedResume(
            personal_data=PersonalData(full_name="Test User", contact_email="test@test.com"),
            experiences=[ExperienceData(company="ACME", position="Developer")],
            educations=[],
            skills=[SkillData(name="Python", proficiency="advanced")],
            certifications=[],
            languages=[],
        )

        # Create a minimal valid PDF
        try:
            from reportlab.pdfgen import canvas as rc
        except ImportError:
            pytest.skip("reportlab not installed")

        buffer = io.BytesIO()
        c = rc.Canvas(buffer)
        c.drawString(100, 750, "Test User - Developer")
        c.showPage()
        c.save()
        pdf_bytes = buffer.getvalue()

        response = client.post(
            "/extract-pdf",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["personal_data"]["full_name"] == "Test User"
        assert data["personal_data"]["contact_email"] == "test@test.com"
        assert len(data["experiences"]) == 1
        assert data["experiences"][0]["company"] == "ACME"
        assert len(data["skills"]) == 1

    @patch("app.routers.pdf.extract_from_pdf")
    def test_timeout_returns_504(self, mock_extract):
        """Test that a timeout returns 504."""
        mock_extract.side_effect = TimeoutError("PDF extraction timed out")

        try:
            from reportlab.pdfgen import canvas as rc
        except ImportError:
            pytest.skip("reportlab not installed")

        buffer = io.BytesIO()
        c = rc.Canvas(buffer)
        c.drawString(100, 750, "Test")
        c.showPage()
        c.save()
        pdf_bytes = buffer.getvalue()

        response = client.post(
            "/extract-pdf",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 504
        assert "timed out" in response.json()["detail"]

    @patch("app.routers.pdf.extract_from_pdf")
    def test_null_fields_in_response(self, mock_extract):
        """Test that non-extractable fields are returned as null."""
        mock_extract.return_value = ExtractedResume(
            personal_data=PersonalData(full_name="Partial", contact_email=None, phone=None, location=None),
            experiences=[],
            educations=[],
            skills=[],
            certifications=[],
            languages=[],
        )

        try:
            from reportlab.pdfgen import canvas as rc
        except ImportError:
            pytest.skip("reportlab not installed")

        buffer = io.BytesIO()
        c = rc.Canvas(buffer)
        c.drawString(100, 750, "Partial Info")
        c.showPage()
        c.save()
        pdf_bytes = buffer.getvalue()

        response = client.post(
            "/extract-pdf",
            files={"file": ("resume.pdf", pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["personal_data"]["full_name"] == "Partial"
        assert data["personal_data"]["contact_email"] is None
        assert data["personal_data"]["phone"] is None
        assert data["experiences"] == []
