"""Token-related models: TokenTransaction, TokenConfig, TokenPackages."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import UUIDMixin
from app.models.enums import TokenTransactionType


class TokenTransaction(Base, UUIDMixin):
    """Token transactions table."""

    __tablename__ = "token_transactions"
    __table_args__ = (
        Index("ix_token_transactions_user_id_created_at", "user_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[TokenTransactionType] = mapped_column(nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User", back_populates="token_transactions")

    def __repr__(self) -> str:
        return f"<TokenTransaction(id={self.id}, amount={self.amount}, type={self.type})>"


class TokenConfig(Base, UUIDMixin):
    """Token configuration table - defines token costs per feature."""

    __tablename__ = "token_config"

    feature_key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    feature_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tokens_required: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    def __repr__(self) -> str:
        return f"<TokenConfig(id={self.id}, feature_key={self.feature_key})>"


class TokenPackage(Base, UUIDMixin):
    """Token packages available for purchase."""

    __tablename__ = "token_packages"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    token_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<TokenPackage(id={self.id}, name={self.name})>"
