"""AI-powered medical report generation using Gemini."""
from __future__ import annotations

import json
import os
import re
from typing import Any

import google.generativeai as genai


def _get_model():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-1.5-flash")


REPORT_PROMPT = """You are a medical AI assistant. Based on the following patient data and symptoms, generate a detailed structured medical report. You MUST respond with ONLY valid JSON — no markdown, no code blocks, no explanations.

Patient Information:
- Age: {age}
- Gender: {gender}
- Medical History: {history}
- Current Symptoms: {symptoms}
- Severity: {severity}
- Duration: {duration} days

Generate JSON with exactly these fields:
{{
  "probable_conditions": [
    {{"name": "Condition Name", "confidence_pct": 85, "description": "Brief clinical description"}}
  ],
  "affected_organs": ["organ1", "organ2"],
  "risk_level": "low",
  "red_flags": [],
  "next_steps": ["Step 1", "Step 2"],
  "treatment_suggestions": ["General approach 1", "Lifestyle suggestion 2"],
  "recommended_specialization": "Neurologist",
  "disclaimer": "This is AI-generated information for educational purposes only and does not constitute medical advice. Please consult a qualified healthcare professional."
}}

Rules:
- probable_conditions: 3-5 conditions ranked by likelihood, confidence_pct between 10-95
- risk_level: exactly one of: "low", "medium", "high", "critical"
- red_flags: list critical warning signs that need immediate attention (empty list [] if none)
- next_steps: 3-5 actionable recommendations
- treatment_suggestions: general lifestyle/approach suggestions ONLY — never specific drug prescriptions
- affected_organs: anatomical organs involved
- recommended_specialization: single best specialist type"""


async def generate_care_report(
    symptoms: list[str],
    age: int | None,
    gender: str | None,
    medical_history: list[str],
    severity: str,
    duration_days: int,
) -> dict[str, Any]:
    """Call Gemini to generate a structured medical report. Returns parsed dict."""
    model = _get_model()

    prompt = REPORT_PROMPT.format(
        age=age or "Not specified",
        gender=gender or "Not specified",
        history=", ".join(medical_history) if medical_history else "None",
        symptoms=", ".join(symptoms),
        severity=severity,
        duration=duration_days,
    )

    response = model.generate_content(prompt)
    raw_text = response.text.strip()

    # Strip markdown code fences if Gemini wraps the response
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        # Fallback: extract first JSON object from response
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            data = _fallback_report(symptoms, severity)

    # Ensure all required keys exist
    data.setdefault("probable_conditions", [{"name": "Unspecified Condition", "confidence_pct": 50, "description": "Requires clinical evaluation"}])
    data.setdefault("affected_organs", [])
    data.setdefault("risk_level", "medium")
    data.setdefault("red_flags", [])
    data.setdefault("next_steps", ["Consult a healthcare professional"])
    data.setdefault("treatment_suggestions", ["Maintain healthy lifestyle", "Stay hydrated", "Get adequate rest"])
    data.setdefault("recommended_specialization", "General Physician")

    return data


def _fallback_report(symptoms: list[str], severity: str) -> dict[str, Any]:
    """Minimal fallback when AI response cannot be parsed."""
    risk = "high" if severity == "severe" else ("medium" if severity == "moderate" else "low")
    return {
        "probable_conditions": [
            {"name": "Requires Clinical Evaluation", "confidence_pct": 0,
             "description": "AI analysis unavailable. Please consult a doctor."}
        ],
        "affected_organs": [],
        "risk_level": risk,
        "red_flags": ["AI analysis failed — consult a doctor for proper diagnosis"] if severity == "severe" else [],
        "next_steps": ["Please visit a qualified physician for a proper examination", "Describe your symptoms in detail to your doctor"],
        "treatment_suggestions": ["Consult a healthcare professional", "Avoid self-medication"],
        "recommended_specialization": "General Physician",
        "disclaimer": "This is AI-generated information for educational purposes only and does not constitute medical advice.",
    }
