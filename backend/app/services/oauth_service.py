"""OAuth2 service for Google and LinkedIn authentication."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import UserRole
from app.models.user import User


# OAuth2 provider configuration
OAUTH_PROVIDERS = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v2/userinfo",
        "scopes": "openid email profile",
    },
    "linkedin": {
        "authorize_url": "https://www.linkedin.com/oauth/v2/authorization",
        "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
        "userinfo_url": "https://api.linkedin.com/v2/userinfo",
        "scopes": "openid profile email",
    },
}


class OAuthService:
    """Service for handling OAuth2 authentication flows."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def get_authorization_url(self, provider: str) -> str:
        """Generate the OAuth2 authorization URL for the given provider.

        Args:
            provider: OAuth provider name ("google" or "linkedin").

        Returns:
            The authorization URL to redirect the user to.

        Raises:
            ValueError: If the provider is not supported.
        """
        if provider not in OAUTH_PROVIDERS:
            raise ValueError(f"Unsupported OAuth provider: {provider}")

        config = OAUTH_PROVIDERS[provider]
        client_id = self._get_client_id(provider)
        redirect_uri = self._get_redirect_uri(provider)

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": config["scopes"],
        }

        if provider == "google":
            params["access_type"] = "offline"
            params["prompt"] = "consent"

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{config['authorize_url']}?{query_string}"

    async def handle_callback(self, provider: str, code: str) -> dict:
        """Exchange authorization code for tokens and create/link user account.

        Args:
            provider: OAuth provider name ("google" or "linkedin").
            code: Authorization code received from the provider callback.

        Returns:
            Dictionary with access_token and refresh_token.

        Raises:
            ValueError: If the provider is not supported or token exchange fails.
        """
        if provider not in OAUTH_PROVIDERS:
            raise ValueError(f"Unsupported OAuth provider: {provider}")

        # Exchange code for access token
        access_token = await self._exchange_code_for_token(provider, code)

        # Fetch user info from provider
        user_info = await self._fetch_user_info(provider, access_token)

        # Create or link user account
        user = await self._create_or_link_user(provider, user_info)

        # Generate JWT token pair
        token_pair = self._generate_token_pair(user)

        return token_pair

    async def _exchange_code_for_token(self, provider: str, code: str) -> str:
        """Exchange authorization code for an access token from the provider."""
        config = OAUTH_PROVIDERS[provider]
        client_id = self._get_client_id(provider)
        client_secret = self._get_client_secret(provider)
        redirect_uri = self._get_redirect_uri(provider)

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                config["token_url"],
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if response.status_code != 200:
            raise ValueError(
                f"Failed to exchange code for token: {response.status_code} - {response.text}"
            )

        token_data = response.json()
        return token_data["access_token"]

    async def _fetch_user_info(self, provider: str, access_token: str) -> dict:
        """Fetch user profile information from the OAuth provider."""
        config = OAUTH_PROVIDERS[provider]

        async with httpx.AsyncClient() as client:
            response = await client.get(
                config["userinfo_url"],
                headers={"Authorization": f"Bearer {access_token}"},
            )

        if response.status_code != 200:
            raise ValueError(
                f"Failed to fetch user info: {response.status_code} - {response.text}"
            )

        data = response.json()

        if provider == "google":
            return {
                "oauth_id": data["id"],
                "email": data["email"],
                "name": data.get("name", data["email"]),
            }
        elif provider == "linkedin":
            return {
                "oauth_id": data["sub"],
                "email": data["email"],
                "name": data.get("name", data["email"]),
            }

        raise ValueError(f"Unsupported provider for user info parsing: {provider}")

    async def _create_or_link_user(self, provider: str, user_info: dict) -> User:
        """Create a new user or link OAuth provider to an existing account.

        If the email already exists in the system, link the OAuth provider.
        If the email doesn't exist, create a new account with role "candidate".
        """
        email = user_info["email"]

        # Check if user with this email already exists
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            # Link OAuth provider to existing account
            existing_user.oauth_provider = provider
            existing_user.oauth_id = user_info["oauth_id"]
            existing_user.email_verified_at = existing_user.email_verified_at or datetime.now(timezone.utc)
            await self.db.flush()
            return existing_user

        # Create new user with default role "candidate"
        new_user = User(
            id=uuid4(),
            email=email,
            name=user_info["name"],
            role=UserRole.candidate,
            oauth_provider=provider,
            oauth_id=user_info["oauth_id"],
            is_active=True,
            failed_login_attempts=0,
            email_verified_at=datetime.now(timezone.utc),
        )
        self.db.add(new_user)
        await self.db.flush()
        return new_user

    def _generate_token_pair(self, user: User) -> dict:
        """Generate access token and refresh token for the user."""
        now = datetime.now(timezone.utc)

        # Access token payload
        access_payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "type": "access",
            "exp": now + timedelta(minutes=settings.jwt_access_token_expire_minutes),
            "iat": now,
        }

        # Refresh token payload
        refresh_payload = {
            "sub": str(user.id),
            "type": "refresh",
            "exp": now + timedelta(days=settings.jwt_refresh_token_expire_days),
            "iat": now,
        }

        access_token = jwt.encode(
            access_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )
        refresh_token = jwt.encode(
            refresh_payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    def _get_client_id(self, provider: str) -> str:
        """Get client ID for the given provider."""
        if provider == "google":
            return settings.google_client_id
        elif provider == "linkedin":
            return settings.linkedin_client_id
        raise ValueError(f"No client ID configured for provider: {provider}")

    def _get_client_secret(self, provider: str) -> str:
        """Get client secret for the given provider."""
        if provider == "google":
            return settings.google_client_secret
        elif provider == "linkedin":
            return settings.linkedin_client_secret
        raise ValueError(f"No client secret configured for provider: {provider}")

    def _get_redirect_uri(self, provider: str) -> str:
        """Get redirect URI for the given provider."""
        if provider == "google":
            return settings.google_redirect_uri
        elif provider == "linkedin":
            return settings.linkedin_redirect_uri
        raise ValueError(f"No redirect URI configured for provider: {provider}")
