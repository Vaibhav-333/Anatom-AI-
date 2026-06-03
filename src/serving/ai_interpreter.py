"""
ai_interpreter.py — Gemini 1.5 Flash multimodal medical report interpreter.

Usage
-----
    from src.serving.ai_interpreter import interpret_document

    result = await interpret_document(
        file_bytes=b"...",
        mime_type="application/pdf",
        file_name="blood_report.pdf",
        mode="simple",
    )
    # result is a dict matching InterpretResponse fields

Environment
-----------
    GEMINI_API_KEY — required. Set in .env or shell before starting the server.
                     Never hardcode.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Literal

import google.generativeai as genai
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Persistent disk cache + in-memory layer
#
# Layout:  data/interpret_cache.json  →  {cache_key: result_dict}
#
# - On startup  : disk cache is loaded into memory automatically.
# - On new hit  : result is written to disk immediately (atomic rename).
# - No TTL on disk entries — pre-cached demo files stay valid forever so
#   the app works without internet at interviews / demos.
# ---------------------------------------------------------------------------

_CACHE_TTL_SECONDS = 60 * 60 * 24 * 365  # 1 year effective TTL in memory
_DISK_CACHE_PATH   = Path("data/interpret_cache.json")

# in-memory layer: key → (result_dict, monotonic_timestamp)
_response_cache: dict[str, tuple[dict, float]] = {}


def _load_disk_cache() -> None:
    """Load persisted results from disk into the in-memory cache on startup."""
    if not _DISK_CACHE_PATH.exists():
        return
    try:
        data: dict[str, dict] = json.loads(_DISK_CACHE_PATH.read_text(encoding="utf-8"))
        now = time.monotonic()
        for key, result in data.items():
            _response_cache[key] = (result, now)
        print(f"[cache] Loaded {len(data)} pre-cached result(s) from {_DISK_CACHE_PATH}")
    except Exception as exc:
        print(f"[cache] Could not load disk cache: {exc}")


def _save_disk_cache() -> None:
    """Atomically write the current in-memory cache to disk."""
    try:
        _DISK_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {key: result for key, (result, _) in _response_cache.items()}
        tmp = _DISK_CACHE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        tmp.replace(_DISK_CACHE_PATH)  # atomic on all major OS
    except Exception as exc:
        print(f"[cache] Could not save disk cache: {exc}")


def _cache_get(key: str) -> dict | None:
    entry = _response_cache.get(key)
    if entry is None:
        return None
    result, ts = entry
    if time.monotonic() - ts > _CACHE_TTL_SECONDS:
        del _response_cache[key]
        return None
    return result


def _cache_set(key: str, result: dict) -> None:
    # Keep memory cache bounded at 200 entries — evict oldest when full
    if len(_response_cache) >= 200:
        oldest_key = min(_response_cache, key=lambda k: _response_cache[k][1])
        del _response_cache[oldest_key]
    _response_cache[key] = (result, time.monotonic())
    _save_disk_cache()   # persist every new result immediately


# Load disk cache as soon as this module is imported
_load_disk_cache()

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_VALID_REGIONS = {"brain", "heart", "lungs", "liver", "kidneys", "spine", "stomach"}

_REGION_COORDS = {
    "brain":   [0.0,  2.3,  0.0],
    "heart":   [-0.3, 0.9,  0.2],
    "lungs":   [0.0,  0.78, 0.0],
    "liver":   [0.45, 0.32, 0.1],
    "kidneys": [0.0,  0.0, -0.3],
    "spine":   [0.0,  0.5, -0.3],
    "stomach": [-0.2, 0.2,  0.2],
}

SIMPLE_PROMPT = """
You are a compassionate medical report interpreter helping a patient understand their results.
Analyse the attached medical document carefully.
The patient wants a simple, empathetic explanation — no medical jargon, no scary language.

