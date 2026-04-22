"""
/api/stats — Phase 2A statistical-test endpoint.

Two request shapes supported:

1) Raw series:
    {
        "op": "ttest_paired" | "ttest_welch" | "anova1" | "pearson" | "cohens_d" | "shapiro",
        "a":  [float, ...],          # for paired/welch/pearson/cohens_d/shapiro
        "b":  [float, ...],          # for paired/welch/pearson/cohens_d
        "groups": [[...], [...]],    # for anova1
        "paired": false              # cohens_d only
    }

2) Dataset-backed (convenience): pulls columns from an uploaded CSV.
    {
        "op": "ttest_paired",
        "dataset_id": "ds_xxx",
        "a_col": "L_ActForce_N",
        "b_col": "R_ActForce_N",
        "groups_cols": ["L_ActForce_N", "R_ActForce_N"]   # for anova1
    }

Response is a uniform stats dict (see `stats_engine.py` module docstring).
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.routers.datasets import get_path
from backend.services import stats_engine


router = APIRouter(prefix="/api/stats", tags=["stats"])


class StatsRequest(BaseModel):
    op: str
    # raw series
    a: Optional[list[float]] = None
    b: Optional[list[float]] = None
    groups: Optional[list[list[float]]] = None
    paired: bool = False
    # dataset-backed convenience
    dataset_id: Optional[str] = None
    a_col: Optional[str] = None
    b_col: Optional[str] = None
    groups_cols: Optional[list[str]] = None


def _col(df: pd.DataFrame, name: str) -> list[float]:
    if name not in df.columns:
        raise HTTPException(status_code=400, detail=f"column '{name}' not in dataset")
    arr = df[name].to_numpy(dtype=float)
    return arr[np.isfinite(arr)].tolist()


@router.post("")
def run_stats(req: StatsRequest) -> dict[str, Any]:
    if req.op not in stats_engine.OP_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown op '{req.op}'. "
                   f"Known: {sorted(stats_engine.OP_REGISTRY.keys())}",
        )

    payload: dict[str, Any] = {"paired": req.paired}

    if req.dataset_id:
        path = get_path(req.dataset_id)
        if not path:
            raise HTTPException(status_code=404, detail=f"dataset '{req.dataset_id}' not found")
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"CSV unreadable: {exc}") from exc

        if req.op == "anova1":
            if not req.groups_cols:
                raise HTTPException(status_code=400, detail="anova1 needs groups_cols")
            payload["groups"] = [_col(df, c) for c in req.groups_cols]
        elif req.op == "shapiro":
            if not req.a_col:
                raise HTTPException(status_code=400, detail="shapiro needs a_col")
            payload["a"] = _col(df, req.a_col)
        else:
            if not req.a_col or not req.b_col:
                raise HTTPException(status_code=400, detail=f"{req.op} needs a_col + b_col")
            payload["a"] = _col(df, req.a_col)
            payload["b"] = _col(df, req.b_col)
    else:
        if req.op == "anova1":
            payload["groups"] = req.groups or []
        elif req.op == "shapiro":
            payload["a"] = req.a or []
        else:
            payload["a"] = req.a or []
            payload["b"] = req.b or []

    try:
        return stats_engine.run(req.op, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"stats failed: {exc}") from exc


@router.get("/ops")
def list_ops() -> list[str]:
    return sorted(stats_engine.OP_REGISTRY.keys())
