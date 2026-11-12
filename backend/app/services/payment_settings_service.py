"""Central source for public payment configuration and service prices."""

from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.payment import ServicePaymentPurpose
from app.core.config import settings
from app.core.secrets import decrypt_secret


DEFAULT_SERVICE_PRICES = {
    ServicePaymentPurpose.resume_analysis: Decimal("5.00"),
    ServicePaymentPurpose.job_compatibility: Decimal("5.00"),
}
DEFAULT_MINIMUM_WALLET_TOPUP = Decimal("1.00")


class PaymentSettingsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_public_config(self) -> dict:
        result = await self.session.execute(text("""
            SELECT resume_analysis_price,
                   job_compatibility_price, minimum_wallet_topup, is_active
              FROM payment_settings
             ORDER BY updated_at DESC NULLS LAST
             LIMIT 1
        """))
        row = result.mappings().first()
        return {
            "currency": "BRL",
            "payments_enabled": bool(row["is_active"]) if row else True,
            "minimum_wallet_topup": (
                Decimal(row["minimum_wallet_topup"])
                if row and row["minimum_wallet_topup"] is not None
                else DEFAULT_MINIMUM_WALLET_TOPUP
            ),
            "prices": {
                purpose.value: (
                    Decimal(row[column])
                    if row and row[column] is not None
                    else DEFAULT_SERVICE_PRICES[purpose]
                )
                for purpose, column in {
                    ServicePaymentPurpose.resume_analysis: "resume_analysis_price",
                    ServicePaymentPurpose.job_compatibility: "job_compatibility_price",
                }.items()
            },
        }

    async def get_price(self, purpose: ServicePaymentPurpose) -> Decimal:
        if purpose == ServicePaymentPurpose.wallet_topup:
            return (await self.get_public_config())["minimum_wallet_topup"]
        return (await self.get_public_config())["prices"][purpose.value]

    async def get_gateway_config(self) -> dict:
        result = await self.session.execute(text("""
            SELECT gateway_provider, gateway_api_key, gateway_secret_key,
                   gateway_webhook_url
              FROM payment_settings
             WHERE is_active = true
             ORDER BY updated_at DESC NULLS LAST
             LIMIT 1
        """))
        row = result.mappings().first()
        return {
            "provider": (row["gateway_provider"] if row and row["gateway_provider"] else settings.payment_gateway),
            "access_token": decrypt_secret(row["gateway_api_key"]) if row and row["gateway_api_key"] else settings.mercadopago_access_token,
            "webhook_secret": decrypt_secret(row["gateway_secret_key"]) if row and row["gateway_secret_key"] else settings.mercadopago_webhook_secret,
            "webhook_url": row["gateway_webhook_url"] if row else None,
            "payer_email": settings.mercadopago_payer_email,
            "sandbox": settings.mercadopago_sandbox,
        }
