"""Wallet and Mercado Pago Checkout Pro routes."""

import hashlib
import hmac
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import CurrentUser, get_current_user
from app.core.database import get_session
from app.models.user import User
from app.schemas.payment import (
    PaymentDetailResponse,
    PublicPaymentConfigResponse,
    WalletBalanceResponse,
    WalletCheckoutReconcileRequest,
    WalletCheckoutRequest,
    WalletCheckoutResponse,
)
from app.services.payment_service import PaymentService
from app.services.payment_settings_service import PaymentSettingsService
from app.services.wallet_service import WalletService

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/config", response_model=PublicPaymentConfigResponse)
async def get_public_payment_config(
    session: AsyncSession = Depends(get_session),
) -> PublicPaymentConfigResponse:
    return PublicPaymentConfigResponse(
        **await PaymentSettingsService(session).get_public_config()
    )


@router.post("/webhooks/mercadopago", include_in_schema=False)
async def mercadopago_webhook(
    request: Request,
    x_signature: str | None = Header(default=None),
    x_request_id: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
):
    gateway_config = await PaymentSettingsService(session).get_gateway_config()
    data_id = request.query_params.get("data.id")
    event_type = request.query_params.get("type")
    parts = dict(
        item.split("=", 1)
        for item in (x_signature or "").split(",")
        if "=" in item
    )
    timestamp, received = parts.get("ts"), parts.get("v1")
    if event_type != "payment":
        return {"received": True}
    if not data_id or not x_request_id or not timestamp or not received:
        raise HTTPException(status_code=401, detail="Webhook inválido")
    if not gateway_config["webhook_secret"]:
        raise HTTPException(status_code=503, detail="Webhook não configurado")
    manifest = f"id:{data_id.lower()};request-id:{x_request_id};ts:{timestamp};"
    expected = hmac.new(
        gateway_config["webhook_secret"].encode(), manifest.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(received, expected):
        raise HTTPException(status_code=401, detail="Assinatura inválida")
    await PaymentService(session).process_mercadopago_payment(data_id)
    return {"received": True}


@router.get("/wallet", response_model=WalletBalanceResponse)
async def get_wallet_balance(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WalletBalanceResponse:
    return WalletBalanceResponse(
        balance=await WalletService(session).get_balance(current_user.id)
    )


@router.post("/checkout/wallet", response_model=WalletCheckoutResponse)
async def create_wallet_checkout(
    data: WalletCheckoutRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WalletCheckoutResponse:
    payer_email = current_user.email
    if not payer_email:
        result = await session.execute(select(User.email).where(User.id == current_user.id))
        payer_email = result.scalar_one_or_none()
    if not payer_email:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return await PaymentService(session).create_wallet_checkout(
        current_user.id, payer_email, data.amount
    )


@router.post("/checkout/wallet/reconcile", response_model=PaymentDetailResponse)
async def reconcile_wallet_checkout(
    data: WalletCheckoutReconcileRequest,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PaymentDetailResponse:
    return await PaymentService(session).reconcile_wallet_checkout(
        data.mercado_pago_payment_id, current_user.id
    )


@router.get("/wallet/transactions")
async def get_wallet_transactions(
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    items = await WalletService(session).get_history(current_user.id)
    return [{
        "id": str(item.id), "amount": item.amount,
        "balance_after": item.balance_after, "type": item.type,
        "reason": item.reason,
        "reference_id": str(item.reference_id) if item.reference_id else None,
        "created_at": item.created_at,
    } for item in items]


@router.get("/{payment_id}", response_model=PaymentDetailResponse)
async def get_payment_detail(
    payment_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PaymentDetailResponse:
    return await PaymentService(session).get_payment_detail(payment_id, current_user.id)
