import pytest
from backend.models.schema import (
    AnalysisType,
    COLUMN_GROUPS,
    AnalysisRequest,
    GraphSpec,
    StatsResult,
    PlotlyTrace,
    PlotlyResponse,
)


class TestAnalysisType:
    def test_all_variants_exist(self):
        expected = {
            "force", "velocity", "position", "current",
            "imu", "gyro", "accel", "gait", "gcp",
            "feedforward", "compare",
        }
        actual = {m.value for m in AnalysisType}
        assert actual == expected


class TestColumnGroups:
    def test_all_types_have_entry(self):
        for t in AnalysisType:
            assert t in COLUMN_GROUPS, f"COLUMN_GROUPS missing key: {t}"

    def test_force_columns_include_actforce(self):
        cols = COLUMN_GROUPS[AnalysisType.force]
        assert "L_ActForce_N" in cols
        assert "R_ActForce_N" in cols

    def test_velocity_columns_correct(self):
        cols = COLUMN_GROUPS[AnalysisType.velocity]
        assert "L_ActVel_mps" in cols
        assert "R_ActVel_mps" in cols

    def test_gcp_columns_include_both_sides(self):
        cols = COLUMN_GROUPS[AnalysisType.gcp]
        assert "L_GCP" in cols
        assert "R_GCP" in cols

    def test_imu_columns_include_pitch_roll_yaw(self):
        cols = COLUMN_GROUPS[AnalysisType.imu]
        for name in ["L_Pitch", "R_Pitch", "L_Roll", "R_Roll", "L_Yaw", "R_Yaw"]:
            assert name in cols

    def test_gyro_uses_Gx_Gy_Gz(self):
        cols = COLUMN_GROUPS[AnalysisType.gyro]
        assert "L_Gx" in cols
        assert "R_Gz" in cols

    def test_accel_uses_Ax_Ay_Az(self):
        cols = COLUMN_GROUPS[AnalysisType.accel]
        assert "L_Ax" in cols
        assert "R_Az" in cols

    def test_gait_columns_include_phase_and_event(self):
        cols = COLUMN_GROUPS[AnalysisType.gait]
        for name in ["L_Phase", "R_Phase", "L_Event", "R_Event", "L_GCP", "R_GCP", "L_ActForce_N", "R_ActForce_N"]:
            assert name in cols

    def test_feedforward_uses_MotionFF(self):
        cols = COLUMN_GROUPS[AnalysisType.feedforward]
        assert "L_MotionFF_mps" in cols
        assert "R_MotionFF_mps" in cols


class TestAnalysisRequest:
    def test_defaults(self):
        req = AnalysisRequest(analysis_type=AnalysisType.force)
        assert req.columns is None
        assert req.sides == ["both"]
        assert req.normalize_gcp is False
        assert req.compare_mode is False
        assert req.file_paths == []
        assert req.statistics is False

    def test_resolve_columns_uses_default_when_none(self):
        req = AnalysisRequest(analysis_type=AnalysisType.force)
        resolved = req.resolve_columns()
        assert "L_ActForce_N" in resolved
        assert "R_ActForce_N" in resolved

    def test_resolve_columns_uses_explicit_when_given(self):
        req = AnalysisRequest(
            analysis_type=AnalysisType.force,
            columns=["L_ActForce_N"],
        )
        resolved = req.resolve_columns()
        assert resolved == ["L_ActForce_N"]

    def test_resolve_columns_left_only(self):
        req = AnalysisRequest(analysis_type=AnalysisType.force, sides=["left"])
        resolved = req.resolve_columns()
        assert all(col.startswith("L_") for col in resolved)
        assert not any(col.startswith("R_") for col in resolved)

    def test_resolve_columns_right_only(self):
        req = AnalysisRequest(analysis_type=AnalysisType.force, sides=["right"])
        resolved = req.resolve_columns()
        assert all(col.startswith("R_") for col in resolved)
        assert not any(col.startswith("L_") for col in resolved)

    def test_resolve_columns_both_returns_all(self):
        req = AnalysisRequest(analysis_type=AnalysisType.force, sides=["both"])
        resolved = req.resolve_columns()
        assert any(col.startswith("L_") for col in resolved)
        assert any(col.startswith("R_") for col in resolved)

    def test_explicit_columns_ignores_sides_filter(self):
        req = AnalysisRequest(
            analysis_type=AnalysisType.force,
            columns=["L_ActForce_N", "R_ActForce_N"],
            sides=["left"],
        )
        resolved = req.resolve_columns()
        assert resolved == ["L_ActForce_N", "R_ActForce_N"]

    def test_json_schema_generation(self):
        schema = AnalysisRequest.model_json_schema()
        assert schema["type"] == "object"
        assert "analysis_type" in schema["properties"]

    def test_resolve_columns_returns_list_type(self):
        """resolve_columns always returns a list, even if COLUMN_GROUPS somehow has empty entry."""
        req = AnalysisRequest(analysis_type=AnalysisType.force)
        result = req.resolve_columns()
        assert isinstance(result, list)

    def test_resolve_columns_compare_falls_back_to_force_cols(self):
        req = AnalysisRequest(analysis_type=AnalysisType.compare)
        result = req.resolve_columns()
        assert "L_ActForce_N" in result


class TestGraphSpec:
    def test_construction(self):
        req = AnalysisRequest(analysis_type=AnalysisType.force)
        spec = GraphSpec(request=req, csv_paths=["/data/trial1.csv"])
        assert spec.csv_paths == ["/data/trial1.csv"]
        assert spec.request.analysis_type == AnalysisType.force


class TestStatsResult:
    def test_construction(self):
        s = StatsResult(
            column="L_ActForce_N", file="trial1.csv",
            mean=30.5, std=4.2, max_val=68.0, min_val=0.0,
        )
        assert s.mean == 30.5


class TestPlotlyModels:
    def test_plotly_trace(self):
        trace = PlotlyTrace(
            x=[0, 1, 2], y=[10.0, 20.0, 30.0],
            name="trial1/L_ActForce_N", mode="lines",
            line={"color": "#1f77b4", "width": 1.5},
        )
        assert trace.name == "trial1/L_ActForce_N"

    def test_plotly_response(self):
        resp = PlotlyResponse(
            data=[{"x": [0], "y": [0], "name": "t", "mode": "lines", "line": {}}],
            layout={"title": {"text": "Force"}},
        )
        assert "title" in resp.layout
