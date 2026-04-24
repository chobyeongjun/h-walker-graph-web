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


def resample_column(df: pd.DataFrame, col: str,
                    hs: np.ndarray, valid: np.ndarray,
                    n_points: int = 101) -> tuple[np.ndarray, np.ndarray] | None:
    """Resample a generic column into per-stride profiles (n_strides x n_points).

    Used for any kinematic / kinetic signal that the analyzer doesn't
    already produce profiles for (joint angles, acceleration, etc.).

    Returns (mean(axis=0), std(axis=0)) or None if no valid strides.
    """
    if col not in df.columns or len(hs) < 2:
        return None
    arr = df[col].to_numpy(dtype=float)
    profiles: list[np.ndarray] = []
    n_strides = len(valid) if valid is not None else len(hs) - 1
    for i in range(n_strides):
        if valid is not None and not valid[i]:
            continue
        if i + 1 >= len(hs):
            break
        chunk = arr[hs[i]: hs[i + 1]]
        valid_chunk = chunk[np.isfinite(chunk)]
        if len(valid_chunk) < 10:
            continue
        # NaN interpolation
        if np.any(np.isnan(chunk)):
            nan_mask = np.isnan(chunk)
            valid_idx = np.where(~nan_mask)[0]
            if len(valid_idx) >= 2:
                chunk = chunk.copy()
                chunk[nan_mask] = np.interp(
                    np.where(nan_mask)[0], valid_idx, chunk[valid_idx])
            else:
                continue
        x_orig = np.linspace(0, 100, len(chunk))
        resampled = np.interp(np.linspace(0, 100, n_points), x_orig, chunk)
        profiles.append(resampled)
    if not profiles:
        return None
    mat = np.vstack(profiles)
    return mat.mean(axis=0), mat.std(axis=0)


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
    """ROM (range of motion) per stride, per IMU channel.

    H-Walker wears one IMU per side, on the SHANK (lower leg). Pitch
    is the sagittal-plane angle. Thigh ROM is NOT measured — earlier
    versions of this function mislabeled R_Pitch as "thigh", which is
    wrong (R_Pitch is the right *shank*). We now name the columns
    after the actual CSV column they came from.
    """
    ls = res.left_stride
    rs = res.right_stride

    candidates: list[tuple[str, str, "AnalysisResult"]] = [
        ("L_Pitch (shank, sag)", "L_Pitch", ls),
        ("R_Pitch (shank, sag)", "R_Pitch", rs),
        # Roll planes if the firmware exposes them — useful when a
        # frontal-plane IMU is added.
        ("L_Roll (shank, fro)",  "L_Roll",  ls),
        ("R_Roll (shank, fro)",  "R_Roll",  rs),
    ]
    series: list[tuple[str, np.ndarray]] = []
    for label, col, side_res in candidates:
        if col not in df.columns:
            continue
        arr = _rom_per_stride(df, col, side_res.hs_indices, side_res.valid_mask)
        if len(arr):
            series.append((label, arr))

    if not series:
        return {
            "label": "ROM per stride · per joint",
            "cols": ["stride_#"],
            "rows": [],
            "summary": {"mean": []},
            "meta": {"n_strides": 0, "channels": []},
        }

    n = max(len(arr) for _, arr in series)
    cols = ["stride_#"] + [f"{label} (°)" for label, _ in series]
    rows = []
    for i in range(n):
        row = [str(i + 1)]
        for _, arr in series:
            row.append(f"{arr[i]:.1f}" if i < len(arr) else "—")
        rows.append(row)
    summary = [_fmt_mean_std(arr, digits=1) for _, arr in series]

    return {
        "label": "ROM per stride · per joint (shank-mounted IMUs)",
        "cols": cols,
        "rows": _truncate_rows(rows, n_max_rows),
        "summary": {"mean": summary},
        "meta": {
            "n_strides": int(n),
            "channels": [label for label, _ in series],
            "note": "H-Walker IMUs are mounted on the shank only — thigh ROM is not measured.",
        },
    }


