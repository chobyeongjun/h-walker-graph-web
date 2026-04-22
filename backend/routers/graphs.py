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
