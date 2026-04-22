"""
Compute metrics — Phase 2A real implementation.

Replaces the mock `computeMetrics.ts` tables with real values derived from
the H-Walker CSV + auto_analyzer `AnalysisResult`.

Each metric returns a payload shape-compatible with the frontend
`ComputeMetric` interface:

    {
        "label":   str,
        "cols":    list[str],
        "rows":    list[list[str]],
        "summary": { "mean": list[str] },
        "meta":    { "n_strides": int, ... }   # extra, tolerated
    }

`n_max_rows` caps table length (default 30). If more strides exist, an
ellipsis row "…" is inserted and the last stride appended.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from tools.auto_analyzer.analyzer import AnalysisResult


# ============================================================
# Helpers
# ============================================================


def _fmt_mean_std(x: np.ndarray, digits: int = 2) -> str:
    arr = x[np.isfinite(x)]
    if len(arr) == 0:
        return "—"
    return f"{np.mean(arr):.{digits}f} ± {np.std(arr, ddof=1) if len(arr) > 1 else 0:.{digits}f}"


def _truncate_rows(rows: list[list[str]], n_max: int = 30) -> list[list[str]]:
    """Keep the first n_max-2 rows, an ellipsis row, then the last row."""
    if len(rows) <= n_max:
        return rows
    width = len(rows[0])
    out = rows[: n_max - 2]
    out.append(["…"] * width)
    out.append(rows[-1])
    return out


def _peak_per_stride(df: pd.DataFrame, col: str,
                     hs: np.ndarray, valid: np.ndarray) -> np.ndarray:
    if col not in df.columns:
        return np.array([])
    arr = df[col].to_numpy(dtype=float)
    out = []
    for i in range(len(valid)):
        if not valid[i] or i + 1 >= len(hs):
            continue
        chunk = arr[hs[i]: hs[i + 1]]
        chunk = chunk[np.isfinite(chunk)]
        out.append(float(np.max(chunk)) if len(chunk) else float("nan"))
    return np.array(out)


def _impulse_per_stride(df: pd.DataFrame, col: str,
                        hs: np.ndarray, valid: np.ndarray, fs: float) -> np.ndarray:
    if col not in df.columns or fs <= 0:
        return np.array([])
    arr = df[col].to_numpy(dtype=float)
    dt = 1.0 / fs
    out = []
    for i in range(len(valid)):
        if not valid[i] or i + 1 >= len(hs):
            continue
        chunk = arr[hs[i]: hs[i + 1]]
        chunk = chunk[np.isfinite(chunk)]
        # Simple rectangular integration; only positive force contributes
        chunk = np.clip(chunk, 0.0, None)
        out.append(float(np.sum(chunk) * dt))
    return np.array(out)


def _loading_rate_per_stride(df: pd.DataFrame, col: str,
                             hs: np.ndarray, valid: np.ndarray,
                             fs: float, window_ms: float = 50.0,
                             body_weight_n: float = 700.0) -> np.ndarray:
    """Initial loading rate (BW/s). Slope over first `window_ms` of the stride
    after heel-strike. BW defaults to 700 N if not given (fallback only)."""
    if col not in df.columns or fs <= 0:
        return np.array([])
    arr = df[col].to_numpy(dtype=float)
    window = max(2, int(round(window_ms / 1000.0 * fs)))
    out = []
    for i in range(len(valid)):
        if not valid[i] or i + 1 >= len(hs):
            continue
        s = hs[i]
        e = min(s + window, hs[i + 1])
        chunk = arr[s:e]
        chunk = chunk[np.isfinite(chunk)]
        if len(chunk) < 2:
            continue
        peak = float(np.max(chunk))
        initial = float(chunk[0])
        dt = (len(chunk) - 1) / fs
        if dt <= 0:
            continue
        bw_per_s = (peak - initial) / body_weight_n / dt
        out.append(bw_per_s)
    return np.array(out)


def _rom_per_stride(df: pd.DataFrame, col: str,
                    hs: np.ndarray, valid: np.ndarray) -> np.ndarray:
    if col not in df.columns:
        return np.array([])
    arr = df[col].to_numpy(dtype=float)
    out = []
    for i in range(len(valid)):
        if not valid[i] or i + 1 >= len(hs):
            continue
        chunk = arr[hs[i]: hs[i + 1]]
        chunk = chunk[np.isfinite(chunk)]
        if len(chunk) < 2:
            continue
        out.append(float(np.max(chunk) - np.min(chunk)))
    return np.array(out)


def _asym_idx(l: float, r: float) -> float:
    if not (np.isfinite(l) and np.isfinite(r)):
        return float("nan")
    denom = (l + r) / 2.0
    if abs(denom) < 1e-12:
        return 0.0
    return abs(l - r) / abs(denom) * 100.0


# ============================================================
# Metric computations
# ============================================================


def per_stride(df: pd.DataFrame, res: AnalysisResult,
               n_max_rows: int = 30) -> dict[str, Any]:
    """Per-stride table: stride#, peak_L, peak_R, stride_T, asym_idx."""
    ls, rs = res.left_stride, res.right_stride
    # Use the *left* hs indices as the timeline reference (matching on index is
    # approximate — L/R strides aren't perfectly aligned, but this matches the
    # mockup's stride-index layout).
    n = min(
        len(ls.stride_times),
        len(rs.stride_times),
        ls.valid_mask.sum() if len(ls.valid_mask) else 0,
        rs.valid_mask.sum() if len(rs.valid_mask) else 0,
    )

    peaks_l = _peak_per_stride(df, "L_ActForce_N", ls.hs_indices, ls.valid_mask)
    peaks_r = _peak_per_stride(df, "R_ActForce_N", rs.hs_indices, rs.valid_mask)

    n = min(n, len(peaks_l), len(peaks_r), len(ls.stride_times), len(rs.stride_times))

    rows = []
    asym_vals = []
    for i in range(n):
        asym = _asym_idx(peaks_l[i], peaks_r[i])
        asym_vals.append(asym)
        rows.append([
            str(i + 1),
            f"{peaks_l[i]:.1f}",
            f"{peaks_r[i]:.1f}",
            f"{ls.stride_times[i]:.2f}",
            f"{asym:.1f}",
        ])

    summary_mean = [
        _fmt_mean_std(peaks_l[:n], digits=1),
        _fmt_mean_std(peaks_r[:n], digits=1),
        _fmt_mean_std(ls.stride_times[:n], digits=2),
        _fmt_mean_std(np.array(asym_vals), digits=1),
    ]

    return {
        "label": "Per-stride metrics",
        "cols": ["stride_#", "peak_L (N)", "peak_R (N)", "stride_T (s)", "asym_idx (%)"],
        "rows": _truncate_rows(rows, n_max_rows),
        "summary": {"mean": summary_mean},
        "meta": {"n_strides": int(n)},
    }


