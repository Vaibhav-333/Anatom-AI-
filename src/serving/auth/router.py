"""
auth/router.py — All authentication and user-management endpoints.

Endpoints
---------
POST /auth/signup              Create a new account (username + password)
GET  /auth/check-username      Check username availability
POST /auth/send-otp            Send/resend OTP to email or phone
POST /auth/verify-otp          Verify OTP and mark contact as confirmed
POST /auth/login               Authenticate and receive JWT pair
POST /auth/refresh             Exchange refresh token for a new access token
POST /auth/logout              Revoke refresh token
POST /auth/forgot-password     Lookup user and send reset OTP
POST /auth/reset-password      Reset password using a valid OTP
GET  /user/me                  Return current authenticated user
POST /user/health-profile      Create / update health profile
GET  /user/health-profile      Retrieve health profile
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from jose import JWTError

from src.serving.auth.dependencies import get_current_user
from src.serving.auth.models import (
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    HealthProfileRequest,
    HealthProfileResponse,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    SendOtpRequest,
    SendOtpResponse,
    SignupRequest,
    SignupResponse,
    TokenResponse,
    UsernameCheckResponse,
    UserResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from src.serving.auth.service import (
    OTP_MAX_ATTEMPTS,
    OTP_RESEND_COOLDOWN_SECONDS,
    MAX_FAILED_LOGIN_ATTEMPTS,
    check_password_history_async,
    create_access_token,
    create_refresh_token,
    decode_token,
    dt_iso,
    generate_otp,
    hash_otp_async,
    hash_password_async,
    is_expired,
    json_dumps,
    json_loads_safe,
    lockout_expiry_dt,
    mask_email,
    mask_phone,
    otp_expiry_dt,
    verify_otp_hash_async,
    verify_password_async,
    PASSWORD_HISTORY_COUNT,
)
from src.serving.database import get_db

router = APIRouter(prefix="", tags=["Auth"])

_UTC = timezone.utc


def _now_iso() -> str:
    return datetime.now(_UTC).isoformat()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _fetch_user_by_id(db: aiosqlite.Connection, user_id: str) -> Optional[dict]:
    rows = await db.execute_fetchall(
        "SELECT * FROM auth_users WHERE id = ?", (user_id,)
    )
    return dict(rows[0]) if rows else None


async def _fetch_user_by_username(db: aiosqlite.Connection, username: str) -> Optional[dict]:
    rows = await db.execute_fetchall(
        "SELECT * FROM auth_users WHERE username = ?", (username,)
    )
    return dict(rows[0]) if rows else None


async def _fetch_user_by_identifier(db: aiosqlite.Connection, identifier: str) -> Optional[dict]:
    """Look up user by username, email, or phone."""
    rows = await db.execute_fetchall(
        "SELECT * FROM auth_users WHERE username = ? OR email = ? OR phone = ?",
        (identifier, identifier, identifier),
    )
    return dict(rows[0]) if rows else None


async def _get_active_otp(
    db: aiosqlite.Connection, user_id: str, purpose: str
) -> Optional[dict]:
    rows = await db.execute_fetchall(
        """SELECT * FROM auth_otps
           WHERE user_id = ? AND purpose = ? AND used = 0
           ORDER BY created_at DESC LIMIT 1""",
        (user_id, purpose),
    )
    return dict(rows[0]) if rows else None


def _build_token_response(
    user_id: str, username: str, health_profile_done: bool,
    remember_me: bool = False
) -> tuple[TokenResponse, str, datetime]:
    access_token, expires_in = create_access_token(user_id, username)
    refresh_token, refresh_expiry = create_refresh_token(user_id, username)
    return (
        TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user_id,
            username=username,
            health_profile_done=health_profile_done,
            expires_in=expires_in,
        ),
        refresh_token,
        refresh_expiry,
    )


# ---------------------------------------------------------------------------
# POST /auth/signup
# ---------------------------------------------------------------------------

@router.post("/auth/signup", response_model=SignupResponse, status_code=201)
async def signup(body: SignupRequest):
    async with get_db() as db:
        existing = await _fetch_user_by_username(db, body.username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username is already taken.",
            )

        user_id = str(uuid.uuid4())
        pw_hash = await hash_password_async(body.password)
        now = _now_iso()

        await db.execute(
            """INSERT INTO auth_users
               (id, username, password_hash, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, body.username, pw_hash, now, now),
        )
        # Seed password history
        await db.execute(
            "INSERT INTO auth_password_history (id, user_id, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), user_id, pw_hash, now),
        )
        await db.commit()

    return SignupResponse(
        user_id=user_id,
        username=body.username,
        message="Account created. Please verify your contact information.",
    )


