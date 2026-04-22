"""Drive API router: /api/drive/*"""
from __future__ import annotations

import re
import secrets
from typing import Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from backend.services.drive_client import DriveClient, SCOPES
from backend.models.drive_schema import DriveFile, DriveFolder

router = APIRouter(prefix="/api/drive", tags=["drive"])

_client = DriveClient()
_oauth_state: str | None = None


def _validate_file_id(file_id: str) -> None:
    """Google Drive file IDs are alphanumeric + _ and - characters."""
    if not re.match(r'^[a-zA-Z0-9_\-]{10,50}$', file_id):
        raise HTTPException(status_code=400, detail=f"Invalid file ID format: {file_id!r}")


def _get_auth_url() -> str:
    global _oauth_state
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds_path = Path("~/.hw_graph/client_secret.json").expanduser()
    if not creds_path.exists():
        raise HTTPException(
            status_code=503,
            detail="client_secret.json not found. Complete Task 1-2 setup.",
        )
    flow = InstalledAppFlow.from_client_secrets_file(
        str(creds_path),
        SCOPES,
        redirect_uri="http://localhost:8000/api/drive/callback",
    )
    _oauth_state = secrets.token_urlsafe(16)
    auth_url, _ = flow.authorization_url(prompt="consent", state=_oauth_state)
    return auth_url


@router.get("/auth")
async def auth_status():
    token_path = Path("~/.hw_graph/token.json").expanduser()
    if token_path.exists():
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        if creds and creds.valid:
            return {"status": "authenticated"}
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
            return {"status": "authenticated"}

    try:
        auth_url = _get_auth_url()
        return {"status": "unauthenticated", "auth_url": auth_url}
    except HTTPException:
        return {"status": "unauthenticated", "auth_url": None}


@router.get("/callback")
async def oauth_callback(code: str = Query(...), state: Optional[str] = Query(None)):
    global _oauth_state
    if _oauth_state and state != _oauth_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    _oauth_state = None  # consume

    from google_auth_oauthlib.flow import InstalledAppFlow

    creds_path = Path("~/.hw_graph/client_secret.json").expanduser()
    token_path = Path("~/.hw_graph/token.json").expanduser()

    flow = InstalledAppFlow.from_client_secrets_file(
        str(creds_path),
        SCOPES,
        redirect_uri="http://localhost:8000/api/drive/callback",
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    token_path.write_text(creds.to_json())
    return {"status": "authenticated", "message": "Token saved. You can close this tab."}


@router.get("/files", response_model=DriveFolder)
async def list_files(folder_id: str = Query("root")):
    if folder_id != "root":
        _validate_file_id(folder_id)
    try:
        items = _client.list_folder(folder_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Drive error: {e}")

    files = [f for f in items if not f.is_folder]
    subfolders = [
        DriveFolder(id=f.id, name=f.name)
        for f in items
        if f.is_folder
    ]

    folder_name = "root" if folder_id == "root" else folder_id
    return DriveFolder(id=folder_id, name=folder_name, files=files, subfolders=subfolders)


@router.get("/download/{file_id}")
async def download_file(file_id: str, filename: str = Query(...)):
    _validate_file_id(file_id)
    try:
        local_path = _client.download_csv(file_id, filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {e}")
    return {"local_path": local_path, "filename": filename}


@router.get("/search", response_model=list[DriveFile])
async def search_files(q: str = Query(...)):
    try:
        results = _client.search_by_date(q)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")
    return results
