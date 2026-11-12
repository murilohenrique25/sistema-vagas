"""Schemas for irreversible self-service account deletion."""

from pydantic import BaseModel, Field


class DeleteAccountRequest(BaseModel):
    confirmation: str = Field(min_length=1, max_length=50)
    password: str | None = Field(default=None, min_length=1, max_length=128)


class DeleteAccountResponse(BaseModel):
    message: str

