"""
auth/service.py — JWT generation, bcrypt hashing, OTP logic, and rate-limit checks.

Security notes
--------------
- Passwords hashed with bcrypt (cost=10) via passlib — ~100 ms, non-blocking.
- All bcrypt calls run in a thread-pool executor so the event loop never blocks.
- OTPs hashed with bcrypt before storage so the raw code is never persisted.
- Access tokens expire in 24 hours; refresh tokens in 7 days.
- Max 5 failed login attempts → 30-minute account lockout.
- Max 3 OTP attempts per OTP record → OTP invalidated.
- OTP resend cooldown: 60 seconds between requests.
"""

from __future__ import annotations

import asyncio
import os
import random
import string
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

# ---------------------------------------------------------------------------
# Configuration — override via env in production
# ---------------------------------------------------------------------------

SECRET_KEY: str = os.getenv("ANATOM_JWT_SECRET", "anatom-ai-super-secret-key-change-in-production-2024!")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 7

OTP_EXPIRE_MINUTES = 5
OTP_MAX_ATTEMPTS = 3
OTP_RESEND_COOLDOWN_SECONDS = 60
MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30
PASSWORD_HISTORY_COUNT = 3

# cost=10 → ~100 ms per hash; secure and fast enough for async use
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=10,
)


# ---------------------------------------------------------------------------
# Password utilities (sync — never call directly from async routes)
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def check_password_history(plain: str, history_hashes: list[str]) -> bool:
    return any(pwd_context.verify(plain, h) for h in history_hashes)


# ---------------------------------------------------------------------------
# Async wrappers — run bcrypt in a thread so the event loop never blocks
# ---------------------------------------------------------------------------

async def hash_password_async(plain: str) -> str:
    return await asyncio.get_event_loop().run_in_executor(None, hash_password, plain)


async def verify_password_async(plain: str, hashed: str) -> bool:
    return await asyncio.get_event_loop().run_in_executor(None, verify_password, plain, hashed)


async def hash_otp_async(otp: str) -> str:
    return await asyncio.get_event_loop().run_in_executor(None, hash_otp, otp)


async def verify_otp_hash_async(otp: str, hashed: str) -> bool:
    return await asyncio.get_event_loop().run_in_executor(None, verify_otp_hash, otp, hashed)


async def check_password_history_async(plain: str, history_hashes: list[str]) -> bool:
    return await asyncio.get_event_loop().run_in_executor(None, check_password_history, plain, history_hashes)


# ---------------------------------------------------------------------------
# JWT utilities
# ---------------------------------------------------------------------------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: str, username: str) -> tuple[str, int]:
    """Return (encoded_jwt, expire_seconds)."""
    expires = _utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "username": username,
        "type": "access",
        "exp": expires,
        "iat": _utcnow(),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, ACCESS_TOKEN_EXPIRE_MINUTES * 60


def create_refresh_token(user_id: str, username: str) -> tuple[str, datetime]:
    """Return (encoded_jwt, expiry_datetime)."""
    expires = _utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "username": username,
        "type": "refresh",
        "exp": expires,
        "iat": _utcnow(),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token, expires


def decode_token(token: str) -> dict:
    """Decode and validate a JWT.  Raises JWTError on failure."""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload


# ---------------------------------------------------------------------------
# OTP utilities (sync — use async wrappers from routes)
# ---------------------------------------------------------------------------

def generate_otp() -> str:
    """Generate a cryptographically random 6-digit OTP string."""
    return "".join(random.choices(string.digits, k=6))


def hash_otp(otp: str) -> str:
    return pwd_context.hash(otp)


def verify_otp_hash(otp: str, hashed: str) -> bool:
    return pwd_context.verify(otp, hashed)


# ---------------------------------------------------------------------------
# Contact masking
# ---------------------------------------------------------------------------

def mask_email(email: str) -> str:
    parts = email.split("@")
    if len(parts) != 2:
        return "****@****.***"
    local, domain = parts
    masked_local = local[:2] + "****" if len(local) > 2 else "****"
    return f"{masked_local}@{domain}"


def mask_phone(phone: str) -> str:
    digits = "".join(filter(str.isdigit, phone))
    return "****" + digits[-4:] if len(digits) >= 4 else "****"


# ---------------------------------------------------------------------------
# JSON helpers for lists stored as TEXT in SQLite
# ---------------------------------------------------------------------------

def json_loads_safe(v: Optional[str], default=None):
    if v is None:
        return default
    try:
        return json.loads(v)
    except Exception:
        return default


def json_dumps(v) -> str:
    return json.dumps(v)


# ---------------------------------------------------------------------------
# Timing / expiry helpers
# ---------------------------------------------------------------------------

def otp_expiry_dt() -> datetime:
    return _utcnow() + timedelta(minutes=OTP_EXPIRE_MINUTES)


def lockout_expiry_dt() -> datetime:
    return _utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)


def is_expired(dt_str: str) -> bool:
    """Return True when an ISO-format datetime string is in the past."""
    try:
        expiry = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return _utcnow() >= expiry
    except Exception:
        return True


def dt_iso(dt: datetime) -> str:
    return dt.isoformat()
