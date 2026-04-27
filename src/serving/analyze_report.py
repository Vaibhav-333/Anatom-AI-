"""
analyze_report.py — Gemini-powered text analysis for the /analyze-report endpoint.

Accepts raw medical report text; returns structured JSON with conditions, affected
organs, severity, and confidence — no file upload required.

Usage
-----
    from src.serving.analyze_report import analyse_text

    result = await analyse_text("Patient presents with arrhythmia and hepatitis B...")
    # result = {"conditions": [...], "summary": "...", "risk_level": "moderate"}

Environment
-----------
    GEMINI_API_KEY — required. Shared with ai_interpreter.py.
"""

from __future__ import annotations

import json
import os
from typing import Any

import google.generativeai as genai
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Model init — one-time at import, shared across requests
# ---------------------------------------------------------------------------

_api_key = os.environ.get("GEMINI_API_KEY", "")
if _api_key:
    genai.configure(api_key=_api_key)

_model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config={"response_mime_type": "application/json"},
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_VALID_SEVERITIES = {"mild", "moderate", "severe"}
_VALID_RISKS      = {"low", "moderate", "high", "critical"}

_PROMPT = """\
You are a clinical AI assistant. Carefully analyse the following medical report text and \
extract ALL diseases, conditions, and abnormalities mentioned or implied.

Return ONLY a valid JSON object with EXACTLY this structure — no markdown, no extra text:
{
  "conditions": [
    {
      "name": "Disease or condition name (proper medical term)",
      "confidence": 0.90,
      "affected_organs": ["Heart"],
      "severity": "moderate",
      "description": "One-sentence clinical description of this condition."
    }
  ],
  "summary": "2-3 sentence plain-language summary of the overall findings.",
  "risk_level": "moderate"
}

Rules:
- "severity" MUST be one of: "mild", "moderate", "severe"
- "risk_level" MUST be one of: "low", "moderate", "high", "critical"
- "confidence" is a float 0.0-1.0 representing how clearly the condition appears in the text
- "affected_organs" MUST use standard anatomical names from this list:
    Heart, Lungs, Brain, Liver, Kidney, Stomach, Colon, Intestine,
    Bladder, Pancreas, Gallbladder, Spleen
- Include ALL conditions mentioned, even if mild
- If the report mentions values out of range, flag the relevant organ
- If NO conditions or abnormalities are found, return:
    {"conditions": [], "summary": "No significant abnormality detected.", "risk_level": "low"}

REPORT TEXT:
"""

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fallback() -> dict[str, Any]:
    return {
        "conditions": [],
        "summary":    "Unable to analyse the report. Please try again.",
        "risk_level": "low",
    }


def _normalise(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate and clean the raw Gemini response."""
    conditions: list[dict] = []
    for item in raw.get("conditions", []):
        if not isinstance(item, dict):
            continue
        sev = str(item.get("severity", "moderate")).lower()
        conf = item.get("confidence", 0.5)
        try:
            conf = float(conf)
        except (TypeError, ValueError):
            conf = 0.5
        organs = item.get("affected_organs", [])
        if isinstance(organs, str):
            organs = [organs]
        conditions.append({
            "name":            str(item.get("name", "Unknown condition")),
            "confidence":      round(max(0.0, min(1.0, conf)), 2),
            "affected_organs": [str(o) for o in organs if isinstance(o, str)],
            "severity":        sev if sev in _VALID_SEVERITIES else "moderate",
            "description":     str(item.get("description", "")),
        })

    risk = str(raw.get("risk_level", "low")).lower()
    return {
        "conditions": conditions,
        "summary":    str(raw.get("summary", "No summary available.")),
        "risk_level": risk if risk in _VALID_RISKS else "low",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def analyse_text(text: str) -> dict[str, Any]:
    """
    Send report text to Gemini and return a normalised analysis dict.

    Raises HTTPException on auth / rate-limit errors.
    Returns a fallback dict on parse errors or unexpected failures.
    """
    if not _api_key:
        raise HTTPException(
            status_code=503,
            detail="Gemini API key not configured. Set GEMINI_API_KEY in .env.",
        )

    # Cap at 6 000 chars to stay well within the token budget
    prompt = _PROMPT + text.strip()[:6000]

    try:
        response = _model.generate_content(prompt)
        raw      = json.loads(response.text)
        return _normalise(raw)
    except json.JSONDecodeError:
        return _fallback()
    except Exception as exc:
        msg = str(exc).lower()
        if "api_key" in msg or "401" in msg or "403" in msg or "api_key_invalid" in msg:
            raise HTTPException(status_code=503, detail="Gemini authentication failed.")
        if "429" in msg or "quota" in msg or "resource_exhausted" in msg:
            raise HTTPException(
                status_code=429,
                detail="Gemini rate limit reached. Please retry in a few seconds.",
            )
        # For any other error, return a graceful fallback instead of 500
        return _fallback()
