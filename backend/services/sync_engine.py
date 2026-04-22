"""
Cross-source sync engine — align Robot × MoCap × Force-plate data
==================================================================

Real-world experiments use a trigger box that broadcasts an analog pulse
to every acquisition system (Vicon, force-plate DAQ, the H-Walker robot
controller, …). Each system records the pulse on its own channel (A7,
TrigIn, SyncPulse, analog_sync, …) and its own sample rate.

The pulse protocol the user described:

    HIGH ─────────────── HIGH
              │   │
              │   │  ← first pulse  → MoCap 녹화 시작
              └───┘
    ⋯⋯⋯⋯⋯⋯⋯ (experiment) ⋯⋯⋯⋯⋯⋯⋯
              │   │
              │   │  ← second pulse → MoCap 녹화 종료
              └───┘
    HIGH ─────────────── HIGH

So: baseline HIGH, brief LOW dip, back to HIGH. Falling edge of the first
pulse = t=0 for the experiment. Falling edge of the last pulse = t=T.

This module:
  • `detect_sync_pulses(sig, fs)`  — find all HIGH→LOW→HIGH pulses
  • `sync_window(sig, fs)`         — first & last falling edges
  • `find_sync_column(df)`         — guess which column is the trigger
  • `crop_to_sync(df, fs, col)`    — slice DataFrame to the sync window
  • `resample_df(df, fs_in, fs_out)` — linear-interp every column onto a
                                       uniform fs_out grid
  • `align_datasets(items)`        — batch: crop each to its A7, upsample
                                       every one to a common target_hz
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


# ─── column-name heuristics ────────────────────────────────────────────
# Ordered: more specific → more generic. First match wins.
_SYNC_COL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^a[_ ]?7$", re.I),                   # A7, a_7
    re.compile(r"^(analog[_ ]?)?sync([_ ]?pulse)?$", re.I),
    re.compile(r"^trig(ger)?([_ ]?in)?$", re.I),
    re.compile(r"^sync$", re.I),
]


def find_sync_column(df: pd.DataFrame) -> Optional[str]:
    """Return the name of the column that looks like an analog sync pulse,
    or None if nothing plausible is found."""
    for c in df.columns:
        for pat in _SYNC_COL_PATTERNS:
            if pat.match(c.strip()):
                return c
    return None


# ─── pulse detection ───────────────────────────────────────────────────

@dataclass
class Pulse:
    fall_idx: int    # sample index where signal crossed HIGH→LOW
    rise_idx: int    # sample index where signal crossed LOW→HIGH
    fall_t: float    # seconds from start of recording
    rise_t: float

    @property
    def width_s(self) -> float:
        return self.rise_t - self.fall_t


def detect_sync_pulses(
    signal: np.ndarray,
    sample_rate: float,
    min_pulse_width_s: float = 0.005,
    max_pulse_width_s: float = 2.0,
    threshold_rel: float = 0.5,
) -> list[Pulse]:
    """Find all HIGH→LOW→HIGH pulses in `signal`.

    Parameters
    ----------
    signal : 1-D ndarray
        Analog sync channel samples.
    sample_rate : float
        Hz, needed to convert sample counts to seconds.
    min_pulse_width_s / max_pulse_width_s : float
        Reject pulses too brief (spikes) or too long (signal dropout).
    threshold_rel : float in (0,1)
        Where to place the LOW-detection line, as a fraction of the
        peak-to-peak range above the minimum.

    Returns
    -------
    list[Pulse], in chronological order.
    """
    sig = np.asarray(signal, dtype=float).ravel()
    if sig.size < 3:
        return []

    lo = float(np.nanmin(sig))
    hi = float(np.nanmax(sig))
    if hi - lo < 1e-9:
        return []      # flat signal — no pulses
    thr = lo + threshold_rel * (hi - lo)

    is_low = sig < thr
    # Edge detection via diff
    edges = np.diff(is_low.astype(np.int8))
    fall_idx = np.flatnonzero(edges == 1) + 1   # sample that first went low
    rise_idx = np.flatnonzero(edges == -1) + 1  # sample that first went back high

    min_w = max(1, int(round(min_pulse_width_s * sample_rate)))
    max_w = max(min_w, int(round(max_pulse_width_s * sample_rate)))

    out: list[Pulse] = []
    for f in fall_idx:
        rs = rise_idx[rise_idx > f]
        if rs.size == 0:
            continue
        r = int(rs[0])
        w = r - int(f)
        if min_w <= w <= max_w:
            out.append(Pulse(
                fall_idx=int(f),
                rise_idx=r,
                fall_t=int(f) / sample_rate,
                rise_t=r / sample_rate,
            ))
    return out


def sync_window(
    signal: np.ndarray,
    sample_rate: float,
    *,
    use_first_and_last: bool = True,
    min_pulse_width_s: float = 0.005,
    max_pulse_width_s: float = 2.0,
) -> Optional[tuple[int, int]]:
    """Return (start_sample, end_sample) from the first and last pulse.

    Uses the FALLING edge as the boundary marker — that's the moment the
    trigger box says "go" / "stop". A user can override with explicit
    indices via `crop_to_sync(..., manual_window=(s,e))`.
    """
    pulses = detect_sync_pulses(
        signal, sample_rate,
        min_pulse_width_s=min_pulse_width_s,
        max_pulse_width_s=max_pulse_width_s,
    )
    if len(pulses) < 2:
        if len(pulses) == 1 and use_first_and_last:
            # Single pulse — treat as "start" and use the recording end.
            # This is intentionally permissive for trigger-box hardware
            # that only fires once at the start.
            return pulses[0].fall_idx, int(signal.size - 1)
        return None
    return pulses[0].fall_idx, pulses[-1].fall_idx


# ─── cropping + resampling ─────────────────────────────────────────────

def crop_to_sync(
    df: pd.DataFrame,
    sample_rate: float,
    sync_col: Optional[str] = None,
    manual_window: Optional[tuple[int, int]] = None,
) -> tuple[pd.DataFrame, Optional[tuple[int, int]]]:
    """Slice `df` to the sync window.

    Returns (cropped_df, (start_sample, end_sample)). If no window can be
    determined AND no manual_window is given, returns the original
    DataFrame with (None).
    """
    if manual_window is not None:
        s, e = manual_window
        return df.iloc[s:e + 1].reset_index(drop=True), (s, e)

    col = sync_col or find_sync_column(df)
    if col is None or col not in df.columns:
        return df.copy().reset_index(drop=True), None
    win = sync_window(df[col].to_numpy(), sample_rate)
    if win is None:
        return df.copy().reset_index(drop=True), None
    s, e = win
    return df.iloc[s:e + 1].reset_index(drop=True), (s, e)


def resample_df(
    df: pd.DataFrame,
    fs_in: float,
    fs_out: float,
    *,
    time_col: Optional[str] = None,
) -> pd.DataFrame:
    """Resample every numeric column onto a uniform `fs_out` grid via
    linear interpolation.

    - `time_col` is optional. If absent, we assume rows are uniformly
      spaced at fs_in.
    - Non-numeric columns are nearest-neighbor-sampled (categorical /
      event columns preserve their value at each new time step).
    - The output carries a new `time_s` column starting at 0.
    """
    n_in = len(df)
    if n_in == 0:
        return df.copy()
    if fs_in <= 0 or fs_out <= 0:
        raise ValueError(f"sample rates must be positive (got fs_in={fs_in}, fs_out={fs_out})")

    # x_in in seconds
    if time_col and time_col in df.columns:
        x_in = df[time_col].to_numpy(dtype=float)
        # Normalize so x_in[0] = 0
        x_in = x_in - x_in[0]
        duration = x_in[-1]
    else:
        duration = (n_in - 1) / fs_in
        x_in = np.arange(n_in) / fs_in

    n_out = int(round(duration * fs_out)) + 1
    x_out = np.linspace(0.0, duration, n_out)

    out = {"time_s": x_out}
    for col in df.columns:
        if col == time_col:
            continue
        series = df[col]
        if pd.api.types.is_numeric_dtype(series):
            y = series.to_numpy(dtype=float)
            # np.interp treats NaN literally — mask first
            valid = ~np.isnan(y)
            if valid.sum() < 2:
                out[col] = np.full(n_out, np.nan)
            else:
                out[col] = np.interp(x_out, x_in[valid], y[valid])
        else:
            # categorical/event — nearest-neighbor
            idx = np.clip(np.searchsorted(x_in, x_out), 0, n_in - 1)
            out[col] = series.to_numpy()[idx]
    return pd.DataFrame(out)


# ─── high-level batch alignment ────────────────────────────────────────

@dataclass
class AlignInput:
    """One input to align_datasets()."""
    ds_id: str
    df: pd.DataFrame
    sample_rate: float
    source_type: str = "unknown"     # 'robot' | 'mocap' | 'forceplate' | 'unknown'
    sync_col: Optional[str] = None   # auto-detect if None
    manual_window: Optional[tuple[int, int]] = None


@dataclass
class AlignResult:
    ds_id: str
    df_synced: pd.DataFrame
    original_fs: float
    target_fs: float
    window_samples: Optional[tuple[int, int]]
    sync_col_used: Optional[str]
    n_in: int
    n_out: int
    duration_s: float


def align_datasets(
    items: list[AlignInput],
    target_hz: Optional[float] = None,
) -> list[AlignResult]:
    """Crop each input to its A7 window, then resample everyone to
    `target_hz` (or the highest input rate if None).

    The cropped-and-resampled DataFrames share:
      • identical number of rows
      • identical `time_s` axis (starting at 0)
      • identical sampling grid

    making them ready for cross-source comparison / plotting.
    """
    if not items:
        return []

    # 1. Crop each to its own sync window (if found)
    cropped: list[tuple[AlignInput, pd.DataFrame, Optional[tuple[int, int]], Optional[str]]] = []
    for it in items:
        col = it.sync_col or find_sync_column(it.df)
        df_crop, win = crop_to_sync(it.df, it.sample_rate, col, it.manual_window)
        cropped.append((it, df_crop, win, col))

    # 2. Determine target rate
    if target_hz is None:
        target_hz = max(it.sample_rate for it in items)

    # 3. Also determine common duration so every output has the same
    #    length (use the shortest synced duration — we don't want to
    #    extrapolate beyond any dataset's coverage).
    durations = []
    for it, df_crop, _win, _col in cropped:
        n = len(df_crop)
        dur = max(0.0, (n - 1) / it.sample_rate) if n > 1 else 0.0
        durations.append(dur)
    common_dur = min(durations) if durations else 0.0

    # 4. Resample each to target_hz, then clip to common_dur
    results: list[AlignResult] = []
    for it, df_crop, win, col in cropped:
        df_rs = resample_df(df_crop, it.sample_rate, target_hz)
        # Clip to common_dur so rows line up 1:1 across datasets
        n_common = int(round(common_dur * target_hz)) + 1
        df_rs = df_rs.iloc[:n_common].reset_index(drop=True)
        results.append(AlignResult(
            ds_id=it.ds_id,
            df_synced=df_rs,
            original_fs=it.sample_rate,
            target_fs=target_hz,
            window_samples=win,
            sync_col_used=col,
            n_in=len(it.df),
            n_out=len(df_rs),
            duration_s=common_dur,
        ))
    return results
