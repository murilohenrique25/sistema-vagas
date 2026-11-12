"""Wallet and Checkout Pro payment schemas."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import PaymentMethod, PaymentStatus
from app.schemas.base import BaseSchema

MIN_PAYMENT_BRL = Decimal("1.00")
MAX_PAYMENT_BRL = Decimal("50000.00")


class ServicePaymentPurpose(str, Enum):
    resume_analysis = "resume_analysis"
    job_compatibility = "job_compatibility"
    wallet_topup = "wallet_topup"


class WalletCheckoutRequest(BaseModel):
    amount: Decimal = Field(..., ge=MIN_PAYMENT_BRL, le=MAX_PAYMENT_BRL)


class WalletCheckoutResponse(BaseModel):
    payment_id: UUID
    preference_id: str
    checkout_url: str
    amount: Decimal
    status: PaymentStatus


class WalletCheckoutReconcileRequest(BaseModel):
    mercado_pago_payment_id: str = Field(..., min_length=1, max_length=100)


class WalletBalanceResponse(BaseModel):
    balance: Decimal
    currency: str = "BRL"


class ServicePricesResponse(BaseModel):
    resume_analysis: Decimal
    job_compatibility: Decimal


class PublicPaymentConfigResponse(BaseModel):
    currency: str = "BRL"
    payments_enabled: bool
    minimum_wallet_topup: Decimal
    prices: ServicePricesResponse


class PaymentDetailResponse(BaseSchema):
    id: UUID
    user_id: UUID
    amount: Decimal
    method: PaymentMethod
    status: PaymentStatus
    external_reference: str | None = None
    confirmed_at: datetime | None = None
    created_at: datetime
