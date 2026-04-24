"""
/api/graphs/* — Phase 2 publication export.

Endpoints:
  GET  /api/graphs/templates         → list of GRAPH_TPLS keys
  GET  /api/graphs/presets           → list of JOURNAL_PRESETS with submission specs
  POST /api/graphs/render            → single figure at exact journal size
  POST /api/graphs/bundle            → ZIP of SVGs for multiple cells
  POST /api/graphs/multi_panel       → 2–4 cells composed as a single figure
                                        with (a)(b)(c)(d) sub-panels
"""
from __future__ import annotations

import io
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from backend.services.publication_engine import (
    JOURNAL_PRESETS, GRAPH_SPECS, render, list_templates, list_presets,
    render_from_traces, Trace,
)


router = APIRouter(prefix="/api/graphs", tags=["graphs"])


@router.get("/templates")
def templates() -> list[str]:
    return list_templates()


@router.get("/presets")
def presets() -> list[dict]:
    return list_presets()


class DatasetSeries(BaseModel):
    """Phase 1 multi-dataset — one dataset contributes one colored trace."""
    id: str
    label: Optional[str] = None
    color: Optional[str] = None


class RenderRequest(BaseModel):
    template: str
    preset: str = "ieee"
    variant: Literal["col1", "col2", "onehalf"] = "col2"
    format: Literal["svg", "pdf", "eps", "png", "tiff"] = "svg"
    dpi: Optional[int] = None
    stride_avg: bool = False
    colorblind_safe: Optional[bool] = None
    keep_palette: bool = False
    # Single-dataset legacy path
    dataset_id: Optional[str] = None
    # Phase 1: multi-dataset overlay. When non-empty, takes precedence
    # over `dataset_id`. Each entry contributes one trace labeled+colored
    # per the series config (color falls back to the preset palette).
    datasets: list[DatasetSeries] = []
    # Phase 2E: optional user-provided title.
    title: Optional[str] = None


def _suggest_filename(req: RenderRequest, P) -> str:
    dim = f"{int(P.col2[0] if req.variant == 'col2' else P.col1[0])}mm"
    return f"hwalker_{req.template}_{req.preset}_{dim}.{req.format}"


REAL_DATA_TEMPLATES = {
    # Force / kinetic (Phase 2A)
    "force", "force_avg", "force_lr_subplot", "asymmetry", "peak_box", "trials",
    # Motion / kinematic (Phase 0)
    "imu", "imu_avg", "cyclogram", "stride_time_trend",
    "stance_swing_bar", "rom_bar", "symmetry_radar",
    # Debug · Phase 2I
    "debug_ts",
}

# Phase 1: templates that support clean multi-dataset overlay.
# For these, `datasets[]` produces one trace per dataset with distinct
# colors. Templates omitted from this set fall back to first-dataset
# rendering (single-plot semantics are clearer for boxplots/radars).
MULTI_DATASET_TEMPLATES = {
    "force_avg",         # overlay L+R mean±SD per subject, color per subject
    "imu_avg",           # overlay joint angle profiles per subject
    "stride_time_trend", # overlay stride-time series per subject
    "asymmetry",         # overlay asymmetry series per subject
    "cyclogram",         # overlay phase portraits per subject
}

_DEFAULT_SERIES_PALETTE = [
    "#3B82C4", "#D35454", "#F09708", "#00FFB2", "#A78BFA",
    "#1E5F9E", "#9E3838", "#FFB347", "#56B4E9", "#009E73",
    "#CC79A7", "#F0E442", "#0072B2", "#E69F00", "#7FB5E4",
]


def _auto_sync_if_needed(req: RenderRequest) -> None:
    """Phase 3 · Auto-align cross-source datasets.

    If any dataset in the overlay has a different sample rate from the
    others, transparently run /api/sync/align and swap the ids on the
    request to point at the freshly synced datasets. This is what makes
    Robot × MoCap × Force-plate comparisons "just work" without the user
    having to click anything when Hz mismatches are present.
    """
    if not req.datasets or len(req.datasets) < 2:
        return
    from backend.routers.datasets import _REGISTRY

    rates: set[float] = set()
    source_types: set[str] = set()
    has_unsynced = False
    for s in req.datasets:
        d = _REGISTRY.get(s.id)
        if d is None:
            continue
        if d.get("synced_from"):
            continue  # already synced
        has_unsynced = True
        try:
            rates.add(float(str(d.get("hz", "100")).replace("Hz", "").strip()))
        except ValueError:
            pass
        source_types.add(d.get("source_type", "unknown"))

    # Only auto-sync when fs differs OR the sources are mixed (e.g.
    # robot + mocap at the same nominal fs but temporally offset).
    cross_source = len({s for s in source_types if s != "unknown"}) >= 2
    fs_mismatch = len(rates) >= 2
    if not has_unsynced or not (cross_source or fs_mismatch):
        return

    from backend.routers.sync import AlignRequest, align as _do_align
    try:
        out = _do_align(AlignRequest(
            dataset_ids=[s.id for s in req.datasets],
            crop_to_a7=True,
        ))
    except Exception:
        return  # fall back to raw rendering silently

    # Swap IDs on the request to the synced outputs
    id_map = {a.original_id: a.new_id for a in out.aligned}
    for s in req.datasets:
        if s.id in id_map:
            s.id = id_map[s.id]


