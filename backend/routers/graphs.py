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


def _suggest_filename(req: RenderRequest, P) -> str:
    dim = f"{int(P.col2[0] if req.variant == 'col2' else P.col1[0])}mm"
    return f"hwalker_{req.template}_{req.preset}_{dim}.{req.format}"


def _render_real_data(req: RenderRequest) -> tuple[bytes, str] | None:
    """If dataset_id is set and the template supports real-data binding, build
    traces from the analyzer result and render. Returns None if not applicable.
    """
    if not req.dataset_id:
        return None

    # Only these templates currently have real-data bindings.
    if req.template not in {"force", "force_avg", "asymmetry", "peak_box", "trials"}:
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
        title = "GRF · stride-averaged" if req.template == "force_avg" else "Ground reaction force"
        return render_from_traces(
            traces, title=title, x_label="Gait cycle (%)", y_label="Force (N)",
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
            traces, title="Asymmetry index across strides",
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
            box_traces, title="Peak vertical GRF",
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
            traces, title=f"Stride overlay (first {n})",
            x_label="Gait cycle (%)", y_label="Force (N)",
            preset=req.preset, variant=req.variant, format=req.format,
            dpi=req.dpi, colorblind_safe=req.colorblind_safe, legend=True,
        )

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
