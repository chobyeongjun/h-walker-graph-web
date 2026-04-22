"""
Tests for chat router — llm_client is patched, no real Ollama calls.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.main import app
from backend.models.schema import AnalysisRequest


def _make_analysis_request(**kwargs) -> AnalysisRequest:
    defaults = {
        "analysis_type": "force",
        "sides": ["both"],
        "normalize_gcp": False,
        "compare_mode": False,
    }
    defaults.update(kwargs)
    return AnalysisRequest(**defaults)


client = TestClient(app)


def test_post_chat_returns_analysis_request():
    mock_req = _make_analysis_request(analysis_type="force")
    with patch("backend.routers.chat.parse_command",
               return_value=mock_req):
        resp = client.post("/api/chat", json={
            "message": "Force 그래프 그려줘",
            "history": [],
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["analysis_request"]["analysis_type"] == "force"
    assert "message" in data


def test_post_chat_accepts_history():
    mock_req = _make_analysis_request(analysis_type="imu")
    with patch("backend.routers.chat.parse_command",
               return_value=mock_req):
        resp = client.post("/api/chat", json={
            "message": "IMU 데이터 보여줘",
            "history": [
                {"role": "user", "content": "이전 메시지"},
                {"role": "assistant", "content": "이전 응답"},
            ],
        })
    assert resp.status_code == 200
    assert resp.json()["analysis_request"]["analysis_type"] == "imu"


def test_post_chat_llm_error_returns_422():
    with patch("backend.routers.chat.parse_command",
               side_effect=ValueError("LLM 응답 파싱 실패: bad json")):
        resp = client.post("/api/chat", json={
            "message": "알 수 없는 명령",
            "history": [],
        })
    assert resp.status_code == 422


def test_get_chat_models():
    mock_list = MagicMock()
    mock_list.models = [
        MagicMock(model="gemma4:e4b"),
        MagicMock(model="llama3:8b"),
    ]
    with patch("backend.routers.chat.ollama.list",
               return_value=mock_list):
        resp = client.get("/api/chat/models")
    assert resp.status_code == 200
    models = resp.json()["models"]
    assert "gemma4:e4b" in models


def test_websocket_chat_flow():
    mock_req = _make_analysis_request(analysis_type="gait", normalize_gcp=True)

    async def fake_stream(*args, **kwargs):
        for token in ["보행", " 분석", " 완료"]:
            yield token

    with patch("backend.routers.chat.parse_command",
               return_value=mock_req), \
         patch("backend.routers.chat.generate_insights_stream",
               side_effect=fake_stream):
        with client.websocket_connect("/ws/chat") as ws:
            ws.send_json({"message": "보행 분석해줘", "history": []})
            msgs = []
            for _ in range(5):
                try:
                    msgs.append(ws.receive_json())
                except Exception:
                    break

    types = [m["type"] for m in msgs]
    assert "analysis_request" in types
    assert "done" in types
    token_msgs = [m for m in msgs if m["type"] == "token"]
    assert len(token_msgs) >= 1
