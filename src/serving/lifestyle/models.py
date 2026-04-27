"""Pydantic models for the Lifestyle Planner module."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel


class NutritionInfo(BaseModel):
    calories: int
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float


class MealEntry(BaseModel):
    name: str
    description: str
    nutrition: NutritionInfo
    prep_time_min: int


class ExerciseEntry(BaseModel):
    name: str
    duration_min: int
    intensity: Literal["light", "moderate", "heavy"]
    instructions: str


class LifestylePlanRequest(BaseModel):
    user_id: str
    goal: Literal["recovery", "fitness", "chronic_management"]
    dietary_pref: str = "vegetarian"
    restrictions: list[str] = []
    activity_level: Literal["sedentary", "light", "moderate", "heavy"]
    plan_date: Optional[str] = None  # "YYYY-MM-DD", defaults to today
    # Injected internally from insights — not required from client
    symptom_trend: Optional[str] = None
    avg_pain: Optional[float] = None


class LifestylePlanResponse(BaseModel):
    id: str
    user_id: str
    goal: str
    dietary_pref: str
    activity_level: str
    plan_date: str
    meals: dict[str, list[MealEntry]]  # breakfast/lunch/dinner/snacks
    daily_nutrition: NutritionInfo
    exercises: list[ExerciseEntry]
    avoid_list: list[str]
    preventive_care: list[str]
    ai_notes: Optional[str]
    auto_adjusted: bool


class LifestylePlanSummary(BaseModel):
    id: str
    plan_date: str
    goal: str
    activity_level: str
    auto_adjusted: bool


class LifestyleShareRequest(BaseModel):
    user_id: str
    expiry_hours: int = 72


class LifestyleShareResponse(BaseModel):
    token: str
    share_url: str
    expires_at: str