Return ONLY a valid JSON object with exactly these fields:
{
  "summary": "Plain-language summary (2-3 sentences, warm and empathetic tone)",
  "findings": [
    {
      "text": "Plain description of the finding",
      "severity": "normal",
      "value": "123",
      "unit": "mg/dL",
      "reference_range": "70-100"
    }
  ],
  "affected_regions": ["brain"],
  "confidence": 0.85,
  "reasoning": "Brief explanation of why the AI flagged specific items",
  "report_type": "blood_report",
  "risk_level": "low",
  "anatomical_mapping": [
    {
      "region_id": "brain",
      "finding_index": 0,
      "camera_focus": [0.0, 2.3, 0.0],
      "severity": "normal"
    }
  ]
}

Rules:
- severity must be one of: "normal", "borderline", "critical"
- affected_regions must only contain values from: brain, heart, lungs, liver, kidneys, spine, stomach
- risk_level must be one of: "low", "moderate", "high", "critical"
- report_type must be one of: blood_report, brain_mri, xray, ct, ultrasound, unknown
- confidence is a float 0.0–1.0 reflecting how clearly the document contained interpretable data
- value, unit, reference_range are optional — omit if not present in the document
- anatomical_mapping: for each region in affected_regions, add one entry.
  Use EXACTLY these camera_focus coordinates:
  brain=[0,2.3,0], heart=[-0.3,0.9,0.2], lungs=[0,0.78,0], liver=[0.45,0.32,0.1],
  kidneys=[0,0,-0.3], spine=[0,0.5,-0.3], stomach=[-0.2,0.2,0.2]
  finding_index is the 0-based index in findings[] for the primary finding related to this region.
  severity in anatomical_mapping must match the severity of that finding.
- Return ONLY the JSON object, no markdown fences, no extra text
"""

DOCTOR_PROMPT = """
You are a clinical decision support system analysing a medical document for a physician.
Provide a thorough clinical-grade interpretation with appropriate medical terminology.

Return ONLY a valid JSON object with exactly these fields:
{
  "summary": "Clinical summary including relevant differential diagnosis considerations",
  "findings": [
    {
      "text": "Clinical description of the finding",
      "severity": "normal",
      "value": "123",
      "unit": "mg/dL",
      "reference_range": "70-100"
    }
  ],
  "affected_regions": ["brain"],
  "confidence": 0.85,
  "reasoning": "Clinical reasoning for flagged findings, including relevant pathophysiology",
  "report_type": "blood_report",
  "risk_level": "low",
  "anatomical_mapping": [
    {
      "region_id": "brain",
      "finding_index": 0,
      "camera_focus": [0.0, 2.3, 0.0],
      "severity": "normal"
    }
  ]
}

Rules:
- severity must be one of: "normal", "borderline", "critical"
- affected_regions must only contain values from: brain, heart, lungs, liver, kidneys, spine, stomach
- risk_level must be one of: "low", "moderate", "high", "critical"
- report_type must be one of: blood_report, brain_mri, xray, ct, ultrasound, unknown
- confidence is a float 0.0–1.0
- value, unit, reference_range are optional
- anatomical_mapping: for each region in affected_regions, add one entry.
  Use EXACTLY these camera_focus coordinates:
  brain=[0,2.3,0], heart=[-0.3,0.9,0.2], lungs=[0,0.78,0], liver=[0.45,0.32,0.1],
  kidneys=[0,0,-0.3], spine=[0,0.5,-0.3], stomach=[-0.2,0.2,0.2]
  finding_index is the 0-based index in findings[] for the primary finding related to this region.
