"""Tests for Drive router and DriveClient. All Drive API calls are mocked."""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from pathlib import Path


FAKE_FILES = [
    {
        "id": "file1",
        "name": "2026-04-15_test.csv",
        "mimeType": "text/csv",
        "modifiedTime": "2026-04-15T10:00:00.000Z",
        "size": "1024",
    },
    {
        "id": "folder1",
        "name": "experiments",
        "mimeType": "application/vnd.google-apps.folder",
        "modifiedTime": "2026-04-14T08:00:00.000Z",
    },
]


@pytest.fixture
def mock_drive_service():
    svc = MagicMock()
    svc.files().list().execute.return_value = {"files": FAKE_FILES}
    svc.files().get().execute.return_value = {"modifiedTime": "2026-04-15T10:00:00.000Z"}
    return svc


@pytest.fixture
def drive_client(tmp_path, mock_drive_service):
    from services.drive_client import DriveClient

    client = DriveClient(
        credentials_path=str(tmp_path / "client_secret.json"),
        cache_dir=str(tmp_path / "cache"),
    )
    client._service = mock_drive_service
    return client


def test_list_folder_returns_drive_files(drive_client):
    items = drive_client.list_folder("root")
    assert len(items) == 2
    csv_files = [f for f in items if f.mimeType == "text/csv"]
    assert csv_files[0].name == "2026-04-15_test.csv"
    assert csv_files[0].size == 1024


def test_list_folder_includes_folders(drive_client):
    items = drive_client.list_folder("root")
    folders = [f for f in items if f.is_folder]
    assert len(folders) == 1
    assert folders[0].name == "experiments"


def test_download_csv_caches_file(drive_client, tmp_path):
    """Second download should NOT re-fetch from Drive."""
    fake_bytes = b"col1,col2\n1,2\n3,4\n"

    with patch("services.drive_client.MediaIoBaseDownload") as MockDL:
        instance = MockDL.return_value
        instance.next_chunk.return_value = (None, True)
        with patch("services.drive_client.io.BytesIO") as MockBuf:
            mock_buf = MagicMock()
            mock_buf.getvalue.return_value = fake_bytes
            MockBuf.return_value = mock_buf

            path1 = drive_client.download_csv("file1", "2026-04-15_test.csv")
            path2 = drive_client.download_csv("file1", "2026-04-15_test.csv")

    assert path1 == path2


def test_search_by_date_normalizes_dashes(drive_client):
    drive_client._service.files().list().execute.return_value = {"files": [FAKE_FILES[0]]}
    results = drive_client.search_by_date("2026-04-15")
    assert len(results) == 1
    call_kwargs = drive_client._service.files().list.call_args_list[-1][1]
    assert "20260415" in call_kwargs["q"]


def test_drive_file_is_folder_property():
    from models.drive_schema import DriveFile
    folder = DriveFile(
        id="f1", name="exp", mimeType="application/vnd.google-apps.folder", modifiedTime="2026-01-01T00:00:00Z"
    )
    assert folder.is_folder is True
    csv = DriveFile(
        id="f2", name="data.csv", mimeType="text/csv", modifiedTime="2026-01-01T00:00:00Z"
    )
    assert csv.is_folder is False
    assert csv.is_csv is True


@pytest.fixture
def app_client(drive_client):
    from fastapi import FastAPI
    import routers.drive as drive_router_module
    drive_router_module._client = drive_client

    mini_app = FastAPI()
    mini_app.include_router(drive_router_module.router)
    return TestClient(mini_app)


def test_list_files_endpoint(app_client):
    resp = app_client.get("/api/drive/files?folder_id=root")
    assert resp.status_code == 200
    data = resp.json()
    assert "files" in data
    assert "subfolders" in data
    assert len(data["subfolders"]) == 1


def test_search_endpoint(app_client, drive_client):
    drive_client._service.files().list().execute.return_value = {"files": [FAKE_FILES[0]]}
    resp = app_client.get("/api/drive/search?q=2026-04-15")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
