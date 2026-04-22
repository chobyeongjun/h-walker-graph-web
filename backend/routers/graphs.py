"""
/api/graphs/* — Phase 2 publication export.

Endpoints:
  GET  /api/graphs/templates         → list of GRAPH_TPLS keys
  GET  /api/graphs/presets           → list of JOURNAL_PRESETS with submission specs
  POST /api/graphs/render            → single figure at exact journal size
  POST /api/graphs/bundle            → ZIP of SVGs for multiple cells
"""
from __future__ import annotations

import io
import zipfile
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


class RenderRequest(BaseModel):
    template: str
    preset: str = "ieee"
    variant: Literal["col1", "col2", "onehalf"] = "col2"
    format: Literal["svg", "pdf", "eps", "png", "tiff"] = "svg"
    dpi: Optional[int] = None
    stride_avg: bool = False
    colorblind_safe: Optional[bool] = None
    keep_palette: bool = False
    dataset_id: Optional[str] = None  # Phase B: pull numeric data from real CSV
    # Phase 2E: optional user-provided title. Journal convention is no
    # in-figure title (caption lives below in the manuscript), so this
    # defaults to empty string = no title drawn.
    title: Optional[str] = None


def _suggest_filename(req: RenderRequest, P) -> str:
    dim = f"{int(P.col2[0] if req.variant == 'col2' else P.col1[0])}mm"
    return f"hwalker_{req.template}_{req.preset}_{dim}.{req.format}"


REAL_DATA_TEMPLATES = {
    # Force / kinetic (Phase 2A)
    "force", "force_avg", "asymmetry", "peak_box", "trials",
    # Motion / kinematic (Phase 0)
    "imu", "imu_avg", "cyclogram", "stride_time_trend",
    "stance_swing_bar", "rom_bar", "symmetry_radar",
}


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
        # Joint angle time series (raw, first 8 seconds)
        if df is None:
            return None
        fs = res.sample_rate
        n_max = int(min(len(df), fs * 8.0))
        t = list(_np.arange(n_max) / fs)
        for col, label, color in [
            ("L_Pitch", "L shank pitch", "#3B82C4"),
            ("R_Pitch", "R shank pitch", "#D35454"),
        ]:
            if col in df.columns:
                traces.append(Trace(kind="line", name=label,
                                    x=t, y=df[col].iloc[:n_max].tolist(),
                                    color=color, width=1.6))
        if not traces:
            return None
        return render_from_traces(
            traces, title=req.title or "",
            x_label="Time (s)", y_label="Pitch (°)",
            preset=req.preset, variant=req.variant, format=req.format,
            dpi=req.dpi, colorblind_safe=req.colorblind_safe, legend=True,
        )

    if req.template == "imu_avg":
        # Joint-angle mean ± SD over 0–100% gait cycle
        if df is None:
            return None
        from backend.services.compute_engine import resample_column
        ls, rs = res.left_stride, res.right_stride
        for col, label, color_line, color_band in [
            ("L_Pitch", "L shank", "#1E5F9E", "#3B82C4"),
            ("R_Pitch", "R shank", "#9E3838", "#D35454"),
        ]:
            if col not in df.columns:
                continue
            side_stride = ls if col.startswith("L_") else rs
            result = resample_column(df, col, side_stride.hs_indices,
                                      side_stride.valid_mask)
            if result is None:
                continue
            mean, std = result
            traces.append(Trace(kind="band", name=f"{label} ± SD",
                                x=gcp_axis, y=list(mean),
                                y_upper=list(mean + std),
                                y_lower=list(mean - std),
                                color=color_band, opacity=0.2))
            traces.append(Trace(kind="line", name=f"{label} mean",
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
    # Real-data path (dataset_id provided + supported template)
    try:
        real = _render_real_data(req)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"real-data render failed: {exc}") from exc

    if real is not None:
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
            try:
                data, _ = render(
                    template=tpl,
                    preset=cell_preset,
                    variant=cell_variant,
                    format=req.format,
                    dpi=req.dpi,
                    stride_avg=stride_avg,
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
