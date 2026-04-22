from fastapi import APIRouter, HTTPException
from backend.models.schema import Study, StudySummary
from backend.services.study_engine import discover_study, run_study_analysis
import os

router = APIRouter(prefix="/api/study", tags=["study"])

# In-memory store for studies
_STUDIES: dict[str, Study] = {}

@router.post("/discover")
def discover(directory: str, name: str = "New Study"):
    if not os.path.isdir(directory):
        raise HTTPException(status_code=400, detail="Invalid directory")
    study = discover_study(directory, name)
    _STUDIES[study.id] = study
    return study

@router.get("/{study_id}/analyze")
def analyze_study(study_id: str):
    if study_id not in _STUDIES:
        raise HTTPException(status_code=404, detail="Study not found")
    summary = run_study_analysis(_STUDIES[study_id])
    return summary

@router.get("/list")
def list_studies():
    return list(_STUDIES.values())
