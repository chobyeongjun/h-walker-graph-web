"""
/api/datasets/* — Phase 2 frontend contract (HANDOFF §2.1).

Wraps the existing tmp-file upload with a richer Dataset shape:
    {id, name, kind, rows, dur, hz, cols:[{name, unit, mapped, mappedManual}], active}

Storage is ephemeral (tmp/) until Phase B introduces SQLite metadata.
"""
from __future__ import annotations

import os
import tempfile
import uuid
from typing import Any

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.services.knowledge_loader import register_csv_columns


router = APIRouter(prefix="/api/datasets", tags=["datasets"])

# In-memory registry. Phase B: move to SQLite + signed URLs.
_REGISTRY: dict[str, dict[str, Any]] = {}


# Phase 2: filename auto-parsing regex list. Tries each pattern in order;
# first match wins. Named groups drive the Dataset.{group, subject_id,
# condition} fields. Keep these case-insensitive and tolerant of
# separators (_, -, .).
import re
_FILENAME_PATTERNS = [
    # explicit labels: subject=s01 · condition=pre · date=2024-05-01
    re.compile(r'(?i)(?:subj(?:ect)?[_-]?)?(?P<subject_id>s\d+)[_\-.]+'
               r'(?P<condition>pre|post|control|experimental|baseline|'
               r'treatment|treadmill|overground|\w{2,12})'
               r'(?:[_\-.]+(?P<date>\d{4}[_\-.]?\d{2}[_\-.]?\d{2}))?'),
    # condition first: pre_s01_… / control-subj02-…
    re.compile(r'(?i)^(?P<condition>pre|post|control|experimental|baseline|'
               r'treatment|fast|slow|natural|\w{3,10})'
               r'[_\-.]+(?:subj(?:ect)?[_-]?)?(?P<subject_id>s\d+|\d{1,3})'),
    # numeric only: 001_pre_…
    re.compile(r'(?i)^(?P<subject_id>\d{1,3})[_\-.]+(?P<condition>[a-z]{3,15})'),
    # trial_N style (keep existing recipe behavior, not really a group)
    re.compile(r'(?i)(?P<subject_id>trial[_-]?\d+)'),
]

_CONDITION_CANONICAL = {
    'pre': 'Pre', 'post': 'Post', 'control': 'Control',
    'experimental': 'Experimental', 'baseline': 'Baseline',
    'treatment': 'Treatment', 'treadmill': 'Treadmill',
    'overground': 'Overground', 'fast': 'Fast', 'slow': 'Slow',
    'natural': 'Natural',
}


def _parse_filename(fname: str) -> dict[str, str]:
    """Extract {subject_id, condition, group, date} from a filename.

    Falls back to empty dict for unrecognized patterns. The user can
    always override via PATCH /api/datasets/{id}/meta.
    """
    import os
    stem = os.path.splitext(os.path.basename(fname))[0]
    for pat in _FILENAME_PATTERNS:
        m = pat.search(stem)
        if not m:
            continue
        out: dict[str, str] = {}
        gd = m.groupdict()
        if gd.get('subject_id'):
            out['subject_id'] = gd['subject_id'].lower()
        if gd.get('condition'):
            cond = gd['condition'].lower()
            out['condition'] = _CONDITION_CANONICAL.get(cond, cond.title())
            # Group defaults to condition (user can override)
            out['group'] = out['condition']
        if gd.get('date'):
            out['date'] = gd['date']
        if out:
            return out
    return {}


_UNIT_HINTS = [
    ('force', 'N'), ('_n', 'N'),
    ('pitch', '°'), ('roll', '°'), ('yaw', '°'),
    ('vel', 'm/s'), ('pos', 'mm'), ('current', 'A'),
    ('time', 's'), ('t_', 's'),
    ('cop', 'mm'),
    ('gcp', '%'),
]
_KIND_HINTS = {
    'force': 'force', 'grf': 'force', 'cop': 'cop',
    'imu': 'imu', 'pitch': 'imu', 'gyro': 'imu', 'acc': 'imu',
    'emg': 'emg', 'trial': 'trials',
}
_ROLE_HINTS = [
    ('time', 'time'), ('t_', 'time'),
    ('l_force', 'L force'), ('l_grf', 'L force'),
    ('r_force', 'R force'), ('r_grf', 'R force'),
    ('shank', 'shank'), ('thigh', 'thigh'),
    ('trial', 'group'),
]


def _guess_unit(col: str) -> str:
    lc = col.lower()
    for hint, unit in _UNIT_HINTS:
        if hint in lc:
            return unit
    return '—'


def _guess_role(col: str) -> tuple[str, float]:
    lc = col.lower()
    for hint, role in _ROLE_HINTS:
        if hint in lc:
            return role, 0.85
    return '—', 0.0