def impulse(df: pd.DataFrame, res: AnalysisResult,
            n_max_rows: int = 30) -> dict[str, Any]:
    ls, rs = res.left_stride, res.right_stride
    fs = res.sample_rate
    imp_l = _impulse_per_stride(df, "L_ActForce_N", ls.hs_indices, ls.valid_mask, fs)
    imp_r = _impulse_per_stride(df, "R_ActForce_N", rs.hs_indices, rs.valid_mask, fs)
    n = min(len(imp_l), len(imp_r))

    rows = []
    delta_vals = []
    for i in range(n):
        d = _asym_idx(imp_l[i], imp_r[i])
        delta_vals.append(d)
        rows.append([str(i + 1), f"{imp_l[i]:.1f}", f"{imp_r[i]:.1f}", f"{d:.1f}"])

    return {
        "label": "Impulse (N·s)",
        "cols": ["stride_#", "L impulse", "R impulse", "Δ (%)"],
        "rows": _truncate_rows(rows, n_max_rows),
        "summary": {"mean": [
            _fmt_mean_std(imp_l, digits=1),
            _fmt_mean_std(imp_r, digits=1),
            _fmt_mean_std(np.array(delta_vals), digits=1),
        ]},
        "meta": {"n_strides": int(n)},
    }


def loading_rate(df: pd.DataFrame, res: AnalysisResult,
                 body_weight_n: float = 700.0,
                 n_max_rows: int = 30) -> dict[str, Any]:
    ls, rs = res.left_stride, res.right_stride
    fs = res.sample_rate
    lr_l = _loading_rate_per_stride(df, "L_ActForce_N", ls.hs_indices, ls.valid_mask,
                                    fs, body_weight_n=body_weight_n)
    lr_r = _loading_rate_per_stride(df, "R_ActForce_N", rs.hs_indices, rs.valid_mask,
                                    fs, body_weight_n=body_weight_n)
    n = min(len(lr_l), len(lr_r))

    rows, deltas = [], []
    for i in range(n):
        d = lr_l[i] - lr_r[i]
        deltas.append(d)
        rows.append([str(i + 1), f"{lr_l[i]:.1f}", f"{lr_r[i]:.1f}", f"{d:+.1f}"])

    return {
        "label": f"Loading rate (BW/s, 0–50ms, BW≈{body_weight_n:.0f}N)",
        "cols": ["stride_#", "L rate", "R rate", "Δ"],
        "rows": _truncate_rows(rows, n_max_rows),
        "summary": {"mean": [
            _fmt_mean_std(lr_l, digits=1),
            _fmt_mean_std(lr_r, digits=1),
            _fmt_mean_std(np.array(deltas), digits=1),
        ]},
        "meta": {"n_strides": int(n), "body_weight_n": body_weight_n},
    }


