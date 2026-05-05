from sqladmin import ModelView
from sqladmin.filters import BooleanFilter, StaticValuesFilter

from apps.users.enums import AccountStatus, KYCTier, UserRole
from apps.users.models import SellerProfile, User, UserProfile


class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users"
    icon = "fa-solid fa-users"

    # Columns shown in the list view
    column_list = [
        User.id,
        User.first_name,
        User.last_name,
        User.email,
        User.phone_number,
        User.account_status,
        User.role,
        User.is_email_verified,
        User.kyc_tier,
        User.created_at,
        User.updated_at,
        User.last_login_at,
    ]

    # Truncate UUID for display)
    column_formatters = {User.id: lambda m, a: str(m.id)[:8] + "..." if m.id else None}

    # Which columns can be searched
    column_searchable_list = [
        User.email,
        User.phone_number,
        User.first_name,
        User.last_name,
    ]

    column_filters = [
        StaticValuesFilter(
            User.account_status,
            title="Account Status",
            values=[(s.value, s.value) for s in AccountStatus],
        ),
        StaticValuesFilter(
            User.role, title="Role", values=[(r.value, r.value) for r in UserRole]
        ),
        StaticValuesFilter(
            User.kyc_tier,
            title="KYC Tier",
            values=[(t.value, t.value) for t in KYCTier],
        ),
        BooleanFilter(User.is_email_verified, title="Email Verified"),
    ]

    # Which fields admin can edit
    form_columns = [
        User.account_status,
        User.role,
        User.is_email_verified,
        User.kyc_tier,
    ]

    # -------- DETAIL VIEW --------
    column_details_list = [
        User.id,
        User.first_name,
        User.last_name,
        User.email,
        User.phone_number,
        User.role,
        User.account_status,
        User.kyc_tier,
        User.is_email_verified,
        User.created_at,
        User.last_login_at,
        "available_wallet",
        "locked_wallet",
        "escrow_wallet",
    ]

    # -------- RELATIONSHIPS --------
    # These assume relationships exist on your model:
    # user.profile, user.kyc_profile, user.wallet

    column_formatters_detail = {
        "profile": lambda m, a: m.profile,
        "kyc_profile": lambda m, a: m.kyc_profile,
        "available_wallet": lambda m, a: (
            f"₦{m.wallet.available_funds:,.2f}" if m.wallet else "No wallet"
        ),
        "locked_wallet": lambda m, a: (
            f"₦{m.wallet.locked_funds:,.2f}" if m.wallet else "No wallet"
        ),
        "escrow_wallet": lambda m, a: (
            f"₦{m.wallet.escrow_funds:,.2f}" if m.wallet else "No wallet"
        ),
    }


class UserProfileAdmin(ModelView, model=UserProfile):
    name = "User Profile"
    name_plural = "User Profiles"
    icon = "fa-solid fa-id-card"

    column_list = [
        UserProfile.user_id,
        UserProfile.bio,
        UserProfile.avatar_url,
        UserProfile.city,
        UserProfile.state,
        UserProfile.onboarding_intent,
        UserProfile.rating,
        UserProfile.total_sales,
        UserProfile.total_purchases,
        UserProfile.bank_code,
        UserProfile.account_number,
        UserProfile.account_name,
        UserProfile.created_at,
        UserProfile.updated_at,
    ]

    # Show email instead of raw object
    column_formatters = {
        UserProfile.user: lambda m, a: m.user.email if m.user else "No user"
    }

    # --- Editable ---
    form_columns = [
        UserProfile.bio,
        UserProfile.city,
        UserProfile.state,
        UserProfile.bank_code,
        UserProfile.account_number,
        UserProfile.account_name,
    ]


class SellerProfileAdmin(ModelView, model=SellerProfile):
    name = "Seller Profile"
    name_plural = "Seller Profiles"
    icon = "fa-solid fa-store"

    column_list = [
        SellerProfile.user_id,
        SellerProfile.seller_type,
        SellerProfile.is_verified,
        SellerProfile.bank_acct_number,
        SellerProfile.bank_name,
        SellerProfile.verified_at,
        SellerProfile.verified_by_id,
        SellerProfile.created_at,
        SellerProfile.updated_at,
    ]

    form_columns = [SellerProfile.is_verified, SellerProfile.seller_type]
