"""
health_guidance.py — Gemini-powered structured health guidance generator.

Given a report's summary, findings, affected regions, and risk level this module
calls Gemini to produce a structured JSON guidance object covering immediate
actions, weekly/monthly plans, nutrition, exercise, and red-flag warning signs.

Usage
-----
    from src.serving.health_guidance import generate_guidance

    guidance_dict = await generate_guidance(
        summary="High cholesterol detected...",
        findings=[{"text": "LDL elevated", "severity": "borderline"}],
        affected_regions=["heart"],
        risk_level="moderate",
    )
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import google.generativeai as genai
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_GUIDANCE_PROMPT = """
You are a certified health coach and nutritionist helping a patient act on their medical report.
Based on the report context below, produce structured, practical, evidence-based health guidance.

Return ONLY a valid JSON object with exactly these fields:
{
  "immediate_actions": ["Action within the next 24 hours"],
  "weekly_plan": ["Activity or habit for this week"],
  "monthly_plan": ["Longer-term goal for this month"],
  "diet_recommendations": [
    {
      "nutrient": "Sodium",
      "direction": "down",
      "detail": "Reduce processed food intake to lower blood pressure"
    }
  ],
  "exercise_guidance": {
    "recommended": [
      { "name": "Brisk walking", "duration": "30 min", "frequency": "5x/week" }
    ],
    "avoid": ["High-impact running if joints are affected"],
    "frequency": "5 days per week"
  },
  "warning_signs": ["Chest pain", "Severe shortness of breath"],
  "red_flags": [
    {
      "sign": "Sudden chest pain radiating to arm",
      "severity": "er",
      "action": "Call emergency services immediately"
    }
  ],
  "supplements": ["Vitamin D 1000 IU daily (discuss with doctor)"],
  "consequence_timeline": "Without addressing elevated cholesterol, arterial plaque may build up over 6-12 months. Over 5 years this significantly raises heart attack and stroke risk.",
  "disclaimer": "This is AI-generated wellness guidance. Always consult a qualified healthcare professional."
}

Rules:
- direction must be one of: "up", "down", "neutral"
- red_flags.severity must be one of: "er" (emergency room), "urgent" (same day), "monitor" (watch over time)
- immediate_actions: 2-4 concrete steps
- weekly_plan: 3-5 items
- monthly_plan: 2-4 items
- diet_recommendations: 3-6 items
- exercise_guidance.recommended: 2-4 exercises
- warning_signs: 3-6 signs
- red_flags: 1-4 items (only include genuinely serious signs)
- supplements: 1-4 items or empty list
- consequence_timeline: 2-3 sentences describing what happens if this guidance is ignored
- Return ONLY the JSON object, no markdown fences, no extra text

