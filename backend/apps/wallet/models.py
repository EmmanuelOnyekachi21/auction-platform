"""ORM models for the wallet application.

Defines the Wallet and WalletTransactions tables which track each
user's fund balances and the full transaction ledger.
"""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import BaseModel

from .enums import BalanceType, ReferenceType, TransactionDirection, TransactionType

if TYPE_CHECKING:
    from apps.users.models import User


class Wallet(BaseModel):
    """Financial wallet associated with a single user.

    Balances are split into three buckets to reflect the lifecycle of
    funds on the platform:

    - ``available_funds``: freely spendable balance.
    - ``locked_funds``: reserved during an active bid or purchase flow,
      not yet released to escrow.
    - ``escrow_funds``: held in escrow pending order completion or dispute
      resolution.

    Attributes:
        user_id: Foreign key referencing the owning ``User``. One wallet
            per user, enforced by the unique constraint.
        available_funds: Spendable balance, precision 10/2.
        locked_funds: Funds reserved but not yet in escrow, precision 10/2.
        escrow_funds: Funds held in escrow, precision 10/2.
        currency: ISO 4217 currency code, defaults to ``NGN``.

    """

    __tablename__ = "wallets"
    __table_args__ = (
        CheckConstraint("available_funds >= 0", name="ck_wallet_available_funds"),
        CheckConstraint("locked_funds >= 0", name="ck_wallet_locked_funds"),
        CheckConstraint("escrow_funds >= 0", name="ck_wallet_escrow_funds"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), unique=True, index=True, nullable=False
    )
    available_funds: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00")
    )
    locked_funds: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )
    escrow_funds: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="NGN")

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="wallet")
    transactions: Mapped[list["WalletTransactions"]] = relationship(
        "WalletTransactions", back_populates="wallet"
    )


class WalletTransactions(BaseModel):
    """Immutable ledger entry recording a single wallet fund movement.

    Every credit or debit against any balance bucket (available, locked,
    escrow) produces one row here, giving a full auditable history of
    all financial activity on a wallet.

    Attributes:
        wallet_id: Foreign key referencing the affected ``Wallet``.
        amount: Absolute value of the transaction, precision 10/2.
        balance_before: Bucket balance immediately before this transaction.
        balance_after: Bucket balance immediately after this transaction.
        description: Human-readable explanation of the movement.
        transaction_type: High-level classification of the transaction.
        direction: Whether funds were credited to or debited from the bucket.
        balance_type: Which balance bucket (available, locked, escrow) changed.
        reference_id: Optional UUID of the entity that triggered the movement.
        reference_type: Optional type of the triggering entity.

    Note:
        ``updated_at`` is set to ``None`` because transaction rows are
        immutable — they are never updated after creation.

    """

    __tablename__ = "wallet_transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_wallet_transaction_amount"),
        Index("ix_wallet_transactions_wallet_id", "wallet_id"),
        Index(
            "ix_wallet_transactions_reference",
            "reference_id",
            "reference_type",
        ),
        Index("ix_wallet_transactions_type", "transaction_type"),
    )

    wallet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wallets.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    balance_before: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    balance_after: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(
        String(15), nullable=False
    )
    direction: Mapped[TransactionDirection] = mapped_column(String(6), nullable=False)
    balance_type: Mapped[BalanceType] = mapped_column(String(12), nullable=False)
    reference_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)
    reference_type: Mapped[ReferenceType] = mapped_column(String(20), nullable=True)
    updated_at = None

    # Relationship
    wallet: Mapped["Wallet"] = relationship("Wallet", back_populates="transactions")
