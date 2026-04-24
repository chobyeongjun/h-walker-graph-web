from fastapi import APIRouter, HTTPException
from backend.models.schema import Study, StudySummary
from backend.services.study_engine import discover_study, run_study_analysis
import json, os

router = APIRouter(prefix="/api/study", tags=["study"])

# ── Persistent storage ──────────────────────────────────────────────────
_STUDY_DIR = os.path.expanduser("~/.hw_graph")
os.makedirs(_STUDY_DIR, exist_ok=True)
_STUDY_REGISTRY_PATH = os.path.join(_STUDY_DIR, "studies.json")
_STUDY_RESULTS_PATH  = os.path.join(_STUDY_DIR, "study_results.json")

def _load_studies() -> dict[str, dict]:
    try:
        if os.path.isfile(_STUDY_REGISTRY_PATH):
            with open(_STUDY_REGISTRY_PATH) as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_studies(studies: dict) -> None:
    try:
        with open(_STUDY_REGISTRY_PATH, "w") as f:
            json.dump(studies, f, indent=2, default=str)
    except Exception as e:
        print(f"[study] registry save failed: {e}")

def _load_results() -> dict[str, dict]:
    try:
        if os.path.isfile(_STUDY_RESULTS_PATH):
            with open(_STUDY_RESULTS_PATH) as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_results(results: dict) -> None:
    try:
        with open(_STUDY_RESULTS_PATH, "w") as f:
            json.dump(results, f, indent=2, default=str)
    except Exception as e:
        print(f"[study] results save failed: {e}")

_STUDIES: dict[str, dict] = _load_studies()
_RESULTS: dict[str, dict] = _load_results()
# ────────────────────────────────────────────────────────────────────────


@router.post("/discover")
def discover(directory: str, name: str = "New Study"):
    if not os.path.isdir(directory):
        raise HTTPException(status_code=400, detail=f"Directory not found: '{directory}'")
    study = discover_study(directory, name)
    _STUDIES[study.id] = study.model_dump()
    _save_studies(_STUDIES)
    return study


@router.get("/{study_id}/analyze")
def analyze_study(study_id: str):
    if study_id not in _STUDIES:
        raise HTTPException(status_code=404, detail="Study not found")
    study = Study(**_STUDIES[study_id])
    summary = run_study_analysis(study)
    _RESULTS[study_id] = summary.model_dump()
    _save_results(_RESULTS)
    return summary


@router.get("/list")
def list_studies():
    return list(_STUDIES.values())


@router.get("/results/{study_id}")
def get_result(study_id: str):
    if study_id not in _RESULTS:
        raise HTTPException(status_code=404, detail="No result yet for this study")
    return _RESULTS[study_id]


@router.delete("/{study_id}")
def delete_study(study_id: str):
    _STUDIES.pop(study_id, None)
    _RESULTS.pop(study_id, None)
    _save_studies(_STUDIES)
    _save_results(_RESULTS)
    return {"deleted": study_id}
