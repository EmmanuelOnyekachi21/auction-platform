"""HTTP endpoints for wallet operations."""

import hmac
import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from apps.payments.flutterwave_service import FlutterwaveService
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
from common.schemas import SuccessResponse
from config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()


def verify_flutterwave_signature(signature: str, secret: str) -> bool:
    """Verify webhook signature from Flutterwave.

    Args:
        signature: verif-hash header from request
        secret: Webhook secret from settings

    Returns:
        True if signature matches, False otherwise

    """
    return hmac.compare_digest(signature, secret)


@router.get("/me", response_model=WalletResponse)
async def get_my_wallet(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    flutterwave_service: FlutterwaveService = Depends(get_flutterwave_service),
):
    """Get current user's wallet balance.

    Args:
        current_user: Authenticated user from dependency
        db: Database session from dependency
        flutterwave_service: Flutterwave service from dependency

    Returns:
        WalletResponse with balance details

    """
    service = WalletService(db, flutterwave_service)
    return await service.get_wallet(current_user.id)


@router.post("/fund", response_model=PaymentInitiationResponse)
async def initiate_funding(
    request: InitiatePaymentRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    flutterwave_service: FlutterwaveService = Depends(get_flutterwave_service),
):
    """Initiate wallet funding via Flutterwave.

    Creates a payment record and returns Flutterwave checkout link.
    User visits the link to complete payment.

    Args:
        request: Payment details (amount, currency)
        current_user: Authenticated user from dependency
        db: Database session from dependency
        flutterwave_service: Flutterwave service from dependency

    Returns:
        PaymentInitiationResponse with payment link

    """
    service = WalletService(db, flutterwave_service)
    return await service.initiate_funding(
        user_id=current_user.id,
        amount=request.amount,
        currency=request.currency,
    )


@router.post("/webhooks/flutterwave", response_model=SuccessResponse)
async def flutterwave_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    flutterwave_service: FlutterwaveService = Depends(get_flutterwave_service),
):
    """Handle Flutterwave payment webhook.

    This endpoint is called by Flutterwave when payment status changes.

    Security:
    - No JWT auth (webhook from Flutterwave, not user)
    - Signature verification prevents spoofing
    - Always verifies with Flutterwave API before trusting
    - Idempotent (safe to retry)

    Args:
        request: FastAPI request object
        db: Database session from dependency
        flutterwave_service: Flutterwave service from dependency

    Returns:
        Success response or error details

    """
    logger.info("Flutter webhook came in")
    # 1. Verify signature
    signature = request.headers.get("verif-hash")
    if not signature:
        logger.error("Missing webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing signature",
        )

    if not verify_flutterwave_signature(signature, settings.flutterwave_webhook_secret):
        logger.error("Invalid webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature",
        )

    # 2. Parse payload
    payload = await request.json()
    logger.info(f"Webhook received: {payload.get('txRef')}")

    # Check event type
    event_type = payload.get("event.type")
    if not event_type:
        logger.warning("Missing event.type")
        return SuccessResponse(
            message="Ignored: missing event type",
            data={"status": "ignored", "reason": "missing_event_type"},
        )

    # Extract payment details
    tx_ref = payload.get("txRef")
    flw_ref = payload.get("flwRef")
    webhook_status = payload.get("status")
    webhook_amount = payload.get("amount")

    if not tx_ref:
        logger.error("Missing txRef")
        return SuccessResponse(
            message="Error: missing transaction reference",
            data={"status": "error", "message": "Missing txRef"},
        )

    # Only process successful payments
    if webhook_status != "successful":
        logger.info(f"Ignoring non-successful payment: {tx_ref}")
        return SuccessResponse(
            message="Ignored: payment not successful",
            data={
                "status": "ignored",
                "reason": f"status_{webhook_status}",
            },
        )

    # 3. Process webhook
    service = WalletService(db, flutterwave_service)

    try:
        await service.handle_webhook(
            transaction_reference=tx_ref,
            provider_reference=flw_ref,
            status=webhook_status,
            amount=Decimal(str(webhook_amount)),
            provider_response=payload,
        )

        logger.info(f"Webhook processed successfully: {tx_ref}")
        return SuccessResponse(
            message="Webhook processed successfully",
            data={"status": "success"},
        )

    except Exception as e:
        logger.error(f"Webhook processing failed for {tx_ref}: {e}")
        return SuccessResponse(
            message="Webhook processing failed",
            data={"status": "error", "message": str(e)},
        )


@router.get("/transactions", response_model=PaginatedResponse)
async def get_transactions(
    transaction_type: Optional[str] = None,
    direction: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    flutterwave_service: FlutterwaveService = Depends(get_flutterwave_service),
):
    """Get user's transaction history with pagination.

    Args:
        transaction_type: Filter by transaction type (optional)
        direction: Filter by direction (CREDIT/DEBIT) (optional)
        page: Page number (default: 1)
        limit: Items per page (default: 20)
        current_user: Authenticated user from dependency
        db: Database session from dependency
        flutterwave_service: Flutterwave service from dependency

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
async def initiate_withdrawal(
    request: WithdrawalRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    flutterwave_service: FlutterwaveService = Depends(get_flutterwave_service),
):
    """Initiate withdrawal from wallet to bank account.

    Debits wallet immediately and creates withdrawal transaction.
    Actual bank transfer happens via background task.

    Args:
        request: Withdrawal details (amount, bank_code, account_number)
        current_user: Authenticated user from dependency
        db: Database session from dependency
        flutterwave_service: Flutterwave service from dependency

    Returns:
        TransactionResponse for the withdrawal

    """
    service = WalletService(db, flutterwave_service)
    return await service.initiate_withdrawal(
        user_id=current_user.id,
        withdrawal_request=request,
    )
