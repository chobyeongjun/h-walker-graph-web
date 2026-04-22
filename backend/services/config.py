"""Central configuration for H-Walker Graph App.

All tunable parameters in one place. Environment variables override defaults.
"""
from __future__ import annotations

import os
from pathlib import Path

# ============================================================
# LLM Provider Selection
# ============================================================
# Provider: "anthropic" (recommended, accurate) or "ollama" (local fallback)
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "anthropic")

# ============================================================
# Anthropic Claude Settings (Primary)
# ============================================================
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
# Default: Haiku 4.5 (fast + accurate + cheap for JSON extraction)
# Options: claude-haiku-4-5, claude-sonnet-4-6, claude-opus-4-7
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")
ANTHROPIC_MAX_TOKENS: int = int(os.getenv("ANTHROPIC_MAX_TOKENS", "1024"))

# ============================================================
# Ollama Settings (Fallback / local)
# ============================================================
OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "gemma4:e4b")
OLLAMA_KEEP_ALIVE: str = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
OLLAMA_MAX_RETRIES: int = int(os.getenv("OLLAMA_MAX_RETRIES", "3"))
OLLAMA_RETRY_DELAY_S: float = float(os.getenv("OLLAMA_RETRY_DELAY_S", "0.5"))
OLLAMA_TIMEOUT_S: float = float(os.getenv("OLLAMA_TIMEOUT_S", "60"))

# ============================================================
# Feedback / Knowledge
# ============================================================
HW_GRAPH_DIR: Path = Path(os.getenv("HW_GRAPH_DIR", "~/.hw_graph")).expanduser()
KNOWLEDGE_DIR: Path = HW_GRAPH_DIR / "knowledge"
FEEDBACK_DIR: Path = HW_GRAPH_DIR / "feedback"
LOGS_DIR: Path = HW_GRAPH_DIR / "logs"
CACHE_DIR: Path = HW_GRAPH_DIR / "cache"

for d in (KNOWLEDGE_DIR, FEEDBACK_DIR, LOGS_DIR, CACHE_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Max number of feedback examples to inject into system prompt
FEEDBACK_POSITIVES_N: int = int(os.getenv("FEEDBACK_POSITIVES_N", "3"))
FEEDBACK_CORRECTIONS_N: int = int(os.getenv("FEEDBACK_CORRECTIONS_N", "5"))

# ============================================================
# Logging
# ============================================================
LOG_LEVEL: str = os.getenv("HW_LOG_LEVEL", "INFO")
LOG_FILE: Path = LOGS_DIR / "graph_app.log"
