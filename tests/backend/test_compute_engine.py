"""Regression tests for compute_engine — locks the scalar-first policy.

These tests exist because cadence and stride_length kept regressing back
into per-window / per-stride tables. Whole-trial parameters MUST report
as a single summary row; per-stride / per-window visualizations go
through explicit graph templates (stride_time_trend, etc.).
"""
from __future__ import annotations

import pandas as pd

from backend.services import compute_engine
from tools.auto_analyzer.analyzer import analyze_file


def _analyze(sample_csv: str):
    df = pd.read_csv(sample_csv)
    res = analyze_file(sample_csv)
    return df, res


# ---------------------------------------------------------------
# Scalar-first contract
# ---------------------------------------------------------------

def test_cadence_is_scalar_summary(sample_csv):
    """Cadence must be a single summary row, not a rolling window table."""
    df, res = _analyze(sample_csv)
    out = compute_engine.cadence(df, res)

    assert out["cols"] == ["L (spm)", "R (spm)", "Mean (spm)"], (
        "cadence cols must be L/R/Mean — not (window, spm). "
        "If you need a time-series, use the stride_time_trend graph."
    )
    assert len(out["rows"]) == 1, (
        f"cadence must report exactly one scalar row, got {len(out['rows'])}"
    )
    assert len(out["summary"]["mean"]) == 1
    assert "spm" in out["summary"]["mean"][0]


def test_stride_length_is_scalar_summary(sample_csv):
    """Stride length must be a single L/R/asym summary row, not per-stride."""
    df, res = _analyze(sample_csv)
    out = compute_engine.stride_length(df, res)

    assert out["cols"] == ["L (m)", "R (m)", "asym (%)"], (
        "stride_length cols must be L/R/asym — not stride_#. "
        "If the user wants per-stride, they must ask for the "
        "stride_time_trend graph or per_stride table."
    )
    assert len(out["rows"]) == 1, (
        f"stride_length must report one scalar row, got {len(out['rows'])}"
    )
    # Summary must carry mean±SD for both sides and an asymmetry %.
    assert len(out["summary"]["mean"]) == 3


def test_scalar_metrics_never_return_stride_number_column(sample_csv):
    """Whole-trial parameters must NOT leak a per-stride index column."""
    df, res = _analyze(sample_csv)
    for name in ("cadence", "stride_length"):
        out = getattr(compute_engine, name)(df, res)
        joined = " ".join(out["cols"]).lower()
        assert "stride_#" not in joined and "window" not in joined, (
            f"{name} regressed to a per-row table ({out['cols']}). "
            "Scalar-first policy broken."
        )


def test_per_stride_still_per_stride(sample_csv):
    """Per-stride must STAY per-stride — only cadence/stride_length scalarized."""
    df, res = _analyze(sample_csv)
    out = compute_engine.per_stride(df, res)
    assert "stride_#" in out["cols"]
    assert len(out["rows"]) >= 2  # at least a couple strides