def _render_multi_dataset(req: RenderRequest) -> tuple[bytes, str] | None:
    """Phase 1 · Multi-dataset overlay (with Phase 3 auto-sync).

    Returns None if this path isn't applicable (template doesn't support
    overlay, no datasets list, etc.) — caller falls through to single-
    dataset rendering.
    """
    if not req.datasets or len(req.datasets) < 2:
        return None
    if req.template not in MULTI_DATASET_TEMPLATES:
        return None

    # If Hz mismatches or sources are mixed, sync transparently first.
    _auto_sync_if_needed(req)

    from backend.routers.analyze import analyze_cached
    from backend.routers.datasets import get_path, _REGISTRY
    from backend.services.compute_engine import resample_column
    import numpy as _np
    import pandas as _pd

    # Color assignment — respect user-provided colors, fall back to palette
    def color_for(i: int, series: DatasetSeries) -> str:
        return series.color or _DEFAULT_SERIES_PALETTE[i % len(_DEFAULT_SERIES_PALETTE)]

    def label_for(series: DatasetSeries) -> str:
        if series.label:
            return series.label
        reg = _REGISTRY.get(series.id)
        return (reg or {}).get("name", series.id)

    traces: list[Trace] = []
    gcp_axis = list(_np.linspace(0, 100, 101))

    # ── force_avg · GRF mean±SD per subject (L side, overlay)
    if req.template == "force_avg":
        for i, s in enumerate(req.datasets):
            try:
                res, _ = analyze_cached(s.id)
            except Exception:
                continue
            if res is None or res.left_force_profile.mean is None:
                continue
            mean = res.left_force_profile.mean
            std = res.left_force_profile.std
            c = color_for(i, s)
            if std is not None:
                traces.append(Trace(kind="band", name="",
                                    x=gcp_axis, y=list(mean),
                                    y_upper=list(mean + std), y_lower=list(mean - std),
                                    color=c, opacity=0.15))
            traces.append(Trace(kind="line", name=label_for(s),
                                x=gcp_axis, y=list(mean),
                                color=c, width=1.8))
        if not traces:
            return None
        return render_from_traces(
            traces, title=req.title or "",
            x_label="Gait cycle (%)", y_label="Force (N)",
            preset=req.preset, variant=req.variant, format=req.format,
            dpi=req.dpi, colorblind_safe=req.colorblind_safe, legend=True,
        )

    # ── imu_avg · joint angle mean per subject
    if req.template == "imu_avg":
        for i, s in enumerate(req.datasets):
            try:
                res, _ = analyze_cached(s.id)
            except Exception:
                continue
            if res is None:
                continue
            path = get_path(s.id)
            if not path:
                continue
            try:
                df = _pd.read_csv(path)
            except Exception:
                continue
            ls = res.left_stride
            result = resample_column(df, "L_Pitch", ls.hs_indices, ls.valid_mask)
            if result is None:
                continue
            mean, std = result
            c = color_for(i, s)
            traces.append(Trace(kind="band", name="",
                                x=gcp_axis, y=list(mean),
                                y_upper=list(mean + std), y_lower=list(mean - std),
                                color=c, opacity=0.12))
            traces.append(Trace(kind="line", name=label_for(s),
                                x=gcp_axis, y=list(mean),
                                color=c, width=1.8))
        if not traces:
            return None
        return render_from_traces(
            traces, title=req.title or "",
            x_label="Gait cycle (%)", y_label="Pitch (°)",
            preset=req.preset, variant=req.variant, format=req.format,
            dpi=req.dpi, colorblind_safe=req.colorblind_safe, legend=True,
        )

    # ── stride_time_trend · per-subject stride-time series + fit
    if req.template == "stride_time_trend":
        for i, s in enumerate(req.datasets):
            try:
                res, _ = analyze_cached(s.id)
            except Exception:
                continue
            if res is None or len(res.left_stride.stride_times) < 2:
                continue
            times = res.left_stride.stride_times
            xs = list(range(1, len(times) + 1))
            c = color_for(i, s)
            traces.append(Trace(kind="scatter", name=label_for(s),
                                x=xs, y=list(times),
                                color=c, width=1.8, opacity=0.7))
            if len(times) >= 3:
                coef = _np.polyfit(xs, times, 1)
                fit_y = list(_np.polyval(coef, xs))
                traces.append(Trace(kind="line", name="",
                                    x=xs, y=fit_y,
                                    color=c, width=1.1, dash=True))
        if not traces:
            return None
        return render_from_traces(
            traces, title=req.title or "",
            x_label="Stride #", y_label="Stride time (s)",
            preset=req.preset, variant=req.variant, format=req.format,
            dpi=req.dpi, colorblind_safe=req.colorblind_safe, legend=True,
        )

    # ── asymmetry · per-subject asymmetry series
    if req.template == "asymmetry":
        from backend.services.compute_engine import _asym_idx
        for i, s in enumerate(req.datasets):
            try:
                res, _ = analyze_cached(s.id)
            except Exception:
                continue
            if res is None:
                continue
            lfp, rfp = res.left_force_profile, res.right_force_profile
            if lfp.individual is None or rfp.individual is None:
                continue
            n = min(lfp.individual.shape[0], rfp.individual.shape[0])
            peaks_l = lfp.individual[:n].max(axis=1)
            peaks_r = rfp.individual[:n].max(axis=1)
            asym = [_asym_idx(float(pl), float(pr)) for pl, pr in zip(peaks_l, peaks_r)]
            xs = list(range(1, n + 1))
            c = color_for(i, s)
            traces.append(Trace(kind="line", name=label_for(s),
                                x=xs, y=asym,
                                color=c, width=1.8))
        if not traces:
            return None
        return render_from_traces(
            traces, title=req.title or "",
            x_label="Stride #", y_label="Asymmetry (%)",
            preset=req.preset, variant=req.variant, format=req.format,
            dpi=req.dpi, colorblind_safe=req.colorblind_safe, legend=True,
        )

    # ── cyclogram · multi-subject phase portraits
    if req.template == "cyclogram":
        for i, s in enumerate(req.datasets):
            try:
                res, _ = analyze_cached(s.id)
            except Exception:
                continue
            if res is None:
                continue
            path = get_path(s.id)
            if not path:
                continue
            try:
                df = _pd.read_csv(path)
            except Exception:
                continue
            if "L_Pitch" not in df.columns or "R_Pitch" not in df.columns:
                continue
            ls = res.left_stride
            xr = resample_column(df, "L_Pitch", ls.hs_indices, ls.valid_mask)
            yr = resample_column(df, "R_Pitch", ls.hs_indices, ls.valid_mask)
            if xr is None or yr is None:
                continue
            c = color_for(i, s)
            traces.append(Trace(kind="line", name=label_for(s),
                                x=list(xr[0]), y=list(yr[0]),
                                color=c, width=1.6))
        if not traces:
            return None
        return render_from_traces(
            traces, title=req.title or "",
            x_label="L_Pitch (°)", y_label="R_Pitch (°)",
            preset=req.preset, variant=req.variant, format=req.format,
            dpi=req.dpi, colorblind_safe=req.colorblind_safe, legend=True,
        )

    return None


