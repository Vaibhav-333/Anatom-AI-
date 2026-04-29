"""
rag_engine.py — Full RAG pipeline for the AI Health Copilot.

Flow:
  query → fetch context (profile + reports + history)
        → FAISS search for relevant chunks
        → build system prompt
        → stream Gemini Flash response
        → yield SSE tokens
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
import threading
from typing import AsyncGenerator, Optional

from src.serving.database import get_db
from src.serving.copilot.embedder import search_report

log = logging.getLogger(__name__)

SYSTEM_TEMPLATE = """You are a compassionate AI health companion for {name}.
Patient profile: {age}-year-old {gender}.
Known conditions: {conditions}.
Current medications: {medications}.
Diet preference: {diet_pref}.
Activity level: {activity_level}.

[RELEVANT REPORT CONTEXT]
{relevant_chunks}

[PREVIOUS REPORTS SUMMARY]
{prev_summaries}

[RECENT CONVERSATION]
{history}

Response guidelines:
- Speak warmly, like a knowledgeable friend — never robotic
- Be concise (under 200 words) unless the user asks for detail
- Highlight dangerously abnormal values in CAPS with ⚠️
- End with one thoughtful follow-up question
- Always include: "⚠️ This is health information, not medical advice. Please consult your doctor."
- If risk is high or critical, start with: "🚨 Some findings need prompt attention."
"""


async def _fetch_profile(user_id: str) -> dict:
    """Fetch health profile for prompt personalisation."""
    async with get_db() as db:
        row = await db.execute_fetchall(
            "SELECT * FROM auth_health_profiles WHERE user_id = ? LIMIT 1",
            (user_id,),
        )
        if row:
            r = row[0]
            return {
                "age": r["age"] or "unknown",
                "gender": r["gender"] or "unspecified",
                "conditions": r["conditions"] or "[]",
                "allergies": r["allergies"] or "[]",
                "activity_level": r["activity_level"] or "moderate",
            }

        # Fallback to profiles table
        row2 = await db.execute_fetchall(
            "SELECT * FROM profiles WHERE id = ? LIMIT 1",
            (user_id,),
        )
        if row2:
            r = row2[0]
            return {
                "age": r["age"] or "unknown",
                "gender": r["gender"] or "unspecified",
                "conditions": r["conditions"] or "[]",
                "allergies": "[]",
                "activity_level": "moderate",
            }
    return {"age": "unknown", "gender": "unspecified", "conditions": "[]", "allergies": "[]", "activity_level": "moderate"}


async def _fetch_report_text(report_id: str) -> tuple[str, str]:
    """Returns (report_text, risk_level) for a given report_id."""
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT interpretation, risk_level, file_name FROM reports WHERE id = ? LIMIT 1",
            (report_id,),
        )
        if rows:
            r = rows[0]
            text = r["interpretation"] or ""
            # Parse JSON if needed
            if text.startswith("{") or text.startswith("["):
                try:
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        text = parsed.get("summary", "") + "\n" + str(parsed.get("findings", ""))
                except Exception:
                    pass
            return text, r["risk_level"] or "low"
    return "", "low"


async def _fetch_previous_reports(user_id: str, exclude_id: Optional[str], limit: int = 2) -> str:
    """Build a short summary of previous reports for context."""
    async with get_db() as db:
        if exclude_id:
            rows = await db.execute_fetchall(
                """SELECT interpretation, risk_level, upload_date, file_name
                   FROM reports WHERE user_id = ? AND id != ?
                   ORDER BY upload_date DESC LIMIT ?""",
                (user_id, exclude_id, limit),
            )
        else:
            rows = await db.execute_fetchall(
                """SELECT interpretation, risk_level, upload_date, file_name
                   FROM reports WHERE user_id = ?
                   ORDER BY upload_date DESC LIMIT ?""",
                (user_id, limit),
            )

    if not rows:
        return "No previous reports available."

    summaries = []
    for r in rows:
        text = r["interpretation"] or ""
        if text.startswith("{"):
            try:
                parsed = json.loads(text)
                text = parsed.get("summary", text[:300])
            except Exception:
                text = text[:300]
        summaries.append(
            f"• {r['file_name']} ({r['upload_date'][:10] if r['upload_date'] else 'n/a'}) "
            f"[{r['risk_level']}]: {text[:200]}"
        )
    return "\n".join(summaries)


async def _fetch_user_name(user_id: str) -> str:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT username FROM auth_users WHERE id = ? LIMIT 1", (user_id,)
        )
        if rows:
            return rows[0]["username"].capitalize()
    return "there"


async def _fetch_history(conversation_id: str, limit: int = 6) -> str:
    async with get_db() as db:
        rows = await db.execute_fetchall(
            """SELECT role, content FROM copilot_messages
               WHERE conversation_id = ?
               ORDER BY created_at DESC LIMIT ?""",
            (conversation_id, limit),
        )
    if not rows:
        return ""
    lines = []
    for r in reversed(rows):
        prefix = "User" if r["role"] == "user" else "AI"
        lines.append(f"{prefix}: {r['content'][:300]}")
    return "\n".join(lines)


async def stream_chat(
    user_id: str,
    query: str,
    conversation_id: Optional[str],
    report_id: Optional[str],
    context_page: str,
) -> AsyncGenerator[str, None]:
    """
    Core RAG streaming pipeline.
    Yields SSE-formatted strings.
    """
    import google.generativeai as genai

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        yield _sse("error", {"message": "AI service not configured."})
        return

    genai.configure(api_key=api_key)

    # 1. Gather context
    profile = await _fetch_profile(user_id)
    name = await _fetch_user_name(user_id)
    history_text = await _fetch_history(conversation_id, limit=6) if conversation_id else ""
    prev_summaries = await _fetch_previous_reports(user_id, exclude_id=report_id)

    # 2. RAG: retrieve relevant chunks
    relevant_chunks = ""
    risk_level = "low"
    if report_id:
        report_text, risk_level = await _fetch_report_text(report_id)
        chunks = search_report(user_id, report_id, query, top_k=5)
        if chunks:
            relevant_chunks = "\n---\n".join(chunks)
        elif report_text:
            # Fallback: use first 1500 chars of report
            relevant_chunks = report_text[:1500]

    if not relevant_chunks:
        relevant_chunks = "No specific report loaded. Answering based on general health profile."

    # 3. Parse profile data
    try:
        import json
        conditions_list = json.loads(profile["conditions"]) if isinstance(profile["conditions"], str) else profile["conditions"]
        conditions = ", ".join(conditions_list) if conditions_list else "none reported"
    except Exception:
        conditions = profile["conditions"] or "none reported"

    # 4. Build prompt
    system_prompt = SYSTEM_TEMPLATE.format(
        name=name,
        age=profile["age"],
        gender=profile["gender"],
        conditions=conditions,
        medications="as per profile",
        diet_pref="balanced",
        activity_level=profile["activity_level"],
        relevant_chunks=relevant_chunks,
        prev_summaries=prev_summaries,
        history=history_text,
    )

    # Add urgency prefix if high risk
    urgency = ""
    if risk_level in ("high", "critical"):
        urgency = "🚨 Some findings in this report need prompt medical attention. "

    full_query = f"{urgency}{query}"

    # 5. Stream Gemini response
    # generate_content(stream=True) uses a synchronous iterator that blocks.
    # We run it in a thread and bridge tokens into the async generator via a queue.

    # Safety settings: health / medical content legitimately mentions symptoms,
    # medications, and anatomy — lower the sensitivity so Gemini doesn't refuse
    # these queries under DANGEROUS_CONTENT or HARASSMENT categories.
    try:
        from google.generativeai.types import HarmCategory, HarmBlockThreshold
        _safety = {
            HarmCategory.HARM_CATEGORY_HARASSMENT:        HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH:       HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        }
    except Exception:
        _safety = None  # older SDK — skip safety override

    model_kwargs: dict = {
        "model_name": "gemini-1.5-flash",
        "system_instruction": system_prompt,
    }
    if _safety:
        model_kwargs["safety_settings"] = _safety

    model = genai.GenerativeModel(**model_kwargs)

    _SENTINEL = object()
    token_queue: queue.Queue = queue.Queue()

    def _run_gemini():
        try:
            response = model.generate_content(full_query, stream=True)
            for chunk in response:
                # chunk.text raises ValueError when a chunk is blocked by a
                # safety filter — catch per-chunk so the rest still streams.
                try:
                    text = chunk.text
                    if text:
                        token_queue.put(text)
                except ValueError:
                    pass  # blocked chunk — skip and continue
        except Exception as exc:
            log.error("Gemini error: %s: %s", type(exc).__name__, exc)
            token_queue.put(exc)
        finally:
            token_queue.put(_SENTINEL)

    thread = threading.Thread(target=_run_gemini, daemon=True)
    thread.start()

    full_response = ""
    error_occurred = False
    loop = asyncio.get_running_loop()

    while True:
        # Poll queue without blocking the event loop
        try:
            item = await loop.run_in_executor(
                None, lambda: token_queue.get(timeout=30)
            )
        except queue.Empty:
            log.warning("Gemini stream timed out after 30s")
            error_occurred = True
            break
        except Exception:
            break

        if item is _SENTINEL:
            break
        if isinstance(item, Exception):
            log.error("Gemini streaming error: %s", item)
            error_occurred = True
            break

        full_response += item
        yield _sse("token", {"content": item})

    thread.join(timeout=2)

    if error_occurred or not full_response:
        fallback = (
            "I'm having trouble reaching the AI right now. "
            "Please consult your doctor for a thorough review. "
            "⚠️ This is health information, not medical advice."
        )
        full_response = fallback
        yield _sse("token", {"content": fallback})

    # 6. Generate follow-up suggestions
    follow_ups = _generate_followups(context_page, risk_level)
    yield _sse("suggested", {"questions": follow_ups})

    # 7. Signal completion (caller saves messages to DB)
    yield _sse("done", {"full_response": full_response})


def _generate_followups(context_page: str, risk_level: str) -> list[str]:
    base = ["What should I avoid?", "Can you explain this in simpler terms?", "Is this serious?"]
    if risk_level in ("high", "critical"):
        return ["Should I go to the ER?", "What are the warning signs?", "What specialist should I see?", "How urgent is this?"]
    if context_page == "results":
        return ["Is this normal for my age?", "What dietary changes help?", "Compare with my last report", "What follow-up tests do I need?"]
    return base + ["Compare with my previous report"]


def _sse(event_type: str, data: dict) -> str:
    return f"data: {json.dumps({'type': event_type, **data})}\n\n"
