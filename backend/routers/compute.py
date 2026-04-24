"""
/api/compute — Phase 2A compute-metric endpoint + generic signal tools.

Endpoints:
  POST /api/compute              → gait metrics (H-Walker CSV only)
  GET  /api/compute/metrics      → list available metric keys
  POST /api/compute/events       → detect HIGH/LOW trigger regions in any column
  POST /api/compute/column_stats → descriptive stats for arbitrary columns
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.routers.analyze import analyze_cached
from backend.routers.datasets import get_path
from backend.services import compute_engine


router = APIRouter(prefix="/api/compute", tags=["compute"])


class ComputeRequest(BaseModel):
    dataset_id: str
    metric: str
    options: Optional[dict[str, Any]] = None


@router.post("")
def compute_metric(req: ComputeRequest) -> dict[str, Any]:
    if req.metric not in compute_engine.METRIC_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown metric '{req.metric}'. "
                   f"Known: {sorted(compute_engine.METRIC_REGISTRY.keys())}",
        )

    res, _payload = analyze_cached(req.dataset_id)
    if res is None:
        raise HTTPException(
            status_code=409,
            detail="Dataset is in generic fallback mode (not H-Walker format). "
                   "Compute metrics require H-Walker CSV.",
        )

    path = get_path(req.dataset_id)
    if not path:
        raise HTTPException(status_code=404, detail=f"dataset '{req.dataset_id}' not found")

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"CSV unreadable: {exc}") from exc

    opts = req.options or {}
    try:
        return compute_engine.compute(req.metric, df, res, **opts)
    except TypeError as exc:
        raise HTTPException(status_code=400, detail=f"bad options: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"compute failed: {exc}") from exc


@router.get("/metrics")
def list_metrics() -> list[str]:
    return sorted(compute_engine.METRIC_REGISTRY.keys())


# ─────────────────────────────────────────────────────────────
# Generic signal tools (work on any CSV, no H-Walker required)
# ─────────────────────────────────────────────────────────────

def _load_df(dataset_id: str) -> pd.DataFrame:
    path = get_path(dataset_id)
    if not path:
        raise HTTPException(status_code=404, detail=f"dataset '{dataset_id}' not found")
    try:
        return pd.read_csv(path)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"CSV unreadable: {exc}") from exc


def _infer_fs(df: pd.DataFrame) -> float:
    """Guess sample rate from the first time-like column."""
    for col in df.columns:
        if col.lower() in ('time', 't', 'timestamp') or 'time' in col.lower():
            try:
                dt = float(df[col].diff().dropna().median())
                if dt > 0:
                    return 1.0 / dt
            except Exception:
                pass
    return 111.0  # H-Walker default


class EventsRequest(BaseModel):
    dataset_id: str
    signal_col: str
    threshold: Optional[float] = None   # None → auto (signal mean)
    min_duration_s: float = 0.1


@router.post("/events")
def detect_events(req: EventsRequest) -> dict[str, Any]:
    """Detect HIGH/LOW trigger regions in an arbitrary signal column.

    Returns a table: Region | Start (s) | End (s) | Duration (s) | Peak | Mean
    """
    df = _load_df(req.dataset_id)

    if req.signal_col not in df.columns:
        available = ", ".join(str(c) for c in df.columns[:30])
        raise HTTPException(
            status_code=422,
            detail=f"Column '{req.signal_col}' not found. Available: {available}",
        )

    signal = df[req.signal_col].fillna(0).to_numpy(dtype=float)
    fs = _infer_fs(df)
    threshold = req.threshold if req.threshold is not None else float(np.mean(signal))
    min_samples = max(1, int(req.min_duration_s * fs))

    high = (signal > threshold).astype(np.int8)
    edges = np.diff(high, prepend=0)
    starts = np.where(edges == 1)[0]
    ends   = np.where(edges == -1)[0]

    # Align: trim leading end if first end precedes first start
    if len(ends) and len(starts) and ends[0] < starts[0]:
        ends = ends[1:]
    # If still unpaired, close last region at final sample
    if len(starts) > len(ends):
        ends = np.append(ends, len(signal) - 1)
    n_pairs = min(len(starts), len(ends))
    starts, ends = starts[:n_pairs], ends[:n_pairs]

    rows: list[list] = []
    for i, (s, e) in enumerate(zip(starts, ends)):
        if e - s < min_samples:
            continue
        seg = signal[s:e]
        rows.append([
            i + 1,
            round(float(s) / fs, 3),
            round(float(e) / fs, 3),
            round(float(e - s) / fs, 3),
            round(float(np.max(seg)), 5),
            round(float(np.mean(seg)), 5),
        ])

    return {
        "label": f"Event Detection · {req.signal_col}",
        "cols": ["Region", "Start (s)", "End (s)", "Duration (s)", "Peak", "Mean"],
        "rows": rows,
        "summary": {"mean": [None] * 6},
        "meta": {
            "signal_col": req.signal_col,
            "threshold": round(threshold, 6),
            "n_events": len(rows),
            "sample_rate_hz": round(fs, 2),
        },
    }


class ColStatsRequest(BaseModel):
    dataset_id: str
    columns: list[str]


@router.post("/column_stats")
def column_stats(req: ColStatsRequest) -> dict[str, Any]:
    """Return descriptive statistics for arbitrary CSV columns."""
    df = _load_df(req.dataset_id)

    rows: list[list] = []
    missing: list[str] = []
    for col in req.columns:
        if col not in df.columns:
            missing.append(col)
            continue
        try:
            s = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(s) == 0:
                continue
            rows.append([
                col,
                f"{s.mean():.5g}",
                f"{s.std():.5g}",
                f"{s.min():.5g}",
                f"{s.quantile(0.25):.5g}",
                f"{s.median():.5g}",
                f"{s.quantile(0.75):.5g}",
                f"{s.max():.5g}",
                str(len(s)),
            ])
        except Exception:
            continue

    if missing:
        avail = ", ".join(str(c) for c in df.columns[:30])
        raise HTTPException(
            status_code=422,
            detail=f"Columns not found: {missing}. Available: {avail}",
        )

    label_cols = req.columns[:3]
    suffix = f" +{len(req.columns)-3} more" if len(req.columns) > 3 else ""
    return {
        "label": f"Column Stats · {', '.join(label_cols)}{suffix}",
        "cols": ["Column", "Mean", "Std", "Min", "Q25", "Median", "Q75", "Max", "N"],
        "rows": rows,
        "summary": {"mean": [None] * 9},
        "meta": {"columns": req.columns},
    }
