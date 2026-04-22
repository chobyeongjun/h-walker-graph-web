"""In-memory session state for conversational context.

Tracks:
  - Last AnalysisRequest (for "다시 그려줘", "GCP로도 해줘" follow-ups)
  - Last CSV paths (for "아까 그 파일로" references)
  - Recent user messages (for implicit feedback on last response)
"""
from __future__ import annotations

import time
from collections import deque
from threading import Lock
from typing import Optional

from backend.models.schema import AnalysisRequest


class SessionState:
    """Single-process session state. Not thread-safe for multi-user."""

    def __init__(self):
        self._lock = Lock()
        self.last_request: Optional[AnalysisRequest] = None
        self.last_csv_paths: list[str] = []
        self.last_timestamp: float = 0.0
        self.last_user_query: str = ""
        # ring buffer of (query, response_dict) tuples
        self.recent: deque = deque(maxlen=10)

    def record(
        self,
        query: str,
        request: Optional[AnalysisRequest] = None,
        csv_paths: Optional[list[str]] = None,
    ) -> None:
        with self._lock:
            self.last_user_query = query
            if request is not None:
                self.last_request = request
            if csv_paths is not None:
                self.last_csv_paths = list(csv_paths)
            self.last_timestamp = time.time()
            self.recent.append({
                "ts": self.last_timestamp,
                "query": query,
                "request": request.model_dump() if request else None,
            })

    def get_context_summary(self) -> str:
        """Return a short context summary for LLM system prompt."""
        with self._lock:
            if not self.last_request:
                return ""
            req = self.last_request
            age = time.time() - self.last_timestamp
            if age > 600:  # 10 minutes old
                return ""
            return (
                "\n## Recent Analysis Context\n"
                f"Last analysis: {req.analysis_type.value}, sides={req.sides}, "
                f"normalize_gcp={req.normalize_gcp}, compare_mode={req.compare_mode}\n"
                f"Last query: \"{self.last_user_query}\" ({age:.0f}s ago)\n"
                "If user says '다시', 'GCP로도', '이번엔 ~' etc., build on this context.\n"
            )

    def get_last(self) -> Optional[dict]:
        with self._lock:
            if not self.recent:
                return None
            return self.recent[-1]


# Global singleton
_session = SessionState()


def get_session() -> SessionState:
    return _session
