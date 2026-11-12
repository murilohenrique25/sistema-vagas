import uuid
import json

import httpx
import pytest

from app.services.payment_gateway import MercadoPagoPaymentGateway


@pytest.mark.asyncio
async def test_checkout_preference_uses_internal_reference_and_secure_returns(monkeypatch):
    captured = {}
    real_client = httpx.AsyncClient

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.read().decode())
        return httpx.Response(201, json={
            "id": "pref-123",
            "init_point": "https://www.mercadopago.com.br/checkout/v1/redirect",
            "sandbox_init_point": "https://sandbox.mercadopago.com.br/checkout/v1/redirect",
        })

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        httpx, "AsyncClient",
        lambda **kwargs: real_client(transport=transport, **kwargs),
    )
    reference = uuid.uuid4()
    gateway = MercadoPagoPaymentGateway(access_token="APP_USR-test-token", sandbox=True)
    result = await gateway.create_checkout_preference(
        5000, reference, "cliente@example.com",
        "https://recruta.example.com", "https://api.example.com/webhook",
    )

    assert result.preference_id == "pref-123"
    assert result.checkout_url.startswith("https://www.mercadopago.com.br")
    assert captured["body"]["external_reference"] == str(reference)
    assert captured["body"]["items"][0]["unit_price"] == 50
    assert captured["body"]["notification_url"] == "https://api.example.com/webhook"
    assert captured["body"]["back_urls"]["success"].startswith("https://")
    assert "payer" not in captured["body"]


@pytest.mark.asyncio
async def test_gateway_payment_info_is_read_from_provider(monkeypatch):
    reference = str(uuid.uuid4())
    real_client = httpx.AsyncClient

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={
            "id": 987654,
            "status": "approved",
            "external_reference": reference,
            "transaction_amount": 50.0,
        })

    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kwargs: real_client(transport=transport, **kwargs)
    )
    gateway = MercadoPagoPaymentGateway(access_token="TEST-token")
    payment = await gateway.get_payment_info("987654")

    assert payment.status == "approved"
    assert payment.external_reference == reference
    assert payment.amount == 50.0
