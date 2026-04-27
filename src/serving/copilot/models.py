"""Pydantic schemas for the AI Copilot endpoints."""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    report_id: Optional[str] = None
    context_page: Optional[str] = "dashboard"


class MessageOut(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: str


class HistoryResponse(BaseModel):
    conversation_id: str
    title: Optional[str]
    messages: list[MessageOut]


class SuggestedResponse(BaseModel):
    questions: list[str]


class EmbedResponse(BaseModel):
    status: str
    chunks_indexed: int