# ---------------------------------------------------------------------------
# GET /auth/check-username
# ---------------------------------------------------------------------------

@router.get("/auth/check-username", response_model=UsernameCheckResponse)
async def check_username(username: str = Query(..., min_length=3, max_length=32)):
    username = username.strip().lower()
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT id FROM auth_users WHERE username = ?", (username,)
        )
    return UsernameCheckResponse(username=username, available=len(rows) == 0)


# ---------------------------------------------------------------------------
# POST /auth/send-otp
# ---------------------------------------------------------------------------

@router.post("/auth/send-otp", response_model=SendOtpResponse)
async def send_otp(body: SendOtpRequest):
    async with get_db() as db:
        user = await _fetch_user_by_id(db, body.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        # Validate contact value uniqueness (for signup)
        if body.purpose == "signup":
            if body.contact_type == "email":
                rows = await db.execute_fetchall(
                    "SELECT id FROM auth_users WHERE email = ? AND id != ?",
                    (body.contact_value, body.user_id),
                )
                if rows:
                    raise HTTPException(status_code=409, detail="Email is already registered.")
            elif body.contact_type == "phone":
                rows = await db.execute_fetchall(
                    "SELECT id FROM auth_users WHERE phone = ? AND id != ?",
                    (body.contact_value, body.user_id),
                )
                if rows:
                    raise HTTPException(status_code=409, detail="Phone number is already registered.")

        # Resend cooldown — check most recent OTP for this purpose
        existing_otp = await _get_active_otp(db, body.user_id, body.purpose)
        if existing_otp:
            created_at_str = existing_otp["created_at"]
            try:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=_UTC)
                elapsed = (datetime.now(_UTC) - created_at).total_seconds()
                if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
                    wait = int(OTP_RESEND_COOLDOWN_SECONDS - elapsed)
                    raise HTTPException(
                        status_code=429,
                        detail=f"Please wait {wait} seconds before resending OTP.",
                    )
            except HTTPException:
                raise
            except Exception:
                pass
            # Invalidate old OTP
            await db.execute(
                "UPDATE auth_otps SET used = 1 WHERE id = ?", (existing_otp["id"],)
            )

        raw_otp = generate_otp()
        otp_hash = await hash_otp_async(raw_otp)
        otp_id = str(uuid.uuid4())
        expires_at = dt_iso(otp_expiry_dt())
        now = _now_iso()

        await db.execute(
            """INSERT INTO auth_otps
               (id, user_id, otp_hash, purpose, contact_type, contact_val, expires_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (otp_id, body.user_id, otp_hash, body.purpose,
             body.contact_type, body.contact_value, expires_at, now),
        )
        await db.commit()

    # Mask contact for display
    if body.contact_type == "email":
        masked = mask_email(body.contact_value)
    else:
        masked = mask_phone(body.contact_value)

    # In production: send email/SMS here via SendGrid / Twilio
    print(f"[DEV OTP] {body.purpose.upper()} OTP for {body.user_id}: {raw_otp}")  # noqa: T201

    return SendOtpResponse(
        message=f"OTP sent to {masked}. Valid for 5 minutes.",
        masked_contact=masked,
        dev_otp=raw_otp,  # Remove in production
    )


# ---------------------------------------------------------------------------
# POST /auth/verify-otp
# ---------------------------------------------------------------------------

@router.post("/auth/verify-otp", response_model=VerifyOtpResponse)
async def verify_otp(body: VerifyOtpRequest):
    async with get_db() as db:
        otp_record = await _get_active_otp(db, body.user_id, body.purpose)

        if not otp_record:
            raise HTTPException(status_code=400, detail="No active OTP found. Please request a new one.")

        if is_expired(otp_record["expires_at"]):
            await db.execute("UPDATE auth_otps SET used = 1 WHERE id = ?", (otp_record["id"],))
            await db.commit()
            raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

        attempts = otp_record["attempts"] + 1

        if attempts > OTP_MAX_ATTEMPTS:
            await db.execute("UPDATE auth_otps SET used = 1 WHERE id = ?", (otp_record["id"],))
            await db.commit()
            raise HTTPException(status_code=429, detail="Too many incorrect attempts. OTP invalidated.")

        if not await verify_otp_hash_async(body.otp, otp_record["otp_hash"]):
            await db.execute(
                "UPDATE auth_otps SET attempts = ? WHERE id = ?",
                (attempts, otp_record["id"]),
            )
            await db.commit()
            remaining = OTP_MAX_ATTEMPTS - attempts
            raise HTTPException(
                status_code=400,
                detail=f"Incorrect OTP. {remaining} attempt(s) remaining.",
            )

        # OTP valid — mark as used and update user contact
        await db.execute("UPDATE auth_otps SET used = 1 WHERE id = ?", (otp_record["id"],))
        now = _now_iso()
        contact_val = otp_record["contact_val"]

        if body.purpose == "signup":
            if body.contact_type == "email":
                await db.execute(
                    "UPDATE auth_users SET email = ?, email_verified = 1, updated_at = ? WHERE id = ?",
                    (contact_val, now, body.user_id),
                )
            else:
                await db.execute(
                    "UPDATE auth_users SET phone = ?, phone_verified = 1, updated_at = ? WHERE id = ?",
                    (contact_val, now, body.user_id),
                )

        await db.commit()

    return VerifyOtpResponse(verified=True, message="Contact verified successfully.")


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

@router.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request):
    async with get_db() as db:
        user = await _fetch_user_by_username(db, body.username)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password.")

        # Check account lock
        if user["is_locked"]:
            locked_until = user.get("locked_until")
            if locked_until and not is_expired(locked_until):
                raise HTTPException(
                    status_code=403,
                    detail="Account locked due to too many failed attempts. Try again later.",
                )
            # Lock expired — reset
            await db.execute(
                "UPDATE auth_users SET is_locked = 0, failed_attempts = 0, locked_until = NULL WHERE id = ?",
                (user["id"],),
            )

        if not await verify_password_async(body.password, user["password_hash"]):
            new_fails = user["failed_attempts"] + 1
            now = _now_iso()
            if new_fails >= MAX_FAILED_LOGIN_ATTEMPTS:
                locked_until = dt_iso(lockout_expiry_dt())
                await db.execute(
                    """UPDATE auth_users
                       SET failed_attempts = ?, is_locked = 1, locked_until = ?, updated_at = ?
                       WHERE id = ?""",
                    (new_fails, locked_until, now, user["id"]),
                )
                await db.commit()
                raise HTTPException(
                    status_code=403,
                    detail=f"Account locked for {30} minutes after {MAX_FAILED_LOGIN_ATTEMPTS} failed attempts.",
                )
            await db.execute(
                "UPDATE auth_users SET failed_attempts = ?, updated_at = ? WHERE id = ?",
                (new_fails, now, user["id"]),
            )
            await db.commit()
            raise HTTPException(status_code=401, detail="Invalid username or password.")

        # Success — reset fail counter, record login
        now = _now_iso()
        await db.execute(
            """UPDATE auth_users
               SET failed_attempts = 0, is_locked = 0, locked_until = NULL, last_login = ?, updated_at = ?
               WHERE id = ?""",
            (now, now, user["id"]),
        )

        token_resp, refresh_tok, refresh_expiry = _build_token_response(
            user["id"], user["username"], bool(user["health_profile_done"])
        )

        device_info = body.device_info or request.headers.get("user-agent", "")
        ip_address = request.client.host if request.client else None

        await db.execute(
            """INSERT INTO auth_sessions
               (id, user_id, refresh_token, device_info, ip_address, expires_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), user["id"], refresh_tok,
             device_info, ip_address, dt_iso(refresh_expiry), now),
        )
        await db.commit()

    return token_resp


