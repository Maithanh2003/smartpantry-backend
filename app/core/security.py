from datetime import UTC, datetime, timedelta
import base64
import hashlib
import hmac
import os

from jose import JWTError, jwt

from settings import get_settings

settings = get_settings()
PBKDF2_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    salt_b64 = base64.b64encode(salt).decode("utf-8")
    digest_b64 = base64.b64encode(digest).decode("utf-8")
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt_b64}${digest_b64}"


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_str, salt_b64, expected_b64 = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_str)
        salt = base64.b64decode(salt_b64.encode("utf-8"))
        expected = base64.b64decode(expected_b64.encode("utf-8"))
    except (ValueError, TypeError):
        return False

    candidate = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)


def _build_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str) -> str:
    return _build_token(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(subject: str) -> str:
    return _build_token(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("INVALID_TOKEN") from exc
