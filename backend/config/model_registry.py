"""Central registry for all SQLAlchemy ORM models.

This module imports every model class defined in the application. It is
critical for two reasons:
1.  **Alembic Autogenerate**: Alembic needs all models to be imported into
    its environment to correctly detect schema changes.
2.  **SQLAlchemy Mapper**: Models referencing each other via string-based
    class names (e.g., ``relationship("User", ...)``) require the referenced
    models to be loaded into the registry first.

Import order generally follows dependency hierarchy to avoid resolution
issues during initialization.
"""

from apps.auctions.models import Auction, AuctionItem, Category, Item, ItemImage
from apps.authentication.models import EmailVerificationToken, PasswordResetToken
from apps.bids.models import Bid
from apps.disputes.models import Dispute, DisputeEvidence
from apps.escrow.models import Escrow
from apps.notifications.models import Notification
from apps.orders.models import Order
from apps.payments.models import Payment

# Users - imported early as it is a frequent foreign-key target.
from apps.users.models import SellerProfile, User, UserProfile, VerificationDoc
from apps.wallet.models import Wallet, WalletTransactions

__all__ = [
    "User",
    "UserProfile",
    "SellerProfile",
    "VerificationDoc",
    "Wallet",
    "WalletTransactions",
    "Payment",
    "Category",
    "Item",
    "ItemImage",
    "Auction",
    "AuctionItem",
    "Bid",
    "Order",
    "Escrow",
    "Dispute",
    "DisputeEvidence",
    "Notification",
    "PasswordResetToken",
    "EmailVerificationToken",
]