- Return ONLY the JSON object, no markdown fences, no extra text
"""

# ---------------------------------------------------------------------------
# Fallback response (used when Gemini call fails or JSON is unparseable)
# ---------------------------------------------------------------------------

def _fallback_response() -> dict:
    return {
        "summary": "Could not parse the AI response. Please retry — this is usually a temporary issue.",
        "findings": [],
        "affected_regions": [],
        "confidence": 0.0,
        "reasoning": "Analysis failed or returned an unexpected format.",
        "report_type": "unknown",
        "risk_level": "low",
        "anatomical_mapping": [],
    }


# ---------------------------------------------------------------------------
# Response normalisation
# ---------------------------------------------------------------------------

def _normalise(raw: dict) -> dict:
    """Validate and clean the Gemini response dict."""
    valid_severities = {"normal", "borderline", "critical"}
    valid_risk = {"low", "moderate", "high", "critical"}
    valid_types = {"blood_report", "brain_mri", "xray", "ct", "ultrasound", "unknown"}

    # Coerce findings
    findings = []
    for f in raw.get("findings", []):
        if not isinstance(f, dict):
            continue
        findings.append({
            "text": str(f.get("text", "")),
            "severity": f.get("severity", "normal") if f.get("severity") in valid_severities else "normal",
            "value": f.get("value"),
            "unit": f.get("unit"),
            "reference_range": f.get("reference_range"),
        })

    # Filter affected regions to known values
    regions = [r for r in raw.get("affected_regions", []) if r in _VALID_REGIONS]

    # Clamp confidence
    confidence = float(raw.get("confidence", 0.5))
    confidence = max(0.0, min(1.0, confidence))

    risk = raw.get("risk_level", "low")
    if risk not in valid_risk:
        risk = "low"

    report_type = raw.get("report_type", "unknown")
    if report_type not in valid_types:
        report_type = "unknown"

    # Auto-upgrade risk: 3+ borderline findings → at least "moderate"
    borderline_count = sum(1 for f in findings if f["severity"] == "borderline")
    if borderline_count >= 3 and risk == "low":
        risk = "moderate"

    # Validate anatomical_mapping entries
    valid_severities = {"normal", "borderline", "critical"}
    anat_mapping = []
    for item in raw.get("anatomical_mapping", []):
        if not isinstance(item, dict):
            continue
        region_id = item.get("region_id", "")
        if region_id not in _VALID_REGIONS:
            continue
        cam = item.get("camera_focus", _REGION_COORDS.get(region_id, [0.0, 0.5, 0.0]))
        if not (isinstance(cam, list) and len(cam) == 3):
            cam = _REGION_COORDS.get(region_id, [0.0, 0.5, 0.0])
        try:
            cam = [float(c) for c in cam]
        except (TypeError, ValueError):
            cam = _REGION_COORDS.get(region_id, [0.0, 0.5, 0.0])
        sev = item.get("severity", "normal")
        if sev not in valid_severities:
            sev = "normal"
        anat_mapping.append({
            "region_id": region_id,
            "finding_index": int(item.get("finding_index", 0)),
            "camera_focus": cam,
            "severity": sev,
        })

    # Auto-fill mapping for any affected region not already included
    mapped_ids = {m["region_id"] for m in anat_mapping}
    for region_id in regions:
        if region_id not in mapped_ids:
            anat_mapping.append({
                "region_id": region_id,
                "finding_index": 0,
                "camera_focus": _REGION_COORDS.get(region_id, [0.0, 0.5, 0.0]),
                "severity": "normal",
            })

    return {
        "summary": str(raw.get("summary", "")),
        "findings": findings,
        "affected_regions": regions,
        "confidence": confidence,
        "reasoning": str(raw.get("reasoning", "")),
        "report_type": report_type,
        "risk_level": risk,
        "anatomical_mapping": anat_mapping,
    }


# ---------------------------------------------------------------------------
# Main interpreter
# ---------------------------------------------------------------------------

async def interpret_document(
    file_bytes: bytes,
    mime_type: str,
    file_name: str,
    mode: Literal["simple", "doctor"] = "simple",
) -> dict:
    """
    Send *file_bytes* to Gemini 2.0 Flash and return a normalised interpretation dict.

    Results are cached for 24 h keyed on sha256(file_bytes)+mode so identical
    uploads never hit the Gemini API twice (saves quota + latency).

    Raises HTTPException on configuration or quota errors so FastAPI returns
    clean JSON error responses instead of 500 tracebacks.
    """
    # ── Cache lookup — skip Gemini entirely if we've seen this exact file ──────
    file_hash = sha256_hex(file_bytes)
    cache_key = f"{file_hash}:{mode}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "GEMINI_API_KEY is not configured. "
                "Set it as an environment variable before starting the server."
            ),
        )

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-flash-lite-latest",
        generation_config={"response_mime_type": "application/json"},
    )
    prompt = SIMPLE_PROMPT if mode == "simple" else DOCTOR_PROMPT

    # ── Build message parts ─────────────────────────────────────────────────
    if mime_type.startswith("image/"):
        # Inline base64 image
        b64 = base64.b64encode(file_bytes).decode("ascii")
        parts = [
            prompt,
            {"inline_data": {"mime_type": mime_type, "data": b64}},
        ]
        response = _call_gemini(model, parts)

    elif mime_type == "application/pdf":
        # Upload PDF via Files API then reference it
        tmp_path = _write_temp(file_bytes, suffix=".pdf")
        try:
            uploaded = genai.upload_file(tmp_path, mime_type="application/pdf")
            parts = [prompt, uploaded]
            response = _call_gemini(model, parts)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    else:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {mime_type}. Upload a PDF or image.",
        )

    # ── Parse response and store in cache ──────────────────────────────────
    try:
        raw = json.loads(response.text)
        result = _normalise(raw)
    except (json.JSONDecodeError, AttributeError):
        result = _fallback_response()

    _cache_set(cache_key, result)
    return result


def _write_temp(data: bytes, suffix: str) -> str:
    """Write bytes to a named temp file and return its path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
    except Exception:
        os.close(fd)
        raise
    return path