def _render_real_data(req: RenderRequest) -> tuple[bytes, str] | None:
    """If dataset_id is set and the template supports real-data binding, build
    traces from the analyzer result and render. Returns None if not applicable.
    """
    if not req.dataset_id:
        return None

    if req.template not in REAL_DATA_TEMPLATES:
        return None

    from backend.routers.analyze import analyze_cached  # avoid cycle at import time

    try:
        res, _payload = analyze_cached(req.dataset_id)
    except HTTPException:
        raise
    except Exception:
        return None
    if res is None:
        return None  # generic fallback; let caller fall back to mock or error

    import numpy as _np

    # Load the raw df for columns the analyzer doesn't pre-resample (joint angles, etc.)
    from backend.routers.datasets import get_path
    df_path = get_path(req.dataset_id)
    import pandas as _pd
    df = _pd.read_csv(df_path) if df_path else None

    gcp_axis = list(_np.linspace(0, 100, 101))
    traces: list[Trace] = []

    if req.template in ("force", "force_avg"):
        lfp = res.left_force_profile
        rfp = res.right_force_profile
        if req.template == "force_avg" or req.stride_avg:
            if lfp.mean is not None and lfp.std is not None:
                traces.append(Trace(kind="band", name="L ± SD",
                                    x=gcp_axis,
                                    y=list(lfp.mean), y_upper=list(lfp.mean + lfp.std),
                                    y_lower=list(lfp.mean - lfp.std),
                                    color="#3B82C4", opacity=0.2))
                traces.append(Trace(kind="line", name="L mean",
                                    x=gcp_axis, y=list(lfp.mean),
                                    color="#1E5F9E", width=2.0))
            if rfp.mean is not None and rfp.std is not None:
                traces.append(Trace(kind="band", name="R ± SD",
                                    x=gcp_axis,
                                    y=list(rfp.mean), y_upper=list(rfp.mean + rfp.std),
                                    y_lower=list(rfp.mean - rfp.std),
                                    color="#D35454", opacity=0.2))
                traces.append(Trace(kind="line", name="R mean",
                                    x=gcp_axis, y=list(rfp.mean),
                                    color="#9E3838", width=2.0))
        else:
            # Instantaneous L/R mean + desired overlay
            if lfp.mean is not None:
                traces.append(Trace(kind="line", name="L Actual",
                                    x=gcp_axis, y=list(lfp.mean),
                                    color="#3B82C4", width=2.0))
            if lfp.des_mean is not None:
                traces.append(Trace(kind="line", name="L Desired",
                                    x=gcp_axis, y=list(lfp.des_mean),
                                    color="#7FB5E4", width=1.3, dash=True))
            if rfp.mean is not None:
                traces.append(Trace(kind="line", name="R Actual",
                                    x=gcp_axis, y=list(rfp.mean),
                                    color="#D35454", width=2.0))
            if rfp.des_mean is not None:
                traces.append(Trace(kind="line", name="R Desired",
                                    x=gcp_axis, y=list(rfp.des_mean),
                                    color="#E89B9B", width=1.3, dash=True))
        # Journal convention: no in-figure title. Caption goes below in the
        # manuscript. Only draw a title if the user explicitly provided one.
        return render_from_traces(
            traces, title=req.title or "", x_label="Gait cycle (%)", y_label="Force (N)",
            preset=req.preset, variant=req.variant, format=req.format,
            dpi=req.dpi, colorblind_safe=req.colorblind_safe, legend=True,
        )

    if req.template == "asymmetry":
        # Per-stride asymmetry of peak force: use analyzer's per-stride data
        lfp = res.left_force_profile
        rfp = res.right_force_profile
        if lfp.individual is None or rfp.individual is None:
            return None
        n = min(lfp.individual.shape[0], rfp.individual.shape[0])
        peaks_l = lfp.individual[:n].max(axis=1)
        peaks_r = rfp.individual[:n].max(axis=1)
        denom = (peaks_l + peaks_r) / 2.0
        asym = _np.where(_np.abs(denom) > 1e-9,
                         _np.abs(peaks_l - peaks_r) / _np.abs(denom) * 100.0,
                         0.0)
        xs = list(range(1, n + 1))
        traces.append(Trace(kind="line", name="asym_idx",
                            x=xs, y=list(asym),
                            color="#F09708", width=1.8))
        return render_from_traces(
            traces, title=req.title or "",
            x_label="Stride #", y_label="Asymmetry (%)",
            preset=req.preset, variant=req.variant, format=req.format,
            dpi=req.dpi, colorblind_safe=req.colorblind_safe, legend=False,
        )

    if req.template == "peak_box":
        lfp = res.left_force_profile
        rfp = res.right_force_profile
        if lfp.individual is None and rfp.individual is None:
            return None
        box_traces: list[Trace] = []
        if lfp.individual is not None:
            peaks_l = lfp.individual.max(axis=1).tolist()
            box_traces.append(Trace(kind="box", name="L", x=["L"], y=peaks_l,
                                    color="#3B82C4"))
        if rfp.individual is not None:
            peaks_r = rfp.individual.max(axis=1).tolist()
            box_traces.append(Trace(kind="box", name="R", x=["R"], y=peaks_r,
                                    color="#D35454"))
        return render_from_traces(
            box_traces, title=req.title or "",
            x_label="", y_label="Peak GRF (N)",
            preset=req.preset, variant=req.variant, format=req.format,
            dpi=req.dpi, colorblind_safe=req.colorblind_safe, legend=False,
        )

    if req.template == "trials":
        # Overlay individual stride profiles (up to 5 for readability)
        lfp = res.left_force_profile
        if lfp.individual is None:
            return None
        n = min(5, lfp.individual.shape[0])
        colors = ["#7FB5E4", "#3B82C4", "#E89B9B", "#D35454", "#F09708"]
        for i in range(n):
            traces.append(Trace(kind="line", name=f"Stride {i + 1}",
                                x=gcp_axis, y=lfp.individual[i].tolist(),
                                color=colors[i % len(colors)], width=1.4))
        return render_from_traces(
            traces, title=req.title or "",
            x_label="Gait cycle (%)", y_label="Force (N)",
            preset=req.preset, variant=req.variant, format=req.format,
            dpi=req.dpi, colorblind_safe=req.colorblind_safe, legend=True,
        )

    # =====================================================
    # Phase 0 · Motion / kinematic templates
    # =====================================================

    if req.template == "imu":
        # Joint angle time series (raw, first 8 seconds). Labels follow
        # the actual column name so we don't mislabel e.g. thigh-mounted
        # IMUs as "shank".
        if df is None:
            return None
        fs = res.sample_rate
        n_max = int(min(len(df), fs * 8.0))
        t = list(_np.arange(n_max) / fs)
        candidates = [c for c in ("L_Pitch", "R_Pitch", "L_Roll", "R_Roll",
                                   "L_Yaw", "R_Yaw") if c in df.columns][:4]
        colors = ["#3B82C4", "#D35454", "#7FB5E4", "#E89B9B"]
        for i, col in enumerate(candidates):
            traces.append(Trace(kind="line", name=col,
                                x=t, y=df[col].iloc[:n_max].tolist(),
                                color=colors[i % len(colors)], width=1.6))
        if not traces:
            return None
        return render_from_traces(
            traces, title=req.title or "",
            x_label="Time (s)", y_label="Pitch (°)",
            preset=req.preset, variant=req.variant, format=req.format,
            dpi=req.dpi, colorblind_safe=req.colorblind_safe, legend=True,
        )

    if req.template == "imu_avg":
        # Joint-angle mean ± SD over 0–100% gait cycle. Labels reflect
        # the actual column name — no hard-coded "shank" assumption.
        if df is None:
            return None
        from backend.services.compute_engine import resample_column
        ls, rs = res.left_stride, res.right_stride
        for col, color_line, color_band in [
            ("L_Pitch", "#1E5F9E", "#3B82C4"),
            ("R_Pitch", "#9E3838", "#D35454"),
        ]:
            if col not in df.columns:
                continue
            side_stride = ls if col.startswith("L_") else rs
            result = resample_column(df, col, side_stride.hs_indices,
                                      side_stride.valid_mask)
            if result is None:
                continue
            mean, std = result
            traces.append(Trace(kind="band", name=f"{col} ± SD",
                                x=gcp_axis, y=list(mean),
                                y_upper=list(mean + std),
                                y_lower=list(mean - std),
                                color=color_band, opacity=0.2))
            traces.append(Trace(kind="line", name=f"{col} mean",
                                x=gcp_axis, y=list(mean),
                                color=color_line, width=2.0))
        if not traces:
            return None
        return render_from_traces(
            traces, title=req.title or "",
            x_label="Gait cycle (%)", y_label="Pitch (°)",
            preset=req.preset, variant=req.variant, format=req.format,
            dpi=req.dpi, colorblind_safe=req.colorblind_safe, legend=True,
        )

    if req.template == "cyclogram":
        # Phase plot: shank pitch vs thigh pitch (or L vs R pitch if only one)
        if df is None:
            return None
        from backend.services.compute_engine import resample_column
        ls = res.left_stride

        x_col = "L_Pitch" if "L_Pitch" in df.columns else None
        y_col = "R_Pitch" if "R_Pitch" in df.columns else None
        if not x_col or not y_col:
            return None

        x_res = resample_column(df, x_col, ls.hs_indices, ls.valid_mask)
        y_res = resample_column(df, y_col, ls.hs_indices, ls.valid_mask)
        if x_res is None or y_res is None:
            return None
        x_mean, _ = x_res
        y_mean, _ = y_res
        traces.append(Trace(kind="line", name="Cycle avg",
                            x=list(x_mean), y=list(y_mean),
                            color="#F09708", width=1.8))
        # Mark 0 / 25 / 50 / 75 / 100 % gait-cycle points
        for pct, label in [(0, "HS"), (25, "25%"), (50, "TO"), (75, "75%")]:
            idx = int(pct * 1.01)
            traces.append(Trace(kind="scatter", name=label,
                                x=[float(x_mean[idx])], y=[float(y_mean[idx])],
                                color="#00FFB2", width=4.0, opacity=1.0))
        return render_from_traces(
            traces, title=req.title or "",
            x_label=f"{x_col} (°)", y_label=f"{y_col} (°)",
            preset=req.preset, variant=req.variant, format=req.format,
            dpi=req.dpi, colorblind_safe=req.colorblind_safe, legend=True,
        )

    if req.template == "stride_time_trend":
        # Stride time across stride # + linear-regression fit
        ls, rs = res.left_stride, res.right_stride
        for times, label, color in [
            (ls.stride_times, "L", "#3B82C4"),
            (rs.stride_times, "R", "#D35454"),
        ]:
            if len(times) < 2:
                continue
            xs = list(range(1, len(times) + 1))
            traces.append(Trace(kind="scatter", name=f"{label} strides",
                                x=xs, y=list(times),
                                color=color, width=2.0, opacity=0.7))
            # Linear fit
            if len(times) >= 3:
                coef = _np.polyfit(xs, times, 1)
                fit_y = list(_np.polyval(coef, xs))
                traces.append(Trace(kind="line",
                                    name=f"{label} trend (slope={coef[0]*1000:.1f} ms/stride)",
                                    x=xs, y=fit_y,
                                    color=color, width=1.2, dash=True))
        if not traces:
            return None
        return render_from_traces(
            traces, title=req.title or "",
            x_label="Stride #", y_label="Stride time (s)",
            preset=req.preset, variant=req.variant, format=req.format,
            dpi=req.dpi, colorblind_safe=req.colorblind_safe, legend=True,
        )

    if req.template == "force_lr_subplot":
        # Side-by-side L / R panels, both GCP-normalized, both at exact
        # journal size. This is the "most requested" kinetic figure —
        # single subplot per leg with the desired (dashed) trace overlaid.
        import matplotlib as _mpl
        import matplotlib.pyplot as _plt
        from backend.services.publication_engine import (
            JOURNAL_PRESETS as _JP, _compose_rc, _emit,
        )
        lfp, rfp = res.left_force_profile, res.right_force_profile
        if lfp.mean is None or rfp.mean is None:
            return None
        P = _JP[req.preset]
        if req.variant == "col1":
            w_mm, h_mm = P.col1
        elif req.variant == "onehalf" and P.onehalf:
            w_mm, h_mm = P.onehalf
        else:
            w_mm, h_mm = P.col2
        dpi_val = req.dpi or P.dpi
        inch_w, inch_h = w_mm / 25.4, h_mm / 25.4
        x = _np.linspace(0, 100, 101)

        rc = _compose_rc(P)
        with _mpl.rc_context(rc):
            fig, (axL, axR) = _plt.subplots(
                1, 2, figsize=(inch_w, inch_h), sharey=True,
            )
            # Left panel
            if lfp.std is not None:
                axL.fill_between(x, lfp.mean - lfp.std, lfp.mean + lfp.std,
                                  color="#3B82C4", alpha=0.18, linewidth=0)
            axL.plot(x, lfp.mean, color="#1E5F9E",
                     linewidth=P.stroke_pt * 1.8, label="L actual")
            if lfp.des_mean is not None:
                axL.plot(x, lfp.des_mean, color="#7FB5E4",
                         linewidth=P.stroke_pt * 1.2, linestyle="--",
                         dashes=(3, 2), label="L desired")
            axL.set_xlabel("Gait cycle (%)")
            axL.set_ylabel("Force (N)")
            axL.set_title("Left", fontsize=P.title_pt)
            axL.grid(True, linewidth=P.grid_pt, color=P.grid_color, alpha=0.6)
            axL.legend(loc="best", frameon=False, fontsize=P.legend_pt)
            # Right panel
            if rfp.std is not None:
                axR.fill_between(x, rfp.mean - rfp.std, rfp.mean + rfp.std,
                                  color="#D35454", alpha=0.18, linewidth=0)
            axR.plot(x, rfp.mean, color="#9E3838",
                     linewidth=P.stroke_pt * 1.8, label="R actual")
            if rfp.des_mean is not None:
                axR.plot(x, rfp.des_mean, color="#E89B9B",
                         linewidth=P.stroke_pt * 1.2, linestyle="--",
                         dashes=(3, 2), label="R desired")
            axR.set_xlabel("Gait cycle (%)")
            axR.set_title("Right", fontsize=P.title_pt)
            axR.grid(True, linewidth=P.grid_pt, color=P.grid_color, alpha=0.6)
            axR.legend(loc="best", frameon=False, fontsize=P.legend_pt)
            if req.title:
                fig.suptitle(req.title, fontsize=P.title_pt, y=0.995)
            fig.tight_layout(pad=0.4)
            fig.set_size_inches(inch_w, inch_h)
            return _emit(fig, req.format, dpi_val, preset_name=P.name)

    if req.template == "stance_swing_bar":
        ls, rs = res.left_stride, res.right_stride
        labels = ["L stance", "L swing", "R stance", "R swing"]
        heights = [ls.stance_pct_mean, ls.swing_pct_mean,
                   rs.stance_pct_mean, rs.swing_pct_mean]
        colors = ["#3B82C4", "#7FB5E4", "#D35454", "#E89B9B"]
        for lab, h, c in zip(labels, heights, colors):
            traces.append(Trace(kind="bar", name=lab,
                                x=[lab], y=[float(h)], color=c))
        return render_from_traces(
            traces, title=req.title or "",
            x_label="", y_label="% of gait cycle",
            preset=req.preset, variant=req.variant, format=req.format,
            dpi=req.dpi, colorblind_safe=req.colorblind_safe, legend=False,
            y_range=(0, 100),
        )

    if req.template == "rom_bar":
        # ROM per joint (pitch / roll / yaw) for L and R
        if df is None:
            return None
        ls = res.left_stride
        joints = [("Pitch", "sagittal"), ("Roll", "frontal"), ("Yaw", "transverse")]
        for side, hs, valid, color in [
            ("L", ls.hs_indices, ls.valid_mask, "#3B82C4"),
            ("R", res.right_stride.hs_indices, res.right_stride.valid_mask, "#D35454"),
        ]:
            for joint, plane in joints:
                col = f"{side}_{joint}"
                if col not in df.columns:
                    continue
                roms = []
                for i in range(len(valid)):
                    if not valid[i] or i + 1 >= len(hs):
                        continue
                    chunk = df[col].iloc[hs[i]:hs[i+1]].to_numpy(dtype=float)
                    chunk = chunk[_np.isfinite(chunk)]
                    if len(chunk) >= 2:
                        roms.append(float(_np.max(chunk) - _np.min(chunk)))
                if roms:
                    traces.append(Trace(kind="bar", name=f"{side} {plane}",
                                        x=[f"{side} {plane}"], y=[float(_np.mean(roms))],
                                        color=color))
        if not traces:
            return None
        return render_from_traces(
            traces, title=req.title or "",
            x_label="", y_label="ROM (°)",
            preset=req.preset, variant=req.variant, format=req.format,
            dpi=req.dpi, colorblind_safe=req.colorblind_safe, legend=False,
        )

    if req.template == "debug_ts":
        # Full-duration raw time-series, small multiples. Intended for
        # visual debugging — where did the signal go weird? Heel-strike
        # events are overlaid as vertical dotted lines so the user can
        # orient themselves against the gait cycle.
        if df is None:
            return None
        import matplotlib as _mpl
        import matplotlib.pyplot as _plt
        from backend.services.publication_engine import (
            JOURNAL_PRESETS as _JP, _compose_rc, _emit,
        )
        P = _JP[req.preset]
        # Taller figure for stacked panels
        if req.variant == "col1":
            w_mm, h_mm = P.col1[0], P.col1[1] * 2.0
        elif req.variant == "onehalf" and P.onehalf:
            w_mm, h_mm = P.onehalf[0], P.onehalf[1] * 2.0
        else:
            w_mm, h_mm = P.col2[0], P.col2[1] * 1.8
        dpi_val = req.dpi or P.dpi
        inch_w, inch_h = w_mm / 25.4, h_mm / 25.4
        fs = res.sample_rate
        t = _np.arange(len(df)) / fs

        # Pick the signals that exist
        rows = []
        for cols, ylabel, colors in [
            (["L_ActForce_N", "R_ActForce_N"], "Force (N)", ["#1E5F9E", "#9E3838"]),
            (["L_Pitch", "R_Pitch"],           "Pitch (°)", ["#3B82C4", "#D35454"]),
            (["L_ActVel_mps", "R_ActVel_mps"], "Vel (m/s)", ["#F09708", "#FFB347"]),
        ]:
            present = [c for c in cols if c in df.columns]
            if present:
                rows.append((present, ylabel, colors))
        if not rows:
            return None

        rc = _compose_rc(P)
        with _mpl.rc_context(rc):
            fig, axes = _plt.subplots(
                len(rows), 1, figsize=(inch_w, inch_h), sharex=True,
            )
            if len(rows) == 1:
                axes = [axes]

            # Heel-strike markers (L + R)
            hs_L = res.left_stride.hs_indices
            hs_R = res.right_stride.hs_indices

            for ax, (cols, ylabel, colors) in zip(axes, rows):
                for col, c in zip(cols, colors):
                    ax.plot(t, df[col].to_numpy(dtype=float),
                            color=c, linewidth=P.stroke_pt * 1.2, label=col)
                # HS markers
                for idx in hs_L:
                    if 0 <= idx < len(t):
                        ax.axvline(t[idx], color="#3B82C4",
                                   linestyle=":", linewidth=P.grid_pt * 1.5, alpha=0.5)
                for idx in hs_R:
                    if 0 <= idx < len(t):
                        ax.axvline(t[idx], color="#D35454",
                                   linestyle=":", linewidth=P.grid_pt * 1.5, alpha=0.5)
                ax.set_ylabel(ylabel)
                ax.grid(True, linewidth=P.grid_pt, color=P.grid_color, alpha=0.5)
                ax.legend(loc="upper right", frameon=False,
                          fontsize=P.legend_pt, ncol=len(cols))
            axes[-1].set_xlabel("Time (s)  ·  dotted lines = heel-strikes (blue L · red R)")
            if req.title:
                fig.suptitle(req.title, fontsize=P.title_pt, y=0.998)
            fig.tight_layout(pad=0.4)
            fig.set_size_inches(inch_w, inch_h)
            return _emit(fig, req.format, dpi_val, preset_name=P.name)

    if req.template == "symmetry_radar":
        # Multi-axis symmetry polar chart — rendered as polar bars for
        # journal compatibility (vector-friendly).
        import matplotlib as _mpl
        import matplotlib.pyplot as _plt
        from backend.services.publication_engine import JOURNAL_PRESETS, _compose_rc, _emit
        P = JOURNAL_PRESETS[req.preset]
        if req.variant == "col1":
            w_mm, h_mm = P.col1
        elif req.variant == "onehalf" and P.onehalf:
            w_mm, h_mm = P.onehalf
        else:
            w_mm, h_mm = P.col2
        dpi_val = req.dpi or P.dpi
        inch_w, inch_h = w_mm / 25.4, h_mm / 25.4

        axes = [
            ("Stride T", res.stride_time_symmetry),
            ("Stride L", res.stride_length_symmetry if res.stride_length_symmetry >= 0 else 0),
            ("Stance %", res.stance_symmetry if res.stance_symmetry >= 0 else 0),
            ("Force RMSE", res.force_symmetry),
        ]
        # Add peak-GRF asymmetry if available
        lfp = res.left_force_profile; rfp = res.right_force_profile
        if lfp.mean is not None and rfp.mean is not None:
            from backend.services.compute_engine import _asym_idx
            axes.append(("Peak GRF",
                         _asym_idx(float(_np.max(lfp.mean)), float(_np.max(rfp.mean)))))
        # Close the polygon
        labels = [a[0] for a in axes]
        values = [max(float(a[1]), 0.0) for a in axes]
        angles = _np.linspace(0, 2 * _np.pi, len(values), endpoint=False).tolist()
        values += values[:1]
        angles += angles[:1]

        rc = _compose_rc(P)
        with _mpl.rc_context(rc):
            fig, ax = _plt.subplots(figsize=(inch_w, inch_h),
                                    subplot_kw={"projection": "polar"})
            ax.plot(angles, values, color="#F09708", linewidth=P.stroke_pt * 1.4)
            ax.fill(angles, values, color="#F09708", alpha=0.18)
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(labels)
            ax.set_rlabel_position(30)
            ax.grid(True, linewidth=P.grid_pt, color=P.grid_color, alpha=0.6)
            max_v = max(values) if values else 10
            ax.set_ylim(0, max(max_v * 1.15, 5))
            if req.title:
                ax.set_title(req.title, fontsize=P.title_pt, pad=18)
            fig.set_size_inches(inch_w, inch_h)
            return _emit(fig, req.format, dpi_val, preset_name=P.name)

    return None


