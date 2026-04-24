"""
/api/sync/* — cross-source data synchronization.

Two endpoints:
  GET  /api/sync/preview/{ds_id}  → detected pulses + signal thumbnail
                                     (for the sync-check modal)
  POST /api/sync/align             → batch: crop + upsample + register
                                     new _synced datasets

Usage pattern:
  1. User uploads robot.csv + mocap.csv + forceplate.csv
  2. Frontend shows 'Hz differ — click Sync' banner when any mismatch
  3. User clicks Sync → POST /api/sync/align with their IDs
  4. Server:
       - reads CSVs
       - auto-detects A7 column in each
       - crops each to its A7 [first_pulse, last_pulse] window
       - resamples ALL to the highest fs via linear interpolation
       - registers each as a new '<original>_synced.csv' dataset
  5. Response returns the new dataset IDs + per-source stats
"""
from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.routers.datasets import (
    _REGISTRY, _UPLOAD_DIR, _save_registry, register_csv_columns,
    _guess_unit, _guess_role, _guess_kind,
)
from backend.services.sync_engine import (
    AlignInput, align_datasets, detect_sync_pulses, find_sync_column,
    sync_window,
)


router = APIRouter(prefix="/api/sync", tags=["sync"])


# ─── preview ──────────────────────────────────────────────────────────

class PreviewPulse(BaseModel):
    fall_idx: int
    rise_idx: int
    fall_t: float
    rise_t: float
    width_s: float


class PreviewResponse(BaseModel):
    ds_id: str
    sync_col: Optional[str]
    sample_rate: float
    duration_s: float
    pulses: list[PreviewPulse]
    window: Optional[tuple[int, int]]
    window_t: Optional[tuple[float, float]]
    signal_thumb: list[float]        # downsampled to ≤ 500 points for plotting
    signal_thumb_t: list[float]


