import asyncio
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class BackendClientError(Exception):
    """Raised when the backend client encounters an error."""
    pass


class BackendClient:
    """HTTP client for internal communication with the main backend service.

    Provides methods to interact with the backend REST API for fetching
    resumes, job details, and other data needed by the AI service.

    Features:
    - Automatic retries with exponential backoff
    - Internal service token authentication
    - Configurable timeouts
    - Structured error handling
    """

    def __init__(self) -> None:
        self._base_url = f"{settings.backend_base_url}{settings.backend_api_prefix}"
        self._timeout = settings.backend_timeout
        self._retry_attempts = settings.backend_retry_attempts
        self._retry_delay = settings.backend_retry_delay

    def _get_headers(self) -> dict[str, str]:
        """Build request headers including internal service auth."""
        headers = {
            "Content-Type": "application/json",
            "X-Service-Name": settings.service_name,
        }
        if settings.internal_service_token:
            headers["Authorization"] = f"Bearer {settings.internal_service_token}"
        return headers

    def _get_client(self) -> httpx.AsyncClient:
        """Create a new async HTTP client with configured defaults."""
        return httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers=self._get_headers(),
        )

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> httpx.Response:
        """Execute an HTTP request with retry logic.

        Retries on connection errors and 5xx responses with
        exponential backoff.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path relative to base URL
            **kwargs: Additional arguments passed to httpx request

        Returns:
            httpx.Response on success

        Raises:
            BackendClientError: After all retries are exhausted
        """
        last_error: Exception | None = None

        for attempt in range(self._retry_attempts):
            try:
                async with self._get_client() as client:
                    response = await client.request(method, path, **kwargs)

                    if response.status_code >= 500:
                        last_error = BackendClientError(
                            f"Backend returned {response.status_code}: {response.text}"
                        )
                        logger.warning(
                            "Backend request failed (attempt %d/%d): %s %s -> %d",
                            attempt + 1,
                            self._retry_attempts,
                            method,
                            path,
                            response.status_code,
                        )
                    else:
                        response.raise_for_status()
                        return response

            except httpx.ConnectError as e:
                last_error = BackendClientError(f"Connection to backend failed: {e}")
                logger.warning(
                    "Backend connection failed (attempt %d/%d): %s",
                    attempt + 1,
                    self._retry_attempts,
                    e,
                )
            except httpx.TimeoutException as e:
                last_error = BackendClientError(f"Backend request timed out: {e}")
                logger.warning(
                    "Backend request timed out (attempt %d/%d): %s",
                    attempt + 1,
                    self._retry_attempts,
                    e,
                )
            except httpx.HTTPStatusError as e:
                # Don't retry on 4xx client errors
                raise BackendClientError(
                    f"Backend returned client error {e.response.status_code}: {e.response.text}"
                ) from e

            # Wait before retry (exponential backoff)
            if attempt < self._retry_attempts - 1:
                delay = self._retry_delay * (2 ** attempt)
                await asyncio.sleep(delay)

        raise last_error or BackendClientError("Backend request failed after all retries")

    async def get_resume(self, candidate_id: str) -> dict:
        """Fetch a candidate's resume from the backend."""
        response = await self._request_with_retry("GET", f"/resumes/{candidate_id}")
        return response.json()

    async def get_job(self, job_id: str) -> dict:
        """Fetch job details from the backend."""
        response = await self._request_with_retry("GET", f"/jobs/{job_id}")
        return response.json()

    async def get_active_jobs(self) -> list[dict]:
        """Fetch all active jobs from the backend."""
        response = await self._request_with_retry(
            "GET", "/jobs", params={"status": "active"}
        )
        return response.json()

    async def get_candidates_for_job(
        self, job_id: str, candidate_ids: list[str]
    ) -> list[dict]:
        """Fetch candidate resumes for a specific job analysis."""
        response = await self._request_with_retry(
            "POST",
            f"/jobs/{job_id}/candidates-data",
            json={"candidate_ids": candidate_ids},
        )
        return response.json()

    async def check_health(self) -> bool:
        """Check if the backend service is reachable.

        Returns:
            True if the backend responds, False otherwise.
        """
        try:
            async with self._get_client() as client:
                response = await client.get("/health")
                return response.status_code == 200
        except (httpx.HTTPError, Exception):
            return False


backend_client = BackendClient()
