"""Admin panel schemas for request/response models."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.base import BaseSchema, PaginatedResponse


# === User Management ===


class AdminUserResponse(BaseSchema):
    """User response for admin panel."""

    id: UUID
    email: str
    name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None


class AdminPaymentSettingsUpdate(BaseModel):
    pix_key_type: str | None = Field(default=None, max_length=30)
    pix_key: str | None = Field(default=None, max_length=255)
    pix_beneficiary_name: str | None = Field(default=None, max_length=255)
    gateway_provider: str | None = Field(default=None, max_length=50)
    gateway_api_key: str | None = None
    gateway_secret_key: str | None = None
    gateway_webhook_url: str | None = Field(default=None, max_length=500)
    bank_name: str | None = Field(default=None, max_length=100)
    bank_agency: str | None = Field(default=None, max_length=30)
    bank_account: str | None = Field(default=None, max_length=50)
    bank_account_type: str | None = Field(default=None, max_length=30)
    resume_analysis_price: Decimal = Field(default=Decimal("5.00"), gt=0, le=50000)
    job_compatibility_price: Decimal = Field(default=Decimal("5.00"), gt=0, le=50000)
    minimum_wallet_topup: Decimal = Field(default=Decimal("1.00"), gt=0, le=50000)
    is_active: bool = True


class AdminUserUpdate(BaseModel):
    """Schema for admin user edit."""

    name: str | None = None
    role: str | None = None
    is_active: bool | None = None


# === Company Management ===


class AdminCompanyResponse(BaseSchema):
    """Company response for admin panel."""

    id: UUID
    owner_id: UUID
    name: str
    cnpj: str
    description: str | None = None
    website: str | None = None
    is_active: bool
    created_at: datetime


class AdminCompanyUpdate(BaseModel):
    """Schema for admin company edit."""

    name: str | None = None
    description: str | None = None
    website: str | None = None
    is_active: bool | None = None


# === Job Management ===


class AdminJobResponse(BaseSchema):
    """Job response for admin panel."""

    id: UUID
    company_id: UUID
    title: str
    modality: str
    contract_type: str
    status: str
    deadline: date | None = None
    created_at: datetime


class AdminJobStatusUpdate(BaseModel):
    """Schema for admin job status change."""

    status: str


# === Application Management ===


class AdminApplicationResponse(BaseSchema):
    """Application response for admin panel."""

    id: UUID
    job_id: UUID
    candidate_id: UUID
    status: str
    applied_at: datetime
    updated_at: datetime | None = None


# === Financial Management ===


class AdminTransactionResponse(BaseSchema):
    """Token transaction response for admin panel."""

    id: UUID
    user_id: UUID
    amount: int
    type: str
    reason: str | None = None
    reference_id: UUID | None = None
    created_at: datetime


class AdminPaymentResponse(BaseSchema):
    """Payment response for admin panel."""

    id: UUID
    user_id: UUID
    amount: Decimal
    method: str
    status: str
    external_reference: str | None = None
    confirmed_at: datetime | None = None
    created_at: datetime


class AdminRevenueResponse(BaseModel):
    """Revenue summary response."""

    start_date: date
    end_date: date
    total_revenue: Decimal
    total_transactions: int


# === Audit Log ===


class AdminAuditLogResponse(BaseSchema):
    """Audit log response for admin panel."""

    id: UUID
    admin_id: UUID
    action: str
    entity_type: str
    entity_id: UUID
    previous_value: dict | None = None
    new_value: dict | None = None
    created_at: datetime
