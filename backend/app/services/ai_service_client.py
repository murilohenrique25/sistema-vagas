"""Client for communicating with the AI microservice with circuit breaker pattern."""

import asyncio
import logging
import time
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _internal_headers() -> dict[str, str]:
    return {"X-Internal-Service-Token": settings.internal_service_token} if settings.internal_service_token else {}

# Timeout for PDF extraction (60 seconds as per requirement 4.2/4.6)
PDF_EXTRACTION_TIMEOUT = 60.0
# Timeout for candidate analysis (60 seconds per requirement 8.1)
ANALYZE_CANDIDATES_TIMEOUT = 60.0
# Timeout for job matching (30 seconds per requirement 9.1)
JOB_MATCHING_TIMEOUT = 30.0


class AIServiceError(Exception):
    """Raised when the AI service returns an error."""

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class AIServiceTimeoutError(AIServiceError):
    """Raised when the AI service does not respond within the timeout."""

    def __init__(self, timeout: float = 60.0):
        super().__init__(
            f"O serviço de IA não respondeu dentro do tempo limite de {int(timeout)} segundos",
            status_code=504,
        )


class AIServiceUnavailableError(AIServiceError):
    """Raised when the AI service is unreachable."""

    def __init__(self):
        super().__init__(
            "O serviço de IA está indisponível no momento",
            status_code=503,
        )


class CircuitBreakerOpenError(AIServiceError):
    """Raised when the circuit breaker is open and requests are not allowed."""

    def __init__(self):
        super().__init__(
            "O serviço de IA está temporariamente indisponível. Tente novamente em alguns segundos.",
            status_code=503,
        )


