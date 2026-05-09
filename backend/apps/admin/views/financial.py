"""SQLAdmin model views for financial entities.

Registers ``WalletTransactionAdmin`` and ``PaymentAdmin`` as read-only
views in the admin panel.
"""

from sqladmin import ModelView
from sqladmin.filters import AllUniqueStringValuesFilter, StaticValuesFilter

from apps.payments.models import Payment
from apps.wallet.enums import BalanceType, TransactionDirection, TransactionType
from apps.wallet.models import WalletTransactions


class WalletTransactionAdmin(ModelView, model=WalletTransactions):
    """Read-only admin view for the wallet transaction ledger.

    Financial records must not be created, edited, or deleted through
    the admin panel.
    """

    name = "Wallet Transaction"
    name_plural = "Wallet Transactions"
    icon = "fa-solid fa-money-bill-transfer"

    can_create = False
    can_edit = False
    can_delete = False

    column_list = [
        WalletTransactions.wallet_id,
        WalletTransactions.transaction_type,
        WalletTransactions.direction,
        WalletTransactions.amount,
        WalletTransactions.balance_type,
        WalletTransactions.description,
        WalletTransactions.created_at,
    ]

    column_formatters = {
        WalletTransactions.wallet_id: lambda m, a: (
            str(m.wallet_id)[:8] + "..." if m.wallet_id else "—"
        ),
    }

    column_filters = [
        StaticValuesFilter(
            WalletTransactions.transaction_type,
            title="Type",
            values=[(t.value, t.value) for t in TransactionType],
        ),
        StaticValuesFilter(
            WalletTransactions.direction,
            title="Direction",
            values=[(d.value, d.value) for d in TransactionDirection],
        ),
        StaticValuesFilter(
            WalletTransactions.balance_type,
            title="Balance Type",
            values=[(b.value, b.value) for b in BalanceType],
        ),
    ]

    column_searchable_list = [WalletTransactions.description]

    column_details_list = "__all__"


class PaymentAdmin(ModelView, model=Payment):
    """Read-only admin view for external payment records.

    Financial records must not be created, edited, or deleted through
    the admin panel.
    """

    name = "Payment"
    name_plural = "Payments"
    icon = "fa-solid fa-credit-card"

    can_create = False
    can_edit = False
    can_delete = False

    column_list = [
        Payment.wallet_id,
        Payment.amount,
        Payment.status,
        Payment.provider,
        Payment.transaction_reference,
        Payment.created_at,
    ]

    column_formatters = {
        Payment.wallet_id: lambda m, a: (
            str(m.wallet_id)[:8] + "..." if m.wallet_id else "—"
        ),
    }

    column_filters = [
        AllUniqueStringValuesFilter(Payment.status, title="Status"),
        AllUniqueStringValuesFilter(Payment.provider, title="Provider"),
    ]

    column_details_list = "__all__"
