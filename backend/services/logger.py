"""Centralized logging for H-Walker Graph App.

Writes to ~/.hw_graph/logs/graph_app.log + stderr.
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from backend.services.config import LOG_LEVEL, LOG_FILE


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("hw_graph")
    if logger.handlers:
        return logger

    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    logger.setLevel(level)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Stderr handler (for development visibility)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    sh.setLevel(level)
    logger.addHandler(sh)

    # Rotating file handler (5MB x 3 files)
    try:
        fh = RotatingFileHandler(
            LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        fh.setFormatter(fmt)
        fh.setLevel(level)
        logger.addHandler(fh)
    except Exception:
        pass  # logging to stderr still works

    logger.propagate = False
    return logger


log = _build_logger()
