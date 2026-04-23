"""
/api/sync/split

HIGH-level (analog HIGH = ON) 기반 조건 구분 & 데이터 분할.

Edge detection (rising/falling)과 다름:
- 신호가 HIGH인 구간 전체 = 하나의 조건 세션
- 신호 값이 바뀌면 다른 조건으로 간주
- 각 조건 구간을 독립적인 CSV로 저장 후 dataset으로 등록

사용 시나리오:
  - 아날로그 채널이 700/750/800/850 같은 여러 레벨을 가질 때
  - 채널이 0(대기) ↔ HIGH(활성) 이진 스위칭일 때
  - Desire Position이 -60/0/60처럼 조건을 표현할 때
"""
from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.routers.datasets import _UPLOAD_DIR, _REGISTRY, _HASH_INDEX, _save_registry, _content_hash, _detect_hz, _guess_kind, _guess_role, _guess_unit, _parse_filename
from backend.services.sync_engine import find_sync_column

router_split = APIRouter(prefix="/api/sync/split", tags=["sync"])


# ─── 요청/응답 스키마 ─────────────────────────────────────────────────

class SplitRequest(BaseModel):
    ds_id: str
    signal_col: Optional[str] = None      # 조건 구분 컬럼 (None이면 자동 탐지)
    baseline_value: Optional[float] = None  # 이 값은 '대기/비활성' (None이면 0 or 최빈값)
    min_duration_s: float = 0.5           # 이 초 미만 구간은 무시 (노이즈)
    merge_gap_s: float = 0.1              # 이 이하 간격은 같은 구간으로 합침


@dataclass
class Segment:
    condition_value: float
    start_idx: int
    end_idx: int
    n_rows: int
    duration_s: float


class SegmentInfo(BaseModel):
    condition_value: float
    start_idx: int
    end_idx: int
    n_rows: int
    duration_s: float
    new_ds_id: Optional[str] = None
    new_name: Optional[str] = None


class SplitResponse(BaseModel):
    source_ds_id: str
    signal_col: str
    n_segments: int
    total_duration_s: float
    segments: list[SegmentInfo]


# ─── 조건 컬럼 자동 탐지 ────────────────────────────────────────────

def _find_condition_column(df: pd.DataFrame, known_sync_col: Optional[str] = None) -> Optional[str]:
    """
    '조건 구분' 역할을 하는 컬럼을 자동으로 찾는다.

    우선순위:
    1. 명시적으로 전달된 signal_col
    2. A7 / analog_sync 등 알려진 패턴
    3. 이진(2개 유니크값) 또는 소수(3~8개 유니크값) 정수/소수 컬럼
       - 값들이 규칙적인 간격을 가질수록 조건 컬럼일 가능성 높음
    """
    if known_sync_col and known_sync_col in df.columns:
        return known_sync_col

    # 먼저 sync 패턴 컬럼 (컬럼명이 문자열인 경우에만)
    try:
        if all(isinstance(c, str) for c in df.columns):
            auto = find_sync_column(df)
            if auto:
                return auto
    except Exception:
        pass

    # 유니크 값이 2~10개이고 일정한 간격을 가진 숫자 컬럼
    candidates = []
    for col in df.select_dtypes(include=[np.number]).columns:
        u = df[col].dropna().unique()
        n_unique = len(u)
        if 2 <= n_unique <= 10:
            # 간격의 표준편차가 낮을수록 "레벨" 컬럼
            sorted_u = np.sort(u)
            if len(sorted_u) >= 2:
                gaps = np.diff(sorted_u)
                cv = np.std(gaps) / (np.mean(gaps) + 1e-9)  # 변동계수
                candidates.append((cv, col, n_unique))

    if candidates:
        # 변동계수가 가장 낮은 컬럼 (가장 규칙적인 레벨 구조)
        candidates.sort(key=lambda x: x[0])
        return candidates[0][1]

    return None


# ─── 구간 탐지 ─────────────────────────────────────────────────────

