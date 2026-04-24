"""Tests for edge-trim fallback in sync_engine (no analog trigger case)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.services.sync_engine import (
    detect_footfall_events,
    edge_trim_window,
    crop_by_edge_trim,
    find_force_column,
)


def _synth_force(n_steps: int, fs: float = 100.0,
                  stride_s: float = 1.0, stance_s: float = 0.6,
                  peak: float = 500.0) -> tuple[np.ndarray, np.ndarray]:
    """Build a synthetic foot-force signal with `n_steps` rectangular pulses."""
    total_s = 0.5 + n_steps * stride_s + 0.5
    n = int(total_s * fs)
    t = np.arange(n) / fs
    sig = np.zeros(n)
    for i in range(n_steps):
        s = int((0.5 + i * stride_s) * fs)
        e = int((0.5 + i * stride_s + stance_s) * fs)
        sig[s:e] = peak
    return t, sig


def test_find_force_column():
    df = pd.DataFrame({
        "time_s": [0, 0.01, 0.02],
        "L_ActForce_N": [1.0, 2.0, 3.0],
        "R_ActForce_N": [4.0, 5.0, 6.0],
    })
    assert find_force_column(df) == "L_ActForce_N"


def test_find_force_column_fallback_grf():
    df = pd.DataFrame({
        "time": [0, 1],
        "vGRF_left": [0, 1],
    })
    assert find_force_column(df) == "vGRF_left"


def test_find_force_column_none():
    df = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
    assert find_force_column(df) is None


def test_detect_footfall_events_count():
    _, sig = _synth_force(n_steps=10, fs=100.0)
    events = detect_footfall_events(sig, 100.0)
    assert len(events) == 10


def test_detect_footfall_events_refractory():
    # Add a spurious HIGH spike 50 ms after step 1 — should be rejected.
    fs = 100.0
    _, sig = _synth_force(n_steps=5, fs=fs, stride_s=1.0, stance_s=0.5)
    # spike at sample 55 (0.55s) — within refractory after event at 50
    sig[55] = 500.0
    events = detect_footfall_events(sig, fs, min_stride_s=0.3)
    assert len(events) == 5  # spike suppressed


def test_edge_trim_window_basic():
    fs = 100.0
    _, sig = _synth_force(n_steps=10, fs=fs)
    df = pd.DataFrame({"L_ActForce_N": sig})
    win = edge_trim_window(df, fs, n_edge=3)
    assert win is not None
    start, end, total = win
    assert total == 10
    # Step i starts at sample (0.5 + i) * 100 = 50 + 100*i
    # n_edge=3 → keep events 3..6 (4th through 7th, 0-indexed 3..6)
    # So start = event[3] = 350, end = event[-4] = event[6] = 650
    assert start == 350
    assert end == 650


def test_edge_trim_window_too_few_events():
    fs = 100.0
    _, sig = _synth_force(n_steps=5, fs=fs)  # only 5 < 2*3+2 = 8
    df = pd.DataFrame({"L_ActForce_N": sig})
    win = edge_trim_window(df, fs, n_edge=3)
    assert win is None


def test_edge_trim_window_no_force_col():
    fs = 100.0
    df = pd.DataFrame({"time": [0, 1], "junk": [2, 3]})
    assert edge_trim_window(df, fs, n_edge=3) is None


def test_crop_by_edge_trim_basic():
    fs = 100.0
    _, sig = _synth_force(n_steps=10, fs=fs)
    df = pd.DataFrame({"time_s": np.arange(len(sig)) / fs,
                        "L_ActForce_N": sig})
    cropped, window, total = crop_by_edge_trim(df, fs, n_edge=3)
    assert window is not None
    assert total == 10
    # Cropped length should be end - start + 1 = 650 - 350 + 1 = 301
    assert len(cropped) == 301


def test_crop_by_edge_trim_passthrough_when_no_force():
    fs = 100.0
    df = pd.DataFrame({"x": [1, 2, 3]})
    cropped, window, total = crop_by_edge_trim(df, fs, n_edge=3)
    assert window is None
    assert total == 0
    assert len(cropped) == 3


def test_edge_trim_with_custom_n_edge():
    fs = 100.0
    _, sig = _synth_force(n_steps=15, fs=fs)
    df = pd.DataFrame({"L_ActForce_N": sig})
    # n_edge=5 → keep events 5..9
    win = edge_trim_window(df, fs, n_edge=5)
    assert win is not None
    start, end, total = win
    assert total == 15
    # events at 50, 150, 250, ..., 1450. n_edge=5 → start=event[5]=550,
    # end=event[-6]=event[9]=950
    assert start == 550
    assert end == 950