def _guess_kind(cols: list[str]) -> str:
    joined = ' '.join(cols).lower()
    # Phase 0: if the CSV carries BOTH force and IMU-family signals, flag
    # it as 'mixed' so the canonical recipe set covers both sides.
    has_force = any(h in joined for h in ('force', 'grf'))
    has_imu = any(h in joined for h in ('pitch', 'gyro', 'acc', '_ax', '_ay', '_az',
                                         '_gx', '_gy', '_gz', 'roll', 'yaw', 'imu'))
    if has_force and has_imu:
        return 'mixed'
    for hint, kind in _KIND_HINTS.items():
        if hint in joined:
            return kind
    return 'force'


@router.post("/upload")
async def upload(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=422, detail="filename missing")
    suffix = '.csv'
    tmp = tempfile.NamedTemporaryFile(
        delete=False, suffix=suffix,
        prefix=(os.path.splitext(file.filename)[0] + '_'),
    )
    try:
        content = await file.read()
        tmp.write(content)
        tmp.close()
        df = pd.read_csv(tmp.name, nrows=500)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"CSV parse failed: {exc}") from exc

    col_names = [str(c).strip() for c in df.columns.tolist()]
    ds_id = 'ds_' + uuid.uuid4().hex[:8]
    hz = 100
    try:
        if 'time' in col_names[0].lower() or 't' == col_names[0].lower():
            dt = df.iloc[:, 0].diff().dropna().median()
            if dt and dt > 0:
                hz = int(round(1.0 / float(dt)))
    except Exception:
        pass
    kind = _guess_kind(col_names)
    rows = len(df) if len(df) < 500 else None
    # For rows > 500, count via size
    if rows is None:
        try:
            with open(tmp.name) as fh:
                rows = sum(1 for _ in fh) - 1
        except Exception:
            rows = len(df)

    cols = []
    for name in col_names:
        role, conf = _guess_role(name)
        cols.append({
            'name': name,
            'unit': _guess_unit(name),
            'mapped': role,
            'inferred_role': role,
            'confidence': conf,
            'preview': df[name].head(5).astype(str).tolist(),
        })

    try:
        register_csv_columns(tmp.name, col_names)
    except Exception:
        pass

    # Phase 2: auto-parse filename for subject/condition/group
    parsed = _parse_filename(file.filename)

    ds = {
        'id': ds_id,
        'name': file.filename,
        'tag': kind,
        'kind': kind,
        'rows': rows,
        'dur': f"{rows / hz:.1f}s" if hz else "—",
        'hz': f"{hz}Hz",
        'cols': cols,
        'active': False,
        'recipeState': {},
        'subject_id': parsed.get('subject_id', ''),
        'condition': parsed.get('condition', ''),
        'group': parsed.get('group', ''),
        'date': parsed.get('date', ''),
        '_path': tmp.name,
    }
    _REGISTRY[ds_id] = ds
    return {k: v for k, v in ds.items() if not k.startswith('_')}


@router.get("")
def list_datasets() -> list[dict[str, Any]]:
    return [{k: v for k, v in d.items() if not k.startswith('_')} for d in _REGISTRY.values()]


@router.get("/{ds_id}")
def get_dataset(ds_id: str) -> dict[str, Any]:
    if ds_id not in _REGISTRY:
        raise HTTPException(status_code=404, detail="dataset not found")
    d = _REGISTRY[ds_id]
    try:
        df = pd.read_csv(d['_path'], nrows=500)
        sample = df.head(500).to_dict(orient='records')
    except Exception:
        sample = []
    return {**{k: v for k, v in d.items() if not k.startswith('_')}, 'sample': sample}


from fastapi import Response

@router.delete("/{ds_id}")
def delete_dataset(ds_id: str) -> Response:
    d = _REGISTRY.pop(ds_id, None)
    if d:
        try:
            os.unlink(d['_path'])
        except Exception:
            pass
        # Also invalidate the analyzer cache
        try:
            from backend.routers.analyze import invalidate_cache
            invalidate_cache(ds_id)
        except Exception:
            pass
    return Response(status_code=204)


@router.patch("/{ds_id}/meta")
def update_meta(ds_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Phase 2 · Update dataset's group/subject/condition tags."""
    if ds_id not in _REGISTRY:
        raise HTTPException(status_code=404, detail="dataset not found")
    d = _REGISTRY[ds_id]
    for key in ('subject_id', 'condition', 'group', 'date'):
        if key in payload:
            d[key] = str(payload[key] or '')
    return {k: v for k, v in d.items() if not k.startswith('_')}


@router.post("/{ds_id}/mapping")
def save_mapping(ds_id: str, payload: dict[str, Any]) -> dict[str, int]:
    if ds_id not in _REGISTRY:
        raise HTTPException(status_code=404, detail="dataset not found")
    columns = payload.get('columns', {}) or {}
    d = _REGISTRY[ds_id]
    updated = 0
    for c in d['cols']:
        new_role = columns.get(c['name'])
        if new_role and new_role != c['mapped']:
            c['mapped'] = new_role
            c['mappedManual'] = True
            updated += 1
    return {'updated': updated}


def get_path(ds_id: str) -> str | None:
    return _REGISTRY.get(ds_id, {}).get('_path')