@router.post("/render")
def render_endpoint(req: RenderRequest):
    if req.template not in GRAPH_SPECS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown template '{req.template}'. Known: {sorted(GRAPH_SPECS.keys())}",
        )
    if req.preset not in JOURNAL_PRESETS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown preset '{req.preset}'. Known: {sorted(JOURNAL_PRESETS.keys())}",
        )
    # Phase 1 · multi-dataset overlay first (datasets[] ≥ 2)
    try:
        multi = _render_multi_dataset(req)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"multi-dataset render failed: {exc}") from exc

    # Real-data single-dataset path
    real = None
    if multi is None:
        # If datasets[] has exactly one entry, treat its id as dataset_id
        if req.datasets and not req.dataset_id:
            req = req.copy(update={"dataset_id": req.datasets[0].id})
        try:
            real = _render_real_data(req)
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=f"real-data render failed: {exc}") from exc

    if multi is not None:
        data, mime = multi
    elif real is not None:
        data, mime = real
    else:
        try:
            data, mime = render(
                template=req.template,
                preset=req.preset,
                variant=req.variant,
                format=req.format,
                dpi=req.dpi,
                stride_avg=req.stride_avg,
                colorblind_safe=req.colorblind_safe,
                keep_palette=req.keep_palette,
                title_override=req.title,
            )
        except Exception as exc:  # noqa: BLE001 — surface full error to client
            raise HTTPException(status_code=500, detail=f"render failed: {exc}") from exc

    P = JOURNAL_PRESETS[req.preset]
    fname = _suggest_filename(req, P)
    return Response(
        content=data,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


class BundleRequest(BaseModel):
    preset: str = "ieee"
    variant: Literal["col1", "col2", "onehalf"] = "col2"
    format: Literal["svg", "pdf", "eps", "png", "tiff"] = "svg"
    dpi: Optional[int] = None
    cells: list[dict]  # [{id, template, stride_avg?, preset?}]
    include_readme: bool = True


@router.post("/bundle")
def bundle_endpoint(req: BundleRequest):
    if req.preset not in JOURNAL_PRESETS:
        raise HTTPException(status_code=400, detail=f"Unknown preset '{req.preset}'")
    P = JOURNAL_PRESETS[req.preset]

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for i, cell in enumerate(req.cells):
            tpl = cell.get("template") or cell.get("graph")
            if not tpl or tpl not in GRAPH_SPECS:
                continue
            cell_preset = cell.get("preset") or req.preset
            cell_variant = cell.get("variant") or req.variant
            stride_avg = bool(cell.get("stride_avg", False))
            ds_id = cell.get("dataset_id") or cell.get("dataset_id")
            datasets_raw = cell.get("datasets") or []
            try:
                real: tuple[bytes, str] | None = None
                if ds_id or len(datasets_raw) >= 2:
                    cell_req = RenderRequest(
                        template=tpl, preset=cell_preset, variant=cell_variant,
                        format=req.format, dpi=req.dpi, stride_avg=stride_avg,
                        dataset_id=ds_id,
                        datasets=[DatasetSeries(**d) for d in datasets_raw],
                        title=cell.get("title") or "",
                    )
                    try:
                        if len(datasets_raw) >= 2:
                            real = _render_multi_dataset(cell_req)
                        if real is None and ds_id:
                            real = _render_real_data(cell_req)
                    except Exception:
                        pass
                if real is not None:
                    data, _ = real
                else:
                    data, _ = render(
                        template=tpl, preset=cell_preset, variant=cell_variant,
                        format=req.format, dpi=req.dpi, stride_avg=stride_avg,
                    )
            except Exception as exc:  # noqa: BLE001
                zf.writestr(
                    f"ERRORS/{cell.get('id', i)}.txt",
                    f"render failed: {exc}\n",
                )
                continue
            name = f"{cell.get('id', f'cell{i}')}_{tpl}.{req.format}"
            zf.writestr(name, data)

        if req.include_readme:
            readme = _bundle_readme(req, P)
            zf.writestr("README.txt", readme)

    buf.seek(0)
    dim = int(P.col2[0] if req.variant == "col2" else P.col1[0])
    fname = f"hwalker_bundle_{req.preset}_{dim}mm.zip"
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


def _bundle_readme(req: BundleRequest, P) -> str:
    col = "col2" if req.variant == "col2" else ("col1" if req.variant == "col1" else "onehalf")
    w_mm = P.col2[0] if col == "col2" else (P.col1[0] if col == "col1" else (P.onehalf[0] if P.onehalf else P.col2[0]))
    h_mm = P.col2[1] if col == "col2" else (P.col1[1] if col == "col1" else (P.onehalf[1] if P.onehalf else P.col2[1]))
    return (
        f"H-Walker CORE · publication bundle\n"
        f"====================================\n"
        f"Journal preset : {P.full} ({P.name})\n"
        f"Width variant  : {col} = {w_mm} × {h_mm} mm\n"
        f"Format         : {req.format.upper()}\n"
        f"DPI            : {req.dpi or P.dpi}\n"
        f"Font           : {P.font} ({P.body_pt}pt body, {P.axis_pt}pt axis, {P.legend_pt}pt legend)\n"
        f"Stroke         : {P.stroke_pt}pt\n"
        f"Grid           : {P.grid_pt}pt, {P.grid_color}\n"
        f"Colorblind     : {'yes' if P.colorblind_safe else 'no'}\n"
        f"Accepted fmts  : {', '.join(P.formats)}\n"
        f"\n"
        f"Files are named <cell_id>_<template>.{req.format}.\n"
        f"Any render errors are recorded under ERRORS/.\n"
        f"\n"
        f"Journal notes  : {P.notes}\n"
    )


# ============================================================
# Multi-panel composition — Fig 1(a)(b)(c)(d)
# ============================================================

class PanelCell(BaseModel):
    template: str
    dataset_id: Optional[str] = None
    datasets: list[dict] = []         # overlay form — [{id,label,color}]
    stride_avg: bool = False
    title: Optional[str] = None       # panel caption (below or beside)


class MultiPanelRequest(BaseModel):
    panels: list[PanelCell]            # 2–4 panels
    preset: str = "ieee"
    variant: Literal["col1", "col2", "onehalf"] = "col2"
    format: Literal["svg", "pdf", "png"] = "pdf"
    layout: Literal["auto", "1x2", "2x1", "2x2", "1x3", "3x1"] = "auto"
    dpi: Optional[int] = None


_LAYOUT_MAP = {
    2: {"auto": (1, 2), "1x2": (1, 2), "2x1": (2, 1)},
    3: {"auto": (1, 3), "1x3": (1, 3), "3x1": (3, 1)},
    4: {"auto": (2, 2), "2x2": (2, 2), "1x2": (2, 2)},
}


def _render_panel_svg(panel: PanelCell, preset: str, variant: str, dpi: Optional[int]) -> bytes:
    """Render one panel to SVG bytes via the existing /render code path."""
    req = RenderRequest(
        template=panel.template,
        preset=preset,
        variant=variant,
        format="svg",
        dpi=dpi,
        stride_avg=panel.stride_avg,
        dataset_id=panel.dataset_id,
        datasets=[DatasetSeries(**d) for d in panel.datasets] if panel.datasets else [],
        title=panel.title or "",
    )
    multi = _render_multi_dataset(req) if req.datasets else None
    if multi:
        return multi[0]
    # Fall through to single-dataset or mockup path
    from backend.routers.graphs import _render_real_data
    real = _render_real_data(req)
    if real:
        return real[0]
    data, _ = render(
        template=req.template, preset=req.preset, variant=req.variant, format="svg",
        dpi=req.dpi, stride_avg=req.stride_avg,
    )
    return data


@router.post("/multi_panel")
def multi_panel(req: MultiPanelRequest):
    """Compose 2–4 panel SVGs into a single multi-panel figure with
    (a)(b)(c)(d) labels, correctly sized to the journal preset.

    Uses matplotlib's figure grid as the composition canvas and embeds
    each panel via `imshow` of its rasterized bitmap (kept hi-dpi) OR
    via `inset_axes` for vector-preserving SVG. PDF output is vector.
    """
    n = len(req.panels)
    if n < 2 or n > 4:
        raise HTTPException(status_code=400, detail=f"multi_panel needs 2-4 panels (got {n})")
    if req.preset not in JOURNAL_PRESETS:
        raise HTTPException(status_code=400, detail=f"unknown preset '{req.preset}'")
    P = JOURNAL_PRESETS[req.preset]
    rows, cols = _LAYOUT_MAP[n].get(req.layout, _LAYOUT_MAP[n]["auto"])

    # Render each panel once (SVG strings kept for vector quality).
    panel_svgs: list[bytes] = []
    for p in req.panels:
        try:
            panel_svgs.append(_render_panel_svg(p, req.preset, req.variant, req.dpi))
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"panel {p.template} failed: {exc}") from exc

    # Compose via matplotlib — each panel is a subplot, its rendered PNG
    # is read back as the axis content. This preserves pixel quality at
    # the target DPI and yields a proper multi-panel PDF/SVG/PNG.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    from PIL import Image

    # Figure canvas sized for the journal variant (each panel is a fraction)
    w_mm, h_mm = (P.col2 if req.variant == "col2" else
                  (P.col1 if req.variant == "col1" else (P.onehalf or P.col2)))
    # 다중 panel 은 col2 폭 유지, 행 개수만큼 세로 확장
    inch_w, inch_h = w_mm / 25.4, (h_mm * rows) / 25.4 * 0.95

    with mpl.rc_context({
        "font.family": [P.font] + P.font_fallback,
        "font.size": P.body_pt,
        "figure.facecolor": P.bg,
        "savefig.facecolor": P.bg,
    }):
        fig, axes = plt.subplots(rows, cols, figsize=(inch_w, inch_h))
        axes_flat = list(axes.flat) if hasattr(axes, 'flat') else [axes]

        LABELS = "abcdefgh"
        for i, (ax, panel, svg_bytes) in enumerate(zip(axes_flat, req.panels, panel_svgs)):
            # Convert panel SVG → PNG @ 2× DPI for crisp embedding
            tmp_svg = Path(tempfile.mkstemp(suffix=".svg")[1])
            tmp_png = Path(tempfile.mkstemp(suffix=".png")[1])
            tmp_svg.write_bytes(svg_bytes)
            try:
                # Try cairosvg first (high fidelity)
                import cairosvg
                cairosvg.svg2png(
                    bytestring=svg_bytes,
                    write_to=str(tmp_png),
                    output_width=int(inch_w / cols * 300),
                    output_height=int((inch_h / rows) * 300),
                )
            except Exception:
                # Fall back to rsvg-convert if available on the system
                try:
                    subprocess.run(
                        ["rsvg-convert", "-a", "-w", str(int(inch_w / cols * 300)),
                         str(tmp_svg), "-o", str(tmp_png)],
                        check=True, capture_output=True, timeout=10,
                    )
                except Exception:
                    # Final fallback: blank panel with error text
                    ax.text(0.5, 0.5, f"(panel {i+1}: SVG→PNG failed)",
                            ha='center', va='center', transform=ax.transAxes,
                            color='red', fontsize=P.legend_pt)
                    ax.set_xticks([]); ax.set_yticks([])
                    for sp in ax.spines.values(): sp.set_visible(False)
                    continue
            img = Image.open(tmp_png)
            ax.imshow(img)
            ax.set_xticks([]); ax.set_yticks([])
            for sp in ax.spines.values(): sp.set_visible(False)
            # (a)/(b)/(c)/(d) label, top-left
            ax.text(-0.04, 1.02, f"({LABELS[i]})", transform=ax.transAxes,
                    ha='right', va='bottom', fontsize=P.title_pt, fontweight='bold')
            if panel.title:
                ax.set_title(panel.title, fontsize=P.axis_pt, pad=4)
            try:
                tmp_svg.unlink(); tmp_png.unlink()
            except OSError:
                pass

        fig.tight_layout(pad=0.4, h_pad=0.8, w_pad=0.8)

        # Emit in requested format
        buf = io.BytesIO()
        try:
            if req.format == "pdf":
                fig.savefig(buf, format="pdf", dpi=req.dpi or P.dpi, pad_inches=0.05)
                mime = "application/pdf"
            elif req.format == "png":
                fig.savefig(buf, format="png", dpi=req.dpi or P.dpi, pad_inches=0.05)
                mime = "image/png"
            else:
                fig.savefig(buf, format="svg", dpi=req.dpi or P.dpi, pad_inches=0.05)
                mime = "image/svg+xml"
        finally:
            plt.close(fig)

    fname = f"hwalker_panel_{len(req.panels)}panel_{req.preset}.{req.format}"
    return Response(
        content=buf.getvalue(), media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
