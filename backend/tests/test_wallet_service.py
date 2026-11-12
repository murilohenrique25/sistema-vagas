from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.wallet_service import WalletService


def result_with(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


@pytest.mark.asyncio
async def test_debit_updates_balance_and_records_ledger():
    user = MagicMock(wallet_balance=Decimal("50.00"))
    session = AsyncMock()
    session.execute.return_value = result_with(user)
    session.add = MagicMock()
    balance = await WalletService(session).debit(uuid4(), Decimal("10.00"), reason="Publicação")
    assert balance == Decimal("40.00")
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_debit_rejects_insufficient_balance():
    user = MagicMock(wallet_balance=Decimal("4.99"))
    session = AsyncMock()
    session.execute.return_value = result_with(user)
    with pytest.raises(HTTPException) as exc:
        await WalletService(session).debit(uuid4(), Decimal("5.00"))
    assert exc.value.status_code == 402


@pytest.mark.asyncio
async def test_credit_updates_balance_and_records_ledger():
    user = MagicMock(wallet_balance=Decimal("10.00"))
    session = AsyncMock()
    session.execute.return_value = result_with(user)
    session.add = MagicMock()
    balance = await WalletService(session).credit(uuid4(), Decimal("50.00"), reason="PIX")
    assert balance == Decimal("60.00")
    session.add.assert_called_once()
