"""Fixtures for user tests.

Provides test fixtures for creating test users, admin users, and
authentication headers for integration testing.
"""

import pytest_asyncio

from apps.users.enums import UserRole
from apps.users.repository import UserRepository


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create a test user with profile and wallet.

    Args:
        db_session: Database session fixture.

    Returns:
        User: A newly created test user instance.

    """
    repo = UserRepository(db_session)
    user = await repo.create(
        {
            "email": "testuser@example.com",
            "first_name": "Emmanuel",
            "last_name": "Onyekachi",
            "password_hash": "hashed_password",
            "phone_number": "+2348012345678",
            "role": UserRole.USER,
            "is_email_verified": True,
        }
    )
    await db_session.commit()
    return user


@pytest_asyncio.fixture
async def test_admin(db_session):
    """Create a test admin user.

    Args:
        db_session: Database session fixture.

    Returns:
        User: A newly created test admin user instance.

    """
    repo = UserRepository(db_session)
    admin = await repo.create(
        {
            "email": "admin@example.com",
            "first_name": "Emmanuel",
            "last_name": "Onyekachi",
            "phone_number": "+2348012345679",
            "password_hash": "hashed_password",
            "role": UserRole.ADMIN,
            "is_email_verified": True,
        }
    )
    await db_session.commit()
    return admin


@pytest_asyncio.fixture
async def auth_headers(test_user):
    """Generate auth headers for test user.

    Args:
        test_user: Test user fixture.

    Returns:
        dict: Authorization header with Bearer token.

    """
    from apps.authentication.jwt_service import create_access_token

    token = create_access_token({"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_auth_headers(test_admin):
    """Generate auth headers for admin user.

    Args:
        test_admin: Test admin user fixture.

    Returns:
        dict: Authorization header with Bearer token for admin.

    """
    from apps.authentication.jwt_service import create_access_token

    token = create_access_token({"sub": str(test_admin.id)})
    return {"Authorization": f"Bearer {token}"}
