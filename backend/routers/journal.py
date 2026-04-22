"""Journal style router: /api/journal/*"""
from __future__ import annotations

import asyncio
import json
from fastapi import APIRouter, HTTPException, Query

from backend.services.journal_resolver import resolve_journal, load_preset, STYLES_DIR

router = APIRouter(prefix="/api/journal", tags=["journal"])


@router.get("/list")
async def list_journals():
    """Returns list of available preset journal keys and names."""
    journals = []
    for p in sorted(STYLES_DIR.glob("*.json")):
        if "cached" in str(p):
            continue
        try:
            data = json.loads(p.read_text())
            journals.append({"key": data.get("key", p.stem), "name": data.get("name", p.stem)})
        except Exception:
            continue
    return {"journals": journals}


@router.get("/resolve")
async def resolve_journal_endpoint(journal_name: str = Query(...)):
    """Resolves a journal name to style parameters. Uses Gemma 4 for unknown journals."""
    try:
        loop = asyncio.get_event_loop()
        style = await loop.run_in_executor(None, resolve_journal, journal_name)
        return style
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Journal resolution failed: {e}")
