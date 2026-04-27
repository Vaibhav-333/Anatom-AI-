"""
auth/dependencies.py — FastAPI dependency for extracting and validating the
current authenticated user from the Authorization: Bearer <token> header.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from jose import JWTError

from src.serving.auth.service import decode_token
from src.serving.database import get_db

_bearer = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """
    Validate the JWT access token and return the payload dict:
    {"sub": user_id, "username": ..., ...}

    Raises 401 on any validation failure.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Verify user still exists and is not locked
    async with get_db() as db:
        row = await db.execute_fetchall(
            "SELECT id, username, is_locked FROM auth_users WHERE id = ?",
            (user_id,),
        )
    if not row:
        raise credentials_exception
    user = dict(row[0])
    if user["is_locked"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked. Please contact support.",
        )
    return {**payload, **user}


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> dict | None:
    """Like get_current_user but returns None instead of raising when missing."""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
