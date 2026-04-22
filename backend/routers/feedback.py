"""Feedback router: collects user feedback to improve LLM quality.

Endpoints:
  POST /api/feedback/positive     — 좋았음 (👍)
  POST /api/feedback/correction   — 잘못됨 (👎) + 수정안 + 이유
  GET  /api/feedback/stats        — 누적 통계
  GET  /api/feedback/recent       — 최근 피드백 (디버깅용)
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.feedback_loader import (
    save_positive,
    save_correction,
    get_stats,
    get_recent_positives,
    get_recent_corrections,
)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class PositiveFeedback(BaseModel):
    query: str
    response: dict
    image: Optional[str] = None   # base64
    note: Optional[str] = None


class CorrectionFeedback(BaseModel):
    query: str
    wrong_response: dict
    correct_response: Optional[dict] = None
    reason: str = ""
    image: Optional[str] = None   # base64


@router.post("/positive")
async def feedback_positive(payload: PositiveFeedback) -> dict:
    """Thumbs up — 좋은 응답이었음."""
    try:
        fb_id = save_positive(
            query=payload.query,
            response=payload.response,
            image_b64=payload.image,
            note=payload.note,
        )
        return {"id": fb_id, "status": "saved", "type": "positive"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/correction")
async def feedback_correction(payload: CorrectionFeedback) -> dict:
    """Thumbs down + correction — 틀렸음, 이렇게 해야 함."""
    try:
        fb_id = save_correction(
            query=payload.query,
            wrong_response=payload.wrong_response,
            correct_response=payload.correct_response,
            reason=payload.reason,
            image_b64=payload.image,
        )
        return {"id": fb_id, "status": "saved", "type": "correction"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def feedback_stats() -> dict:
    """Feedback 누적 통계."""
    return get_stats()


@router.get("/recent")
async def feedback_recent(limit: int = 10) -> dict:
    """최근 피드백 목록 (디버깅용)."""
    return {
        "positives": get_recent_positives(limit),
        "corrections": get_recent_corrections(limit),
    }
