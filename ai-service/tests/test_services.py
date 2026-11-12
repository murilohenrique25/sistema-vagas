"""Tests for AI service layer: LLM integration and BackendClient."""

import os

import pytest

from app.services.llm import (
    BaseState,
    CandidateAnalysisState,
    JobMatchingState,
    PDFExtractionState,
    create_graph_builder,
    get_llm,
)
from app.services.backend_client import BackendClient, BackendClientError


class TestLLMService:
    """Tests for the LLM service integration."""

    def test_get_llm_returns_chat_openai_instance(self, monkeypatch):
        """Test that get_llm returns a configured ChatOpenAI instance."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-testing")
        llm = get_llm()
        assert llm is not None
        assert llm.temperature == 0.0

    def test_get_llm_with_custom_temperature(self, monkeypatch):
        """Test that get_llm accepts custom temperature."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-for-testing")
        llm = get_llm(temperature=0.7)
        assert llm.temperature == 0.7

    def test_create_graph_builder_with_default_state(self):
        """Test that create_graph_builder works with default BaseState."""
        builder = create_graph_builder()
        assert builder is not None

    def test_create_graph_builder_with_pdf_state(self):
        """Test that create_graph_builder works with PDFExtractionState."""
        builder = create_graph_builder(PDFExtractionState)
        assert builder is not None

    def test_create_graph_builder_with_candidate_state(self):
        """Test that create_graph_builder works with CandidateAnalysisState."""
        builder = create_graph_builder(CandidateAnalysisState)
        assert builder is not None

    def test_create_graph_builder_with_job_matching_state(self):
        """Test that create_graph_builder works with JobMatchingState."""
        builder = create_graph_builder(JobMatchingState)
        assert builder is not None

    def test_base_state_has_expected_keys(self):
        """Test that BaseState TypedDict has the expected fields."""
        annotations = BaseState.__annotations__
        assert "input" in annotations
        assert "output" in annotations
        assert "error" in annotations

    def test_pdf_extraction_state_has_expected_keys(self):
        """Test that PDFExtractionState has the expected fields."""
        annotations = PDFExtractionState.__annotations__
        assert "pdf_text" in annotations
        assert "extracted_data" in annotations
        assert "error" in annotations

    def test_candidate_analysis_state_has_expected_keys(self):
        """Test that CandidateAnalysisState has the expected fields."""
        annotations = CandidateAnalysisState.__annotations__
        assert "job_requirements" in annotations
        assert "candidate_resumes" in annotations
        assert "scores" in annotations
        assert "error" in annotations

    def test_job_matching_state_has_expected_keys(self):
        """Test that JobMatchingState has the expected fields."""
        annotations = JobMatchingState.__annotations__
        assert "candidate_profile" in annotations
        assert "active_jobs" in annotations
        assert "matches" in annotations
        assert "error" in annotations


class TestBackendClient:
    """Tests for the BackendClient internal HTTP REST communication."""

    def test_backend_client_initializes_with_config(self):
        """Test that BackendClient initializes with expected configuration."""
        client = BackendClient()
        assert client._base_url == "http://localhost:8000/v1"
        assert client._timeout == 30
        assert client._retry_attempts == 3

    def test_backend_client_headers_include_service_name(self):
        """Test that request headers include the service name."""
        client = BackendClient()
        headers = client._get_headers()
        assert headers["Content-Type"] == "application/json"
        assert headers["X-Service-Name"] == "ai-recruitment-service"

    def test_backend_client_headers_include_auth_when_token_set(self, monkeypatch):
        """Test that headers include Authorization when internal token is set."""
        from app.config import settings

        original_token = settings.internal_service_token
        monkeypatch.setattr(settings, "internal_service_token", "test-token-123")
        client = BackendClient()
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer test-token-123"

    def test_backend_client_headers_no_auth_when_token_empty(self):
        """Test that headers do not include Authorization when token is empty."""
        client = BackendClient()
        headers = client._get_headers()
        # Default token is empty string
        assert "Authorization" not in headers

    def test_backend_client_error_is_exception(self):
        """Test that BackendClientError is a proper exception."""
        error = BackendClientError("test error")
        assert str(error) == "test error"
        assert isinstance(error, Exception)

    @pytest.mark.asyncio
    async def test_check_health_returns_false_on_connection_error(self):
        """Test that check_health returns False when backend is unreachable."""
        client = BackendClient()
        # Backend isn't running in test, so this should return False
        result = await client.check_health()
        assert result is False
