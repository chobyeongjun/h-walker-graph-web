"""GCP-primary heel-strike detection regression tests.

The user observed two related bugs that pointed at the same root cause —
the heel-strike detector was using the firmware Event column, which on
some H-Walker builds pulses on every detected heel strike of either
foot:

  - stride_time came out around 0.6 s on a 1.0 m/s treadmill (real
    stride is ~1.0–1.2 s; 0.6 s is step time)
  - stance % came out near 50 % when normal walking is ~60 % stance

The fix in analyzer._detect_heel_strikes switches the primary cue to
the per-side GCP active-segment start (the GCP sawtooth ramps 0→1+
ONLY during the matching side's stance). This file pins:

  1. GCP active-segment starts are picked up correctly
  2. A step-pulsing Event signal still produces a stride-spaced output
     (the fallback halves the rate via gap-median heuristic)
  3. stance/swing % tracks the GCP active mask, not a phase guess
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from tools.auto_analyzer import analyzer


# ---------------------------------------------------------------
# Synthetic GCP signal (per-side sawtooth)
# ---------------------------------------------------------------

def _gcp_sawtooth(n: int, fs: float, stride_s: float,
                  stance_frac: float = 0.6) -> np.ndarray:
    """Per-side GCP: ramps 0→1 during stance phase, 0 during swing,
    repeating every `stride_s` seconds. Mimics H-Walker firmware."""
    g = np.zeros(n)
    stride_n = int(round(stride_s * fs))
    stance_n = int(round(stride_s * stance_frac * fs))
    for start in range(0, n - stride_n, stride_n):
        end = start + stance_n
        g[start:end] = np.linspace(0.01, 1.0, end - start)
    return g


# ---------------------------------------------------------------
# 1. GCP primary path
# ---------------------------------------------------------------

def test_gcp_primary_matches_known_stride_count():
    """5 s of 1.0-Hz gait at 100 Hz, 60% stance. The synthetic sawtooth
    leaves the trailing partial stride empty, so we expect 4 full
    strides (the 5th would start at 400 ms but only have 100 ms of
    samples remaining)."""
    fs = 100.0
    n = int(5.0 * fs)
    df = pd.DataFrame({"L_GCP": _gcp_sawtooth(n, fs, stride_s=1.0)})
    hs = analyzer._detect_heel_strikes(df, "L", fs)
    assert hs.size == 4, f"expected 4 strides, got {hs.size}: {hs}"
    gaps = np.diff(hs) / fs
    assert np.allclose(gaps, 1.0, atol=0.02)


def test_gcp_primary_ignores_short_event_pulses():
    """Even when a step-pulsing Event exists, GCP primary wins and
    produces stride-spaced output (not step-spaced)."""
    fs = 100.0
    n = int(5.0 * fs)
    # GCP says 1 Hz strides; Event pulses every 0.5 s (per-step)
    gcp = _gcp_sawtooth(n, fs, stride_s=1.0)
    event = np.zeros(n)
    for i in range(0, n, int(fs * 0.5)):
        event[i:i+2] = 1.0  # 20-ms-wide pulse
    df = pd.DataFrame({"L_GCP": gcp, "L_Event": event})
    hs = analyzer._detect_heel_strikes(df, "L", fs)
    gaps = np.diff(hs) / fs
    assert np.allclose(gaps, 1.0, atol=0.05), (
        f"GCP primary should give stride-spaced HS, got gaps={gaps}"
    )


# ---------------------------------------------------------------
# 2. Event fallback (per-step → de-paired to stride)
# ---------------------------------------------------------------

def test_event_fallback_repairs_step_pulses_to_strides():
    """No GCP, only an Event that fires per-step (every 0.5 s).
    Detector should keep every other edge so output is stride-spaced."""
    fs = 100.0
    n = int(5.0 * fs)
    event = np.zeros(n)
    for i in range(0, n, int(fs * 0.5)):
        event[i:i+2] = 1.0
    df = pd.DataFrame({"L_Event": event})
    hs = analyzer._detect_heel_strikes(df, "L", fs)
    gaps = np.diff(hs) / fs
    # Heuristic re-pairing keeps every other edge → ≈ 1.0 s
    assert np.median(gaps) > 0.7, (
        f"Step-pulsing Event should be re-paired to stride spacing, "
        f"got median gap={np.median(gaps):.3f}s"
    )


# ---------------------------------------------------------------
# 3. Stance / swing fraction from GCP active mask
# ---------------------------------------------------------------

def test_stance_fraction_reflects_gcp_active_mask():
    """A 60% stance synthetic signal must yield ~60% stance ratio,
    not the ~48% the old Phase-fallback was giving on real data."""
    fs = 100.0
    n = int(5.0 * fs)
    df = pd.DataFrame({"L_GCP": _gcp_sawtooth(n, fs, stride_s=1.0,
                                              stance_frac=0.6)})
    hs = analyzer._detect_heel_strikes(df, "L", fs)
    valid = np.ones(len(hs) - 1, dtype=bool)
    stance, swing = analyzer._compute_stance_swing(df, "L", hs, valid)
    assert stance, "stance list should not be empty"
    mean_stance = float(np.mean(stance))
    assert 55 < mean_stance < 65, (
        f"expected ~60% stance, got {mean_stance:.1f}%"
    )
    # Stance + swing must always sum to 100 (within float noise)
    for s, sw in zip(stance, swing):
        assert abs((s + sw) - 100.0) < 0.5
