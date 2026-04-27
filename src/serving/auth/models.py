"""
auth/models.py — Pydantic request/response schemas for the auth system.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, field_validator, model_validator


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3 or len(v) > 32:
            raise ValueError("Username must be 3–32 characters.")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username may only contain letters, digits, hyphens, and underscores.")
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        specials = set("!@#$%^&*()_+-=[]{}|;':\",./<>?")
        if not any(c in specials for c in v):
            raise ValueError("Password must contain at least one special character.")
        return v


class SignupResponse(BaseModel):
    user_id: str
    username: str
    message: str


# ---------------------------------------------------------------------------
# OTP
# ---------------------------------------------------------------------------

class SendOtpRequest(BaseModel):
    user_id: str
    contact_type: str   # "email" | "phone"
    contact_value: str
    purpose: str        # "signup" | "reset_password"

    @field_validator("contact_type")
    @classmethod
    def contact_type_valid(cls, v: str) -> str:
        if v not in ("email", "phone"):
            raise ValueError("contact_type must be 'email' or 'phone'.")
        return v

    @field_validator("purpose")
    @classmethod
    def purpose_valid(cls, v: str) -> str:
        if v not in ("signup", "reset_password"):
            raise ValueError("purpose must be 'signup' or 'reset_password'.")
        return v


class SendOtpResponse(BaseModel):
    message: str
    masked_contact: str
    # DEV ONLY — remove in production
    dev_otp: Optional[str] = None


class VerifyOtpRequest(BaseModel):
    user_id: str
    otp: str
    purpose: str
    contact_type: str

    @field_validator("otp")
    @classmethod
    def otp_digits(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit() or len(v) != 6:
            raise ValueError("OTP must be exactly 6 digits.")
        return v


class VerifyOtpResponse(BaseModel):
    verified: bool
    message: str


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str
    remember_me: bool = False
    device_info: Optional[str] = None

    @field_validator("username")
    @classmethod
    def username_clean(cls, v: str) -> str:
        return v.strip().lower()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    health_profile_done: bool
    expires_in: int  # seconds


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------

class RefreshRequest(BaseModel):
    refresh_token: str


# ---------------------------------------------------------------------------
# Forgot / Reset password
# ---------------------------------------------------------------------------

class ForgotPasswordRequest(BaseModel):
    identifier: str  # username or email or phone

    @field_validator("identifier")
    @classmethod
    def identifier_clean(cls, v: str) -> str:
        return v.strip().lower()


class ForgotPasswordResponse(BaseModel):
    user_id: str
    message: str
    masked_contact: str
    contact_type: str
    dev_otp: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    user_id: str
    otp: str
    new_password: str

    @field_validator("otp")
    @classmethod
    def otp_digits(cls, v: str) -> str:
        v = v.strip()
        if not v.isdigit() or len(v) != 6:
            raise ValueError("OTP must be exactly 6 digits.")
        return v

    @field_validator("new_password")
    @classmethod
    def password_strong(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit.")
        specials = set("!@#$%^&*()_+-=[]{}|;':\",./<>?")
        if not any(c in specials for c in v):
            raise ValueError("Password must contain at least one special character.")
        return v


# ---------------------------------------------------------------------------
# Username check
# ---------------------------------------------------------------------------

class UsernameCheckResponse(BaseModel):
    username: str
    available: bool


# ---------------------------------------------------------------------------
# Current user
# ---------------------------------------------------------------------------

class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str]
    phone: Optional[str]
    email_verified: bool
    phone_verified: bool
    health_profile_done: bool
    last_login: Optional[str]
    created_at: str


# ---------------------------------------------------------------------------
# Health profile
# ---------------------------------------------------------------------------

class HealthProfileRequest(BaseModel):
    age: int
    gender: str
    height_cm: float
    weight_kg: float
    blood_group: str
    conditions: list[str] = []
    allergies: list[str] = []
    smoking: bool = False
    alcohol: str = "none"
    activity_level: str = "moderate"
    family_history: list[str] = []

    @field_validator("age")
    @classmethod
    def age_range(cls, v: int) -> int:
        if not (0 < v < 130):
            raise ValueError("Age must be between 1 and 129.")
        return v

    @field_validator("gender")
    @classmethod
    def gender_valid(cls, v: str) -> str:
        allowed = {"male", "female", "non_binary", "prefer_not_to_say"}
        if v.lower() not in allowed:
            raise ValueError(f"gender must be one of {allowed}.")
        return v.lower()

    @field_validator("activity_level")
    @classmethod
    def activity_valid(cls, v: str) -> str:
        allowed = {"sedentary", "light", "moderate", "active", "very_active"}
        if v.lower() not in allowed:
            raise ValueError(f"activity_level must be one of {allowed}.")
        return v.lower()

    @field_validator("alcohol")
    @classmethod
    def alcohol_valid(cls, v: str) -> str:
        allowed = {"none", "occasional", "moderate", "heavy"}
        if v.lower() not in allowed:
            raise ValueError(f"alcohol must be one of {allowed}.")
        return v.lower()


class HealthProfileResponse(BaseModel):
    id: str
    user_id: str
    age: Optional[int]
    gender: Optional[str]
    height_cm: Optional[float]
    weight_kg: Optional[float]
    blood_group: Optional[str]
    conditions: list[str]
    allergies: list[str]
    smoking: bool
    alcohol: str
    activity_level: str
    family_history: list[str]
    created_at: str
    updated_at: str