def detect_condition_segments(
    signal: pd.Series,
    sample_rate: float,
    baseline_value: Optional[float] = None,
    min_duration_s: float = 0.5,
    merge_gap_s: float = 0.1,
) -> list[Segment]:
    """
    HIGH-level 기반 조건 구간 탐지.

    - baseline_value(기본값 None → 0 or 최빈값)을 '비활성' 상태로 간주
    - 나머지 HIGH 레벨 구간들을 독립 세그먼트로 분류
    - 같은 레벨이 연속되면 하나의 세그먼트로 합침
    - min_duration_s 미만 구간은 제거
    """
    sig = signal.reset_index(drop=True)
    n = len(sig)

    # baseline 결정
    # - 명시적으로 지정된 경우 → 그 값이 '비활성'
    # - None이고 0이 있으면 → 0이 '대기/비활성'
    # - None이고 0이 없으면 → baseline 없음 (모든 구간이 활성)
    has_zero = (sig == 0).any()
    if baseline_value is None:
        effective_baseline = 0.0 if has_zero else None
    else:
        effective_baseline = baseline_value

    min_samples = max(1, int(round(min_duration_s * sample_rate)))
    merge_samples = max(0, int(round(merge_gap_s * sample_rate)))

    # 연속 구간 탐지
    segments: list[Segment] = []
    i = 0
    while i < n:
        val = sig.iloc[i]
        if effective_baseline is not None and (val == effective_baseline) or (isinstance(val, float) and np.isnan(val)):
            i += 1
            continue

        # 이 값이 유지되는 끝 지점 찾기
        j = i + 1
        while j < n and sig.iloc[j] == val:
            j += 1

        seg_len = j - i
        if seg_len >= min_samples:
            segments.append(Segment(
                condition_value=float(val),
                start_idx=i,
                end_idx=j - 1,
                n_rows=seg_len,
                duration_s=seg_len / sample_rate,
            ))
        i = j

    return segments


# ─── API 엔드포인트 ─────────────────────────────────────────────────

@router_split.post("/preview")
def split_preview(req: SplitRequest) -> dict[str, Any]:
    """실제 분할은 하지 않고 감지된 구간만 반환 (확인용)."""
    ds = _REGISTRY.get(req.ds_id)
    if not ds:
        raise HTTPException(status_code=404, detail=f"Dataset '{req.ds_id}' not found")

    df = _load_df(ds["_path"])
    sample_rate = _parse_hz(ds.get("hz", "100Hz"))

    sig_col = req.signal_col or _find_condition_column(df, ds.get("sync_col"))
    if not sig_col:
        raise HTTPException(status_code=422, detail="조건 구분 컬럼을 찾을 수 없습니다. signal_col을 직접 지정해주세요.")

    segments = detect_condition_segments(
        df[sig_col], sample_rate,
        baseline_value=req.baseline_value,
        min_duration_s=req.min_duration_s,
        merge_gap_s=req.merge_gap_s,
    )

    total_dur = sum(s.duration_s for s in segments)
    return {
        "source_ds_id": req.ds_id,
        "signal_col": sig_col,
        "baseline_value": req.baseline_value,
        "n_segments": len(segments),
        "total_duration_s": round(total_dur, 3),
        "segments": [
            {
                "condition_value": s.condition_value,
                "start_idx": s.start_idx,
                "end_idx": s.end_idx,
                "n_rows": s.n_rows,
                "duration_s": round(s.duration_s, 3),
            }
            for s in segments
        ],
    }


