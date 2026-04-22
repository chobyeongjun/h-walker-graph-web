"""Feedback storage and retrieval for continuous LLM quality improvement.

Stores user feedback (positive/corrections) with optional screenshots.
Recent feedback is automatically injected as few-shot examples into
the LLM system prompt, creating a self-improving loop.

Directory structure:
  ~/.hw_graph/feedback/
    positive/         — 좋았던 상호작용 (query + correct_response)
    corrections/      — 틀렸던 상호작용 (query + wrong + correct + reason)
    images/           — 스크린샷 (optional)
    index.jsonl       — 빠른 조회용 인덱스
"""
from __future__ import annotations

import base64
import json
import time
from pathlib import Path
from typing import Optional

FEEDBACK_DIR = Path("~/.hw_graph/feedback").expanduser()
POSITIVE_DIR = FEEDBACK_DIR / "positive"
CORRECTIONS_DIR = FEEDBACK_DIR / "corrections"
IMAGES_DIR = FEEDBACK_DIR / "images"
INDEX_FILE = FEEDBACK_DIR / "index.jsonl"

for d in (POSITIVE_DIR, CORRECTIONS_DIR, IMAGES_DIR):
    d.mkdir(parents=True, exist_ok=True)


def _now_id() -> str:
    """Unique ID based on timestamp."""
    return time.strftime("%Y%m%d-%H%M%S") + f"-{int(time.time() * 1000) % 1000:03d}"


def _save_image(image_b64: str, fb_id: str) -> str | None:
    """Save base64 image to disk. Returns filename or None."""
    if not image_b64:
        return None
    try:
        if "," in image_b64:
            image_b64 = image_b64.split(",", 1)[1]
        raw = base64.b64decode(image_b64)
        fname = f"{fb_id}.png"
        (IMAGES_DIR / fname).write_bytes(raw)
        return fname
    except Exception:
        return None


def _append_index(entry: dict) -> None:
    """Append entry to index.jsonl for quick scanning."""
    with INDEX_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def save_positive(
    query: str,
    response: dict,
    image_b64: Optional[str] = None,
    note: Optional[str] = None,
) -> str:
    """User liked this interaction (thumbs up).

    Args:
        query: original user query
        response: the AnalysisRequest/response dict that was generated
        image_b64: optional screenshot showing what was generated
        note: optional free-text comment
    """
    fb_id = _now_id()
    image_file = _save_image(image_b64, fb_id) if image_b64 else None

    entry = {
        "id": fb_id,
        "type": "positive",
        "timestamp": int(time.time()),
        "query": query,
        "response": response,
        "image": image_file,
        "note": note,
    }
    (POSITIVE_DIR / f"{fb_id}.json").write_text(
        json.dumps(entry, indent=2, ensure_ascii=False)
    )
    _append_index({
        "id": fb_id,
        "type": "positive",
        "ts": entry["timestamp"],
        "query": query[:100],
    })
    return fb_id


def save_correction(
    query: str,
    wrong_response: dict,
    correct_response: Optional[dict] = None,
    reason: str = "",
    image_b64: Optional[str] = None,
) -> str:
    """User flagged the response as wrong (thumbs down).

    Args:
        query: original user query
        wrong_response: what LLM produced (which was wrong)
        correct_response: what the user expected (optional)
        reason: why it was wrong (e.g. "X축이 Sample이 아니라 GCP여야 함")
        image_b64: optional screenshot showing the problem
    """
    fb_id = _now_id()
    image_file = _save_image(image_b64, fb_id) if image_b64 else None

    entry = {
        "id": fb_id,
        "type": "correction",
        "timestamp": int(time.time()),
        "query": query,
        "wrong_response": wrong_response,
        "correct_response": correct_response,
        "reason": reason,
        "image": image_file,
    }
    (CORRECTIONS_DIR / f"{fb_id}.json").write_text(
        json.dumps(entry, indent=2, ensure_ascii=False)
    )
    _append_index({
        "id": fb_id,
        "type": "correction",
        "ts": entry["timestamp"],
        "query": query[:100],
        "reason": reason[:100],
    })
    return fb_id


def _load_recent(d: Path, limit: int) -> list[dict]:
    """Load most recent N feedback entries from a directory."""
    files = sorted(d.glob("*.json"), key=lambda p: p.name, reverse=True)[:limit]
    out = []
    for fp in files:
        try:
            out.append(json.loads(fp.read_text()))
        except Exception:
            continue
    return out


def get_recent_positives(limit: int = 5) -> list[dict]:
    return _load_recent(POSITIVE_DIR, limit)


def get_recent_corrections(limit: int = 5) -> list[dict]:
    return _load_recent(CORRECTIONS_DIR, limit)


def format_as_few_shot(
    positives_n: int = 3,
    corrections_n: int = 5,
) -> str:
    """Format recent feedback as few-shot examples for LLM system prompt.

    Corrections are emphasized more since they capture failure modes.
    """
    positives = get_recent_positives(positives_n)
    corrections = get_recent_corrections(corrections_n)

    if not positives and not corrections:
        return ""

    parts = ["\n## 학습된 패턴 (실제 사용자 피드백 기반)\n"]

    if corrections:
        parts.append("### ⚠️ 자주 하는 실수와 교정 (반드시 피할 것)\n")
        for c in corrections:
            parts.append(
                f"사용자: {c['query']}\n"
                f"❌ 잘못된 응답: {json.dumps(c['wrong_response'], ensure_ascii=False)}\n"
                + (f"✅ 올바른 응답: {json.dumps(c['correct_response'], ensure_ascii=False)}\n" if c.get('correct_response') else "")
                + (f"이유: {c['reason']}\n" if c.get('reason') else "")
                + "\n"
            )

    if positives:
        parts.append("### ✓ 좋은 예시 (이렇게 답변하면 됨)\n")
        for p in positives:
            parts.append(
                f"사용자: {p['query']}\n"
                f"응답: {json.dumps(p['response'], ensure_ascii=False)}\n\n"
            )

    return "".join(parts)


def get_stats() -> dict:
    """Return feedback statistics."""
    n_pos = len(list(POSITIVE_DIR.glob("*.json")))
    n_corr = len(list(CORRECTIONS_DIR.glob("*.json")))
    n_img = len(list(IMAGES_DIR.glob("*.png")))
    return {
        "positives": n_pos,
        "corrections": n_corr,
        "images": n_img,
        "total": n_pos + n_corr,
    }
