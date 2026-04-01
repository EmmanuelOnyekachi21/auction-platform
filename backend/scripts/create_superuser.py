"""One-off script to create a superuser account.

Usage:
    python scripts/create_superuser.py
"""

import asyncio
import sys
import uuid

from passlib.context import CryptContext
from sqlalchemy import select

sys.path.insert(0, ".")

from sqlalchemy.ext.asyncio import AsyncSession

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
        # Check if user already exists
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
    asyncio.run(
        create_superuser(
            first_name="Admin",
            last_name="User",
            email="admin@example.com",
            phone_number="08000000000",
            password="changeme123",
        )
    )
