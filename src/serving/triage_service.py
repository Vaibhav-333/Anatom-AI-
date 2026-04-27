"""
triage_service.py — AI Triage System for Anatom-AI.

Combines report analysis, patient symptoms, and personal health profile to
determine an urgency level with actionable recommendation.

Triage levels:
    🟢 low       — Monitor; follow up at next routine appointment
    🟡 moderate  — See a doctor within a week
    🔴 high      — See a doctor within 24 hours
    🚨 emergency — Seek emergency care immediately

Logic: Rule-based fast-path first (deterministic, no LLM latency on critical
cases). LLM (Gemini) enriches the explanation and triggered_by rationale.
Falls back gracefully to rule-based result if Gemini is unavailable.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import google.generativeai as genai

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TRIAGE_LEVELS = ("low", "moderate", "high", "emergency")

# Keywords that immediately escalate to emergency
_EMERGENCY_KEYWORDS = frozenset([
    "loss of consciousness", "unconscious", "cardiac arrest", "heart attack",
    "stroke", "sepsis", "anaphylaxis", "severe chest pain", "respiratory failure",
    "pulmonary embolism", "aortic dissection", "ruptured", "hemorrhage",
    "intracranial bleed", "meningitis", "acute abdomen", "trauma",
    "severe allergic reaction", "epiglottitis", "status epilepticus",
])

# Keywords that escalate to high
_HIGH_KEYWORDS = frozenset([
    "critical", "urgent", "immediate", "high risk", "severe",
    "significantly elevated", "dangerously", "abnormal ecg",
    "troponin", "d-dimer elevated", "creatinine elevated", "potassium critical",
    "sodium critical", "glucose critical", "hemoglobin critical",
    "platelet critical", "wbc critical", "coagulation",
])

_TRIAGE_PROMPT = """\
You are a clinical triage AI. Given the patient data below, return a structured
triage assessment. Be precise and evidence-based.

REPORT ANALYSIS:
Risk Level: {risk_level}
Probable Conditions: {conditions}
Red Flags: {red_flags}
Summary: {summary}

PATIENT PROFILE:
{profile_text}

Your task:
1. Determine the triage level: "low" | "moderate" | "high" | "emergency"
2. Write a short action recommendation (1 sentence, patient-friendly)
3. Write a brief explanation (2-3 sentences) explaining WHY this level was assigned
4. List the top 2-4 factors that drove this level

Return ONLY valid JSON — no markdown, no extra text:
{{
  "level": "high",
  "recommendation": "Visit a doctor within 24 hours.",
  "explanation": "Elevated cardiac markers combined with existing hypertension indicate an increased risk of cardiovascular event. Your sedentary lifestyle and age further raise this concern.",
  "triggered_by": ["Elevated troponin levels", "Existing hypertension", "Sedentary lifestyle"]
}}