def _call_gemini(model: genai.GenerativeModel, parts: list, retries: int = 2):
    """Call Gemini with automatic retry on rate-limit, transparent errors otherwise."""
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return model.generate_content(parts)
        except Exception as exc:
            last_exc = exc
            msg = str(exc)
            msg_lower = msg.lower()

            # Auth / key errors — do NOT retry, fail immediately
            if (
                "403" in msg
                or "401" in msg
                or "api_key_invalid" in msg_lower
                or "unauthenticated" in msg_lower
                or "api_key" in msg_lower
            ):
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Gemini API key is invalid or lacks permissions. "
                        "Get a valid key from https://aistudio.google.com/app/apikey "
                        "and update GEMINI_API_KEY in your .env file."
                    ),
                )

            # Model not found — switch to lite fallback
            if "404" in msg or "not found" in msg_lower:
                try:
                    fallback = genai.GenerativeModel(
                        model_name="gemini-flash-lite-latest",
                        generation_config={"response_mime_type": "application/json"},
                    )
                    return fallback.generate_content(parts)
                except Exception as fb_exc:
                    raise HTTPException(
                        status_code=502,
                        detail=f"Gemini model unavailable: {str(fb_exc)[:200]}",
                    )

            # Rate limit — wait and retry
            if "429" in msg or "resource_exhausted" in msg_lower or "quota" in msg_lower:
                if attempt < retries:
                    time.sleep(3 * (attempt + 1))  # 3s, then 6s
                    continue
                raise HTTPException(
                    status_code=429,
                    detail="Gemini is temporarily rate-limited. Wait a moment and try again.",
                )

            # Unknown error — surface it so it can be debugged
            raise HTTPException(
                status_code=502,
                detail=f"Gemini error: {msg[:300]}",
            )

    # Should never reach here, but just in case
    raise HTTPException(status_code=502, detail=f"Gemini call failed: {str(last_exc)[:200]}")


# ---------------------------------------------------------------------------
# File hash helper (used by caller for cache lookups)
# ---------------------------------------------------------------------------

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