def rom(df: pd.DataFrame, res: AnalysisResult,
        n_max_rows: int = 30) -> dict[str, Any]:
    """ROM per stride. Uses Pitch columns (shank) if present."""
    ls = res.left_stride
    # Prefer L_Pitch (shank) and R_Pitch as "thigh" proxy when no explicit thigh column
    shank_col = "L_Pitch" if "L_Pitch" in df.columns else None
    thigh_col = "R_Pitch" if "R_Pitch" in df.columns else None

    shank = _rom_per_stride(df, shank_col, ls.hs_indices, ls.valid_mask) if shank_col else np.array([])
    thigh = _rom_per_stride(df, thigh_col, ls.hs_indices, ls.valid_mask) if thigh_col else np.array([])
    n = min(len(shank), len(thigh)) if (len(shank) and len(thigh)) else max(len(shank), len(thigh))

    cols = ["stride"]
    if len(shank):
        cols.append(f"{shank_col or 'shank'} ROM (°)")
    if len(thigh):
        cols.append(f"{thigh_col or 'thigh'} ROM (°)")

    rows = []
    for i in range(n):
        row = [str(i + 1)]
        if len(shank):
            row.append(f"{shank[i]:.1f}" if i < len(shank) else "—")
        if len(thigh):
            row.append(f"{thigh[i]:.1f}" if i < len(thigh) else "—")
        rows.append(row)

    summary = []
    if len(shank):
        summary.append(_fmt_mean_std(shank, digits=1))
    if len(thigh):
        summary.append(_fmt_mean_std(thigh, digits=1))

    return {
        "label": "ROM per stride",
        "cols": cols,
        "rows": _truncate_rows(rows, n_max_rows),
        "summary": {"mean": summary},
        "meta": {"n_strides": int(n), "shank_col": shank_col, "thigh_col": thigh_col},
    }


def cadence(df: pd.DataFrame, res: AnalysisResult,
            window_s: float = 4.0) -> dict[str, Any]:
    """Cadence per rolling window (average of L + R steps)."""
    fs = res.sample_rate
    total_dur = res.duration_s
    ls, rs = res.left_stride, res.right_stride

    n_windows = int(total_dur // window_s)
    rows = []
    cadences = []
    for w in range(n_windows):
        t0, t1 = w * window_s, (w + 1) * window_s
        i0, i1 = int(t0 * fs), int(t1 * fs)
        steps = 0
        if len(ls.hs_indices):
            steps += int(np.sum((ls.hs_indices >= i0) & (ls.hs_indices < i1)))
        if len(rs.hs_indices):
            steps += int(np.sum((rs.hs_indices >= i0) & (rs.hs_indices < i1)))
        spm = steps / window_s * 60.0
        cadences.append(spm)
        rows.append([f"{t0:.0f}-{t1:.0f}s", f"{spm:.0f}"])

    return {
        "label": "Cadence",
        "cols": ["window", "spm"],
        "rows": rows or [["0-0s", f"{(ls.cadence + rs.cadence) / 2:.0f}"]],
        "summary": {"mean": [_fmt_mean_std(np.array(cadences) if cadences else
                                            np.array([(ls.cadence + rs.cadence) / 2]),
                                            digits=0)]},
        "meta": {"window_s": window_s, "n_windows": n_windows},
    }


def target_dev(df: pd.DataFrame, res: AnalysisResult,
               n_max_rows: int = 30) -> dict[str, Any]:
    """Force tracking deviation per stride."""
    lft = res.left_force_tracking
    rft = res.right_force_tracking
    rmses_l = lft.rmse_per_stride
    rmses_r = rft.rmse_per_stride
    n = min(len(rmses_l), len(rmses_r)) if len(rmses_l) and len(rmses_r) else max(len(rmses_l), len(rmses_r))

    rows = []
    for i in range(n):
        l_val = float(rmses_l[i]) if i < len(rmses_l) else float("nan")
        r_val = float(rmses_r[i]) if i < len(rmses_r) else float("nan")
        pair = [v for v in (l_val, r_val) if np.isfinite(v)]
        rmse_avg = float(np.mean(pair)) if pair else float("nan")
        rows.append([
            f"S{i + 1}",
            f"{rmse_avg:.2f}" if np.isfinite(rmse_avg) else "—",
            "—",
        ])

    return {
        "label": "Target deviation (Des vs Act force)",
        "cols": ["stride", "RMSE (N)", "peak Δ (%)"],
        "rows": _truncate_rows(rows, n_max_rows),
        "summary": {"mean": [
            _fmt_mean_std(np.concatenate([rmses_l, rmses_r]) if len(rmses_l) or len(rmses_r)
                          else np.array([0.0]), digits=2),
            "improving" if len(rmses_l) > 1 and rmses_l[-1] < rmses_l[0] else "stable",
        ]},
        "meta": {"n_strides": int(n), "global_rmse_L": lft.rmse, "global_rmse_R": rft.rmse},
    }


# ============================================================
# Dispatcher
# ============================================================


METRIC_REGISTRY = {
    "per_stride": per_stride,
    "impulse": impulse,
    "loading_rate": loading_rate,
    "rom": rom,
    "cadence": cadence,
    "target_dev": target_dev,
}


def compute(metric: str, df: pd.DataFrame, res: AnalysisResult,
            **kwargs) -> dict[str, Any]:
    if metric not in METRIC_REGISTRY:
        raise ValueError(f"Unknown metric '{metric}'. Known: {sorted(METRIC_REGISTRY.keys())}")
    return METRIC_REGISTRY[metric](df, res, **kwargs)
