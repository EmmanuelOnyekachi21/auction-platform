"""HTTP endpoints for wallet operations."""

import hashlib
import hmac
import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.payments.paystack_service import PaystackService
from apps.users.models import User
from apps.wallet.schemas import (
    InitiatePaymentRequest,
    PaymentInitiationResponse,
    TransactionResponse,
    WalletResponse,
    WithdrawalRequest,
)
from apps.wallet.service import WalletService
from common.dependency import get_current_active_user, get_db, get_flutterwave_service
from common.pagination import PaginatedResponse
from common.rate_limiter import limiter
from common.schemas import SuccessResponse
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def verify_paystack_signature(
    payload_bytes: bytes, signature: str, secret: str
) -> bool:
    """Verify Paystack webhook signature using HMAC-SHA512.

    Args:
        payload_bytes: Raw request body bytes
        signature: x-paystack-signature header value
        secret: Paystack secret key

    Returns:
        True if signature is valid

    """
    expected = hmac.new(
        secret.encode("utf-8"),
        payload_bytes,
        hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.get("/me", response_model=WalletResponse)
async def get_my_wallet(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    flutterwave_service: PaystackService = Depends(get_flutterwave_service),
):
    """Get current user's wallet balance.

    Args:
        current_user: Authenticated user from dependency
        db: Database session from dependency
        flutterwave_service: Paystack service from dependency

    Returns:
        WalletResponse with balance details

    """
    service = WalletService(db, flutterwave_service)
    return await service.get_wallet(current_user.id)


@router.post("/fund", response_model=PaymentInitiationResponse)
@limiter.limit("10/hour")
async def initiate_funding(
    request: Request,
    data: InitiatePaymentRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    flutterwave_service: PaystackService = Depends(get_flutterwave_service),
):
    """Initiate wallet funding via Paystack.

    Creates a payment record and returns Paystack checkout link.
    User visits the link to complete payment.

    Args:
        data: Payment details (amount, currency)
        current_user: Authenticated user from dependency
        db: Database session from dependency
        flutterwave_service: Paystack service from dependency

    Returns:
        PaymentInitiationResponse with payment link

    """
    service = WalletService(db, flutterwave_service)
    return await service.initiate_funding(
        user_id=current_user.id,
        amount=data.amount,
        currency=data.currency,
    )


@router.post("/webhooks/paystack", response_model=SuccessResponse)
@limiter.limit("100/minute")
async def paystack_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    flutterwave_service: PaystackService = Depends(get_flutterwave_service),
):
    """Handle Paystack payment webhook.

    Security: HMAC-SHA512 signature verification using x-paystack-signature header.
    """
    raw_body = await request.body()

    # 1. Verify signature
    signature = request.headers.get("x-paystack-signature")
    if not signature:
        logger.error("Missing Paystack webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing signature",
        )

    if not verify_paystack_signature(raw_body, signature, settings.paystack_secret_key):
        logger.error("Invalid Paystack webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    # 2. Parse payload
    payload = await request.json()
    event = payload.get("event", "")
    logger.info(f"Paystack webhook received: {event}")

    # Only process charge.success events
    if event != "charge.success":
        return SuccessResponse(
            message="Ignored",
            data={"status": "ignored", "event": event},
        )

    data = payload.get("data", {})
    tx_ref = data.get("reference")
    webhook_status = data.get("status")
    webhook_amount = data.get("amount", 0)

    if not tx_ref:
        return SuccessResponse(
            message="Error: missing reference", data={"status": "error"}
        )

    # 3. Process webhook
    service = WalletService(db, flutterwave_service)
    try:
        await service.handle_webhook(
            transaction_reference=tx_ref,
            provider_reference=tx_ref,
            status=webhook_status,
            amount=Decimal(str(webhook_amount)) / 100,  # kobo to naira
            provider_response=payload,
        )
        logger.info(f"Paystack webhook processed: {tx_ref}")
        return SuccessResponse(
            message="Webhook processed successfully",
            data={"status": "success"},
        )
    except Exception as e:
        logger.error(f"Paystack webhook processing failed for {tx_ref}: {e}")
        return SuccessResponse(
            message="Webhook processing failed",
            data={"status": "error", "message": str(e)},
        )


@router.get("/payments/{payment_id}/status")
async def get_payment_status(
    payment_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Poll payment status for a given payment ID.

    Used by the frontend confirm page to determine if the webhook
    has been processed and the wallet has been credited.

    Returns status: pending | completed | failed
    """
    from uuid import UUID

    from sqlalchemy import select

    from apps.payments.models import Payment

    try:
        pid = UUID(payment_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payment ID")

    stmt = select(Payment).where(Payment.id == pid)
    result = await db.execute(stmt)
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Security: only the wallet owner can poll this
    from apps.wallet.models import Wallet

    wallet_stmt2 = select(Wallet).where(Wallet.id == payment.wallet_id)
    wallet_result = await db.execute(wallet_stmt2)
    wallet = wallet_result.scalar_one_or_none()

    if not wallet or wallet.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    return {
        "payment_id": str(payment.id),
        "status": payment.status,  # PENDING | COMPLETED | FAILED
        "amount": str(payment.amount),
        "currency": payment.currency,
        "transaction_reference": payment.transaction_reference,
        "webhook_received": payment.webhook_received_at is not None,
    }


@router.get("/transactions", response_model=PaginatedResponse)
async def get_transactions(
    transaction_type: Optional[str] = None,
    direction: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    flutterwave_service: PaystackService = Depends(get_flutterwave_service),
):
    """Get user's transaction history with pagination.

    Args:
        transaction_type: Filter by transaction type (optional)
        direction: Filter by direction (CREDIT/DEBIT) (optional)
        page: Page number (default: 1)
        limit: Items per page (default: 20)
        current_user: Authenticated user from dependency
        db: Database session from dependency
        flutterwave_service: Paystack service from dependency

    Returns:
        Paginated response with transactions

    """
    service = WalletService(db, flutterwave_service)

    return await service.get_transactions(
        user_id=current_user.id,
        transaction_type=transaction_type,
        direction=direction,
        page=page,
        limit=limit,
    )


@router.post("/withdraw", response_model=TransactionResponse)
@limiter.limit("5/hour")
async def initiate_withdrawal(
    request: Request,
    data: WithdrawalRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    flutterwave_service: PaystackService = Depends(get_flutterwave_service),
):
    """Initiate withdrawal from wallet to bank account.

    Debits wallet immediately and creates withdrawal transaction.
    Actual bank transfer happens via background task.

    Args:
        data: Withdrawal details (amount, bank_code, account_number)
        current_user: Authenticated user from dependency
        db: Database session from dependency
        flutterwave_service: Paystack service from dependency

    Returns:
        TransactionResponse for the withdrawal

    """
    service = WalletService(db, flutterwave_service)
    return await service.initiate_withdrawal(
        user_id=current_user.id,
        withdrawal_request=data,
    )
