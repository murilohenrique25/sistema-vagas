"""Employer-owned company profile schemas."""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def normalize_and_validate_cnpj(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 14 or len(set(digits)) == 1:
        raise ValueError("CNPJ inválido")

    def digit(base: str, weights: list[int]) -> str:
        total = sum(int(n) * w for n, w in zip(base, weights))
        remainder = total % 11
        return str(0 if remainder < 2 else 11 - remainder)

    first = digit(digits[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    second = digit(digits[:12] + first, [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    if digits[-2:] != first + second:
        raise ValueError("CNPJ inválido")
    return digits


class CompanyUpsert(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    cnpj: str = Field(min_length=14, max_length=18)
    description: str | None = Field(default=None, max_length=5000)
    website: str | None = Field(default=None, max_length=500)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    industry: str | None = Field(default=None, max_length=120)
    company_size: str | None = Field(default=None, max_length=30)
    city: str | None = Field(default=None, max_length=120)
    state: str | None = Field(default=None, min_length=2, max_length=2)
    address: str | None = Field(default=None, max_length=500)
    logo_url: str | None = Field(default=None, max_length=500)

    @field_validator("cnpj")
    @classmethod
    def normalize_cnpj(cls, value: str) -> str:
        return normalize_and_validate_cnpj(value)

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value: str | None) -> str | None:
        return value.upper() if value else value


class CompanyResponse(CompanyUpsert):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    owner_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None
    cnpj_status: str | None = None
    cnpj_checked_at: datetime | None = None
    cnpj_source: str | None = None


class CnpjLookupResponse(BaseModel):
    cnpj: str
    legal_name: str
    name: str
    status: str
    industry: str | None = None
    phone: str | None = None
    city: str | None = None
    state: str | None = None
    address: str | None = None
    source: str = "BrasilAPI/Minha Receita"