RULES:
- level must be exactly one of: low | moderate | high | emergency
- recommendation: plain language, 1 sentence, actionable
- explanation: 2-3 sentences, reference specific findings
- triggered_by: 2-4 items, specific to THIS patient's data
- If profile data is missing, rely only on report findings
"""

# ---------------------------------------------------------------------------
# Rule-based fast-path
# ---------------------------------------------------------------------------

def _rule_based_triage(
    risk_level: str,
    red_flags: list[str],
    findings_text: str,
    conditions: list[str],
) -> dict[str, Any]:
    """
    Deterministic triage — no LLM. Used as fallback and emergency fast-path.
    Returns a partial triage dict (no 'explanation' from LLM).
    """
    combined_text = (
        " ".join(red_flags + conditions + [findings_text, risk_level]).lower()
    )

    # Emergency check — highest priority
    for kw in _EMERGENCY_KEYWORDS:
        if kw in combined_text:
            return {
                "level": "emergency",
                "recommendation": "Seek emergency medical care immediately. Do not delay.",
                "explanation": (
                    f"Critical finding detected: '{kw}' is present. "
                    "This requires immediate emergency evaluation."
                ),
                "triggered_by": [f"Critical keyword detected: {kw}"],
            }

    # Red flags present + critical risk
    if red_flags and risk_level in ("high", "critical"):
        return {
            "level": "high",
            "recommendation": "See a doctor within 24 hours.",
            "explanation": (
                "Multiple red flags were identified alongside a high overall risk level. "
                "Prompt medical evaluation is strongly advised."
            ),
            "triggered_by": [f"Red flag: {rf}" for rf in red_flags[:3]],
        }

    # High-risk keywords in findings
    for kw in _HIGH_KEYWORDS:
        if kw in combined_text:
            return {
                "level": "high",
                "recommendation": "See a doctor within 24 hours.",
                "explanation": (
                    f"The finding '{kw}' indicates elevated medical urgency. "
                    "A healthcare provider should review this promptly."
                ),
                "triggered_by": [f"Elevated finding: {kw}"],
            }

    # Map backend risk_level to triage level
    risk_map = {
        "critical": "emergency",
        "high": "high",
        "medium": "moderate",
        "moderate": "moderate",
        "low": "low",
    }
    level = risk_map.get(risk_level.lower(), "low")

    recommendations = {
        "emergency": "Seek emergency medical care immediately.",
        "high": "See a doctor within 24 hours.",
        "moderate": "Schedule a doctor's appointment within the next week.",
        "low": "Monitor your symptoms and follow up at your next routine appointment.",
    }
    explanations = {
        "emergency": "Critical risk level detected in report analysis.",
        "high": "The overall risk level is high — prompt medical attention is advised.",
        "moderate": "Moderate risk findings were detected. Medical review within a week is recommended.",
        "low": "No urgent findings detected. Continue monitoring your health.",
    }

    return {
        "level": level,
        "recommendation": recommendations[level],
        "explanation": explanations[level],
        "triggered_by": [f"Risk level: {risk_level}"] + [rf for rf in red_flags[:2]],
    }


# ---------------------------------------------------------------------------
# LLM enrichment
# ---------------------------------------------------------------------------

def _get_model() -> genai.GenerativeModel:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return None  # type: ignore[return-value]
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name="gemini-flash-lite-latest",
        generation_config={"response_mime_type": "application/json"},
    )


def _strip_json(text: str) -> str:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return m.group(0) if m else text


def _build_profile_text(user_profile: dict | None) -> str:
    if not user_profile:
        return "No profile available."
    conditions = ", ".join(user_profile.get("conditions", [])) or "none reported"
    meds = ", ".join(user_profile.get("medications", [])) or "none reported"
    bmi = user_profile.get("bmi")
    bmi_str = f"{bmi:.1f}" if bmi else "unknown"
    age = user_profile.get("age", "unknown")
    gender = user_profile.get("gender", "unknown")
    name = user_profile.get("name", "")
    name_str = f"Name: {name}, " if name else ""
    return (
        f"{name_str}Age: {age}, Gender: {gender}, BMI: {bmi_str}\n"
        f"Known Conditions: {conditions}\n"
        f"Medications: {meds}"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def run_triage(
    risk_level: str,
    red_flags: list[str],
    probable_conditions: list[dict],
    summary: str,
    findings: list[dict] | None = None,
    user_profile: dict | None = None,
) -> dict[str, Any]:
    """
    Run the full triage pipeline.

    1. Rule-based fast-path (always executes, guarantees a result)
    2. LLM enrichment (overwrites explanation + triggered_by if successful)

    Returns a TriageResult dict with keys:
        level, recommendation, explanation, triggered_by
    """
    conditions_text = [c.get("name", "") for c in probable_conditions]
    findings_text = " ".join(
        f.get("text", "") for f in (findings or [])
    )

    # Always run rule-based first
    result = _rule_based_triage(
        risk_level=risk_level,
        red_flags=red_flags,
        findings_text=findings_text,
        conditions=conditions_text,
    )

    # Emergency — skip LLM, speed matters
    if result["level"] == "emergency":
        return result

    # Try LLM enrichment
    model = _get_model()
    if model is None:
        return result

    try:
        conditions_str = ", ".join(conditions_text) or "none identified"
        red_flags_str = "; ".join(red_flags) or "none"
        profile_text = _build_profile_text(user_profile)

        prompt = _TRIAGE_PROMPT.format(
            risk_level=risk_level,
            conditions=conditions_str,
            red_flags=red_flags_str,
            summary=summary[:500],
            profile_text=profile_text,
        )
        response = model.generate_content(prompt)
        raw = json.loads(_strip_json(response.text))

        level = raw.get("level", "").lower()
        if level not in TRIAGE_LEVELS:
            level = result["level"]

        # Never downgrade an emergency from rule-based
        if result["level"] == "emergency":
            level = "emergency"

        return {
            "level": level,
            "recommendation": str(raw.get("recommendation", result["recommendation"])),
            "explanation": str(raw.get("explanation", result["explanation"])),
            "triggered_by": [
                str(t) for t in raw.get("triggered_by", result["triggered_by"])
            ][:4],
        }
    except Exception:
        # Graceful fallback to rule-based result
        return result
