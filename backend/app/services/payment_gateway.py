"""Checkout Pro payment gateway implementations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import uuid

import httpx

from app.core.config import settings


@dataclass
class CheckoutPreferenceResult:
    preference_id: str
    checkout_url: str


@dataclass
class GatewayPaymentInfo:
    payment_id: str
    status: str
    external_reference: str | None
    amount: float


class PaymentGatewayUnavailableError(Exception):
    pass


class PaymentGatewayInterface(ABC):
    @abstractmethod
    async def create_checkout_preference(
        self, amount_cents: int, reference_id: uuid.UUID, payer_email: str,
        frontend_url: str, notification_url: str,
    ) -> CheckoutPreferenceResult: ...

    @abstractmethod
    async def get_payment_info(self, payment_id: str) -> GatewayPaymentInfo: ...


class SandboxPaymentGateway(PaymentGatewayInterface):
    """Local-only checkout substitute; never selected in production."""

    async def create_checkout_preference(
        self, amount_cents: int, reference_id: uuid.UUID, payer_email: str,
        frontend_url: str, notification_url: str,
    ) -> CheckoutPreferenceResult:
        return CheckoutPreferenceResult(
            preference_id=f"sandbox-{reference_id}",
            checkout_url=f"{frontend_url.rstrip('/')}/dashboard/wallet?checkout=pending",
        )

    async def get_payment_info(self, payment_id: str) -> GatewayPaymentInfo:
        raise PaymentGatewayUnavailableError()


class MercadoPagoPaymentGateway(PaymentGatewayInterface):
    base_url = "https://api.mercadopago.com"

    def __init__(
        self, access_token: str | None = None, payer_email: str | None = None,
        sandbox: bool | None = None,
    ) -> None:
        self.access_token = access_token or settings.mercadopago_access_token
        self.payer_email = payer_email or settings.mercadopago_payer_email
        self.sandbox = settings.mercadopago_sandbox if sandbox is None else sandbox
        if not self.access_token:
            raise RuntimeError("MERCADOPAGO_ACCESS_TOKEN não configurado")

    def _headers(self, idempotency_key: str | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key
        return headers

    async def create_checkout_preference(
        self, amount_cents: int, reference_id: uuid.UUID, payer_email: str,
        frontend_url: str, notification_url: str,
    ) -> CheckoutPreferenceResult:
        wallet_url = f"{frontend_url.rstrip('/')}/dashboard/wallet"
        payload = {
            "items": [{
                "id": "wallet-credit",
                "title": "Crédito para carteira Recruta IA",
                "description": "Saldo para utilizar nos serviços da plataforma",
                "currency_id": "BRL", "quantity": 1,
                "unit_price": amount_cents / 100,
            }],
            "external_reference": str(reference_id),
            "back_urls": {
                "success": f"{wallet_url}?checkout=success",
                "pending": f"{wallet_url}?checkout=pending",
                "failure": f"{wallet_url}?checkout=failure",
            },
            "auto_return": "approved",
            "notification_url": notification_url,
            "statement_descriptor": "RECRUTA IA",
        }
        if not self.sandbox and payer_email:
            payload["payer"] = {"email": payer_email}
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    f"{self.base_url}/checkout/preferences",
                    headers=self._headers(str(reference_id)), json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise PaymentGatewayUnavailableError() from exc
        checkout_url = data.get("init_point")
        if not data.get("id") or not checkout_url:
            raise PaymentGatewayUnavailableError()
        return CheckoutPreferenceResult(
            preference_id=str(data["id"]), checkout_url=checkout_url
        )

    async def get_payment_info(self, payment_id: str) -> GatewayPaymentInfo:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.base_url}/v1/payments/{payment_id}",
                    headers=self._headers(),
                )
                response.raise_for_status()
                data = response.json()
            return GatewayPaymentInfo(
                payment_id=str(data["id"]), status=str(data.get("status", "")),
                external_reference=data.get("external_reference"),
                amount=float(data.get("transaction_amount", 0)),
            )
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise PaymentGatewayUnavailableError() from exc


def get_payment_gateway(
    provider: str | None = None, access_token: str | None = None,
    payer_email: str | None = None, sandbox: bool | None = None,
) -> PaymentGatewayInterface:
    selected = provider or settings.payment_gateway
    if selected == "mercadopago":
        return MercadoPagoPaymentGateway(access_token, payer_email, sandbox=sandbox)
    if selected == "sandbox" and settings.environment != "production":
        return SandboxPaymentGateway()
    raise RuntimeError("Gateway de pagamento inválido para este ambiente")
