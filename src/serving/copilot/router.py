"""
router.py — FastAPI router for the AI Health Copilot.

Endpoints:
  POST   /copilot/chat              — SSE streaming chat
  GET    /copilot/history/{id}      — conversation message history
  DELETE /copilot/history/{id}      — clear/delete a conversation
  POST   /copilot/embed/{report_id} — chunk + embed a report
  GET    /copilot/suggested/{id}    — auto-generated question chips
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from src.serving.auth.dependencies import get_current_user
from src.serving.database import get_db
from src.serving.copilot.models import (
    ChatRequest,
    EmbedResponse,
    HistoryResponse,
    MessageOut,
    SuggestedResponse,
)
from src.serving.copilot.rag_engine import stream_chat
from src.serving.copilot.embedder import index_report, search_report

router = APIRouter(prefix="/copilot", tags=["copilot"])

_SUGGESTED_DEFAULT = [
    "Is this normal for my age?",
    "What should I improve?",
    "Any diet suggestions?",
    "Compare with my last report",
]


# ── Chat (SSE) ────────────────────────────────────────────────────────────────

@router.post("/chat")
async def chat(
    body: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]

    async def event_stream():
        conv_id = body.conversation_id
        full_response = ""

        # Save user message first (create conversation if needed)
        async with get_db() as db:
            if not conv_id:
                conv_id = str(uuid.uuid4())
                title = body.query[:60] + ("…" if len(body.query) > 60 else "")
                await db.execute(
                    """INSERT INTO copilot_conversations (id, user_id, report_id, title)
                       VALUES (?, ?, ?, ?)""",
                    (conv_id, user_id, body.report_id, title),
                )
            else:
                # Update updated_at
                await db.execute(
                    "UPDATE copilot_conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (conv_id,),
                )

            user_msg_id = str(uuid.uuid4())
            await db.execute(
                "INSERT INTO copilot_messages (id, conversation_id, role, content) VALUES (?, ?, ?, ?)",
                (user_msg_id, conv_id, "user", body.query),
            )
            await db.commit()

        # Yield conversation_id immediately so client can track it
        yield f"data: {json.dumps({'type': 'init', 'conversation_id': conv_id})}\n\n"

        # Stream RAG response
        async for chunk in stream_chat(
            user_id=user_id,
            query=body.query,
            conversation_id=conv_id,
            report_id=body.report_id,
            context_page=body.context_page or "dashboard",
        ):
            yield chunk
            # Capture full response from done event
            try:
                payload = json.loads(chunk.removeprefix("data: ").strip())
                if payload.get("type") == "done":
                    full_response = payload.get("full_response", "")
            except Exception:
                pass

        # Save assistant message
        if full_response:
            async with get_db() as db:
                ai_msg_id = str(uuid.uuid4())
                await db.execute(
                    "INSERT INTO copilot_messages (id, conversation_id, role, content) VALUES (?, ?, ?, ?)",
                    (ai_msg_id, conv_id, "assistant", full_response),
                )
                await db.commit()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── History ───────────────────────────────────────────────────────────────────

@router.get("/history/{conversation_id}", response_model=HistoryResponse)
async def get_history(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    async with get_db() as db:
        conv_rows = await db.execute_fetchall(
            "SELECT * FROM copilot_conversations WHERE id = ? AND user_id = ? LIMIT 1",
            (conversation_id, user_id),
        )
        if not conv_rows:
            raise HTTPException(status_code=404, detail="Conversation not found.")

        msg_rows = await db.execute_fetchall(
            "SELECT * FROM copilot_messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,),
        )

    return HistoryResponse(
        conversation_id=conversation_id,
        title=conv_rows[0]["title"],
        messages=[
            MessageOut(
                id=r["id"],
                role=r["role"],
                content=r["content"],
                created_at=str(r["created_at"]),
            )
            for r in msg_rows
        ],
    )


@router.get("/conversations")
async def list_conversations(current_user: dict = Depends(get_current_user)):
    """List all conversations for the current user (most recent first)."""
    user_id = current_user["id"]
    async with get_db() as db:
        rows = await db.execute_fetchall(
            """SELECT id, title, report_id, created_at, updated_at
               FROM copilot_conversations WHERE user_id = ?
               ORDER BY updated_at DESC LIMIT 20""",
            (user_id,),
        )
    return [
        {
            "id": r["id"],
            "title": r["title"] or "Untitled",
            "report_id": r["report_id"],
            "updated_at": str(r["updated_at"]),
        }
        for r in rows
    ]


@router.delete("/history/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    async with get_db() as db:
        result = await db.execute(
            "DELETE FROM copilot_conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        )
        await db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"status": "deleted"}


# ── Embedding ─────────────────────────────────────────────────────────────────

@router.post("/embed/{report_id}", response_model=EmbedResponse)
async def embed_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Chunk and embed a report for RAG retrieval. Called after upload."""
    user_id = current_user["id"]
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT interpretation, user_id FROM reports WHERE id = ? LIMIT 1",
            (report_id,),
        )

    if not rows:
        raise HTTPException(status_code=404, detail="Report not found.")
    if rows[0]["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Access denied.")

    text = rows[0]["interpretation"] or ""
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                parts = [parsed.get("summary", "")]
                findings = parsed.get("findings", [])
                if isinstance(findings, list):
                    parts += [f"{f.get('text', '')} {f.get('value', '')} {f.get('unit', '')}" for f in findings]
                text = "\n".join(parts)
        except Exception:
            pass

    n = index_report(user_id, report_id, text)
    return EmbedResponse(status="ok", chunks_indexed=n)


# ── Suggested questions ───────────────────────────────────────────────────────

@router.get("/suggested/{report_id}", response_model=SuggestedResponse)
async def get_suggested(
    report_id: str,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT report_type, risk_level FROM reports WHERE id = ? AND user_id = ? LIMIT 1",
            (report_id, user_id),
        )

    if not rows:
        return SuggestedResponse(questions=_SUGGESTED_DEFAULT)

    report_type = rows[0]["report_type"] or "unknown"
    risk_level = rows[0]["risk_level"] or "low"

    questions = _build_suggested(report_type, risk_level)
    return SuggestedResponse(questions=questions)


def _build_suggested(report_type: str, risk_level: str) -> list[str]:
    base = ["Compare with my last report", "What lifestyle changes help?"]

    if risk_level in ("high", "critical"):
        return [
            "Is this serious? Should I see a doctor urgently?",
            "What are the warning signs I should watch for?",
            "What specialist should I consult?",
            "What can I do right now to help?",
        ]

    type_map = {
        "blood_report": [
            "Are my blood levels normal?",
            "What foods should I eat or avoid?",
            "What does my haemoglobin level mean?",
        ],
        "brain_mri": [
            "What does this MRI finding mean?",
            "Is immediate treatment needed?",
            "What follow-up scans are recommended?",
        ],
        "ct": [
            "What does the CT scan show?",
            "Are these findings concerning?",
            "What are the next steps?",
        ],
        "xray": [
            "What does this X-ray finding mean?",
            "Is this normal for my age?",
            "What follow-up is needed?",
        ],
        "ultrasound": [
            "What does this ultrasound indicate?",
            "Should I be concerned?",
            "What lifestyle changes help?",
        ],
    }

    specific = type_map.get(report_type, ["Is this normal for my age?", "What should I improve?"])
    return (specific + base)[:4]
