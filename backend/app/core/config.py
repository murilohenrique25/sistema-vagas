"""Application configuration loaded from environment variables."""

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Sistema Vagas API"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"
    frontend_url: str = "http://localhost:5173"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sistema_vagas"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 20
    redis_cache_ttl: int = 300  # Default cache TTL in seconds (max 300s per design)
    redis_session_ttl: int = 86400  # Session TTL: 24 hours in seconds (per requirement 16.3)

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    email_verification_expire_hours: int = 24
    password_reset_expire_minutes: int = 30
    max_active_jobs_per_company: int = 10
    cnpj_lookup_url: str = "https://brasilapi.com.br/api/cnpj/v1"
    cnpj_lookup_timeout_seconds: int = 8

    # Transactional email (SMTP)
    smtp_enabled: bool = False
    smtp_host: str = "email-ssl.com.br"
    smtp_port: int = 465
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_ssl: bool = True
    smtp_use_tls: bool = False
    smtp_timeout_seconds: int = 15
    email_from: str = ""
    email_from_name: str = "Recruta IA"
    email_reply_to: str = ""

    # OAuth2 - Google
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/v1/auth/oauth/google/callback"

    # OAuth2 - LinkedIn
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_redirect_uri: str = "http://localhost:8000/v1/auth/oauth/linkedin/callback"

    # AI Service
    ai_service_url: str = "http://localhost:8001"
    ai_service_timeout: int = 120  # seconds
    internal_service_token: str = ""

    # Payments
    payment_gateway: str = "sandbox"
    mercadopago_access_token: str = ""
    mercadopago_webhook_secret: str = ""
    mercadopago_payer_email: str = ""
    mercadopago_sandbox: bool = False
    payment_settings_encryption_key: str = ""

    # CORS
    cors_origins: list[str] = ["http://localhost:5173"]

    # OpenAPI / Swagger
    openapi_url: str = "/openapi.json"
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.environment.lower() == "production":
            problems = []
            if self.debug:
                problems.append("DEBUG deve ser false")
            if self.jwt_secret_key == "change-me-in-production" or len(self.jwt_secret_key) < 32:
                problems.append("JWT_SECRET_KEY deve ter pelo menos 32 caracteres aleatórios")
            if self.payment_gateway != "mercadopago":
                problems.append("PAYMENT_GATEWAY deve ser mercadopago")
            if not self.mercadopago_access_token:
                problems.append("MERCADOPAGO_ACCESS_TOKEN é obrigatório")
            if not self.mercadopago_webhook_secret:
                problems.append("MERCADOPAGO_WEBHOOK_SECRET é obrigatório")
            if len(self.internal_service_token) < 32:
                problems.append("INTERNAL_SERVICE_TOKEN deve ter pelo menos 32 caracteres")
            if any("localhost" in origin for origin in self.cors_origins):
                problems.append("CORS_ORIGINS não pode conter localhost")
            if self.smtp_enabled:
                if not self.smtp_host or not self.smtp_username or not self.smtp_password or not self.email_from:
                    problems.append("SMTP habilitado exige SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD e EMAIL_FROM")
                if self.smtp_use_ssl and self.smtp_use_tls:
                    problems.append("SMTP_USE_SSL e SMTP_USE_TLS não podem estar ativos ao mesmo tempo")
            if problems:
                raise ValueError("Configuração de produção inválida: " + "; ".join(problems))
        return self


settings = Settings()