# ---------------------------------------------------------------------------
# POST /auth/refresh
# ---------------------------------------------------------------------------

@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest):
    credentials_exc = HTTPException(status_code=401, detail="Invalid or expired refresh token.")
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise credentials_exc
        user_id = payload.get("sub")
        if not user_id:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM auth_sessions WHERE refresh_token = ? AND is_revoked = 0",
            (body.refresh_token,),
        )
        if not rows or is_expired(dict(rows[0])["expires_at"]):
            raise credentials_exc

        user = await _fetch_user_by_id(db, user_id)
        if not user:
            raise credentials_exc

        # Rotate refresh token
        now = _now_iso()
        new_access, expires_in = create_access_token(user["id"], user["username"])
        new_refresh, new_refresh_expiry = create_refresh_token(user["id"], user["username"])

        await db.execute(
            "UPDATE auth_sessions SET is_revoked = 1 WHERE refresh_token = ?",
            (body.refresh_token,),
        )
        await db.execute(
            """INSERT INTO auth_sessions
               (id, user_id, refresh_token, expires_at, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), user["id"], new_refresh, dt_iso(new_refresh_expiry), now),
        )
        await db.commit()

    return TokenResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        user_id=user["id"],
        username=user["username"],
        health_profile_done=bool(user["health_profile_done"]),
        expires_in=expires_in,
    )


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------

@router.post("/auth/logout", status_code=204)
async def logout(body: RefreshRequest):
    async with get_db() as db:
        await db.execute(
            "UPDATE auth_sessions SET is_revoked = 1 WHERE refresh_token = ?",
            (body.refresh_token,),
        )
        await db.commit()


# ---------------------------------------------------------------------------
# POST /auth/forgot-password
# ---------------------------------------------------------------------------

@router.post("/auth/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(body: ForgotPasswordRequest):
    async with get_db() as db:
        user = await _fetch_user_by_identifier(db, body.identifier)

    # Always return 200 to prevent user enumeration
    if not user:
        return ForgotPasswordResponse(
            user_id="",
            message="If that account exists, a reset code has been sent.",
            masked_contact="****",
            contact_type="email",
        )

    # Determine which contact to send OTP to
    contact_type = "email" if user.get("email_verified") else "phone"
    contact_val = user.get("email") if user.get("email_verified") else user.get("phone")

    if not contact_val:
        raise HTTPException(
            status_code=400,
            detail="No verified contact method found. Please contact support.",
        )

    async with get_db() as db:
        # Invalidate old reset OTPs
        await db.execute(
            "UPDATE auth_otps SET used = 1 WHERE user_id = ? AND purpose = 'reset_password'",
            (user["id"],),
        )
        raw_otp = generate_otp()
        otp_id = str(uuid.uuid4())
        now = _now_iso()
        reset_otp_hash = await hash_otp_async(raw_otp)

        await db.execute(
            """INSERT INTO auth_otps
               (id, user_id, otp_hash, purpose, contact_type, contact_val, expires_at, created_at)
               VALUES (?, ?, ?, 'reset_password', ?, ?, ?, ?)""",
            (otp_id, user["id"], reset_otp_hash,
             contact_type, contact_val, dt_iso(otp_expiry_dt()), now),
        )
        await db.commit()

    masked = mask_email(contact_val) if contact_type == "email" else mask_phone(contact_val)
    print(f"[DEV OTP] PASSWORD RESET OTP for {user['username']}: {raw_otp}")  # noqa: T201

    return ForgotPasswordResponse(
        user_id=user["id"],
        message=f"Reset code sent to {masked}.",
        masked_contact=masked,
        contact_type=contact_type,
        dev_otp=raw_otp,
    )


# ---------------------------------------------------------------------------
# POST /auth/reset-password
# ---------------------------------------------------------------------------

@router.post("/auth/reset-password", status_code=200)
async def reset_password(body: ResetPasswordRequest):
    async with get_db() as db:
        otp_record = await _get_active_otp(db, body.user_id, "reset_password")
        if not otp_record:
            raise HTTPException(status_code=400, detail="No active reset OTP. Please request a new one.")

        if is_expired(otp_record["expires_at"]):
            await db.execute("UPDATE auth_otps SET used = 1 WHERE id = ?", (otp_record["id"],))
            await db.commit()
            raise HTTPException(status_code=400, detail="OTP has expired.")

        attempts = otp_record["attempts"] + 1
        if attempts > OTP_MAX_ATTEMPTS:
            await db.execute("UPDATE auth_otps SET used = 1 WHERE id = ?", (otp_record["id"],))
            await db.commit()
            raise HTTPException(status_code=429, detail="Too many attempts. Request a new OTP.")

        if not await verify_otp_hash_async(body.otp, otp_record["otp_hash"]):
            await db.execute(
                "UPDATE auth_otps SET attempts = ? WHERE id = ?",
                (attempts, otp_record["id"]),
            )
            await db.commit()
            raise HTTPException(status_code=400, detail="Incorrect OTP.")

        # Check password history
        hist_rows = await db.execute_fetchall(
            """SELECT password_hash FROM auth_password_history
               WHERE user_id = ? ORDER BY created_at DESC LIMIT ?""",
            (body.user_id, PASSWORD_HISTORY_COUNT),
        )
        history_hashes = [r[0] for r in hist_rows]
        if await check_password_history_async(body.new_password, history_hashes):
            raise HTTPException(
                status_code=400,
                detail=f"You cannot reuse any of your last {PASSWORD_HISTORY_COUNT} passwords.",
            )

        new_hash = await hash_password_async(body.new_password)
        now = _now_iso()

        # Mark OTP used, update password, revoke all sessions
        await db.execute("UPDATE auth_otps SET used = 1 WHERE id = ?", (otp_record["id"],))
        await db.execute(
            "UPDATE auth_users SET password_hash = ?, updated_at = ? WHERE id = ?",
            (new_hash, now, body.user_id),
        )
        await db.execute(
            "UPDATE auth_sessions SET is_revoked = 1 WHERE user_id = ?",
            (body.user_id,),
        )
        await db.execute(
            "INSERT INTO auth_password_history (id, user_id, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), body.user_id, new_hash, now),
        )
        await db.commit()

    return {"message": "Password reset successfully. Please log in."}


# ---------------------------------------------------------------------------
# GET /user/me
# ---------------------------------------------------------------------------

@router.get("/user/me", response_model=UserResponse)
async def get_me(current: dict = Depends(get_current_user)):
    async with get_db() as db:
        user = await _fetch_user_by_id(db, current["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user.get("email"),
        phone=user.get("phone"),
        email_verified=bool(user["email_verified"]),
        phone_verified=bool(user["phone_verified"]),
        health_profile_done=bool(user["health_profile_done"]),
        last_login=user.get("last_login"),
        created_at=user["created_at"],
    )


# ---------------------------------------------------------------------------
# POST /user/health-profile  (create or update)
# ---------------------------------------------------------------------------

@router.post("/user/health-profile", response_model=HealthProfileResponse, status_code=201)
async def save_health_profile(
    body: HealthProfileRequest,
    current: dict = Depends(get_current_user),
):
    user_id = current["sub"]
    now = _now_iso()

    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT id FROM auth_health_profiles WHERE user_id = ?", (user_id,)
        )
        profile_id = dict(existing[0])["id"] if existing else str(uuid.uuid4())

        if existing:
            await db.execute(
                """UPDATE auth_health_profiles SET
                   age=?, gender=?, height_cm=?, weight_kg=?, blood_group=?,
                   conditions=?, allergies=?, smoking=?, alcohol=?,
                   activity_level=?, family_history=?, updated_at=?
                   WHERE user_id=?""",
                (
                    body.age, body.gender, body.height_cm, body.weight_kg,
                    body.blood_group, json_dumps(body.conditions),
                    json_dumps(body.allergies), int(body.smoking),
                    body.alcohol, body.activity_level,
                    json_dumps(body.family_history), now, user_id,
                ),
            )
        else:
            await db.execute(
                """INSERT INTO auth_health_profiles
                   (id, user_id, age, gender, height_cm, weight_kg, blood_group,
                    conditions, allergies, smoking, alcohol, activity_level,
                    family_history, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    profile_id, user_id, body.age, body.gender,
                    body.height_cm, body.weight_kg, body.blood_group,
                    json_dumps(body.conditions), json_dumps(body.allergies),
                    int(body.smoking), body.alcohol, body.activity_level,
                    json_dumps(body.family_history), now, now,
                ),
            )

        await db.execute(
            "UPDATE auth_users SET health_profile_done = 1, updated_at = ? WHERE id = ?",
            (now, user_id),
        )
        await db.commit()

    return HealthProfileResponse(
        id=profile_id,
        user_id=user_id,
        age=body.age,
        gender=body.gender,
        height_cm=body.height_cm,
        weight_kg=body.weight_kg,
        blood_group=body.blood_group,
        conditions=body.conditions,
        allergies=body.allergies,
        smoking=body.smoking,
        alcohol=body.alcohol,
        activity_level=body.activity_level,
        family_history=body.family_history,
        created_at=now,
        updated_at=now,
    )


# ---------------------------------------------------------------------------
# GET /user/health-profile
# ---------------------------------------------------------------------------

@router.get("/user/health-profile", response_model=HealthProfileResponse)
async def get_health_profile(current: dict = Depends(get_current_user)):
    user_id = current["sub"]
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM auth_health_profiles WHERE user_id = ?", (user_id,)
        )
    if not rows:
        raise HTTPException(status_code=404, detail="Health profile not found.")
    p = dict(rows[0])
    return HealthProfileResponse(
        id=p["id"],
        user_id=p["user_id"],
        age=p.get("age"),
        gender=p.get("gender"),
        height_cm=p.get("height_cm"),
        weight_kg=p.get("weight_kg"),
        blood_group=p.get("blood_group"),
        conditions=json_loads_safe(p.get("conditions"), []),
        allergies=json_loads_safe(p.get("allergies"), []),
        smoking=bool(p.get("smoking", 0)),
        alcohol=p.get("alcohol", "none"),
        activity_level=p.get("activity_level", "moderate"),
        family_history=json_loads_safe(p.get("family_history"), []),
        created_at=p["created_at"],
        updated_at=p["updated_at"],
    )
