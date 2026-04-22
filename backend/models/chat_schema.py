from __future__ import annotations
from typing import Optional
from pydantic import BaseModel
from .schema import AnalysisRequest


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []
    images: list[str] = []  # optional base64-encoded images for vision


class ChatResponse(BaseModel):
    message: str
    action: str = "plot"  # "plot" | "clarify" | "insight"
    analysis_request: Optional[AnalysisRequest] = None
    insights: list[str] = []
