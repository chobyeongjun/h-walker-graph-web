"""Google Drive OAuth2 client with local CSV cache."""
from __future__ import annotations

import io
import re
import hashlib
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from backend.models.drive_schema import DriveFile, DriveFolder

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


class DriveClient:
    def __init__(
        self,
        credentials_path: str = "~/.hw_graph/client_secret.json",
        cache_dir: str = "~/.hw_graph/cache",
    ):
        self.credentials_path = Path(credentials_path).expanduser()
        self.cache_dir = Path(cache_dir).expanduser()
        self.token_path = self.credentials_path.parent / "token.json"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._service = None

    def authenticate(self) -> None:
        """OAuth2 flow. Saves token to ~/.hw_graph/token.json."""
        creds: Optional[Credentials] = None

        if self.token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.credentials_path.exists():
                    raise FileNotFoundError(
                        f"client_secret.json not found at {self.credentials_path}. "
                        "Follow Task 1-2 credential setup instructions."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_path), SCOPES
                )
                creds = flow.run_local_server(port=0)

            self.token_path.write_text(creds.to_json())

        self._service = build("drive", "v3", credentials=creds)

    def _ensure_authenticated(self) -> None:
        if self._service is None:
            self.authenticate()

    def list_folder(self, folder_id: str = "root") -> list[DriveFile]:
        self._ensure_authenticated()
        results = (
            self._service.files()
            .list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="files(id,name,mimeType,modifiedTime,size)",
                orderBy="name",
                pageSize=200,
            )
            .execute()
        )
        items = results.get("files", [])
        return [
            DriveFile(
                id=f["id"],
                name=f["name"],
                mimeType=f["mimeType"],
                modifiedTime=f["modifiedTime"],
                size=int(f.get("size", 0)) if f.get("size") else None,
            )
            for f in items
        ]

    def download_csv(self, file_id: str, filename: str) -> str:
        """Downloads CSV to cache_dir. Skips if cached and not modified. Returns local path."""
        self._ensure_authenticated()

        meta = (
            self._service.files()
            .get(fileId=file_id, fields="modifiedTime")
            .execute()
        )
        remote_mtime = meta["modifiedTime"]

        cache_key = hashlib.md5(f"{file_id}:{remote_mtime}".encode()).hexdigest()[:8]
        stem = Path(filename).stem
        stem = re.sub(r'[^a-zA-Z0-9_\-.]', '_', stem)
        local_path = self.cache_dir / f"{stem}_{cache_key}.csv"
        local_path = local_path.resolve()
        if not str(local_path).startswith(str(self.cache_dir.resolve())):
            raise ValueError(f"Invalid filename: {filename!r}")

        if local_path.exists():
            return str(local_path)

        request = self._service.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        local_path.write_bytes(buf.getvalue())
        return str(local_path)

    def search_by_date(self, date_str: str) -> list[DriveFile]:
        """Searches Drive for CSV files whose name contains date_str."""
        self._ensure_authenticated()
        normalized = date_str.replace("-", "")
        query = (
            f"name contains '{normalized}' and mimeType='text/csv' and trashed=false"
        )
        results = (
            self._service.files()
            .list(
                q=query,
                fields="files(id,name,mimeType,modifiedTime,size)",
                orderBy="modifiedTime desc",
                pageSize=50,
            )
            .execute()
        )
        items = results.get("files", [])
        return [
            DriveFile(
                id=f["id"],
                name=f["name"],
                mimeType=f["mimeType"],
                modifiedTime=f["modifiedTime"],
                size=int(f.get("size", 0)) if f.get("size") else None,
            )
            for f in items
        ]
