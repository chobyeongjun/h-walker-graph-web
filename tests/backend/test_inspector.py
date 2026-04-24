"""Tests for the per-sync inspector — sync cycle detection + window slicing.

User-stated definition (CLAUDE.md):
    "디지털/아날로그 sync 신호의 한 사이클 — falling edge 후 rising
     edge 부터 다시 falling edge 까지가 1 sync."

Each falling edge of the Sync column starts a cycle and the next falling
edge ends it. A trailing falling edge with no successor is dropped.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backend.routers import inspector


# ---------------------------------------------------------------
# Synthetic sync waveforms
# ---------------------------------------------------------------

def _square_wave(n: int, fs: float, period_s: float, duty: float = 0.5) -> np.ndarray:
    """Square wave: high for `duty * period`, low for the rest, repeating."""
    t = np.arange(n) / fs
    phase = (t % period_s) / period_s
    return (phase < duty).astype(float)


def _time_axis(n: int, fs: float) -> np.ndarray:
    return np.arange(n) / fs


# ---------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------

def test_detect_full_cycles():
    """3.5 s of a 1 Hz square wave (starts HIGH at t=0) at 100 Hz has
    falling edges at 0.5, 1.5, 2.5 — three falling edges, so two
    complete falling→falling cycles."""
    fs = 100.0
    n = int(3.5 * fs)
    t = _time_axis(n, fs)
    sync = _square_wave(n, fs, period_s=1.0)
    cycles = inspector._detect_sync_cycles(sync, t)
    assert len(cycles) == 2, f"expected 2 cycles, got {len(cycles)}: {cycles}"
    # Each cycle should be ≈ 1 s long (within one sample of 0.01 s tolerance)
    for s, e in cycles:
        assert abs((e - s) - 1.0) < 0.02


def test_detect_no_cycles_when_constant():
    """All-zero or all-one sync → no cycles."""
    fs = 100.0
    t = _time_axis(200, fs)
    assert inspector._detect_sync_cycles(np.zeros(200), t) == []
    assert inspector._detect_sync_cycles(np.ones(200), t) == []


def test_detect_no_cycles_when_no_falling_edge_pair():
    """A single falling edge followed by no further falling edge yields
    nothing — we need a closing edge to call it a cycle."""
    fs = 100.0
    t = _time_axis(200, fs)
    sync = np.concatenate([np.ones(50), np.zeros(150)])  # 1→0 once, then nothing
    cycles = inspector._detect_sync_cycles(sync, t)
    assert cycles == []


def test_detect_handles_analog_signal():
    """Analog (non-binary) sync — threshold at midpoint, treat as
    boolean. A clean sine wave should produce one cycle per period."""
    fs = 1000.0
    n = 5000  # 5 s
    t = _time_axis(n, fs)
    # 2 Hz sine → 10 cycles in 5 s. We expect 9 fully-bracketed cycles
    # because the first falling edge occurs at t≈0.25 s and we need a
    # *pair* of falling edges to bracket each.
    sync = np.sin(2 * np.pi * 2 * t)
    cycles = inspector._detect_sync_cycles(sync, t)
    assert 8 <= len(cycles) <= 10
    for s, e in cycles:
        assert abs((e - s) - 0.5) < 0.01  # 2 Hz → 0.5 s period


# ---------------------------------------------------------------
# /window endpoint downsampling
# ---------------------------------------------------------------

def test_downsample_indices_below_max_returns_full_range():
    out = inspector._downsample_indices(100, max_points=4000)
    assert np.array_equal(out, np.arange(100))


def test_downsample_indices_above_max_strides_evenly():
    out = inspector._downsample_indices(10000, max_points=1000)
    assert len(out) == 1000
    assert out[0] == 0
    assert out[-1] == 9999
    # Roughly even stride
    diffs = np.diff(out)
    assert diffs.max() - diffs.min() <= 1


# ---------------------------------------------------------------
# End-to-end through the /syncs endpoint helper
# ---------------------------------------------------------------

@pytest.fixture
def sync_csv(monkeypatch):
    """Build a synthetic DataFrame and patch inspector._read_df so the
    endpoint helpers don't need the datasets router (which pulls in
    python-multipart at import time)."""
    fs = 100.0
    n = 350  # 3.5 s
    t = _time_axis(n, fs)
    df = pd.DataFrame({
        "Time_s": t,
        "Sync": _square_wave(n, fs, period_s=1.0),
        "L_ActForce_N": np.sin(2 * np.pi * 1.0 * t) * 30 + 50,
        "L_Pitch":      np.cos(2 * np.pi * 1.0 * t) * 10,
    })
    monkeypatch.setattr(inspector, "_read_df", lambda ds_id: df)
    return "ds_test"


def test_list_syncs_endpoint_returns_two_cycles(sync_csv):
    """3.5 s of 1 Hz square wave → 3 falling edges → 2 full cycles."""
    resp = inspector.list_syncs(sync_csv)
    assert resp.column == "Sync"
    assert len(resp.cycles) == 2
    assert resp.cycles[0].index == 0
    assert resp.cycles[1].index == 1
    for c in resp.cycles:
        assert c.duration > 0.5


def test_fetch_window_slices_and_downsamples(sync_csv):
    req = inspector.WindowRequest(
        columns=["L_ActForce_N", "L_Pitch", "missing_col"],
        t_start=0.5, t_end=2.5,
        max_points=80,
    )
    resp = inspector.fetch_window(sync_csv, req)
    assert "missing_col" in resp.columns_missing
    names = {s.name for s in resp.series}
    assert names == {"L_ActForce_N", "L_Pitch"}
    assert len(resp.t) == resp.n_returned
    assert resp.n_returned <= 80
    assert resp.n_total >= resp.n_returned
    # All series share the same length as the time axis
    for s in resp.series:
        assert len(s.y) == len(resp.t)


def test_fetch_window_rejects_inverted_range(sync_csv):
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        inspector.fetch_window(
            sync_csv,
            inspector.WindowRequest(columns=["L_Pitch"], t_start=2.0, t_end=1.0),
        )
