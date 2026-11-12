"""Token service: balance, debit, credit, refund, history, and low balance notification."""

import logging
import math
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import (
    DeliveryStatus,
    NotificationChannel,
    TokenTransactionType,
)
from app.models.notification import Notification
from app.models.token import TokenTransaction
from app.schemas.token import (
    PaginatedTransactionsResponse,
    TokenBalanceResponse,
    TokenTransactionResponse,
)

logger = logging.getLogger(__name__)

# Default page size for transaction history
DEFAULT_PAGE_SIZE = 20


class TokenService:
    """Service handling token-related business logic.

    Implements:
    - Balance query (Req 10.4)
    - Debit with balance validation (Req 10.4, 10.5)
    - Credit (Req 10.4)
    - Refund (Req 10.6)
    - Paginated transaction history (Req 10.6)
    - Low balance notification (Req 10.8)
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_balance(self, user_id: UUID) -> TokenBalanceResponse:
        """Get the current token balance for a user.

        Balance is calculated as the sum of all transactions:
        - credits add to balance
        - debits subtract from balance
        - refunds add back to balance
        """
        balance = await self._calculate_balance(user_id)
        return TokenBalanceResponse(user_id=user_id, balance=balance)

    async def debit(
        self,
        user_id: UUID,
        amount: int,
        reason: str,
        reference_id: UUID | None = None,
    ) -> TokenTransaction:
        """Debit tokens from user balance (Req 10.4, 10.5).

        Validates that the user has sufficient balance before debiting.
        Raises HTTPException 400 if insufficient balance.
        After successful debit, checks for low balance notification.
        """
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A quantidade de tokens deve ser maior que zero",
            )

        current_balance = await self._calculate_balance(user_id)

        if current_balance < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Saldo insuficiente. Saldo atual: {current_balance} tokens. "
                    f"Necessário: {amount} tokens."
                ),
            )

        transaction = TokenTransaction(
            user_id=user_id,
            amount=-amount,
            type=TokenTransactionType.debit,
            reason=reason,
            reference_id=reference_id,
        )
        self.session.add(transaction)
        await self.session.flush()
        await self.session.refresh(transaction)

        # Check if low balance notification should be sent (Req 10.8)
        new_balance = current_balance - amount
        await self._check_low_balance_notification(user_id, new_balance)

        return transaction

    async def credit(
        self,
        user_id: UUID,
        amount: int,
        reason: str,
        reference_id: UUID | None = None,
    ) -> TokenTransaction:
        """Credit tokens to user balance.

        Used for purchases, plan bonuses, and administrative adjustments.
        """
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A quantidade de tokens deve ser maior que zero",
            )

        transaction = TokenTransaction(
            user_id=user_id,
            amount=amount,
            type=TokenTransactionType.credit,
            reason=reason,
            reference_id=reference_id,
        )
        self.session.add(transaction)
        await self.session.flush()
        await self.session.refresh(transaction)

        return transaction

    async def refund(self, transaction_id: UUID) -> TokenTransaction:
        """Refund a previous debit transaction (Req 10.6).

        Validates:
        - Original transaction exists
        - Original transaction is a debit
        - Original transaction has not already been refunded
        """
        # Fetch original transaction
        result = await self.session.execute(
            select(TokenTransaction).where(TokenTransaction.id == transaction_id)
        )
        original = result.scalar_one_or_none()

        if not original:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transação original não encontrada",
            )

        if original.type != TokenTransactionType.debit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Apenas transações de débito podem ser estornadas",
            )

        # Check if already refunded (look for existing refund referencing this transaction)
        existing_refund = await self.session.execute(
            select(TokenTransaction).where(
                TokenTransaction.reference_id == transaction_id,
                TokenTransaction.type == TokenTransactionType.refund,
            )
        )
        if existing_refund.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta transação já foi estornada",
            )

        # Create refund transaction (amount is positive, restoring balance)
        refund_amount = abs(original.amount)
        refund_transaction = TokenTransaction(
            user_id=original.user_id,
            amount=refund_amount,
            type=TokenTransactionType.refund,
            reason=f"Estorno: {original.reason or 'transação anterior'}",
            reference_id=transaction_id,
        )
        self.session.add(refund_transaction)
        await self.session.flush()
        await self.session.refresh(refund_transaction)

        return refund_transaction

    async def get_history(
        self, user_id: UUID, page: int = 1, page_size: int = DEFAULT_PAGE_SIZE
    ) -> PaginatedTransactionsResponse:
        """Get paginated transaction history for a user (Req 10.6).

        Returns transactions ordered by created_at descending.
        """
        # Count total
        count_query = select(func.count(TokenTransaction.id)).where(
            TokenTransaction.user_id == user_id
        )
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        # Fetch paginated transactions
        offset = (page - 1) * page_size
        query = (
            select(TokenTransaction)
            .where(TokenTransaction.user_id == user_id)
            .order_by(TokenTransaction.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(query)
        transactions = result.scalars().all()

        items = [
            TokenTransactionResponse(
                id=t.id,
                user_id=t.user_id,
                amount=abs(t.amount),
                type=t.type,
                reason=t.reason,
                reference_id=t.reference_id,
                created_at=t.created_at,
            )
            for t in transactions
        ]

        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return PaginatedTransactionsResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    # --- Private helpers ---

    async def _calculate_balance(self, user_id: UUID) -> int:
        """Calculate current balance from all transactions.

        Credits and refunds are positive amounts, debits are negative.
        """
        result = await self.session.execute(
            select(func.coalesce(func.sum(TokenTransaction.amount), 0)).where(
                TokenTransaction.user_id == user_id
            )
        )
        return int(result.scalar_one())

    async def _check_low_balance_notification(
        self, user_id: UUID, current_balance: int
    ) -> None:
        """Check if user should receive a low balance notification (Req 13.5).

        Sends notification if balance is ≤10% of average consumption
        over the last 30 days.

        Uses NotificationService for proper queuing and retry.
        Wrapped in try/except so notification failure doesn't block the debit operation.
        """
        try:
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

            # Calculate total consumption over last 30 days (sum of all debits)
            result = await self.session.execute(
                select(func.coalesce(func.sum(func.abs(TokenTransaction.amount)), 0)).where(
                    TokenTransaction.user_id == user_id,
                    TokenTransaction.type == TokenTransactionType.debit,
                    TokenTransaction.created_at >= thirty_days_ago,
                )
            )
            total_consumption_30d = int(result.scalar_one())

            # If no consumption in the last 30 days, no notification needed
            if total_consumption_30d == 0:
                return

            # Calculate 10% threshold of average consumption
            threshold = total_consumption_30d * 0.10

            if current_balance <= threshold:
                from app.services.notification_service import NotificationService

                notification_service = NotificationService(self.session)
                await notification_service.send_notification(
                    user_id=user_id,
                    title="Saldo de tokens baixo",
                    message=(
                        f"Seu saldo de tokens está baixo: {current_balance} tokens restantes. "
                        f"Com base no seu consumo dos últimos 30 dias, recomendamos recarregar."
                    ),
                    channel=NotificationChannel.both,
                )
        except Exception as e:
            logger.error(
                "Failed to send low balance notification for user %s: %s",
                user_id,
                e,
            )