@router_split.post("/execute")
def split_execute(req: SplitRequest) -> SplitResponse:
    """
    조건 구간 탐지 후 각 구간을 독립 CSV로 저장하고 데이터셋으로 등록.
    반환: 등록된 새 데이터셋 ID + 메타 목록
    """
    ds = _REGISTRY.get(req.ds_id)
    if not ds:
        raise HTTPException(status_code=404, detail=f"Dataset '{req.ds_id}' not found")

    df = _load_df(ds["_path"])
    sample_rate = _parse_hz(ds.get("hz", "100Hz"))
    src_name = os.path.splitext(ds["name"])[0]

    sig_col = req.signal_col or _find_condition_column(df, ds.get("sync_col"))
    if not sig_col:
        raise HTTPException(status_code=422, detail="조건 구분 컬럼을 찾을 수 없습니다. signal_col을 직접 지정해주세요.")

    segments = detect_condition_segments(
        df[sig_col], sample_rate,
        baseline_value=req.baseline_value,
        min_duration_s=req.min_duration_s,
        merge_gap_s=req.merge_gap_s,
    )

    if not segments:
        raise HTTPException(status_code=422, detail="유효한 조건 구간이 감지되지 않았습니다.")

    result_segments: list[SegmentInfo] = []

    for idx, seg in enumerate(segments):
        seg_df = df.iloc[seg.start_idx: seg.end_idx + 1].reset_index(drop=True)
        cond_label = f"cond{int(seg.condition_value)}"
        new_name = f"{src_name}_{cond_label}_seg{idx+1}.csv"

        # 저장 & 등록
        csv_bytes = seg_df.to_csv(index=False).encode()
        chash = _content_hash(csv_bytes)

        if chash in _HASH_INDEX:
            new_id = _HASH_INDEX[chash]
        else:
            save_path = _UPLOAD_DIR / f"{chash}.csv"
            save_path.write_bytes(csv_bytes)
            new_id = "ds_" + uuid.uuid4().hex[:8]

            col_names = [str(c).strip() for c in seg_df.columns.tolist()]
            hz = _detect_hz(col_names, seg_df)
            kind = _guess_kind(col_names)
            rows = len(seg_df)
            cols_meta = []
            for cname in col_names:
                role, conf = _guess_role(cname)
                cols_meta.append({
                    "name": cname,
                    "unit": _guess_unit(cname),
                    "mapped": role,
                    "inferred_role": role,
                    "confidence": conf,
                    "preview": seg_df[cname].head(5).astype(str).tolist(),
                })

            parsed = _parse_filename(new_name)
            new_ds: dict[str, Any] = {
                "id": new_id,
                "name": new_name,
                "tag": kind,
                "kind": kind,
                "rows": rows,
                "dur": f"{rows / hz:.1f}s" if hz else "—",
                "hz": f"{hz}Hz",
                "cols": cols_meta,
                "active": False,
                "recipeState": {},
                "subject_id": parsed.get("subject_id", ""),
                "condition": cond_label,
                "group": cond_label,
                "date": parsed.get("date", ""),
                "sync_col": None,
                "source_type": ds.get("source_type", "unknown"),
                "synced_from": None,
                "split_from": req.ds_id,
                "split_condition": seg.condition_value,
                "_path": str(save_path),
                "_content_hash": chash,
            }
            _REGISTRY[new_id] = new_ds
            _HASH_INDEX[chash] = new_id

        result_segments.append(SegmentInfo(
            condition_value=seg.condition_value,
            start_idx=seg.start_idx,
            end_idx=seg.end_idx,
            n_rows=seg.n_rows,
            duration_s=round(seg.duration_s, 3),
            new_ds_id=new_id,
            new_name=new_name,
        ))

    _save_registry()
    total_dur = sum(s.duration_s for s in result_segments)

    return SplitResponse(
        source_ds_id=req.ds_id,
        signal_col=sig_col,
        n_segments=len(result_segments),
        total_duration_s=round(total_dur, 3),
        segments=result_segments,
    )


# ─── 헬퍼 ──────────────────────────────────────────────────────────

def _load_df(path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
        # 컬럼 수 불일치 (헤더 < 데이터) 자동 처리
        with open(path) as f:
            header_cols = len(f.readline().split(","))
            data_cols = len(f.readline().split(","))
        if data_cols > header_cols:
            df = pd.read_csv(path, header=None, skiprows=1, index_col=False)
        return df
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"CSV 읽기 실패: {e}")


def _parse_hz(hz_str: str) -> float:
    try:
        return float(hz_str.replace("Hz", "").strip())
    except Exception:
        return 100.0
