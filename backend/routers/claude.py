"""
/api/claude/complete — HANDOFF §2.6.

Direct Anthropic SDK call (no legacy wrapping) so Q&A is plain prose,
≤3 sentences, grounded in the current workspace state.
Korean in, Korean out. English in, English out.

Phase B: /api/claude/stream for SSE, and suggested_cells parsing.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.config import (
    LLM_PROVIDER, ANTHROPIC_API_KEY, ANTHROPIC_MODEL, ANTHROPIC_MAX_TOKENS,
)


router = APIRouter(prefix="/api/claude", tags=["claude"])


class ClaudeContext(BaseModel):
    cells: list[dict[str, Any]] = []
    active_dataset_id: Optional[str] = None


class ClaudeCompleteRequest(BaseModel):
    prompt: str
    context: ClaudeContext = ClaudeContext()


class ClaudeCompleteResponse(BaseModel):
    reply: str
    suggested_cells: list[dict[str, Any]] = []


SYSTEM = (
    "You are a biomechanics research assistant inside H-Walker CORE — a gait "
    "analysis workspace for cable-driven walking rehabilitation research. "
    "Given the current workspace state (cells already created, active "
    "dataset), answer the user's question in ≤3 sentences. Be specific and "
    "quantitative when the data permits, otherwise say what's needed to "
    "answer. If the user writes Korean, answer in Korean; English → English. "
    "Never fabricate numbers. Do not use markdown headers."
)


def _context_block(ctx: ClaudeContext) -> str:
    cells_summary = ", ".join(
        f"{c.get('id', '?')}:{c.get('type', '?')}"
        + (f"/{c.get('graph') or c.get('op') or c.get('metric') or ''}")
        for c in ctx.cells[:20]
    ) or "(no cells yet)"
    return (
        f"Active dataset: {ctx.active_dataset_id or '(none)'}\n"
        f"Cells: {cells_summary}"
    )


@router.post("/complete", response_model=ClaudeCompleteResponse)
def complete(req: ClaudeCompleteRequest) -> ClaudeCompleteResponse:
    if LLM_PROVIDER != "anthropic":
        raise HTTPException(
            status_code=503,
            detail=f"LLM_PROVIDER={LLM_PROVIDER}; set it to 'anthropic' for /api/claude/complete.",
        )
    if not ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=503,
            detail=(
                "ANTHROPIC_API_KEY is not set. Export it before running "
                "`python3 run.py` so the Claude proxy can authenticate."
            ),
        )

    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="anthropic SDK not installed. Run: pip install anthropic",
        ) from exc

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    user_msg = f"{_context_block(req.context)}\n\nQuestion: {req.prompt}"

    try:
        msg = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=ANTHROPIC_MAX_TOKENS,
            system=SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Anthropic API: {exc}") from exc

    # Concatenate all text blocks in the response
    parts: list[str] = []
    for block in msg.content:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    reply = "\n".join(parts).strip() or "(empty)"
    return ClaudeCompleteResponse(reply=reply, suggested_cells=[])


@router.get("/health")
def claude_health() -> dict[str, Any]:
    return {
        "provider": LLM_PROVIDER,
        "model": ANTHROPIC_MODEL,
        "key_present": bool(ANTHROPIC_API_KEY),
    }
