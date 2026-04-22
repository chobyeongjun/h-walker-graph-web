"""Detect implicit user feedback from chat messages.

When user says things like:
  - "이거 이상해" / "틀렸어" / "잘못됐어"
  - "맞아" / "좋아" / "정확해" / "완벽"
automatically save as feedback without explicit button click.
"""
from __future__ import annotations

import re
from typing import Optional


POSITIVE_PATTERNS = [
    r"완벽",
    r"맞아(요|아)?",
    r"정확(해|하다)",
    r"좋(아|다|네)",
    r"그래\s*(이거|이렇게)",
    r"perfect",
    r"correct",
    r"exactly",
    r"great",
    r"good",
    r"👍",
    r"✓",
]

NEGATIVE_PATTERNS = [
    r"이상(해|하다)",
    r"틀렸어",
    r"잘못",
    r"아니(야|다)",
    r"다시",
    r"not\s+right",
    r"wrong",
    r"incorrect",
    r"bad",
    r"👎",
    r"❌",
    r"이렇게\s*(아니|말고)",
    r"(X|x)축이",  # 축 관련 지적
    r"(Y|y)축이",
]


def detect_sentiment(message: str) -> Optional[str]:
    """Return 'positive', 'negative', or None.

    Positive overrides if both detected.
    """
    msg = message.strip()
    if len(msg) > 200:
        # Long messages unlikely to be simple feedback
        return None

    for pat in POSITIVE_PATTERNS:
        if re.search(pat, msg, flags=re.IGNORECASE):
            return "positive"

    for pat in NEGATIVE_PATTERNS:
        if re.search(pat, msg, flags=re.IGNORECASE):
            return "negative"

    return None
