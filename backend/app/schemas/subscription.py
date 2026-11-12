"""Subscription-related schemas for plans, upgrades, downgrades, and billing."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import PaymentMethod, SubscriptionPlan, SubscriptionStatus
from app.schemas.base import BaseSchema


# --- Plan definitions ---


class PlanFeatures(BaseSchema):
    """Features included in a subscription plan."""

    max_active_jobs: int | None = Field(
        None, description="Máximo de vagas ativas (null = ilimitado)"
    )
    ai_credits_monthly: int | None = Field(
        None, description="Créditos de IA mensais (null = ilimitado)"
    )
    highlights_included: bool = Field(
        False, description="Se destaques de vaga estão inclusos"
    )
    dashboard_metrics: bool = Field(
        False, description="Se dashboard avançado de métricas está disponível"
    )


class PlanResponse(BaseSchema):
    """Response schema for a subscription plan."""

    plan: SubscriptionPlan
    name: str
    description: str
    price_monthly: float
    features: PlanFeatures


# --- Subscription responses ---


class SubscriptionResponse(BaseSchema):
    """Response schema for the user's current subscription."""

    id: UUID
    user_id: UUID
    plan: SubscriptionPlan
    status: SubscriptionStatus
    current_period_start: date | None = None
    current_period_end: date | None = None
    retry_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None


# --- Request schemas ---


class SubscribeRequest(BaseModel):
    """Request schema for subscribing or upgrading to a plan."""

    plan: SubscriptionPlan = Field(
        ..., description="Plano desejado (professional ou enterprise)"
    )
    payment_method: PaymentMethod = Field(
        ..., description="Método de pagamento (pix ou credit_card)"
    )


class DowngradeRequest(BaseModel):
    """Request schema for downgrading to a lower plan."""

    plan: SubscriptionPlan = Field(
        ..., description="Plano de destino (free ou professional)"
    )


# --- Internal/admin schemas ---


class RetryBillingResult(BaseSchema):
    """Result of a billing retry attempt."""

    subscription_id: UUID
    user_id: UUID
    attempt_number: int
    success: bool
    message: str


class ProcessRecurringBillingResponse(BaseSchema):
    """Response for the recurring billing processing endpoint."""

    processed: int
    successful: int
    failed: int
    suspended: int
    results: list[RetryBillingResult]


class ProcessGracePeriodResponse(BaseSchema):
    """Response for the grace period processing endpoint."""

    processed: int
    downgraded: int
    details: list[dict]
