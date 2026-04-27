"""
diagnostic_engine.py — AI-driven question generation and diagnostic finalization.

Provides two public async functions:
  generate_next_question — Gemini generates the next follow-up question
  finalize_diagnostic    — Generates full CareReport from analysis + Q&A
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import google.generativeai as genai
from fastapi import HTTPException

MAX_QUESTIONS = 5

_QUESTION_PROMPT = """\
You are an AI medical assistant conducting a diagnostic interview after reviewing a patient's uploaded report.
{profile_block}
REPORT ANALYSIS:
Type: {report_type}
Summary: {summary}
Key Findings:
{findings}
Affected Body Regions: {regions}
Risk Level: {risk_level}

DIAGNOSTIC CONVERSATION SO FAR ({qa_count} of max {max_q} questions):
{qa_history}

Your task: Generate the NEXT most clinically important question to ask this patient.
Focus on:
- Clarifying abnormal findings (e.g. high WBC → ask about fever/fatigue)
- Duration, onset, and severity of symptoms
- Related symptoms not mentioned in the report
- Relevant past medical history specific to these findings
- Red-flag symptoms that may need urgent attention

If you have enough information (qa_count >= max_q or findings are very clear), return done=true.
Questions must feel natural, like a caring doctor speaking to a patient.

Return ONLY valid JSON — no markdown, no extra text:
{{"done": false, "question": {{"text": "Your question here", "type": "multiple_choice", "options": ["Option A", "Option B", "Option C"], "question_number": {next_num}, "total_questions": {max_q}}}}}
OR if done: {{"done": true}}

TYPE RULES:
- "multiple_choice": include "options" array (3-4 choices)
- "boolean": options must be exactly ["Yes", "No"]
- "slider": include "min_label" and "max_label" (no options), scale 1-10
- "text": free-form, no options
"""

_FINALIZE_PROMPT = """\
You are an advanced clinical AI generating a comprehensive diagnostic report.
{profile_block}
UPLOADED REPORT:
Type: {report_type}
Summary: {summary}
Key Findings: {findings}
Affected Regions: {regions}
Initial Risk Level: {risk_level}
Initial Confidence: {confidence}%

PATIENT INTERVIEW (Q&A):
{qa_history}

Synthesize ALL of the above to generate a refined medical analysis.
Return ONLY valid JSON — no markdown, no extra text:
{{
  "probable_conditions": [
    {{"name": "Condition Name", "confidence_pct": 85, "description": "One-sentence clinical description."}}
  ],
  "affected_organs": ["Heart"],
  "risk_level": "medium",
  "red_flags": ["Warning requiring attention"],
  "next_steps": ["Actionable step 1", "Actionable step 2"],
  "treatment_suggestions": ["General lifestyle suggestion"],
  "recommended_specialization": "Cardiologist",
  "personalized_insights": [
    {{"factor": "sedentary lifestyle", "impact": "increases cardiovascular risk", "severity": "high"}}
  ],
  "personalized_ai_summary": "Paragraph 1 of the narrative.\\n\\nParagraph 2.\\n\\nParagraph 3.\\n\\nParagraph 4.",
  "disclaimer": "AI-generated for informational purposes only. Consult a qualified healthcare professional."
}}

