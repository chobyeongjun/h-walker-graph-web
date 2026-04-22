import pytest
from backend.services.graph_publication import (
    JOURNAL_RCPARAMS,
    SERIES_COLORS,
    render_svg,
)
from backend.models.schema import AnalysisRequest, AnalysisType


class TestJournalRcparams:
    EXPECTED_JOURNALS = {
        "ieee_tnsre", "jner", "ieee_ral", "science_robotics",
        "biomechanics", "gait_posture", "plos_one", "nature",
        "icra_iros", "default",
    }

    def test_all_journals_present(self):
        assert set(JOURNAL_RCPARAMS.keys()) == self.EXPECTED_JOURNALS

    def test_each_entry_has_required_keys(self):
        required = {"figsize", "font_size", "line_width", "font_family"}
        for journal, params in JOURNAL_RCPARAMS.items():
            missing = required - set(params.keys())
            assert not missing, f"{journal} missing: {missing}"

    def test_figsize_is_tuple_of_two(self):
        for journal, params in JOURNAL_RCPARAMS.items():
            fs = params["figsize"]
            assert isinstance(fs, tuple) and len(fs) == 2, \
                f"{journal} figsize bad: {fs}"

    def test_ieee_tnsre_is_single_column(self):
        # IEEE TNSRE single-column = 3.5 inches wide
        assert JOURNAL_RCPARAMS["ieee_tnsre"]["figsize"][0] == pytest.approx(3.5)

    def test_plos_one_is_larger(self):
        assert JOURNAL_RCPARAMS["plos_one"]["figsize"][0] > 4.0

    def test_font_size_is_positive_int_or_float(self):
        for journal, params in JOURNAL_RCPARAMS.items():
            assert params["font_size"] > 0

    def test_line_width_is_positive(self):
        for journal, params in JOURNAL_RCPARAMS.items():
            assert params["line_width"] > 0

    def test_ieee_ral_matches_tnsre_specs(self):
        """IEEE RA-L and TNSRE use same single-column format."""
        assert JOURNAL_RCPARAMS["ieee_ral"]["figsize"] == \
               JOURNAL_RCPARAMS["ieee_tnsre"]["figsize"]


class TestSeriesColorsConsistency:
    def test_same_10_colors_as_graph_quick(self):
        from backend.services.graph_quick import SERIES_COLORS as QC
        assert SERIES_COLORS == QC


class TestRenderSvg:
    def test_returns_string(self, sample_csv):
        req = AnalysisRequest(
            analysis_type=AnalysisType.force,
            columns=["L_ActForce_N", "R_ActForce_N"],
        )
        svg = render_svg(req, [sample_csv])
        assert isinstance(svg, str)

    def test_output_contains_svg_tag(self, sample_csv):
        req = AnalysisRequest(
            analysis_type=AnalysisType.force,
            columns=["L_ActForce_N"],
        )
        svg = render_svg(req, [sample_csv])
        assert "<svg" in svg

    def test_default_journal_works(self, sample_csv):
        req = AnalysisRequest(
            analysis_type=AnalysisType.force,
            columns=["L_ActForce_N"],
        )
        svg = render_svg(req, [sample_csv], journal="default")
        assert "<svg" in svg

    def test_ieee_tnsre_journal_works(self, sample_csv):
        req = AnalysisRequest(
            analysis_type=AnalysisType.force,
            columns=["L_ActForce_N"],
        )
        svg = render_svg(req, [sample_csv], journal="ieee_tnsre")
        assert "<svg" in svg

    def test_all_journals_produce_svg(self, sample_csv):
        req = AnalysisRequest(
            analysis_type=AnalysisType.force,
            columns=["L_ActForce_N"],
        )
        for journal in JOURNAL_RCPARAMS:
            svg = render_svg(req, [sample_csv], journal=journal)
            assert "<svg" in svg, f"Journal {journal} did not produce SVG"

    def test_normalize_gcp_mode(self, sample_csv):
        req = AnalysisRequest(
            analysis_type=AnalysisType.force,
            columns=["L_ActForce_N"],
            normalize_gcp=True,
        )
        svg = render_svg(req, [sample_csv])
        assert "<svg" in svg

    def test_compare_mode_produces_subplots(self, two_csv_paths):
        req = AnalysisRequest(
            analysis_type=AnalysisType.force,
            columns=["L_ActForce_N"],
            compare_mode=True,
        )
        svg = render_svg(req, two_csv_paths)
        assert "<svg" in svg

    def test_unknown_journal_falls_back_to_default(self, sample_csv):
        req = AnalysisRequest(
            analysis_type=AnalysisType.force,
            columns=["L_ActForce_N"],
        )
        # Should not raise; falls back to default
        svg = render_svg(req, [sample_csv], journal="nonexistent_journal_xyz")
        assert "<svg" in svg

    def test_svg_is_non_trivially_long(self, sample_csv):
        req = AnalysisRequest(
            analysis_type=AnalysisType.force,
            columns=["L_ActForce_N"],
        )
        svg = render_svg(req, [sample_csv])
        assert len(svg) > 1000  # Real SVG has substantial content

    def test_multiple_files_single_axes(self, two_csv_paths):
        req = AnalysisRequest(
            analysis_type=AnalysisType.force,
            columns=["L_ActForce_N"],
            compare_mode=False,
        )
        svg = render_svg(req, two_csv_paths)
        assert "<svg" in svg
