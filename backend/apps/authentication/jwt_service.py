"""JWT creation, decoding, and token-pair utilities.

Wraps ``python-jose`` to issue and validate signed JWTs for the
auction platform's authentication flow.  All tokens are signed with
the application's ``secret_key`` using the configured algorithm.

Token types
-----------
- access  : short-lived bearer token used to authenticate API requests.
- refresh : longer-lived token carrying a unique ``jti`` claim, used to
  obtain a new access token without re-authenticating.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import ExpiredSignatureError, JWTError, jwt

from common.exceptions import TokenExpiredException, TokenInvalidException
from config.settings import settings


def create_access_token(data: dict) -> str:
    """Encode a short-lived access JWT from the given payload data.

    Adds ``exp`` (expiry) and ``type="access"`` claims to a copy of
    ``data`` before encoding.

    Args:
        data: Base claims to include in the token, typically containing
            ``sub``, ``email``, and ``role``.

    Returns:
        A signed JWT string valid for ``access_token_expire_minutes``.

    """
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    to_encode["type"] = "access"
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def create_refresh_token(data: dict) -> str:
    """Encode a longer-lived refresh JWT from the given payload data.

    Adds ``exp``, ``type="refresh"``, and a unique ``jti`` claim to a
    copy of ``data``.  The ``jti`` allows individual refresh tokens to
    be revoked without invalidating all tokens for the user.

    Args:
        data: Base claims to include in the token, typically containing
            ``sub``, ``email``, and ``role``.

    Returns:
        A signed JWT string valid for ``refresh_token_expire_days``.

    """
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    to_encode["type"] = "refresh"
    to_encode["jti"] = str(uuid4())
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT, returning its payload claims.

    Args:
        token: The raw JWT string to decode.

    Returns:
        A dictionary of the token's decoded claims.

    Raises:
        TokenExpiredException: If the token's ``exp`` claim is in the past.
        TokenInvalidException: If the token cannot be decoded or its
            signature is invalid.

    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
    except ExpiredSignatureError:
        raise TokenExpiredException()
    except JWTError:
        raise TokenInvalidException()

    return payload


def create_token_pair(user_id: str, email: str, role: str) -> dict:
    """Create an access and refresh token pair for a user.

    Builds the shared base claims from the provided identity fields and
    delegates to ``create_access_token`` and ``create_refresh_token``.

    Args:
        user_id: The user's UUID as a string, stored in the ``sub`` claim.
        email: The user's email address, stored in the ``email`` claim.
        role: The user's role string, stored in the ``role`` claim.

    Returns:
        A dictionary with keys ``access_token``, ``refresh_token``, and
        ``token_type`` (always ``"bearer"``).

    """
    data = {"sub": str(user_id), "email": email, "role": role}
    return {
        "access_token": create_access_token(data),
        "refresh_token": create_refresh_token(data),
        "token_type": "bearer",
    }
