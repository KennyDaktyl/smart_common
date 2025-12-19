"""
Shared security utilities for Smart Energy platform.

Responsibilities:
- Password hashing and verification (users)
- JWT access / refresh / action tokens
- Encryption of technical secrets (API keys, agent secrets)
"""

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from cryptography.fernet import Fernet
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from smart_common.core.config import settings


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# Password hashing (USER PASSWORDS)
# ---------------------------------------------------------------------

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

BCRYPT_MAX_BYTES = 72


def _normalize_password(password: str) -> str:
    """
    Normalize password to bcrypt max length (72 bytes).
    """
    raw = password.encode("utf-8")
    if len(raw) > BCRYPT_MAX_BYTES:
        raw = raw[:BCRYPT_MAX_BYTES]
    return raw.decode("utf-8", errors="ignore")


def hash_password(password: str) -> str:
    """
    Hash user password using bcrypt.
    """
    return pwd_context.hash(_normalize_password(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify user password against bcrypt hash.
    """
    return pwd_context.verify(
        _normalize_password(plain_password),
        hashed_password,
    )


# ---------------------------------------------------------------------
# JWT TOKENS
# ---------------------------------------------------------------------

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    ACTION = "action"


def _create_token(
    payload: dict[str, Any],
    expires_delta: timedelta,
    token_type: TokenType,
) -> str:
    """
    Internal helper for JWT creation.
    """
    to_encode = payload.copy()
    to_encode.update(
        {
            "exp": datetime.now(timezone.utc) + expires_delta,
            "type": token_type.value,
        }
    )

    return jwt.encode(
        to_encode,
        settings.jwt_secret_str,
        algorithm=ALGORITHM,
    )


def create_access_token(
    payload: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create JWT access token.
    """
    return _create_token(
        payload,
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        TokenType.ACCESS,
    )


def create_refresh_token(payload: dict[str, Any]) -> str:
    """
    Create JWT refresh token.
    """
    return _create_token(
        payload,
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        TokenType.REFRESH,
    )


def create_action_token(
    payload: dict[str, Any],
    expires_delta: timedelta,
) -> str:
    """
    Create short-lived JWT action token
    (e.g. email confirmation, reset password).
    """
    return _create_token(
        payload,
        expires_delta,
        TokenType.ACTION,
    )


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode JWT token.

    Raises:
        ExpiredSignatureError
        JWTError
    """
    return jwt.decode(
        token,
        settings.jwt_secret_str,
        algorithms=[ALGORITHM],
    )


def decode_and_validate_token(
    token: str,
    expected_type: TokenType,
) -> dict[str, Any] | None:
    """
    Decode token and validate its type.
    Returns payload or None.
    """
    try:
        payload = decode_token(token)
    except ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None
    except JWTError as exc:
        logger.debug(f"JWT decode failed: {exc}")
        return None

    if payload.get("type") != expected_type.value:
        logger.warning(
            "Invalid token type: expected=%s got=%s",
            expected_type,
            payload.get("type"),
        )
        return None

    return payload


# ---------------------------------------------------------------------
# SECRET ENCRYPTION (TECHNICAL SECRETS)
# ---------------------------------------------------------------------

fernet = Fernet(settings.fernet_key_bytes)


def encrypt_secret(value: str) -> str:
    """
    Encrypt technical secret (API key, agent secret, provider password).
    """
    return fernet.encrypt(value.encode()).decode()


def decrypt_secret(token: str) -> str:
    """
    Decrypt previously encrypted technical secret.
    """
    return fernet.decrypt(token.encode()).decode()
