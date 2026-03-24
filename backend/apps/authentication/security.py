"""Password hashing and token utilities for authentication.

Wraps ``bcrypt`` for password operations and the standard
``secrets`` / ``hashlib`` modules for secure token generation and
one-way token hashing (used for email-verification and password-reset
tokens stored in the database).
"""

import hashlib
import secrets

import bcrypt

_ROUNDS = 12


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the given plain-text password.

    Args:
        plain: The raw password string supplied by the user.

    Returns:
        A bcrypt-hashed string safe to store in the database.

    """
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=_ROUNDS)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a stored bcrypt hash.

    Args:
        plain: The raw password string supplied by the user.
        hashed: The bcrypt hash retrieved from the database.

    Returns:
        ``True`` if the password matches the hash, ``False`` otherwise.

    """
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def generate_token() -> str:
    """Generate a cryptographically secure URL-safe random token.

    Produces 32 bytes of randomness encoded as a URL-safe base64 string
    (43 characters).  Suitable for use as email-verification or
    password-reset tokens sent to users.

    Returns:
        A 43-character URL-safe random token string.

    """
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """Return a SHA-256 hex digest of the given token.

    Used to store a one-way hash of a plain token in the database so
    that the raw token value is never persisted.  On verification the
    incoming token is hashed again and compared against the stored digest.

    Args:
        raw_token: The plain token string to hash.

    Returns:
        A 64-character lowercase hexadecimal SHA-256 digest.

    """
    return hashlib.sha256(raw_token.encode()).hexdigest()
