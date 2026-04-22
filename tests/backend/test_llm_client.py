"""
Tests for llm_client.py — all ollama.chat calls are mocked.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from backend.models.schema import AnalysisRequest
from backend.services.llm_client import parse_command, generate_insights


def _make_ollama_response(data: dict) -> MagicMock:
    """Helper: wrap dict as ollama chat response object."""
    msg = MagicMock()
    msg.content = json.dumps(data)
    resp = MagicMock()
    resp.message = msg
    return resp


def test_parse_command_force_graph():
    payload = {
        "analysis_type": "force",
        "sides": ["both"],
        "normalize_gcp": False,
        "compare_mode": False,
    }
    with patch("backend.services.llm_client.ollama.chat",
               return_value=_make_ollama_response(payload)) as mock_chat:
        result = parse_command("Force 그래프 그려줘")

    assert isinstance(result, AnalysisRequest)
    assert result.analysis_type == "force"


def test_parse_command_normalize_gcp():
    payload = {
        "analysis_type": "force",
        "sides": ["both"],
        "normalize_gcp": True,
        "compare_mode": False,
    }
    with patch("backend.services.llm_client.ollama.chat",
               return_value=_make_ollama_response(payload)):
        result = parse_command("GCP에 맞춰서 Force 보여줘")

    assert result.normalize_gcp is True


def test_parse_command_invalid_json_raises():
    bad_msg = MagicMock()
    bad_msg.content = "이건 JSON이 아닙니다"
    bad_resp = MagicMock()
    bad_resp.message = bad_msg

    with patch("backend.services.llm_client.ollama.chat",
               return_value=bad_resp):
        with pytest.raises(ValueError, match="LLM 응답 파싱 실패"):
            parse_command("뭔가 이상한 명령")


def test_parse_command_uses_correct_params():
    payload = {
        "analysis_type": "gait",
        "sides": ["both"],
        "normalize_gcp": True,
        "compare_mode": False,
    }
    with patch("backend.services.llm_client.ollama.chat",
               return_value=_make_ollama_response(payload)) as mock_chat:
        parse_command("보행 분석해줘", model="gemma4:e4b")

    call_kwargs = mock_chat.call_args[1]  # keyword args
    assert call_kwargs["model"] == "gemma4:e4b"
    assert "format" in call_kwargs
    assert call_kwargs["options"]["temperature"] == 0


def test_generate_insights_returns_string():
    """generate_insights returns a non-empty string."""
    from backend.models.schema import StatsResult
    stats = [
        StatsResult(column="L_ActForce_N", file="trial.csv",
                    mean=25.0, std=5.0, max_val=50.0, min_val=0.0),
        StatsResult(column="R_ActForce_N", file="trial.csv",
                    mean=22.0, std=4.5, max_val=48.0, min_val=0.0),
    ]
    req = AnalysisRequest(analysis_type="force")
    fake_content = "왼쪽 힘이 오른쪽보다 약간 큽니다."
    mock_resp = MagicMock()
    mock_resp.message.content = fake_content

    with patch("backend.services.llm_client.ollama.chat",
               return_value=mock_resp):
        result = generate_insights(req, stats)

    assert isinstance(result, str)
    assert len(result) > 0
