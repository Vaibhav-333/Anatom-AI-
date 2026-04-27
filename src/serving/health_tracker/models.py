"""Pydantic models for the Health Tracker module."""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ── Symptom Log ──────────────────────────────────────────────────────────────

class SymptomLogCreate(BaseModel):
    user_id: str
    logged_at: Optional[datetime] = None
    pain_level: Optional[int] = Field(None, ge=0, le=10)
    fever_celsius: Optional[float] = None
    fever_fahrenheit: Optional[float] = None  # converted server-side
    fatigue: Optional[Literal["low", "medium", "high"]] = None
    mood: Optional[int] = Field(None, ge=1, le=5)
    sleep_hours: Optional[float] = Field(None, ge=0, le=24)
    custom_symptoms: list[str] = []
    notes: Optional[str] = None


class SymptomLogResponse(BaseModel):
    id: str
    user_id: str
    logged_at: str
    date_key: str
    pain_level: Optional[int]
    fever_celsius: Optional[float]
    fatigue: Optional[str]
    mood: Optional[int]
    sleep_hours: Optional[float]
    custom_symptoms: list[str]
    notes: Optional[str]


class SymptomTrendPoint(BaseModel):
    date: str
    avg_pain: Optional[float]
    avg_mood: Optional[float]
    avg_sleep: Optional[float]
    avg_fever: Optional[float]
    entry_count: int


class CalendarHeatmapPoint(BaseModel):
    date: str
    intensity: float  # 0.0–1.0


# ── Medication ────────────────────────────────────────────────────────────────

class MedicationCreate(BaseModel):
    user_id: str
    name: str
    dosage: str
    frequency: Literal["once_daily", "twice_daily", "thrice_daily", "as_needed"]
    duration_days: Optional[int] = None
    start_date: str  # "YYYY-MM-DD"


class MedicationResponse(BaseModel):
    id: str
    user_id: str
    name: str
    dosage: str
    frequency: str
    duration_days: Optional[int]
    start_date: str
    end_date: Optional[str]
    active: bool


class MedLogCreate(BaseModel):
    medication_id: str
    user_id: str
    scheduled_for: str
    status: Literal["taken", "missed"]
    taken_at: Optional[str] = None


class MedLogResponse(BaseModel):
    id: str
    medication_id: str
    user_id: str
    scheduled_for: str
    taken_at: Optional[str]
    status: str
    date_key: str


class AdherenceStats(BaseModel):
    medication_id: str
    medication_name: str
    total_doses: int
    taken: int
    missed: int
    adherence_pct: float
    last_7_days: list[dict]


# ── Insights ──────────────────────────────────────────────────────────────────

class InsightAlert(BaseModel):
    type: str   # "anomaly"|"deterioration"|"improvement"|"reminder"
    severity: str  # "info"|"warning"|"critical"
    title: str
    message: str
    metric: Optional[str] = None


class InsightsResponse(BaseModel):
    trend: str  # "improving"|"stable"|"worsening"
    weekly_score: float
    alerts: list[InsightAlert]
    suggestions: list[str]
    correlation_notes: list[str]
    prediction_next_3_days: dict


# ── Weekly Score ──────────────────────────────────────────────────────────────

class WeeklyScoreResponse(BaseModel):
    id: str
    user_id: str
    week_key: str
    score: float
    symptom_avg: Optional[float]
    adherence_pct: Optional[float]
    sleep_avg: Optional[float]
    trend: str
    streak_days: int
    badges: list[str]


# ── Share ─────────────────────────────────────────────────────────────────────

class HealthTrackerShareRequest(BaseModel):
    user_id: str
    expiry_hours: int = 72


class HealthTrackerShareResponse(BaseModel):
    token: str
    share_url: str
    expires_at: str
