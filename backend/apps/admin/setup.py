"""SQLAdmin configuration for KaraKaja admin panel."""

import logging

from sqladmin import Admin
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.requests import Request

from apps.admin.views.kyc import KYCDocumentAdmin, KYCProfileAdmin
from apps.admin.views.users import SellerProfileAdmin, UserAdmin, UserProfileAdmin
from apps.authentication.security import verify_password
from apps.users.repository import UserRepository
from config.database import engine
from config.settings import settings

from .dashboard import DashboardView
from .views.auctions import (
    AuctionAdmin,
    BidIncrementTierAdmin,
    CategoryAdmin,
    ItemAdmin,
)
from .views.financial import PaymentAdmin, WalletTransactionAdmin
from .views.orders import DisputeAdmin, EscrowAdmin, OrderAdmin

logger = logging.getLogger(__name__)

SECRET_KEY = settings.secret_key


class AdminAuthBackend(AuthenticationBackend):
    """Authentication backend for SQLAdmin.

    Verifies that the user exists, has the correct password,
    and holds an ADMIN or SUPERUSER role.
    """

    async def login(self, request: Request) -> bool:
        """Handle login form submission."""
        form = await request.form()
        email = form.get("username")  # SQLAdmin uses 'username' field name
        password = form.get("password")

        if not email or not password:
            return False

        # Create a fresh DB session for this request
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            repo = UserRepository(session)
            user = await repo.get_by_email(email)

        if not user:
            return False

        if not verify_password(password, user.password_hash):
            return False

        if user.role.value not in ("ADMIN", "SUPERUSER"):
            return False

        # Store user id in session token
        request.session.update({"admin_user_id": str(user.id)})
        return True

    async def authenticate(self, request: Request) -> bool:
        """Check if the current session is authenticated ."""
        return "admin_user_id" in request.session

    async def logout(self, request: Request) -> None:
        """Clear the session on logout."""
        request.session.clear()
        return True


def create_admin(app) -> Admin:
    """Create and configure the SQLAdmin instance.

    Args:
        app: The FastAPI application instance.

    Returns:
        Admin: Configured SQLAdmin instance.

    """
    auth_backend = AdminAuthBackend(secret_key=SECRET_KEY)
    admin = Admin(
        app=app,
        engine=engine,
        authentication_backend=auth_backend,
        title="KaraKaja Admin",
        base_url="/admin",
        templates_dir="templates",  # backend/templates/ for custom pages
    )

    admin.add_view(UserAdmin)
    admin.add_view(UserProfileAdmin)
    admin.add_view(SellerProfileAdmin)
    admin.add_view(KYCProfileAdmin)
    admin.add_view(KYCDocumentAdmin)

    # Auctions
    admin.add_view(CategoryAdmin)
    admin.add_view(ItemAdmin)
    admin.add_view(AuctionAdmin)
    admin.add_view(BidIncrementTierAdmin)

    # Orders, Escrow, Disputes
    admin.add_view(OrderAdmin)
    admin.add_view(EscrowAdmin)
    admin.add_view(DisputeAdmin)

    # Financial audit
    admin.add_view(WalletTransactionAdmin)
    admin.add_view(PaymentAdmin)

    # Custom dashboard page
    admin.add_base_view(DashboardView)

    logger.info("SQLAdmin configured successfully")

    return admin