def cadence(df: pd.DataFrame, res: AnalysisResult,
            **_: Any) -> dict[str, Any]:
    """Average cadence (steps/min) — a single scalar summary.

    Cadence is a whole-trial parameter, not a per-window time-series. The
    correct reportable value is the grand mean across strides for each side
    plus a combined value. For on-the-fly fatigue inspection use the
    `fatigue_index` metric or ask the LLM for a `stride_time_trend` graph.
    """
    ls, rs = res.left_stride, res.right_stride
    combined = 0.0
    if ls.cadence and rs.cadence:
        combined = (ls.cadence + rs.cadence) / 2.0
    elif ls.cadence:
        combined = ls.cadence
    elif rs.cadence:
        combined = rs.cadence

    rows = [[
        f"{ls.cadence:.1f}" if ls.cadence else "—",
        f"{rs.cadence:.1f}" if rs.cadence else "—",
        f"{combined:.1f}" if combined else "—",
    ]]

    # NB: both ls.cadence and rs.cadence are *whole-body* cadence
    # estimates (steps/min) derived from each side's own HS series. They
    # should be ≈equal for symmetric gait — a large L/R disagreement
    # hints at dropped heel strikes on one side. Combined = average of
    # the two estimates (not a sum).
    return {
        "label": "Cadence (steps/min · whole-trial avg)",
        "cols": ["from L HS (spm)", "from R HS (spm)", "Combined (spm)"],
        "rows": rows,
        "summary": {"mean": [f"{combined:.1f} spm"]},
        "meta": {
            "n_strides_L": int(ls.n_strides),
            "n_strides_R": int(rs.n_strides),
            "stride_time_mean_L": float(ls.stride_time_mean),
            "stride_time_mean_R": float(rs.stride_time_mean),
        },
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


def stride_length(df: pd.DataFrame, res: AnalysisResult,
                  **_: Any) -> dict[str, Any]:
    """Average stride length (m) via ZUPT — a single scalar summary.

    Like cadence, stride length is a whole-trial parameter. We report
    L mean±SD, R mean±SD, and the asymmetry index between them. Per-stride
    series are available via `per_stride` or `stride_time_trend` graph if
    the user explicitly wants to see intra-trial variability.
    """
    ls, rs = res.left_stride, res.right_stride
    L = ls.stride_lengths[np.isfinite(ls.stride_lengths)]
    R = rs.stride_lengths[np.isfinite(rs.stride_lengths)]

    l_mean = float(np.mean(L)) if len(L) else float("nan")
    r_mean = float(np.mean(R)) if len(R) else float("nan")
    asym = _asym_idx(l_mean, r_mean) if np.isfinite(l_mean) and np.isfinite(r_mean) else float("nan")

    rows = [[
        _fmt_mean_std(L, digits=3),
        _fmt_mean_std(R, digits=3),
        f"{asym:.1f}" if np.isfinite(asym) else "—",
    ]]

    return {
        "label": "Stride length (m, ZUPT · whole-trial avg)",
        "cols": ["L (m)", "R (m)", "asym (%)"],
        "rows": rows,
        "summary": {"mean": [
            _fmt_mean_std(L, digits=3),
            _fmt_mean_std(R, digits=3),
            f"{asym:.1f}%" if np.isfinite(asym) else "—",
        ]},
        "meta": {
            "n_strides_L": int(len(L)),
            "n_strides_R": int(len(R)),
        },
    }


def stance_time(df: pd.DataFrame, res: AnalysisResult,
                n_max_rows: int = 30) -> dict[str, Any]:
    """Per-stride stance-phase duration (s) = stride_time × stance%."""
    ls, rs = res.left_stride, res.right_stride
    n = min(len(ls.stride_times), len(rs.stride_times))

    l_st = ls.stride_times[:n] * (ls.stance_pct_mean / 100.0) if ls.stance_pct_mean else np.array([])
    r_st = rs.stride_times[:n] * (rs.stance_pct_mean / 100.0) if rs.stance_pct_mean else np.array([])

    rows = []
    for i in range(n):
        l_val = f"{l_st[i]:.3f}" if i < len(l_st) else "—"
        r_val = f"{r_st[i]:.3f}" if i < len(r_st) else "—"
        rows.append([str(i + 1), l_val, r_val])

    return {
        "label": "Stance time (s)",
        "cols": ["stride_#", "L stance (s)", "R stance (s)"],
        "rows": _truncate_rows(rows, n_max_rows),
        "summary": {"mean": [
            _fmt_mean_std(l_st, digits=3),
            _fmt_mean_std(r_st, digits=3),
        ]},
        "meta": {
            "n_strides": int(n),
            "L_stance_pct": ls.stance_pct_mean,
            "R_stance_pct": rs.stance_pct_mean,
        },
    }


def swing_time(df: pd.DataFrame, res: AnalysisResult,
               n_max_rows: int = 30) -> dict[str, Any]:
    """Per-stride swing-phase duration (s) = stride_time × swing%."""
    ls, rs = res.left_stride, res.right_stride
    n = min(len(ls.stride_times), len(rs.stride_times))

    l_sw = ls.stride_times[:n] * (ls.swing_pct_mean / 100.0) if ls.swing_pct_mean else np.array([])
    r_sw = rs.stride_times[:n] * (rs.swing_pct_mean / 100.0) if rs.swing_pct_mean else np.array([])

    rows = []
    for i in range(n):
        l_val = f"{l_sw[i]:.3f}" if i < len(l_sw) else "—"
        r_val = f"{r_sw[i]:.3f}" if i < len(r_sw) else "—"
        rows.append([str(i + 1), l_val, r_val])

    return {
        "label": "Swing time (s)",
        "cols": ["stride_#", "L swing (s)", "R swing (s)"],
        "rows": _truncate_rows(rows, n_max_rows),
        "summary": {"mean": [
            _fmt_mean_std(l_sw, digits=3),
            _fmt_mean_std(r_sw, digits=3),
        ]},
        "meta": {"n_strides": int(n)},
    }


def fatigue_index(df: pd.DataFrame, res: AnalysisResult,
                  **_kwargs) -> dict[str, Any]:
    """Fatigue = % change in stride time between first and last 10% of strides."""
    rows = [
        ["L", f"{res.left_fatigue:+.2f}%",
         "increasing (slower)" if res.left_fatigue > 2 else
         "stable" if abs(res.left_fatigue) <= 2 else
         "decreasing (faster)"],
        ["R", f"{res.right_fatigue:+.2f}%",
         "increasing (slower)" if res.right_fatigue > 2 else
         "stable" if abs(res.right_fatigue) <= 2 else
         "decreasing (faster)"],
    ]
    return {
        "label": "Fatigue index (stride time: first 10% vs last 10%)",
        "cols": ["side", "Δ%", "interpretation"],
        "rows": rows,
        "summary": {"mean": [
            f"{res.left_fatigue:+.2f}% / {res.right_fatigue:+.2f}%",
            "—",
        ]},
        "meta": {
            "L_fatigue_pct": res.left_fatigue,
            "R_fatigue_pct": res.right_fatigue,
        },
    }


def symmetry_summary(df: pd.DataFrame, res: AnalysisResult,
                     **_kwargs) -> dict[str, Any]:
    """Six-axis symmetry summary (0% = perfect, higher = more asymmetric)."""
    rows = [
        ["stride time",   f"{res.stride_time_symmetry:.2f}"],
        ["stride length", f"{res.stride_length_symmetry:.2f}" if res.stride_length_symmetry >= 0 else "—"],
        ["stance %",      f"{res.stance_symmetry:.2f}" if res.stance_symmetry >= 0 else "—"],
        ["force RMSE",    f"{res.force_symmetry:.2f}" if res.force_symmetry > 0 else "—"],
    ]
    # Peak-force asymmetry (derived)
    lft, rft = res.left_force_tracking, res.right_force_tracking
    lfp, rfp = res.left_force_profile, res.right_force_profile
    if lfp.mean is not None and rfp.mean is not None:
        peak_l = float(np.max(lfp.mean))
        peak_r = float(np.max(rfp.mean))
        rows.append(["peak GRF", f"{_asym_idx(peak_l, peak_r):.2f}"])

    values = [float(r[1].replace("%", "")) for r in rows if r[1] != "—"]
    return {
        "label": "Symmetry summary (% asymmetry · 0 = perfect)",
        "cols": ["metric", "Δ (%)"],
        "rows": rows,
        "summary": {"mean": [
            f"{np.mean(values):.2f}" if values else "—",
            "",
        ]},
        "meta": {
            "avg_asymmetry": float(np.mean(values)) if values else 0.0,
            "max_asymmetry_metric": rows[int(np.argmax([
                float(r[1].replace("%", "")) if r[1] != "—" else -1 for r in rows
            ]))][0] if values else None,
        },
    }


# ============================================================
# Dispatcher
# ============================================================


METRIC_REGISTRY = {
    "per_stride":        per_stride,
    "impulse":           impulse,
    "loading_rate":      loading_rate,
    "rom":               rom,
    "cadence":           cadence,
    "target_dev":        target_dev,
    # Phase 0: motion-data metrics
    "stride_length":     stride_length,
    "stance_time":       stance_time,
    "swing_time":        swing_time,
    "fatigue_index":     fatigue_index,
    "symmetry_summary":  symmetry_summary,
}


def compute(metric: str, df: pd.DataFrame, res: AnalysisResult,
            **kwargs) -> dict[str, Any]:
    if metric not in METRIC_REGISTRY:
        raise ValueError(f"Unknown metric '{metric}'. Known: {sorted(METRIC_REGISTRY.keys())}")
    return METRIC_REGISTRY[metric](df, res, **kwargs)
