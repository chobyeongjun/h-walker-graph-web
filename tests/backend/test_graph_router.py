import json
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


class TestQuickEndpoint:
    def test_post_quick_returns_200(self, sample_csv):
        payload = {
            "request": {
                "analysis_type": "force",
                "columns": ["L_ActForce_N", "R_ActForce_N"],
                "sides": ["both"],
                "normalize_gcp": False,
                "compare_mode": False,
                "file_paths": [],
                "statistics": False,
            },
            "csv_paths": [sample_csv],
        }
        resp = client.post("/api/graph/quick", json=payload)
        assert resp.status_code == 200

    def test_quick_response_has_data_and_layout(self, sample_csv):
        payload = {
            "request": {
                "analysis_type": "force",
                "columns": ["L_ActForce_N"],
            },
            "csv_paths": [sample_csv],
        }
        resp = client.post("/api/graph/quick", json=payload)
        body = resp.json()
        assert "data" in body
        assert "layout" in body

    def test_quick_data_is_non_empty(self, sample_csv):
        payload = {
            "request": {
                "analysis_type": "force",
                "columns": ["L_ActForce_N"],
            },
            "csv_paths": [sample_csv],
        }
        resp = client.post("/api/graph/quick", json=payload)
        body = resp.json()
        assert len(body["data"]) > 0

    def test_quick_trace_has_x_y_name(self, sample_csv):
        payload = {
            "request": {
                "analysis_type": "force",
                "columns": ["L_ActForce_N"],
            },
            "csv_paths": [sample_csv],
        }
        resp = client.post("/api/graph/quick", json=payload)
        trace = resp.json()["data"][0]
        assert "x" in trace
        assert "y" in trace
        assert "name" in trace

    def test_quick_nonexistent_csv_returns_422_or_500(self, tmp_path):
        payload = {
            "request": {
                "analysis_type": "force",
                "columns": ["L_ActForce_N"],
            },
            "csv_paths": [str(tmp_path / "ghost.csv")],
        }
        resp = client.post("/api/graph/quick", json=payload)
        assert resp.status_code in (404, 422, 500)

    def test_quick_normalize_gcp_returns_101_point_traces(self, sample_csv):
        payload = {
            "request": {
                "analysis_type": "force",
                "columns": ["L_ActForce_N"],
                "normalize_gcp": True,
            },
            "csv_paths": [sample_csv],
        }
        resp = client.post("/api/graph/quick", json=payload)
        trace = resp.json()["data"][0]
        assert len(trace["x"]) == 101


class TestPublicationEndpoint:
    def test_post_publication_returns_200(self, sample_csv):
        payload = {
            "request": {
                "analysis_type": "force",
                "columns": ["L_ActForce_N"],
            },
            "csv_paths": [sample_csv],
        }
        resp = client.post("/api/graph/publication", json=payload)
        assert resp.status_code == 200

    def test_publication_content_type_is_svg(self, sample_csv):
        payload = {
            "request": {
                "analysis_type": "force",
                "columns": ["L_ActForce_N"],
            },
            "csv_paths": [sample_csv],
        }
        resp = client.post("/api/graph/publication", json=payload)
        assert "svg" in resp.headers["content-type"]

    def test_publication_body_contains_svg_tag(self, sample_csv):
        payload = {
            "request": {
                "analysis_type": "force",
                "columns": ["L_ActForce_N"],
            },
            "csv_paths": [sample_csv],
        }
        resp = client.post("/api/graph/publication", json=payload)
        assert "<svg" in resp.text

    def test_publication_journal_query_param(self, sample_csv):
        payload = {
            "request": {
                "analysis_type": "force",
                "columns": ["L_ActForce_N"],
            },
            "csv_paths": [sample_csv],
        }
        resp = client.post(
            "/api/graph/publication?journal=ieee_tnsre",
            json=payload,
        )
        assert resp.status_code == 200
        assert "<svg" in resp.text

    def test_publication_default_journal_when_omitted(self, sample_csv):
        payload = {
            "request": {
                "analysis_type": "force",
                "columns": ["L_ActForce_N"],
            },
            "csv_paths": [sample_csv],
        }
        resp = client.post("/api/graph/publication", json=payload)
        assert resp.status_code == 200


class TestJournalListEndpoint:
    def test_get_journal_list_returns_200(self):
        resp = client.get("/api/journal/list")
        assert resp.status_code == 200

    def test_journal_list_is_a_list(self):
        resp = client.get("/api/journal/list")
        body = resp.json()
        assert isinstance(body, list)

    def test_journal_list_contains_expected_journals(self):
        resp = client.get("/api/journal/list")
        journals = resp.json()
        for expected in ["ieee_tnsre", "jner", "default", "nature"]:
            assert expected in journals, f"Missing journal: {expected}"

    def test_journal_list_has_10_entries(self):
        from backend.services.graph_publication import JOURNAL_RCPARAMS
        resp = client.get("/api/journal/list")
        assert len(resp.json()) == len(JOURNAL_RCPARAMS)
