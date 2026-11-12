"""Token-related schemas for balance, transactions, and operations."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import TokenTransactionType
from app.schemas.base import BaseSchema, PaginatedResponse


class TokenBalanceResponse(BaseSchema):
    """Response schema for token balance query."""

    user_id: UUID
    balance: int
    currency: str = "tokens"


class TokenTransactionResponse(BaseSchema):
    """Response schema for a single token transaction."""

    id: UUID
    user_id: UUID
    amount: int
    type: TokenTransactionType
    reason: str | None = None
    reference_id: UUID | None = None
    created_at: datetime


class PaginatedTransactionsResponse(PaginatedResponse[TokenTransactionResponse]):
    """Paginated response for token transaction history."""

    pass


class TokenDebitRequest(BaseModel):
    """Request schema for debiting tokens (internal use)."""

    amount: int = Field(..., gt=0, description="Quantidade de tokens a debitar")
    reason: str = Field(..., max_length=500, description="Motivo do débito")
    reference_id: UUID | None = Field(
        None, description="ID de referência (ex: análise IA, destaque)"
    )


class TokenCreditRequest(BaseModel):
    """Request schema for crediting tokens (internal use)."""

    amount: int = Field(..., gt=0, description="Quantidade de tokens a creditar")
    reason: str = Field(..., max_length=500, description="Motivo do crédito")
    reference_id: UUID | None = Field(
        None, description="ID de referência (ex: pagamento, pacote)"
    )


class TokenRefundRequest(BaseModel):
    """Request schema for refunding a transaction."""

    transaction_id: UUID = Field(
        ..., description="ID da transação original a ser estornada"
    )
