"""One-off script to create a superuser account.

Usage:
    python scripts/create_superuser.py --first-name Admin --last-name User \
        --email admin@example.com --phone 08000000000 --password changeme123
"""

import argparse
import asyncio
import sys
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, ".")

import config.model_registry  # noqa: F401
from apps.authentication.security import hash_password
from apps.users.enums import AccountStatus, UserRole
from apps.users.kyc_models import KYCProfile
from apps.users.models import User, UserProfile
from apps.wallet.models import Wallet
from config.database import engine


async def create_superuser(
    first_name: str,
    last_name: str,
    email: str,
    phone_number: str,
    password: str,
) -> None:
    """Create an admin superuser account with all required related records.

    Creates the ``User``, ``UserProfile``, ``Wallet``, and ``KYCProfile``
    records in a single transaction. No-ops if the email already exists.

    Args:
        first_name: Admin user's given name.
        last_name: Admin user's family name.
        email: Email address — used as login identifier (must be unique).
        phone_number: Nigerian mobile number.
        password: Plain-text password; will be hashed before storing.

    """
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            print(f"User with email {email} already exists.")
            return

        user = User(
            id=uuid.uuid4(),
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            account_status=AccountStatus.ACTIVE,
            is_email_verified=True,
        )
        session.add(user)
        await session.flush()

        # Create UserProfile
        profile = UserProfile(user_id=user.id)
        session.add(profile)

        # Create Wallet — required for any financial operations
        wallet = Wallet(
            user_id=user.id,
            available_funds=Decimal("0.00"),
            locked_funds=Decimal("0.00"),
            escrow_funds=Decimal("0.00"),
            currency="NGN",
        )
        session.add(wallet)

        # Create KYCProfile — required for KYC limit checks
        kyc_profile = KYCProfile(user_id=user.id)
        session.add(kyc_profile)

        await session.commit()
        print(f"Superuser '{email}' created successfully.")
        print(f"  Role: {UserRole.ADMIN.value}")
        print("  Email verified: True")
        print("  Wallet: created")
        print("  KYC profile: created")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create an Admin")
    parser.add_argument("--first-name", required=True)
    parser.add_argument("--last-name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--phone", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    asyncio.run(
        create_superuser(
            first_name=args.first_name,
            last_name=args.last_name,
            email=args.email,
            phone_number=args.phone,
            password=args.password,
        )
    )
