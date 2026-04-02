"""One-off script to create a superuser account.

Usage:
    python scripts/create_superuser.py --first-name Admin --last-name User \
        --email admin@example.com --phone 08000000000 --password changeme123
"""

import argparse
import asyncio
import sys
import uuid

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, ".")

import config.model_registry  # noqa: F401
from apps.users.enums import AccountStatus, UserRole
from apps.users.models import User, UserProfile
from config.database import engine

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_superuser(
    first_name: str,
    last_name: str,
    email: str,
    phone_number: str,
    password: str,
) -> None:
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
            password_hash=pwd_context.hash(password),
            role=UserRole.SUPERUSER,
            account_status=AccountStatus.ACTIVE,
            is_email_verified=True,
        )
        session.add(user)
        await session.flush()

        profile = UserProfile(id=uuid.uuid4(), user_id=user.id)
        session.add(profile)

        await session.commit()
        print(f"Superuser '{email}' created successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a superuser")
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
