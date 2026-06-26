"""Admin panel router for user management operations."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from apps.auctions.enums import AuctionStatus
from apps.auctions.service import AuctionService
from apps.orders.enums import OrderStatus
from apps.orders.schemas import OrderDetailResponse
from apps.orders.service import OrderService
from apps.payments.paystack_service import PaystackService
from apps.users.enums import AccountStatus, KYCTier
from apps.users.models import User
from apps.users.service import UserService
from apps.wallet.service import WalletService
from common.dependency import get_db, get_flutterwave_service, require_admin
from common.schemas import MessageResponse, PaginatedResponse

router = APIRouter()


class UpdateStatusRequest(BaseModel):
    """Request body for updating a user's account status.

    Attributes:
        account_status: The new account status to apply.

    """

    account_status: AccountStatus


@router.get("/verify-users", status_code=200)
async def get_unverified_sellers(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get a list of users with pending seller verification."""
    service = UserService(db)
    return await service.get_unverified_sellers(
        has_seller_profile=True,
        seller_verified=False,
        limit=limit,
    )


@router.get("/wallet-summary", status_code=200)
async def get_platform_wallet_summary(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Retrieve aggregate sums of funds across all wallets.

    Calculates the total available, locked, and escrow funds.
    """
    from decimal import Decimal

    from sqlalchemy import func, select

    from apps.wallet.models import Wallet

    stmt = select(
        func.sum(Wallet.available_funds).label("available_funds"),
        func.sum(Wallet.locked_funds).label("locked_funds"),
        func.sum(Wallet.escrow_funds).label("escrow_funds"),
    )
    result = await db.execute(stmt)
    row = result.fetchone()

    available = Decimal("0.00")
    locked = Decimal("0.00")
    escrow = Decimal("0.00")

    if row:
        available = (
            row.available_funds if row.available_funds is not None else Decimal("0.00")
        )
        locked = row.locked_funds if row.locked_funds is not None else Decimal("0.00")
        escrow = row.escrow_funds if row.escrow_funds is not None else Decimal("0.00")

    return {
        "available_funds": float(available),
        "locked_funds": float(locked),
        "escrow_funds": float(escrow),
    }


@router.get("/kyc/pending", status_code=200)
async def get_pending_kyc_documents(
    page: int = 1,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get all pending KYC documents for review (Admin view)."""
    from sqlalchemy import select

    from apps.users.enums import KYCStatus
    from apps.users.kyc_models import KYCDocumentModel
    from common.pagination import paginate

    stmt = (
        select(KYCDocumentModel)
        .where(KYCDocumentModel.status == KYCStatus.PENDING)
        .order_by(KYCDocumentModel.created_at.asc())
    )

    result = await paginate(stmt, page, limit, db)

    result.data = [
        {
            "id": str(doc.id),
            "user_id": str(doc.user_id),
            "document_type": doc.document_type.value if doc.document_type else None,
            "document_url": doc.document_url,
            "status": doc.status.value if doc.status else None,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
        }
        for doc in result.data
    ]
    return result


@router.get("/users", status_code=200)
async def get_all_users(
    search: str | None = None,
    account_status: AccountStatus | None = None,
    kyc_tier: KYCTier | None = None,
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get paginated list of all users with optional filters."""
    service = UserService(db)
    return await service.get_all_users(
        search=search,
        account_status=account_status,
        kyc_tier=kyc_tier,
        page=page,
        limit=limit,
    )


@router.get("/users/{user_id}", status_code=200)
async def get_user_detail(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Get full detail for a single user including all relationships."""
    service = UserService(db)
    return await service.get_user_detail(user_id)


@router.patch("/users/{user_id}/status", status_code=200)
async def update_user_status(
    user_id: UUID,
    data: UpdateStatusRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a user's account status (suspend, ban, reactivate)."""
    service = UserService(db)
    return await service.update_user_status(user_id, data.account_status)


@router.get("/auctions", status_code=200, response_model=PaginatedResponse)
async def get_auctions(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    status: Optional[AuctionStatus] = None,
    page: int = 1,
    limit: int = 20,
):
    """Get all auctions for admin dashboard with optional status filter."""
    service = AuctionService(db)
    return await service.get_all_auctions(status, page, limit)


@router.patch(
    "/auctions/{auction_id}/cancel", status_code=200, response_model=MessageResponse
)
async def cancel_auction(
    auction_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Cancel an auction.

    Requires: An Admin

    """
    service = AuctionService(db)
    return await service.cancel_auction_admin(auction_id=auction_id)


@router.get("/orders", status_code=200)
async def get_admin_orders(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    status: Optional[OrderStatus] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
):
    service = OrderService(db)
    return await service.get_orders_admin(
        page,
        limit,
        status,
        search,
    )


@router.get("/orders/{order_id}", status_code=200, response_model=OrderDetailResponse)
async def get_admin_order_detail(
    order_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get full details for a single order (Admin view).

    Includes escrow and dispute details where applicable.
    """
    service = OrderService(db)
    order = await service._order_repo.get_by_id(order_id)
    if not order:
        from common.exceptions import OrderNotFoundException

        raise OrderNotFoundException()
    escrow = await service._escrow_repo.get_by_order_id(order_id)
    return service._build_order_detail(order, escrow)


@router.get("/wallet-transactions", status_code=200)
async def get_admin_wallet_transactions(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    flutterwave_service: PaystackService = Depends(get_flutterwave_service),
    transaction_type: Optional[str] = None,
    direction: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
):
    """Get all wallet transactions across the platform (Admin view)."""
    service = WalletService(db, flutterwave_service)
    return await service.get_wallet_transactions_admin(
        page=page,
        limit=limit,
        transaction_type=transaction_type,
        direction=direction,
        search=search,
    )


@router.get("/payments", status_code=200)
async def get_admin_payments(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    flutterwave_service: PaystackService = Depends(get_flutterwave_service),
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
):
    """Get all payments across the platform (Admin view)."""
    service = WalletService(db, flutterwave_service)
    return await service.get_payments_admin(
        page=page,
        limit=limit,
        status=status,
        search=search,
    )


@router.get("/settings", status_code=200)
async def get_admin_settings(
    admin: User = Depends(require_admin),
):
    """Retrieve platform configuration settings for administration view."""
    from config.settings import settings

    return {
        "commission_rate": 0.05,  # 5% platform commission
        "bvn_verification_enabled": settings.bvn_verification_enabled,
        "max_auction_duration_hours": settings.max_auction_duration_hours,
        "min_auction_duration_mins": settings.min_auction_duration_mins,
        "shipping_deadline_days": settings.shipping_deadline,
        "tier_limits": {
            "tier_1": {
                "max_bid": float(settings.tier_1_max_bid),
                "max_wallet_balance": float(settings.tier_1_max_wallet_balance),
                "max_withdrawal": float(settings.tier_1_max_withdrawal),
            },
            "tier_2": {
                "max_bid": float(settings.tier_2_max_bid),
                "max_wallet_balance": float(settings.tier_2_max_wallet_balance),
                "max_daily_withdrawal": float(settings.tier_2_max_daily_withdrawal),
            },
            "tier_3": {
                "max_bid": float(settings.tier_3_max_bid),
                "max_wallet_balance": float(settings.tier_3_max_wallet_balance),
                "max_daily_withdrawal": float(settings.tier_3_max_daily_withdrawal),
            },
        },
    }
