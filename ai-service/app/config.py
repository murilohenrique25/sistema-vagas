from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """AI microservice configuration settings."""

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.0
    # Base URL for OpenAI-compatible providers (Groq, Gemini, OpenRouter, etc.).
    # Leave empty to use the official OpenAI API.
    openai_base_url: str = ""
    # Method used by with_structured_output.
    # "function_calling" works with Groq tool-calling models and OpenAI.
    # "json_schema" is OpenAI's native structured output (not supported by all Groq models).
    openai_structured_output_method: str = "function_calling"

    # Service
    ai_service_host: str = "0.0.0.0"
    ai_service_port: int = 8001
    service_name: str = "ai-recruitment-service"
    service_version: str = "0.1.0"
    environment: str = "development"

    # Backend principal communication
    backend_base_url: str = "http://localhost:8000"
    backend_api_prefix: str = "/v1"
    backend_timeout: int = 30
    backend_retry_attempts: int = 3
    backend_retry_delay: float = 1.0

    # Internal service authentication
    internal_service_token: str = ""

    # Timeouts (seconds)
    pdf_extraction_timeout: int = 60
    candidate_analysis_timeout: int = 60
    job_matching_timeout: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def validate_production(self):
        if self.environment.lower() == "production":
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY é obrigatória em produção")
            if len(self.internal_service_token) < 32:
                raise ValueError("INTERNAL_SERVICE_TOKEN deve ter pelo menos 32 caracteres")
            if "localhost" in self.backend_base_url:
                raise ValueError("BACKEND_BASE_URL não pode usar localhost em produção")
        return self


settings = Settings()