@router.get("/preview/{ds_id}", response_model=PreviewResponse)
def preview(ds_id: str) -> PreviewResponse:
    """Detect A7 pulses in this dataset and return a small thumbnail so
    the UI can draw the signal with the detected window overlaid."""
    d = _REGISTRY.get(ds_id)
    if d is None:
        raise HTTPException(status_code=404, detail=f"dataset '{ds_id}' not found")
    path = d.get("_path")
    if not path or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail=f"dataset file missing")

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"CSV unreadable: {exc}") from exc

    fs_raw = d.get("hz", "100Hz")
    try:
        fs = float(str(fs_raw).replace("Hz", "").strip())
    except ValueError:
        fs = 100.0

    col = find_sync_column(df)
    pulses_objs = []
    window = None
    window_t = None
    if col is not None:
        pulses_objs = detect_sync_pulses(df[col].to_numpy(), fs)
        w = sync_window(df[col].to_numpy(), fs)
        if w is not None:
            window = (int(w[0]), int(w[1]))
            window_t = (w[0] / fs, w[1] / fs)
        sig = df[col].to_numpy(dtype=float)
    else:
        sig = None

    # Thumbnail downsample for plotting (cap at 500 points)
    thumb: list[float] = []
    thumb_t: list[float] = []
    if sig is not None and len(sig) > 0:
        cap = 500
        if len(sig) <= cap:
            idx = range(len(sig))
        else:
            step = max(1, len(sig) // cap)
            idx = range(0, len(sig), step)
        for i in idx:
            thumb.append(float(sig[i]))
            thumb_t.append(i / fs)

    return PreviewResponse(
        ds_id=ds_id,
        sync_col=col,
        sample_rate=fs,
        duration_s=len(df) / fs,
        pulses=[PreviewPulse(
            fall_idx=p.fall_idx, rise_idx=p.rise_idx,
            fall_t=p.fall_t, rise_t=p.rise_t, width_s=p.width_s,
        ) for p in pulses_objs],
        window=window,
        window_t=window_t,
        signal_thumb=thumb,
        signal_thumb_t=thumb_t,
    )


# ─── align ────────────────────────────────────────────────────────────

class AlignRequest(BaseModel):
    dataset_ids: list[str]
    target_hz: Optional[float] = None     # default: max(fs) of inputs
    crop_to_a7: bool = True                # false → skip A7 crop, only resample
    suffix: str = "_synced"                # appended to dataset name


class AlignedDatasetInfo(BaseModel):
    original_id: str
    new_id: str
    original_name: str
    new_name: str
    original_fs: float
    target_fs: float
    window: Optional[tuple[int, int]]
    window_t: Optional[tuple[float, float]]
    sync_col_used: Optional[str]
    n_in: int
    n_out: int
    duration_s: float


class AlignResponse(BaseModel):
    target_hz: float
    common_duration_s: float
    aligned: list[AlignedDatasetInfo]
    notes: list[str]


@router.post("/align", response_model=AlignResponse)
def align(req: AlignRequest) -> AlignResponse:
    """Crop + resample all datasets to a common time grid."""
    if len(req.dataset_ids) < 1:
        raise HTTPException(status_code=400, detail="need ≥1 dataset_id")

    items: list[AlignInput] = []
    notes: list[str] = []
    for did in req.dataset_ids:
        d = _REGISTRY.get(did)
        if d is None:
            raise HTTPException(status_code=404, detail=f"dataset '{did}' not found")
        path = d.get("_path")
        if not path or not os.path.isfile(path):
            raise HTTPException(status_code=404, detail=f"dataset '{did}' file missing")
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"{did}: {exc}") from exc
        try:
            fs = float(str(d.get("hz", "100")).replace("Hz", "").strip())
        except ValueError:
            fs = 100.0
        sync_col = find_sync_column(df) if req.crop_to_a7 else None
        if req.crop_to_a7 and sync_col is None:
            notes.append(f"{d.get('name', did)}: no A7-like column detected · will not crop")
        items.append(AlignInput(
            ds_id=did, df=df, sample_rate=fs,
            source_type=d.get("source_type", "unknown"),
            sync_col=sync_col if req.crop_to_a7 else None,
        ))

    results = align_datasets(items, target_hz=req.target_hz)
    target_fs = results[0].target_fs if results else (req.target_hz or 100.0)
    common_dur = results[0].duration_s if results else 0.0
    if common_dur == 0.0:
        notes.append("warning: common duration is 0s — are all windows valid?")

    aligned: list[AlignedDatasetInfo] = []
    for r in results:
        original = _REGISTRY[r.ds_id]
        new_id = "ds_" + uuid.uuid4().hex[:8]
        new_name = original["name"].replace(".csv", "") + req.suffix + ".csv"
        new_path = _UPLOAD_DIR / f"{new_id}.csv"
        # Persist the resampled CSV to disk + register
        try:
            r.df_synced.to_csv(new_path, index=False)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"write failed for {new_id}: {exc}") from exc

        cols = r.df_synced.columns.tolist()
        col_meta = [{
            "name": c,
            "unit": _guess_unit(c),
            "mapped": _guess_role(c)[0],
            "inferred_role": _guess_role(c)[0],
            "confidence": _guess_role(c)[1],
            "preview": r.df_synced[c].head(5).astype(str).tolist(),
        } for c in cols]

        new_ds = {
            "id": new_id,
            "name": new_name,
            "tag": original.get("tag", _guess_kind(cols)),
            "kind": original.get("kind", _guess_kind(cols)),
            "rows": len(r.df_synced),
            "dur": f"{r.duration_s:.2f}s",
            "hz": f"{int(round(target_fs))}Hz",
            "cols": col_meta,
            "active": False,
            "recipeState": {},
            "subject_id": original.get("subject_id", ""),
            "condition": original.get("condition", ""),
            "group": original.get("group", ""),
            "date": original.get("date", ""),
            # Sync provenance
            "synced_from": r.ds_id,
            "source_type": original.get("source_type", "unknown"),
            "sync_target_hz": target_fs,
            "sync_window": list(r.window_samples) if r.window_samples else None,
            "_path": str(new_path),
            "_content_hash": "synced:" + new_id,
        }
        _REGISTRY[new_id] = new_ds
        try:
            register_csv_columns(str(new_path), cols)
        except Exception:
            pass

        aligned.append(AlignedDatasetInfo(
            original_id=r.ds_id,
            new_id=new_id,
            original_name=original["name"],
            new_name=new_name,
            original_fs=r.original_fs,
            target_fs=r.target_fs,
            window=list(r.window_samples) if r.window_samples else None,
            window_t=(r.window_samples[0] / r.original_fs,
                      r.window_samples[1] / r.original_fs) if r.window_samples else None,
            sync_col_used=r.sync_col_used,
            n_in=r.n_in,
            n_out=r.n_out,
            duration_s=r.duration_s,
        ))

    _save_registry()
    return AlignResponse(
        target_hz=target_fs,
        common_duration_s=common_dur,
        aligned=aligned,
        notes=notes,
    )


# ─── health / metadata ────────────────────────────────────────────────

@router.get("/needs-sync")
def needs_sync_check() -> dict[str, Any]:
    """Are there datasets with mismatched sample rates currently loaded?
    Frontend polls this to decide whether to show the sync banner."""
    rates: dict[str, list[str]] = {}
    for did, d in _REGISTRY.items():
        hz = str(d.get("hz", "100Hz"))
        rates.setdefault(hz, []).append(did)
    mixed = len(rates) > 1
    return {
        "mixed": mixed,
        "rates": {k: v for k, v in rates.items()},
        "n_datasets": len(_REGISTRY),
    }
