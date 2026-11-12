"""Transactional wallet operations in Brazilian reais."""
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.wallet import WalletTransaction


class WalletService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_balance(self, user_id: UUID) -> Decimal:
        result = await self.session.execute(select(User.wallet_balance).where(User.id == user_id))
        balance = result.scalar_one_or_none()
        return Decimal(balance or 0).quantize(Decimal("0.01"))

    async def get_history(self, user_id: UUID, limit: int = 50) -> list[WalletTransaction]:
        result = await self.session.execute(
            select(WalletTransaction).where(WalletTransaction.user_id == user_id)
            .order_by(WalletTransaction.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def debit(
        self, user_id: UUID, amount: Decimal, reason: str = "Débito da carteira",
        reference_id: UUID | None = None, operation_id: str | None = None,
    ) -> Decimal:
        if operation_id:
            existing = await self.session.execute(
                select(WalletTransaction.id).where(WalletTransaction.operation_id == operation_id)
            )
            if existing.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Operação já processada.")
        result = await self.session.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
        balance = Decimal(user.wallet_balance or 0)
        if balance < amount:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Saldo insuficiente. Disponível: R$ {balance:.2f}; necessário: R$ {amount:.2f}.",
            )
        user.wallet_balance = balance - amount
        self.session.add(WalletTransaction(
            user_id=user_id, amount=-amount, balance_after=user.wallet_balance,
            type="debit", reason=reason, reference_id=reference_id, operation_id=operation_id,
        ))
        await self.session.flush()
        return user.wallet_balance

    async def credit(
        self, user_id: UUID, amount: Decimal, reason: str = "Crédito da carteira",
        reference_id: UUID | None = None, operation_id: str | None = None,
    ) -> Decimal:
        result = await self.session.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")
        user.wallet_balance = Decimal(user.wallet_balance or 0) + amount
        self.session.add(WalletTransaction(
            user_id=user_id, amount=amount, balance_after=user.wallet_balance,
            type="credit", reason=reason, reference_id=reference_id, operation_id=operation_id,
        ))
        await self.session.flush()
        return user.wallet_balance