RULES:
- probable_conditions: top 3-5 conditions ranked by confidence_pct (0-100)
- risk_level: "low" | "medium" | "high" | "critical"
- red_flags: empty [] if none present
- treatment_suggestions: general lifestyle/diet/exercise approach ONLY — never prescribe medications
- Use patient answers to adjust condition ranking and confidence scores
- personalized_insights: 1-3 concise insights connecting the patient's specific situation to the
  diagnosis. Derive them from the Q&A interview answers and report findings even when no profile
  is provided (e.g. "Patient reported dizziness and chest discomfort → increases urgency of
  cardiovascular evaluation"). When a patient profile is available, also reference their age,
  BMI, existing conditions, or medications.
  Each insight: {{"factor": "...", "impact": "...", "severity": "low"|"moderate"|"high"}}
  severity: "high" if a major risk driver, "moderate" if contributing, "low" if minor context.
  Always return at least 1 insight when any finding or Q&A answer is present.
- personalized_ai_summary: A doctor-like narrative explanation of the full diagnosis. Rules:
  * 10-15 sentences total, organised in 3-4 short paragraphs separated by \\n\\n in the JSON string.
  * Paragraph 1 (3-4 sentences): Start with the patient's first name from PATIENT PROFILE if
    available (e.g. "Vaibhav, based on your report..."), otherwise use "Based on your report...".
    Explain what the report found and what the top probable condition is in simple terms.
  * Paragraph 2 (3-4 sentences): Explain what the risk level means for this specific patient,
    reference specific findings or values if available, and explain why it matters.
  * Paragraph 3 (2-3 sentences): Connect the patient's interview answers and lifestyle factors
    to the findings. Reference Q&A data and any profile information.
  * Paragraph 4 (2-3 sentences): What the patient should do next — which specialist to see,
    lifestyle changes, monitoring steps.
  * Use second person throughout ("your", "you"). Use plain language, no raw clinical jargon
    unless explained. Be reassuring but honest. Always generate this — minimum 8 sentences.
  * The value must be a valid JSON string — use \\n\\n (escaped) between paragraphs, never
    actual newlines inside the JSON string.
"""


def _get_model() -> genai.GenerativeModel:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config={"response_mime_type": "application/json"},
    )


def _fmt_findings(findings: list[dict]) -> str:
    if not findings:
        return "No specific findings extracted."
    lines = []
    for f in findings:
        line = f"- {f.get('text', '')} [{f.get('severity', 'normal')}]"
        if f.get("value") and f.get("reference_range"):
            line += f" | Value: {f['value']} {f.get('unit', '')} (Ref: {f['reference_range']})"
        lines.append(line)
    return "\n".join(lines)


def _fmt_qa(qa_history: list[dict]) -> str:
    if not qa_history:
        return "No questions asked yet."
    return "\n".join(
        f"Q{i + 1}: {qa['question']}\nA{i + 1}: {qa['answer']}"
        for i, qa in enumerate(qa_history)
    )


def _strip_json(text: str) -> str:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return m.group(0) if m else text


def _build_profile_block(user_profile: dict | None) -> str:
    """Build a PATIENT PROFILE block to prepend to prompts, or return empty string."""
    if not user_profile:
        return ""
    name = user_profile.get("name", "")
    age = user_profile.get("age", "unknown")
    gender = user_profile.get("gender", "unknown")
    bmi = user_profile.get("bmi")
    bmi_str = f"{bmi:.1f}" if bmi else "unknown"
    blood_type = user_profile.get("blood_type") or "unknown"
    conditions = ", ".join(user_profile.get("conditions", [])) or "none reported"
    meds = ", ".join(user_profile.get("medications", [])) or "none reported"
    name_line = f"Name: {name}, " if name else ""
    return (
        f"PATIENT PROFILE:\n"
        f"  {name_line}Age: {age}, Gender: {gender}, "
        f"BMI: {bmi_str}, Blood Type: {blood_type}\n"
        f"  Known Conditions: {conditions}\n"
        f"  Current Medications: {meds}\n\n"
    )


async def generate_next_question(
    report_type: str,
    summary: str,
    findings: list[dict],
    regions: list[str],
    risk_level: str,
    qa_history: list[dict],
    user_profile: dict | None = None,
) -> dict[str, Any]:
    """Returns {"done": True} or {"done": False, "question": DiagQuestion}."""
    qa_count = len(qa_history)
    if qa_count >= MAX_QUESTIONS:
        return {"done": True}

    try:
        prompt = _QUESTION_PROMPT.format(
            profile_block=_build_profile_block(user_profile),
            report_type=report_type,
            summary=summary,
            findings=_fmt_findings(findings),
            regions=", ".join(regions) or "Unknown",
            risk_level=risk_level,
            qa_count=qa_count,
            max_q=MAX_QUESTIONS,
            qa_history=_fmt_qa(qa_history),
            next_num=qa_count + 1,
        )
        model = _get_model()
        response = model.generate_content(prompt)
        raw = json.loads(_strip_json(response.text))
        if raw.get("done") or not raw.get("question", {}).get("text"):
            return {"done": True}
        return {"done": False, "question": raw["question"]}
    except (json.JSONDecodeError, AttributeError, Exception):
        return {"done": True}


async def finalize_diagnostic(
    initial_analysis: dict,
    qa_history: list[dict],
    user_profile: dict | None = None,
) -> dict[str, Any]:
    """Returns dict with probable_conditions, risk_level, red_flags, personalized_insights, etc."""
    try:
        prompt = _FINALIZE_PROMPT.format(
            profile_block=_build_profile_block(user_profile),
            report_type=initial_analysis.get("report_type", "unknown"),
            summary=initial_analysis.get("summary", ""),
            findings=_fmt_findings(initial_analysis.get("findings", [])),
            regions=", ".join(initial_analysis.get("affected_regions", [])) or "Unknown",
            risk_level=initial_analysis.get("risk_level", "low"),
            confidence=int(initial_analysis.get("confidence", 0.5) * 100),
            qa_history=_fmt_qa(qa_history),
        )
        model = _get_model()
        response = model.generate_content(prompt)
        raw = json.loads(_strip_json(response.text))
    except Exception:
        raw = {}

    conditions = [
        {
            "name": str(c["name"]),
            "confidence_pct": int(c.get("confidence_pct", 50)),
            "description": str(c.get("description", "")),
        }
        for c in raw.get("probable_conditions", [])
        if isinstance(c, dict) and c.get("name")
    ]

    risk = raw.get("risk_level", "low")
    if risk not in ("low", "medium", "high", "critical"):
        risk = initial_analysis.get("risk_level", "low")

    # Validate and sanitize personalized_insights
    valid_severities = {"low", "moderate", "high"}
    raw_insights = raw.get("personalized_insights", [])
    personalized_insights = [
        {
            "factor": str(i.get("factor", "")),
            "impact": str(i.get("impact", "")),
            "severity": i.get("severity", "moderate") if i.get("severity") in valid_severities else "moderate",
        }
        for i in raw_insights
        if isinstance(i, dict) and i.get("factor") and i.get("impact")
    ]

    return {
        "probable_conditions": conditions,
        "affected_organs": raw.get("affected_organs", initial_analysis.get("affected_regions", [])),
        "risk_level": risk,
        "red_flags": raw.get("red_flags", []),
        "next_steps": raw.get("next_steps", ["Consult a qualified healthcare professional."]),
        "treatment_suggestions": raw.get("treatment_suggestions", []),
        "recommended_specialization": raw.get("recommended_specialization", "General Physician"),
        "personalized_insights": personalized_insights,
        "personalized_ai_summary": str(raw.get("personalized_ai_summary", "")).strip(),
        "disclaimer": raw.get(
            "disclaimer",
            "AI-generated for informational purposes only. Always consult a qualified healthcare professional.",
        ),
    }
