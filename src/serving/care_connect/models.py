"""Pydantic schemas for CareConnect AI endpoints."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------

class GenerateReportRequest(BaseModel):
    user_id: str
    symptoms: list[str] = Field(..., min_length=1)
    age: Optional[int] = Field(None, ge=1, le=120)
    gender: Optional[str] = None
    medical_history: list[str] = Field(default_factory=list)
    severity: str = Field("moderate", pattern="^(mild|moderate|severe)$")
    duration_days: int = Field(1, ge=1, le=3650)


class ProbableCondition(BaseModel):
    name: str
    confidence_pct: int
    description: str


class CareReport(BaseModel):
    id: str
    user_id: str
    created_at: str
    symptoms: list[str]
    user_age: Optional[int]
    user_gender: Optional[str]
    medical_history: list[str]
    severity: str
    duration_days: int
    probable_conditions: list[ProbableCondition]
    affected_organs: list[str]
    risk_level: str
    red_flags: list[str]
    next_steps: list[str]
    treatment_suggestions: list[str]
    recommended_specialization: str
    pdf_path: Optional[str] = None


class CareReportSummary(BaseModel):
    id: str
    created_at: str
    symptoms: list[str]
    risk_level: str
    recommended_specialization: str
    probable_conditions: list[ProbableCondition]


# ---------------------------------------------------------------------------
# Doctor
# ---------------------------------------------------------------------------

class Doctor(BaseModel):
    id: str
    name: str
    specialization: str
    subspecialties: list[str]
    experience_years: int
    rating: float
    review_count: int
    consultation_fee: int
    mode: str
    hospital: str
    city: str
    latitude: float
    longitude: float
    availability: dict
    verified: bool
    profile_image: Optional[str]
    degrees: list[str]
    languages: list[str]
    about: str
    relevance_score: Optional[float] = None


class DoctorRecommendRequest(BaseModel):
    conditions: list[str] = Field(default_factory=list)
    specialization: Optional[str] = None
    city: Optional[str] = None
    max_fee: Optional[int] = None
    mode: Optional[str] = None


# ---------------------------------------------------------------------------
# Sharing
# ---------------------------------------------------------------------------

class ShareReportRequest(BaseModel):
    expiry_hours: int = Field(48, ge=1, le=720)


class ShareReportResponse(BaseModel):
    token: str
    share_url: str
    expires_at: str
    view_count: int = 0


class PublicReportResponse(BaseModel):
    report_id: str
    created_at: str
    symptoms: list[str]
    probable_conditions: list[ProbableCondition]
    risk_level: str
    red_flags: list[str]
    next_steps: list[str]
    recommended_specialization: str
    expires_at: str
    view_count: int


# ---------------------------------------------------------------------------
# Saved Doctors
# ---------------------------------------------------------------------------

class SaveDoctorRequest(BaseModel):
    user_id: str
    doctor_id: str


# ---------------------------------------------------------------------------
# Generate Report Response
# ---------------------------------------------------------------------------

class GenerateReportResponse(BaseModel):
    report_id: str
    report: CareReport
    recommended_doctors: list[Doctor]