Report context:
"""

# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------

def _fallback_guidance() -> dict:
    return {
        "immediate_actions": [
            "Schedule a follow-up appointment with your doctor",
            "Keep a symptom diary for the next 7 days",
        ],
        "weekly_plan": [
            "Take a 20-minute walk each day",
            "Reduce processed food consumption",
            "Stay hydrated with 8 glasses of water daily",
        ],
        "monthly_plan": [
            "Establish a regular sleep schedule",
            "Review medications with your healthcare provider",
        ],
        "diet_recommendations": [
            {"nutrient": "Vegetables", "direction": "up", "detail": "Aim for 5 portions per day"},
            {"nutrient": "Sugar", "direction": "down", "detail": "Limit added sugar to <25g/day"},
            {"nutrient": "Water", "direction": "up", "detail": "Drink at least 2L per day"},
        ],
        "exercise_guidance": {
            "recommended": [
                {"name": "Walking", "duration": "20-30 min", "frequency": "Daily"},
                {"name": "Stretching", "duration": "10 min", "frequency": "Morning and evening"},
            ],
            "avoid": [],
            "frequency": "Daily",
        },
        "warning_signs": [
            "Severe or worsening chest pain",
            "Sudden difficulty breathing",
            "Unusual swelling in legs or feet",
        ],
        "red_flags": [
            {
                "sign": "Sudden chest pain with shortness of breath",
                "severity": "er",
                "action": "Call emergency services immediately",
            }
        ],
        "supplements": [],
        "consequence_timeline": (
            "Without addressing these findings, symptoms may worsen over time. "
            "Please consult your healthcare provider to understand the specific risks for your situation."
        ),
        "disclaimer": (
            "This is AI-generated wellness guidance and not a substitute for professional medical advice. "
            "Always consult a qualified healthcare professional before making health decisions."
        ),
    }


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

async def generate_guidance(
    summary: str,
    findings: list[dict[str, Any]],
    affected_regions: list[str],
    risk_level: str,
    user_profile: dict | None = None,
) -> dict:
    """
    Call Gemini to generate structured health guidance for a report.
    Returns a guidance dict; falls back gracefully on any error.
    """
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY is not configured.",
        )

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-flash-lite-latest",
        generation_config={"response_mime_type": "application/json"},
    )

    # Build optional patient profile block
    profile_text = ""
    if user_profile:
        conditions = ", ".join(user_profile.get("conditions", [])) or "none reported"
        meds = ", ".join(user_profile.get("medications", [])) or "none reported"
        bmi = user_profile.get("bmi")
        bmi_str = f"{bmi:.1f}" if bmi else "unknown"
        profile_text = (
            f"Patient Profile:\n"
            f"  Age: {user_profile.get('age', 'unknown')}, "
            f"Gender: {user_profile.get('gender', 'unknown')}, "
            f"BMI: {bmi_str}\n"
            f"  Known Conditions: {conditions}\n"
            f"  Current Medications: {meds}\n\n"
        )

    # Build context block
    findings_text = "\n".join(
        f"  - [{f.get('severity', 'normal').upper()}] {f.get('text', '')}"
        for f in findings[:10]
    )
    context = (
        profile_text
        + f"Risk Level: {risk_level}\n"
        f"Affected Regions: {', '.join(affected_regions) or 'none identified'}\n"
        f"Summary: {summary}\n"
        f"Key Findings:\n{findings_text or '  No specific findings listed.'}"
    )

    prompt = _GUIDANCE_PROMPT + context

    # Retry once on rate-limit
    for attempt in range(2):
        try:
            response = model.generate_content(prompt)
            raw = json.loads(response.text)
            return _validate_guidance(raw)
        except json.JSONDecodeError:
            return _fallback_guidance()
        except Exception as exc:
            msg = str(exc)
            if "429" in msg or "quota" in msg.lower() or "rate" in msg.lower():
                if attempt == 0:
                    time.sleep(3)
                    continue
            if "403" in msg or "401" in msg or "api_key" in msg.lower():
                raise HTTPException(
                    status_code=503,
                    detail="Gemini API key is invalid or lacks permissions.",
                )
            # On unknown error: return fallback instead of crashing
            return _fallback_guidance()

    return _fallback_guidance()


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_guidance(raw: dict) -> dict:
    """Coerce the Gemini response to the expected structure."""
    valid_directions = {"up", "down", "neutral"}
    valid_flag_sev = {"er", "urgent", "monitor"}

    diet = []
    for item in raw.get("diet_recommendations", []):
        if isinstance(item, str):
            diet.append({"nutrient": item, "direction": "neutral", "detail": item})
        elif isinstance(item, dict):
            d = item.get("direction", "neutral")
            diet.append({
                "nutrient": str(item.get("nutrient", "")),
                "direction": d if d in valid_directions else "neutral",
                "detail": str(item.get("detail", "")),
            })

    ex_raw = raw.get("exercise_guidance", {})
    if not isinstance(ex_raw, dict):
        ex_raw = {}
    recommended = []
    for ex in ex_raw.get("recommended", []):
        if isinstance(ex, str):
            recommended.append({"name": ex, "duration": "", "frequency": ""})
        elif isinstance(ex, dict):
            recommended.append({
                "name": str(ex.get("name", "")),
                "duration": str(ex.get("duration", "")),
                "frequency": str(ex.get("frequency", "")),
            })

    red_flags = []
    for rf in raw.get("red_flags", []):
        if isinstance(rf, dict):
            sev = rf.get("severity", "monitor")
            red_flags.append({
                "sign": str(rf.get("sign", "")),
                "severity": sev if sev in valid_flag_sev else "monitor",
                "action": str(rf.get("action", "")),
            })

    return {
        "immediate_actions": [str(a) for a in raw.get("immediate_actions", [])],
        "weekly_plan": [str(a) for a in raw.get("weekly_plan", [])],
        "monthly_plan": [str(a) for a in raw.get("monthly_plan", [])],
        "diet_recommendations": diet,
        "exercise_guidance": {
            "recommended": recommended,
            "avoid": [str(a) for a in ex_raw.get("avoid", [])],
            "frequency": str(ex_raw.get("frequency", "")),
        },
        "warning_signs": [str(w) for w in raw.get("warning_signs", [])],
        "red_flags": red_flags,
        "supplements": [str(s) for s in raw.get("supplements", [])],
        "consequence_timeline": str(raw.get("consequence_timeline", "")),
        "disclaimer": str(raw.get("disclaimer", _fallback_guidance()["disclaimer"])),
    }
