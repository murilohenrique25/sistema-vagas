"""OAuth2 authentication routes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.services.oauth_service import OAuthService

router = APIRouter(prefix="/auth/oauth", tags=["auth"])

SUPPORTED_PROVIDERS = ("google", "linkedin")


@router.get("/{provider}")
async def oauth_redirect(provider: str) -> RedirectResponse:
    """Redirect user to the OAuth2 provider's authorization page.

    Args:
        provider: OAuth provider name ("google" or "linkedin").

    Returns:
        Redirect response to the provider's authorization URL.
    """
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported OAuth provider: {provider}. Supported: {', '.join(SUPPORTED_PROVIDERS)}",
        )

    # We don't need DB here, just generating the URL
    # Using a temporary None session since get_authorization_url doesn't use DB
    service = OAuthService(db=None)  # type: ignore[arg-type]

    try:
        authorization_url = service.get_authorization_url(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return RedirectResponse(url=authorization_url)


@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str = Query(..., description="Authorization code from OAuth provider"),
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Handle the OAuth2 callback from the provider.

    Exchanges the authorization code for tokens, fetches user info,
    creates or links the user account, and returns JWT tokens.

    Args:
        provider: OAuth provider name ("google" or "linkedin").
        code: Authorization code received from the provider.
        db: Database session dependency.

    Returns:
        Dictionary with access_token, refresh_token, and token_type.
    """
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported OAuth provider: {provider}. Supported: {', '.join(SUPPORTED_PROVIDERS)}",
        )

    service = OAuthService(db=db)

    try:
        token_pair = await service.handle_callback(provider, code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return token_pair
