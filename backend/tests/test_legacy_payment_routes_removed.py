"""Regression tests ensuring legacy monetization APIs stay unavailable."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path",
    [
        ("POST", "/v1/payments/pix"),
        ("POST", "/v1/payments/card"),
        ("POST", "/v1/payments/tokenize-card"),
        ("POST", "/v1/payments/pix/confirm"),
        ("GET", "/v1/tokens/packages"),
        ("GET", "/v1/admin/tokens/packages"),
        ("GET", "/v1/admin/tokens/config"),
        ("POST", "/v1/scheduler/process-recurring-billing"),
    ],
)
async def test_legacy_route_is_not_exposed(method: str, path: str):
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.request(method, path)
    assert response.status_code in {404, 405}
