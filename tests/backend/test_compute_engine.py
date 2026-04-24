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

    assert out["cols"] == ["from L HS (spm)", "from R HS (spm)", "Combined (spm)"], (
        "cadence cols must declare the heel-strike source per side and a "
        "Combined estimate — not (window, spm) and not generic L/R/Mean. "
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


# ---------------------------------------------------------------
# Scientific correctness — cadence formula
# ---------------------------------------------------------------

def test_cadence_formula_is_steps_per_minute(sample_csv):
    """Cadence must be whole-body steps/min = 120 / stride_time_s.

    stride_time is the time between two heel strikes on the SAME leg
    = 1 full gait cycle = 2 steps (one L step + one R step). So:
        cadence [steps/min] = (60 / stride_time_s) * 2 = 120 / T
    A past audit tried to 'simplify' this by removing the * 2, which
    halves the reported cadence — this test locks the correct formula.
    """
    df, res = _analyze(sample_csv)

    # Synthetic CSV in conftest has ~1 Hz gait (stride_time ≈ 1.0 s).
    # Whole-body cadence should be ~120 spm, NOT 60 spm.
    ls = res.left_stride
    assert ls.stride_time_mean > 0, "no strides detected — fixture broken"
    expected = 120.0 / ls.stride_time_mean  # same as (60/T) * 2
    assert abs(ls.cadence - expected) < 1e-6, (
        f"cadence formula regressed: got {ls.cadence:.2f}, "
        f"expected {expected:.2f} = 120 / {ls.stride_time_mean:.3f}s. "
        "Do NOT remove the *2 in analyzer.py — see comment there."
    )
    # Sanity: for ~1 Hz gait, cadence must be in the 100-130 spm
    # range, not 50-65 (which would mean * 2 got dropped).
    assert 90 < ls.cadence < 140, (
        f"cadence {ls.cadence:.1f} spm is not physiologically plausible "
        "for ~1 Hz synthetic gait — check the formula."
    )


# ---------------------------------------------------------------
# Bad-data defenses
# ---------------------------------------------------------------

def test_analyze_file_rejects_zero_sample_rate(sample_csv, monkeypatch):
    """If estimate_sample_rate ever returns 0 (malformed CSV, future
    refactor), analyze_file must raise a clear ValueError rather than
    let a silent ZeroDivisionError surface 20 lines deep in ZUPT
    integration."""
    import pytest
    from tools.graph_analyzer.data_manager import DataManager

    monkeypatch.setattr(DataManager, "estimate_sample_rate",
                        staticmethod(lambda df: 0.0))
    with pytest.raises(ValueError, match="sample rate"):
        analyze_file(sample_csv)
