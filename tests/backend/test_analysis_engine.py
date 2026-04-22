import numpy as np
import pandas as pd
import pytest

from backend.services.analysis_engine import (
    load_csv,
    resolve_gcp,
    detect_heel_strikes,
    normalize_to_gcp,
    compute_stats,
    compute_symmetry_index,
)
from backend.models.schema import StatsResult


class TestLoadCsv:
    def test_returns_dataframe(self, sample_csv):
        df = load_csv(sample_csv)
        assert isinstance(df, pd.DataFrame)

    def test_row_count(self, sample_csv):
        df = load_csv(sample_csv)
        assert len(df) == 500

    def test_expected_columns_present(self, sample_csv):
        df = load_csv(sample_csv)
        for col in ["L_ActForce_N", "R_ActForce_N", "L_GCP", "R_GCP"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_column_names_are_stripped(self, tmp_path):
        """Columns with leading/trailing spaces must be stripped."""
        df = pd.DataFrame({" L_ActForce_N ": [1.0, 2.0], " R_ActForce_N ": [3.0, 4.0]})
        path = str(tmp_path / "spaced.csv")
        df.to_csv(path, index=False)
        loaded = load_csv(path)
        assert "L_ActForce_N" in loaded.columns
        assert "R_ActForce_N" in loaded.columns


class TestResolveGcp:
    def test_returns_array(self, sample_csv_path_and_df):
        path, df = sample_csv_path_and_df
        gcp = resolve_gcp(df, "L")
        assert isinstance(gcp, np.ndarray)

    def test_length_matches_dataframe(self, sample_csv_path_and_df):
        path, df = sample_csv_path_and_df
        gcp = resolve_gcp(df, "L")
        assert len(gcp) == len(df)

    def test_values_normalized_0_to_1(self, sample_csv_path_and_df):
        path, df = sample_csv_path_and_df
        gcp = resolve_gcp(df, "L")
        assert gcp.min() >= 0.0
        assert gcp.max() <= 1.0

    def test_both_sides_supported(self, sample_csv_path_and_df):
        path, df = sample_csv_path_and_df
        for side in ["L", "R"]:
            gcp = resolve_gcp(df, side)
            assert len(gcp) == len(df)

    def test_already_normalized_passthrough(self, sample_csv_path_and_df):
        """GCP values already in 0-1 should not be scaled again."""
        path, df = sample_csv_path_and_df
        df2 = df.copy()
        df2["L_GCP"] = df2["L_GCP"] / 100.0
        gcp = resolve_gcp(df2, "L")
        assert gcp.max() <= 1.0


class TestDetectHeelStrikes:
    def test_returns_indices_array(self):
        gcp = np.tile(np.linspace(0, 1, 110), 4)  # 4 strides
        hs = detect_heel_strikes(gcp)
        assert isinstance(hs, np.ndarray)
        assert hs.dtype in (np.int32, np.int64, int)

    def test_detects_correct_number_of_strides(self):
        """4 repetitions of 0→1 sawtooth = 4 heel strikes (at resets)."""
        gcp = np.tile(np.linspace(0, 1, 110), 4)
        hs = detect_heel_strikes(gcp)
        # Expect 3-5 crossings (boundary at start may or may not be detected)
        assert 2 <= len(hs) <= 5

    def test_hs_indices_within_bounds(self):
        gcp = np.tile(np.linspace(0, 1, 110), 4)
        hs = detect_heel_strikes(gcp)
        assert all(0 <= i < len(gcp) for i in hs)

    def test_hs_sorted_ascending(self):
        gcp = np.tile(np.linspace(0, 1, 110), 4)
        hs = detect_heel_strikes(gcp)
        assert list(hs) == sorted(hs)


class TestNormalizeToGcp:
    def test_returns_101_points(self):
        gcp = np.tile(np.linspace(0, 1, 110), 5)
        signal = np.sin(np.linspace(0, 10 * np.pi, len(gcp)))
        hs = detect_heel_strikes(gcp)
        mean_101, std_101 = normalize_to_gcp(signal, hs)
        assert len(mean_101) == 101
        assert len(std_101) == 101

    def test_mean_is_finite(self):
        gcp = np.tile(np.linspace(0, 1, 110), 5)
        signal = np.sin(np.linspace(0, 10 * np.pi, len(gcp)))
        hs = detect_heel_strikes(gcp)
        mean_101, std_101 = normalize_to_gcp(signal, hs)
        assert np.all(np.isfinite(mean_101))
        assert np.all(np.isfinite(std_101))

    def test_std_is_non_negative(self):
        gcp = np.tile(np.linspace(0, 1, 110), 5)
        signal = np.sin(np.linspace(0, 10 * np.pi, len(gcp)))
        hs = detect_heel_strikes(gcp)
        _, std_101 = normalize_to_gcp(signal, hs)
        assert np.all(std_101 >= 0)

    def test_fewer_than_2_strides_returns_zeros(self):
        signal = np.sin(np.linspace(0, np.pi, 100))
        hs = np.array([0], dtype=int)
        mean_101, std_101 = normalize_to_gcp(signal, hs)
        assert len(mean_101) == 101
        assert np.all(std_101 == 0)


class TestComputeStats:
    def test_returns_list_of_stats_results(self, sample_csv):
        df = load_csv(sample_csv)
        results = compute_stats(df, ["L_ActForce_N", "R_ActForce_N"], "trial_001.csv")
        assert len(results) == 2
        assert all(isinstance(r, StatsResult) for r in results)

    def test_column_names_in_results(self, sample_csv):
        df = load_csv(sample_csv)
        results = compute_stats(df, ["L_ActForce_N"], "trial_001.csv")
        assert results[0].column == "L_ActForce_N"

    def test_file_name_in_results(self, sample_csv):
        df = load_csv(sample_csv)
        results = compute_stats(df, ["L_ActForce_N"], "trial_001.csv")
        assert results[0].file == "trial_001.csv"

    def test_mean_within_expected_range(self, sample_csv):
        df = load_csv(sample_csv)
        results = compute_stats(df, ["L_ActForce_N"], "trial_001.csv")
        assert 0 < results[0].mean < 50

    def test_max_does_not_exceed_70(self, sample_csv):
        df = load_csv(sample_csv)
        results = compute_stats(df, ["L_ActForce_N"], "trial_001.csv")
        assert results[0].max_val <= 72  # allow tiny noise overshoot

    def test_min_is_non_negative_for_force(self, sample_csv):
        df = load_csv(sample_csv)
        results = compute_stats(df, ["L_ActForce_N"], "trial_001.csv")
        assert results[0].min_val >= 0

    def test_std_is_positive(self, sample_csv):
        df = load_csv(sample_csv)
        results = compute_stats(df, ["L_ActForce_N"], "trial_001.csv")
        assert results[0].std > 0


class TestComputeSymmetryIndex:
    def test_identical_signals_return_zero(self):
        sig = np.ones(100) * 25.0
        assert compute_symmetry_index(sig, sig) == pytest.approx(0.0)

    def test_returns_float(self):
        left = np.ones(100) * 30.0
        right = np.ones(100) * 20.0
        result = compute_symmetry_index(left, right)
        assert isinstance(result, float)

    def test_returns_positive_value(self):
        left = np.ones(100) * 30.0
        right = np.ones(100) * 20.0
        result = compute_symmetry_index(left, right)
        assert result > 0

    def test_known_value(self):
        # |30-20| / ((30+20)/2) * 100 = 10/25*100 = 40.0
        left = np.ones(100) * 30.0
        right = np.ones(100) * 20.0
        result = compute_symmetry_index(left, right)
        assert result == pytest.approx(40.0, rel=1e-5)
