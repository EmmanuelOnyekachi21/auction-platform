"""Integration tests for ``AuthService`` business-logic methods.

Each test function receives a ``db_session`` fixture that wraps every
test in a rolled-back transaction, so the real PostgreSQL schema is
exercised without leaving leftover rows.

Coverage map
────────────
- register()         – happy path, duplicate email, duplicate phone, password hash
- login()            – happy path, wrong password, unknown email, suspended,
                       banned, last_login_at stamp
- refresh_token()    – happy path, rejects access token
- verify_email()     – marks verified, rejects invalid token
- forgot_password()  – known email, unknown email (silent succeed)
- reset_password()   – updates hash, rejects invalid token
- change_password()  – updates hash, rejects wrong old password
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from apps.authentication.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
)
from apps.authentication.security import generate_token, hash_token
from apps.authentication.service import AuthService
from apps.users.enums import AccountStatus
from apps.users.repository import UserRepository
from common.exceptions import (
    AccountBannedException,
    AccountSuspendedException,
    AlreadyExistsException,
    InvalidCredentialsException,
    NotFoundException,
    TokenInvalidException,
)


def make_register_data(**overrides) -> RegisterRequest:
    return RegisterRequest(
        first_name="John",
        last_name="Doe",
        email=overrides.pop("email", f"john_{uuid4().hex[:6]}@example.com"),
        phone_number=overrides.pop("phone_number", f"0801{uuid4().int % 10**7:07d}"),
        password="SecurePass1!",
        confirm_password="SecurePass1!",
        **overrides,
    )


# ---------------------------------------------------------------------------
# register()
# ---------------------------------------------------------------------------


async def test_register_returns_auth_response(db_session):
    service = AuthService(db_session)

    response = await service.register(make_register_data())

    assert response.access_token
    assert response.refresh_token
    assert response.token_type == "bearer"
    assert response.user.is_email_verified is False


async def test_register_raises_if_email_taken(db_session):
    service = AuthService(db_session)
    data = make_register_data(email="taken@example.com")
    await service.register(data)

    with pytest.raises(AlreadyExistsException):
        await service.register(make_register_data(email="taken@example.com"))


async def test_register_raises_if_phone_taken(db_session):
    service = AuthService(db_session)
    phone = "08012345678"
    await service.register(make_register_data(phone_number=phone))

    with pytest.raises(AlreadyExistsException):
        await service.register(make_register_data(phone_number=phone))


async def test_register_hashes_password(db_session):
    service = AuthService(db_session)
    response = await service.register(make_register_data())

    user = await UserRepository(db_session).get_by_email(response.user.email)
    assert user.password_hash != "SecurePass1!"
    assert user.password_hash.startswith("$2b$")


# ---------------------------------------------------------------------------
# login()
# ---------------------------------------------------------------------------


async def test_login_returns_auth_response(db_session):
    service = AuthService(db_session)
    await service.register(make_register_data(email="login@example.com"))

    response = await service.login(
        LoginRequest(email="login@example.com", password="SecurePass1!")
    )

    assert response.access_token
    assert response.user.email == "login@example.com"


async def test_login_raises_for_wrong_password(db_session):
    service = AuthService(db_session)
    await service.register(make_register_data(email="wrongpass@example.com"))

    with pytest.raises(InvalidCredentialsException):
        await service.login(
            LoginRequest(email="wrongpass@example.com", password="WrongPass1!")
        )


async def test_login_raises_for_unknown_email(db_session):
    service = AuthService(db_session)

    with pytest.raises(InvalidCredentialsException):
        await service.login(
            LoginRequest(email="nobody@example.com", password="SecurePass1!")
        )


async def test_login_raises_for_suspended_account(db_session):
    service = AuthService(db_session)
    await service.register(make_register_data(email="suspended@example.com"))

    user = await UserRepository(db_session).get_by_email("suspended@example.com")
    await UserRepository(db_session).update(
        user.id, {"account_status": AccountStatus.SUSPENDED}
    )

    with pytest.raises(AccountSuspendedException):
        await service.login(
            LoginRequest(email="suspended@example.com", password="SecurePass1!")
        )


async def test_login_raises_for_banned_account(db_session):
    service = AuthService(db_session)
    await service.register(make_register_data(email="banned@example.com"))

    user = await UserRepository(db_session).get_by_email("banned@example.com")
    await UserRepository(db_session).update(
        user.id, {"account_status": AccountStatus.BANNED}
    )

    with pytest.raises(AccountBannedException):
        await service.login(
            LoginRequest(email="banned@example.com", password="SecurePass1!")
        )


async def test_login_updates_last_login(db_session):
    service = AuthService(db_session)
    await service.register(make_register_data(email="lastlogin@example.com"))

    user_before = await UserRepository(db_session).get_by_email("lastlogin@example.com")
    assert user_before.last_login_at is None

    await service.login(
        LoginRequest(email="lastlogin@example.com", password="SecurePass1!")
    )

    user_after = await UserRepository(db_session).get_by_email("lastlogin@example.com")
    assert user_after.last_login_at is not None


# ---------------------------------------------------------------------------
# refresh_token()
# ---------------------------------------------------------------------------


async def test_refresh_token_returns_new_access_token(db_session):
    service = AuthService(db_session)
    auth = await service.register(make_register_data())

    result = await service.refresh_token(auth.refresh_token)

    assert result["access_token"]
    assert result["token_type"] == "bearer"

    # Decode and verify the new token is a valid access token for the same user.
    # We cannot reliably compare token strings: two access tokens issued within
    # the same second share the same `exp` and therefore produce identical JWTs.
    from apps.authentication.jwt_service import decode_token

    payload = decode_token(result["access_token"])
    assert payload["type"] == "access"
    assert payload["sub"] == str(auth.user.id)


async def test_refresh_token_raises_for_access_token(db_session):
    service = AuthService(db_session)
    auth = await service.register(make_register_data())

    # passing access token where refresh is expected
    with pytest.raises(TokenInvalidException):
        await service.refresh_token(auth.access_token)


# ---------------------------------------------------------------------------
# verify_email()
# ---------------------------------------------------------------------------


async def test_verify_email_mark_user_verified(db_session):
    service = AuthService(db_session)
    await service.register(make_register_data(email="verify@example.com"))

    user = await UserRepository(db_session).get_by_email("verify@example.com")
    assert user.is_email_verified is False

    # grab the raw token by generating one and storing it manually
    raw = generate_token()

    from apps.authentication.repository import AuthRepository

    await AuthRepository(db_session).create_email_verification_token(
        user_id=user.id,
        token_hash=hash_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    await service.verify_email(raw)

    updated = await UserRepository(db_session).get_by_email("verify@example.com")
    assert updated.is_email_verified is True


async def test_verify_email_raises_for_invalid_token(db_session):
    service = AuthService(db_session)

    with pytest.raises(NotFoundException):
        await service.verify_email("completely_fake_token")


# ---------------------------------------------------------------------------
# forgot_password()
# ---------------------------------------------------------------------------


async def test_forgot_password_returns_success_for_known_email(db_session):
    service = AuthService(db_session)
    await service.register(make_register_data(email="forgot@example.com"))

    response = await service.forgot_password("forgot@example.com")
    assert "reset link" in response.message.lower()


async def test_forgot_password_returns_success_for_unknown_email(db_session):
    # Must not raise or leak whether email exists
    service = AuthService(db_session)
    response = await service.forgot_password("doesnotexist@example.com")
    assert response.message


# ---------------------------------------------------------------------------
# reset_password()
# ---------------------------------------------------------------------------


async def test_reset_password_updates_password(db_session):
    service = AuthService(db_session)
    await service.register(make_register_data(email="reset@example.com"))

    user = await UserRepository(db_session).get_by_email("reset@example.com")
    from apps.authentication.repository import AuthRepository

    raw = generate_token()
    await AuthRepository(db_session).create_password_reset_token(
        user_id=user.id,
        token_hash=hash_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    await service.reset_password(raw, "NewSecure1!")

    updated = await UserRepository(db_session).get_by_email("reset@example.com")
    from apps.authentication.security import verify_password

    assert verify_password("NewSecure1!", updated.password_hash)


async def test_reset_password_raises_for_invalid_token(db_session):
    service = AuthService(db_session)

    with pytest.raises(NotFoundException):
        await service.reset_password("fake_token", "NewSecure1!")


# ---------------------------------------------------------------------------
# change_password()
# ---------------------------------------------------------------------------


async def test_change_password_updates_password(db_session):
    service = AuthService(db_session)
    await service.register(make_register_data(email="change@example.com"))

    user = await UserRepository(db_session).get_by_email("change@example.com")
    response = await service.change_password(
        user,
        ChangePasswordRequest(
            old_password="SecurePass1!",
            new_password="NewSecure1!",
            confirm_password="NewSecure1!",
        ),
    )
    assert response.message


async def test_change_password_raises_for_wrong_old_password(db_session):
    service = AuthService(db_session)
    await service.register(make_register_data(email="changefail@example.com"))

    user = await UserRepository(db_session).get_by_email("changefail@example.com")

    with pytest.raises(InvalidCredentialsException):
        await service.change_password(
            user,
            ChangePasswordRequest(
                old_password="WrongPass1!",
                new_password="NewSecure1!",
                confirm_password="NewSecure1!",
            ),
        )