class CircuitBreaker:
    """Circuit breaker pattern implementation.

    States:
    - CLOSED: Normal operation, requests pass through.
    - OPEN: Requests are blocked after consecutive failures.
    - HALF_OPEN: A single request is allowed to test if the service recovered.

    Opens after `failure_threshold` consecutive failures.
    Transitions to HALF_OPEN after `recovery_timeout` seconds.
    Closes again on a successful request in HALF_OPEN state.
    """

    STATE_CLOSED = "closed"
    STATE_OPEN = "open"
    STATE_HALF_OPEN = "half_open"

    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = self.STATE_CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None

    @property
    def state(self) -> str:
        """Get current circuit breaker state, considering time-based transitions."""
        if self._state == self.STATE_OPEN and self._last_failure_time is not None:
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                self._state = self.STATE_HALF_OPEN
        return self._state

    def record_success(self) -> None:
        """Record a successful call. Resets the circuit breaker to closed."""
        self._failure_count = 0
        self._state = self.STATE_CLOSED
        self._last_failure_time = None

    def record_failure(self) -> None:
        """Record a failed call. Opens the circuit after threshold is reached."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = self.STATE_OPEN
            logger.warning(
                "Circuit breaker OPEN after %d consecutive failures",
                self._failure_count,
            )

    def allow_request(self) -> bool:
        """Check if a request is allowed through the circuit breaker."""
        current_state = self.state
        if current_state == self.STATE_CLOSED:
            return True
        if current_state == self.STATE_HALF_OPEN:
            return True
        return False


class AIServiceClient:
    """HTTP client for the AI microservice with circuit breaker.

    Implements:
    - PDF extraction (Req 4.1, 4.2, 4.6)
    - Candidate analysis (Req 8.1)
    - Job matching (Req 9.1)
    - Circuit breaker (opens after 3 failures, half-open after 30s)
    """

    def __init__(self):
        self.base_url = settings.ai_service_url
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30.0,
        )

    async def extract_pdf(self, file_bytes: bytes, filename: str) -> dict[str, Any]:
        """Send a PDF file to the AI service for structured data extraction.

        Args:
            file_bytes: Raw bytes of the PDF file.
            filename: Original filename of the uploaded PDF.

        Returns:
            Dictionary with extracted resume data matching the ExtractedResume schema.

        Raises:
            AIServiceTimeoutError: If the AI service does not respond within 60 seconds.
            AIServiceUnavailableError: If the AI service is unreachable.
            CircuitBreakerOpenError: If circuit breaker is open.
            AIServiceError: For other AI service errors.
        """
        if not self.circuit_breaker.allow_request():
            raise CircuitBreakerOpenError()

        url = f"{self.base_url}/extract-pdf"

        try:
            async with httpx.AsyncClient(timeout=PDF_EXTRACTION_TIMEOUT) as client:
                response = await client.post(
                    url,
                    files={"file": (filename, file_bytes, "application/pdf")},
                    headers=_internal_headers(),
                )

            if response.status_code == 200:
                self.circuit_breaker.record_success()
                return response.json()

            # Handle specific error codes from AI service
            detail = "Erro desconhecido no serviço de IA"
            try:
                error_body = response.json()
                detail = error_body.get("detail", detail)
            except Exception:
                pass

            self.circuit_breaker.record_failure()
            raise AIServiceError(detail, status_code=response.status_code)

        except httpx.TimeoutException:
            logger.warning("AI service timed out during PDF extraction")
            self.circuit_breaker.record_failure()
            raise AIServiceTimeoutError(PDF_EXTRACTION_TIMEOUT)

        except httpx.ConnectError:
            logger.error("Cannot connect to AI service at %s", self.base_url)
            self.circuit_breaker.record_failure()
            raise AIServiceUnavailableError()

        except (AIServiceError, CircuitBreakerOpenError):
            raise

        except Exception as e:
            logger.exception("Unexpected error calling AI service")
            self.circuit_breaker.record_failure()
            raise AIServiceError(f"Erro inesperado ao comunicar com o serviço de IA: {e}")

    async def analyze_candidates(
        self, job_requirements: dict[str, Any], candidates: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Send candidate analysis request to the AI microservice.

        Args:
            job_requirements: Job data with title, responsibilities, required_skills, etc.
            candidates: List of candidate resume data (max 200).

        Returns:
            Dictionary with analysis results (job_id, total_candidates, results).

        Raises:
            AIServiceTimeoutError: If response exceeds 60s timeout.
            AIServiceUnavailableError: If the AI service is unreachable.
            CircuitBreakerOpenError: If circuit breaker is open.
            AIServiceError: For other errors.
        """
        if not self.circuit_breaker.allow_request():
            raise CircuitBreakerOpenError()

        url = f"{self.base_url}/analyze-candidates"
        payload = {
            "job_requirements": job_requirements,
            "candidates": candidates,
        }

        try:
            async with httpx.AsyncClient(timeout=ANALYZE_CANDIDATES_TIMEOUT) as client:
                response = await client.post(url, json=payload, headers=_internal_headers())

            if response.status_code == 200:
                self.circuit_breaker.record_success()
                return response.json()

            detail = "Erro na análise de candidatos"
            try:
                error_body = response.json()
                detail = error_body.get("detail", detail)
            except Exception:
                pass

            self.circuit_breaker.record_failure()
            raise AIServiceError(detail, status_code=response.status_code)

        except httpx.TimeoutException:
            logger.warning("AI service timed out during candidate analysis")
            self.circuit_breaker.record_failure()
            raise AIServiceTimeoutError(ANALYZE_CANDIDATES_TIMEOUT)

        except httpx.ConnectError:
            logger.error("Cannot connect to AI service at %s", self.base_url)
            self.circuit_breaker.record_failure()
            raise AIServiceUnavailableError()

        except (AIServiceError, CircuitBreakerOpenError):
            raise

        except Exception as e:
            logger.exception("Unexpected error during candidate analysis")
            self.circuit_breaker.record_failure()
            raise AIServiceError(f"Erro inesperado na análise de candidatos: {e}")

    async def match_jobs(
        self,
        candidate_id: str,
        resume: dict[str, Any],
        active_jobs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Send job matching request to the AI microservice.

        Args:
            candidate_id: Unique identifier of the candidate.
            resume: Candidate resume data (experiences, skills, etc.).
            active_jobs: List of active job data to compare against.

        Returns:
            Dictionary with match results (candidate_id, matches).

        Raises:
            AIServiceTimeoutError: If response exceeds 30s timeout.
            AIServiceUnavailableError: If the AI service is unreachable.
            CircuitBreakerOpenError: If circuit breaker is open.
            AIServiceError: For other errors.
        """
        if not self.circuit_breaker.allow_request():
            raise CircuitBreakerOpenError()

        url = f"{self.base_url}/match-jobs"
        payload = {
            "candidate_id": candidate_id,
            "resume": resume,
            "active_jobs": active_jobs,
        }

        try:
            async with httpx.AsyncClient(timeout=JOB_MATCHING_TIMEOUT) as client:
                response = await client.post(url, json=payload, headers=_internal_headers())

            if response.status_code == 200:
                self.circuit_breaker.record_success()
                return response.json()

            detail = "Erro na análise de compatibilidade"
            try:
                error_body = response.json()
                detail = error_body.get("detail", detail)
            except Exception:
                pass

            self.circuit_breaker.record_failure()
            raise AIServiceError(detail, status_code=response.status_code)

        except httpx.TimeoutException:
            logger.warning("AI service timed out during job matching")
            self.circuit_breaker.record_failure()
            raise AIServiceTimeoutError(JOB_MATCHING_TIMEOUT)

        except httpx.ConnectError:
            logger.error("Cannot connect to AI service at %s", self.base_url)
            self.circuit_breaker.record_failure()
            raise AIServiceUnavailableError()

        except (AIServiceError, CircuitBreakerOpenError):
            raise

        except Exception as e:
            logger.exception("Unexpected error during job matching")
            self.circuit_breaker.record_failure()
            raise AIServiceError(f"Erro inesperado na análise de compatibilidade: {e}")


# Singleton instance
ai_service_client = AIServiceClient()
