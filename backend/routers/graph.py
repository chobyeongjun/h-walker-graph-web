"""FastAPI router for graph generation endpoints."""
from __future__ import annotations

import base64
import tempfile
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel

import pandas as pd

from backend.models.schema import GraphSpec
from backend.services.graph_publication import JOURNAL_RCPARAMS, render_svg, render_full_analysis_svgs
from backend.services.graph_quick import build_quick_response
from backend.services.analysis_engine import run_full_analysis, result_to_dict, full_analysis_to_stats
from backend.services.knowledge_loader import register_csv_columns

router = APIRouter()


class FileUpload(BaseModel):
    name: str
    content: str  # base64 data URL or plain base64


class UploadRequest(BaseModel):
    files: list[FileUpload]


class UploadResponse(BaseModel):
    paths: list[str]
    columns: list[list[str]] = []  # CSV column headers per file


@router.post("/files/upload", response_model=UploadResponse)
def upload_files(payload: UploadRequest) -> UploadResponse:
    """Accept base64-encoded CSV files, save to temp dir, return paths.

    Also parses CSV headers and registers them for LLM context injection.
    """
    paths = []
    all_columns = []
    for f in payload.files:
        content = f.content
        # Strip data URL prefix if present: "data:text/csv;base64,..."
        if "," in content:
            content = content.split(",", 1)[1]
        raw = base64.b64decode(content)
        # Save to temp file
        tmp = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".csv",
            prefix=f.name.replace(".csv", "") + "_",
        )
        tmp.write(raw)
        tmp.close()
        paths.append(tmp.name)

        # Parse CSV headers and register for LLM
        try:
            df = pd.read_csv(tmp.name, nrows=0)
            cols = [c.strip() for c in df.columns.tolist()]
            all_columns.append(cols)
            register_csv_columns(tmp.name, cols)
        except Exception:
            all_columns.append([])

    return UploadResponse(paths=paths, columns=all_columns)


@router.post("/graph/quick")
def quick_graph(spec: GraphSpec) -> dict:
    """Return Plotly-compatible JSON traces for interactive graphs."""
    try:
        result = build_quick_response(spec.request, spec.csv_paths)
        return result
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/graph/publication")
def publication_graph(
    spec: GraphSpec,
    journal: str = Query(default="default"),
) -> Response:
    """Render a publication-quality matplotlib SVG."""
    try:
        svg_str = render_svg(spec.request, spec.csv_paths, journal=journal)
        return Response(content=svg_str, media_type="image/svg+xml")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class FullAnalysisRequest(BaseModel):
    csv_paths: list[str]
    journal: str = "default"
    graph_types: Optional[list[str]] = None


@router.post("/analyze/full")
def full_analysis(req: FullAnalysisRequest) -> dict:
    """Run full gait analysis (stride, force, ZUPT, symmetry, fatigue) and return
    structured results + publication-quality graph images.

    Returns:
        {
            "results": [AnalysisResult dict per file],
            "graphs": {name: base64 PNG data URI},
        }
    """
    try:
        results = [run_full_analysis(p) for p in req.csv_paths]
        results_json = [result_to_dict(r) for r in results]
        graphs = render_full_analysis_svgs(
            req.csv_paths, journal=req.journal, graph_types=req.graph_types,
        )
        return {"results": results_json, "graphs": graphs}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
