"""Central registry that imports all models for Alembic autogenerate."""

# Users
# Auctions
from apps.auctions.models import Auction, AuctionItem, Category, Item, ItemImage

# Authentication
from apps.authentication.models import PasswordResetToken

# Bids
from apps.bids.models import Bid

# Disputes
from apps.disputes.models import Dispute, DisputeEvidence

# Escrow
from apps.escrow.models import Escrow

# Notifications
from apps.notifications.models import Notification

# Orders
from apps.orders.models import Order
from apps.users.models import SellerProfile, User, UserProfile, VerificationDoc

# Wallet
from apps.wallet.models import Wallet, WalletTransactions

__all__ = [
    "User",
    "UserProfile",
    "SellerProfile",
    "VerificationDoc",
    "Wallet",
    "WalletTransactions",
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
]
