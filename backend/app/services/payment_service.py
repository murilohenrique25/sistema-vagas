"""Wallet funding through Mercado Pago Checkout Pro."""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import PaymentMethod, PaymentStatus
from app.models.subscription import Payment
from app.schemas.payment import MAX_PAYMENT_BRL, MIN_PAYMENT_BRL, PaymentDetailResponse, ServicePaymentPurpose, WalletCheckoutResponse
from app.services.payment_gateway import PaymentGatewayInterface, PaymentGatewayUnavailableError, get_payment_gateway
from app.services.payment_settings_service import PaymentSettingsService
from app.services.wallet_service import WalletService


class PaymentService:
    def __init__(self, session: AsyncSession, gateway: PaymentGatewayInterface | None = None) -> None:
        self.session = session
        self.gateway = gateway

    async def _get_gateway(self) -> PaymentGatewayInterface:
        if self.gateway:
            return self.gateway
        config = await PaymentSettingsService(self.session).get_gateway_config()
        return get_payment_gateway(
            config["provider"], config["access_token"], config["payer_email"],
            sandbox=config["sandbox"],
        )

    async def create_wallet_checkout(self, user_id: UUID, payer_email: str, amount: Decimal) -> WalletCheckoutResponse:
        payment_config = await PaymentSettingsService(self.session).get_public_config()
        if not payment_config["payments_enabled"]:
            raise HTTPException(status_code=503, detail="Pagamentos temporariamente indisponíveis.")
        amount = amount.quantize(Decimal("0.01"))
        self._validate_amount(amount)
        minimum = payment_config["minimum_wallet_topup"]
        if amount < minimum:
            raise HTTPException(status_code=422, detail=f"O valor mínimo para adicionar saldo é R$ {minimum:.2f}.")
        gateway_config = await PaymentSettingsService(self.session).get_gateway_config()
        notification_url = gateway_config.get("webhook_url")
        if not notification_url or not notification_url.startswith("https://"):
            raise HTTPException(status_code=503, detail="Webhook HTTPS do Mercado Pago não está configurado.")

        payment = Payment(
            user_id=user_id, amount=amount, method=PaymentMethod.checkout_pro,
            status=PaymentStatus.pending, purpose=ServicePaymentPurpose.wallet_topup.value,
        )
        self.session.add(payment)
        await self.session.flush()
        await self.session.refresh(payment)
        try:
            preference = await (await self._get_gateway()).create_checkout_preference(
                amount_cents=int(amount * 100), reference_id=payment.id,
                payer_email=payer_email, frontend_url=settings.frontend_url,
                notification_url=notification_url,
            )
        except PaymentGatewayUnavailableError:
            payment.status = PaymentStatus.failed
            await self.session.flush()
            raise HTTPException(status_code=503, detail="Não foi possível abrir o Mercado Pago. Tente novamente.")
        payment.external_reference = preference.preference_id
        await self.session.flush()
        return WalletCheckoutResponse(
            payment_id=payment.id, preference_id=preference.preference_id,
            checkout_url=preference.checkout_url, amount=amount,
            status=PaymentStatus.pending,
        )

    async def process_mercadopago_payment(self, mercado_pago_payment_id: str, expected_user_id: UUID | None = None) -> bool:
        try:
            info = await (await self._get_gateway()).get_payment_info(mercado_pago_payment_id)
        except PaymentGatewayUnavailableError:
            raise HTTPException(status_code=503, detail="Não foi possível validar o pagamento no Mercado Pago.")
        try:
            internal_id = UUID(info.external_reference or "")
        except (TypeError, ValueError):
            return False
        result = await self.session.execute(select(Payment).where(Payment.id == internal_id).with_for_update())
        payment = result.scalar_one_or_none()
        if not payment or payment.purpose != ServicePaymentPurpose.wallet_topup.value:
            return False
        if expected_user_id is not None and payment.user_id != expected_user_id:
            raise HTTPException(status_code=404, detail="Pagamento não encontrado.")
        if payment.status == PaymentStatus.confirmed:
            return True
        gateway_amount = Decimal(str(info.amount)).quantize(Decimal("0.01"))
        if gateway_amount != Decimal(payment.amount).quantize(Decimal("0.01")):
            payment.status = PaymentStatus.failed
            await self.session.flush()
            return False
        payment.external_reference = info.payment_id
        if info.status == "approved":
            payment.status = PaymentStatus.confirmed
            payment.confirmed_at = datetime.now(timezone.utc)
            await WalletService(self.session).credit(
                payment.user_id, payment.amount, reason="Recarga da carteira via Mercado Pago",
                reference_id=payment.id, operation_id=f"checkout-credit:{payment.id}",
            )
            payment.consumed_at = payment.confirmed_at
        elif info.status in {"rejected", "cancelled", "refunded", "charged_back"}:
            payment.status = PaymentStatus.failed
        await self.session.flush()
        return True

    async def reconcile_wallet_checkout(self, mercado_pago_payment_id: str, user_id: UUID) -> PaymentDetailResponse:
        processed = await self.process_mercadopago_payment(mercado_pago_payment_id, expected_user_id=user_id)
        if not processed:
            raise HTTPException(status_code=404, detail="Pagamento não encontrado.")
        info = await (await self._get_gateway()).get_payment_info(mercado_pago_payment_id)
        try:
            internal_id = UUID(info.external_reference or "")
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=404, detail="Pagamento não encontrado.") from exc
        return await self.get_payment_detail(internal_id, user_id)

    async def get_payment_detail(self, payment_id: UUID, user_id: UUID) -> PaymentDetailResponse:
        result = await self.session.execute(select(Payment).where(Payment.id == payment_id, Payment.user_id == user_id))
        payment = result.scalar_one_or_none()
        if not payment:
            raise HTTPException(status_code=404, detail="Pagamento não encontrado.")
        return PaymentDetailResponse(
            id=payment.id, user_id=payment.user_id, amount=payment.amount,
            method=payment.method, status=payment.status,
            external_reference=payment.external_reference,
            confirmed_at=payment.confirmed_at, created_at=payment.created_at,
        )

    @staticmethod
    def _validate_amount(amount: Decimal) -> None:
        if amount < MIN_PAYMENT_BRL:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Valor mínimo de pagamento é R$ {MIN_PAYMENT_BRL}.")
        if amount > MAX_PAYMENT_BRL:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Valor máximo de pagamento é R$ {MAX_PAYMENT_BRL}.")
