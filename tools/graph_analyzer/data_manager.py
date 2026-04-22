"""
H-Walker Graph Analyzer - Data Manager
CSV 로드, 통계, 수학 연산, Gait 파라미터 계산
"""

import os
import json
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional


# All known CSV columns from H-Walker firmware
ALL_COLUMNS = [
    "Time_ms", "Freq_Hz",
    "L_DesForce_N", "L_ActForce_N", "L_ErrForce_N",
    "L_DesVel_mps", "L_ActVel_mps", "L_ErrVel_mps",
    "L_DesPos_deg", "L_ActPos_deg", "L_ErrPos_deg",
    "L_DesCurr_A", "L_ActCurr_A", "L_ErrCurr_A",
    "L_PosInteg", "L_VelInteg",
    "R_DesForce_N", "R_ActForce_N", "R_ErrForce_N",
    "R_DesVel_mps", "R_ActVel_mps", "R_ErrVel_mps",
    "R_DesPos_deg", "R_ActPos_deg", "R_ErrPos_deg",
    "R_DesCurr_A", "R_ActCurr_A", "R_ErrCurr_A",
    "R_PosInteg", "R_VelInteg",
    "L_Rate", "L_Roll", "L_Pitch", "L_Yaw",
    "L_Gx", "L_Gy", "L_Gz", "L_Ax", "L_Ay", "L_Az",
    "L_Dx", "L_Dy", "L_Dz", "L_Batt",
    "L_Event", "L_GCP", "L_Phase", "L_StepTime",
    "R_Rate", "R_Roll", "R_Pitch", "R_Yaw",
    "R_Gx", "R_Gy", "R_Gz", "R_Ax", "R_Ay", "R_Az",
    "R_Dx", "R_Dy", "R_Dz", "R_Batt",
    "R_Event", "R_GCP", "R_Phase", "R_StepTime",
    "Sync", "Mode", "Mark",
    # Columns that may appear in newer firmware
    "L_HO_GCP", "R_HO_GCP",
    "L_AdmVel_mps", "R_AdmVel_mps",
    "L_MotionFF_mps", "R_MotionFF_mps",
    "L_TreadmillFF_mps", "R_TreadmillFF_mps",
    "TFF_Gain", "FF_Gain_F",
]

# Column groups for quick selection
COLUMN_GROUPS = {
    "Force": ["L_DesForce_N", "L_ActForce_N", "L_ErrForce_N",
              "R_DesForce_N", "R_ActForce_N", "R_ErrForce_N"],
    "GCP": ["L_GCP", "R_GCP"],
    "IMU Angle": ["L_Pitch", "R_Pitch", "L_Roll", "R_Roll", "L_Yaw", "R_Yaw"],
    "Gyro": ["L_Gx", "L_Gy", "L_Gz", "R_Gx", "R_Gy", "R_Gz"],
    "Accel": ["L_Ax", "L_Ay", "L_Az", "R_Ax", "R_Ay", "R_Az"],
    "Velocity": ["L_DesVel_mps", "L_ActVel_mps", "L_ErrVel_mps",
                 "R_DesVel_mps", "R_ActVel_mps", "R_ErrVel_mps"],
    "Position": ["L_DesPos_deg", "L_ActPos_deg", "L_ErrPos_deg",
                 "R_DesPos_deg", "R_ActPos_deg", "R_ErrPos_deg"],
    "Current": ["L_DesCurr_A", "L_ActCurr_A", "L_ErrCurr_A",
                "R_DesCurr_A", "R_ActCurr_A", "R_ErrCurr_A"],
    "Gait": ["L_Event", "R_Event", "L_Phase", "R_Phase",
             "L_StepTime", "R_StepTime", "L_HO_GCP", "R_HO_GCP"],
    "Feedforward": ["L_MotionFF_mps", "R_MotionFF_mps",
                    "L_TreadmillFF_mps", "R_TreadmillFF_mps",
                    "L_AdmVel_mps", "R_AdmVel_mps", "TFF_Gain", "FF_Gain_F"],
    "Control": ["Mode", "Mark"],
}


@dataclass
class LoadedFile:
    path: str
    name: str
    df: pd.DataFrame
    color: str
    style_idx: int


class DataManager:
    """Manages loaded CSV files and provides data processing utilities."""

    SERIES_COLORS = [
        '#4C9EFF', '#2DD4BF', '#A78BFA', '#FB923C', '#F472B6',
        '#FCD34D', '#4ADE80', '#F87171', '#818CF8', '#22D3EE',
    ]

    def __init__(self):
        self.files: list[LoadedFile] = []

    def load_csv(self, path: str) -> Optional[LoadedFile]:
        """Load a CSV file. Returns LoadedFile or None on failure."""
        if any(f.path == path for f in self.files):
            return None
        if len(self.files) >= 20:
            return None
        try:
            df = pd.read_csv(path)
            df.columns = df.columns.str.strip()
            # Remove duplicate header rows (Teensy CSV sometimes repeats headers)
            first_col = df.columns[0]
            mask = df[first_col] != first_col  # rows where first col equals header name
            if mask.sum() < len(df):
                df = df[mask].reset_index(drop=True)
            # Convert all numeric columns
            for col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        except Exception:
            return None

        idx = len(self.files)
        lf = LoadedFile(
            path=path,
            name=os.path.basename(path),
            df=df,
            color=self.SERIES_COLORS[idx % len(self.SERIES_COLORS)],
            style_idx=idx % 4,
        )
        self.files.append(lf)
        return lf

    def remove_file(self, path: str):
        self.files = [f for f in self.files if f.path != path]
        # Reassign colors
        for i, f in enumerate(self.files):
            f.color = self.SERIES_COLORS[i % len(self.SERIES_COLORS)]
            f.style_idx = i % 4

    def get_available_columns(self) -> list[str]:
        """Return union of all columns across loaded files."""
        cols = set()
        for f in self.files:
            cols.update(f.df.columns.tolist())
        # Preserve known order, then append unknown
        ordered = [c for c in ALL_COLUMNS if c in cols]
        extras = sorted(cols - set(ALL_COLUMNS))
        return ordered + extras

    # ================================================================
    # STATISTICS
    # ================================================================

    @staticmethod
    def compute_stats(y: np.ndarray) -> dict:
        """Compute comprehensive statistics for a 1D array."""
        valid = y[np.isfinite(y)]
        if len(valid) == 0:
            return {k: 0.0 for k in [
                'mean', 'std', 'min', 'max', 'rms', 'median', 'p2p', 'count',
                'variance', 'skewness', 'kurtosis', 'cv', 'iqr',
                'q1', 'q3', 'p5', 'p95', 'nan_count', 'nan_pct',
            ]}
        n = len(valid)
        mean = float(np.mean(valid))
        std = float(np.std(valid))
        q1 = float(np.percentile(valid, 25))
        q3 = float(np.percentile(valid, 75))

        # Skewness and Kurtosis (Fisher's)
        if std > 0 and n > 2:
            skew = float(np.mean(((valid - mean) / std) ** 3))
            kurt = float(np.mean(((valid - mean) / std) ** 4) - 3)
        else:
            skew, kurt = 0.0, 0.0

        nan_count = int(np.sum(~np.isfinite(y)))
        return {
            'count': n,
            'mean': mean,
            'std': std,
            'variance': std ** 2,
            'min': float(np.min(valid)),
            'max': float(np.max(valid)),
            'median': float(np.median(valid)),
            'rms': float(np.sqrt(np.mean(valid ** 2))),
            'p2p': float(np.ptp(valid)),
            'skewness': skew,
            'kurtosis': kurt,
            'cv': abs(std / mean * 100) if abs(mean) > 1e-12 else 0.0,
            'iqr': float(q3 - q1),
            'q1': q1,
            'q3': q3,
            'p5': float(np.percentile(valid, 5)),
            'p95': float(np.percentile(valid, 95)),
            'nan_count': nan_count,
            'nan_pct': nan_count / len(y) * 100 if len(y) > 0 else 0,
        }

    # ================================================================
    # MATH OPERATIONS
    # ================================================================

    @staticmethod
    def derivative(y: np.ndarray, dt: float = 1.0) -> np.ndarray:
        """Numerical derivative (central diff)."""
        return np.gradient(y, dt)

    @staticmethod
    def moving_average(y: np.ndarray, window: int = 10) -> np.ndarray:
        """Simple moving average."""
        if window < 2 or len(y) < window:
            return y.copy()
        kernel = np.ones(window) / window
        return np.convolve(y, kernel, mode='same')

    @staticmethod
    def lowpass_filter(y: np.ndarray, cutoff_ratio: float = 0.1) -> np.ndarray:
        """Simple FFT-based lowpass filter. cutoff_ratio: fraction of Nyquist."""
        n = len(y)
        if n < 4:
            return y.copy()
        fft = np.fft.rfft(y)
        freqs = np.fft.rfftfreq(n)
        fft[freqs > cutoff_ratio] = 0
        return np.fft.irfft(fft, n=n)

    @staticmethod
    def integrate(y: np.ndarray, dt: float = 1.0) -> np.ndarray:
        """Cumulative trapezoidal integration."""
        return np.cumsum(y) * dt

    @staticmethod
    def butterworth_filter(y: np.ndarray, cutoff_hz: float, fs: float,
                           order: int = 4, btype: str = 'low') -> np.ndarray:
        """Butterworth IIR filter. Falls back to FFT filter if scipy unavailable."""
        try:
            from scipy.signal import butter, filtfilt
            nyq = fs / 2.0
            normalized = cutoff_hz / nyq
            if normalized >= 1.0:
                normalized = 0.99
            b, a = butter(order, normalized, btype=btype)
            return filtfilt(b, a, y)
        except ImportError:
            # Fallback: FFT-based
            ratio = cutoff_hz / (fs / 2.0)
            return DataManager.lowpass_filter(y, ratio)

    @staticmethod
    def savgol_filter(y: np.ndarray, window: int = 21, polyorder: int = 3) -> np.ndarray:
        """Savitzky-Golay smoothing filter."""
        try:
            from scipy.signal import savgol_filter as _sg
            if window % 2 == 0:
                window += 1
            window = min(window, len(y))
            if window <= polyorder:
                return y.copy()
            return _sg(y, window, polyorder)
        except ImportError:
            return DataManager.moving_average(y, window)

    @staticmethod
    def remove_outliers(y: np.ndarray, method: str = 'iqr',
                        threshold: float = 1.5) -> np.ndarray:
        """Replace outliers with NaN. Methods: 'iqr', 'zscore', 'sigma'."""
        result = y.copy().astype(np.float64)
        valid = result[np.isfinite(result)]
        if len(valid) < 4:
            return result

        if method == 'zscore':
            z = np.abs((result - np.nanmean(result)) / (np.nanstd(result) + 1e-12))
            result[z > threshold] = np.nan
        elif method == 'sigma':
            mu, sigma = np.nanmean(result), np.nanstd(result)
            result[np.abs(result - mu) > threshold * sigma] = np.nan
        else:  # IQR
            q1 = np.nanpercentile(result, 25)
            q3 = np.nanpercentile(result, 75)
            iqr = q3 - q1
            result[(result < q1 - threshold * iqr) | (result > q3 + threshold * iqr)] = np.nan
        return result

    @staticmethod
    def interpolate_nan(y: np.ndarray) -> np.ndarray:
        """Linear interpolation to fill NaN values."""
        result = y.copy().astype(np.float64)
        nans = np.isnan(result)
        if not np.any(nans):
            return result
        valid_idx = np.where(~nans)[0]
        if len(valid_idx) < 2:
            return result
        result[nans] = np.interp(np.where(nans)[0], valid_idx, result[valid_idx])
        return result

    @staticmethod
    def normalize(y: np.ndarray, method: str = 'zscore') -> np.ndarray:
        """Normalize data. Methods: 'zscore', 'minmax', 'percent'."""
        valid = y[np.isfinite(y)]
        if len(valid) < 2:
            return y.copy()
        if method == 'minmax':
            vmin, vmax = np.min(valid), np.max(valid)
            if vmax - vmin < 1e-12:
                return np.zeros_like(y)
            return (y - vmin) / (vmax - vmin)
        elif method == 'percent':
            baseline = np.mean(valid[:min(50, len(valid))])
            if abs(baseline) < 1e-12:
                return y.copy()
            return (y - baseline) / abs(baseline) * 100
        else:  # zscore
            return (y - np.mean(valid)) / (np.std(valid) + 1e-12)

    @staticmethod
    def resample(y: np.ndarray, target_length: int) -> np.ndarray:
        """Resample signal to target length using linear interpolation."""
        if len(y) == target_length:
            return y.copy()
        x_orig = np.linspace(0, 1, len(y))
        x_new = np.linspace(0, 1, target_length)
        return np.interp(x_new, x_orig, y)

    @staticmethod
    def find_peaks(y: np.ndarray, prominence: float = None,
                   distance: int = None) -> tuple:
        """Find peaks in signal. Returns (peak_indices, peak_values)."""
        try:
            from scipy.signal import find_peaks as _fp
            kwargs = {}
            if prominence is not None:
                kwargs['prominence'] = prominence
            if distance is not None:
                kwargs['distance'] = distance
            idx, props = _fp(y, **kwargs)
            return idx, y[idx]
        except ImportError:
            # Simple fallback
            if len(y) < 3:
                return np.array([]), np.array([])
            peaks = []
            for i in range(1, len(y) - 1):
                if y[i] > y[i-1] and y[i] > y[i+1]:
                    peaks.append(i)
            peaks = np.array(peaks)
            return peaks, y[peaks] if len(peaks) > 0 else (peaks, np.array([]))

    @staticmethod
    def find_valleys(y: np.ndarray, prominence: float = None,
                     distance: int = None) -> tuple:
        """Find valleys (local minima) in signal."""
        idx, vals = DataManager.find_peaks(-y, prominence=prominence, distance=distance)
        return idx, -vals

    @staticmethod
    def cross_correlation(a: np.ndarray, b: np.ndarray) -> tuple:
        """Compute normalized cross-correlation. Returns (lags, correlation)."""
        a = (a - np.mean(a)) / (np.std(a) + 1e-12)
        b = (b - np.mean(b)) / (np.std(b) + 1e-12)
        n = max(len(a), len(b))
        corr = np.correlate(a, b, mode='full') / n
        lags = np.arange(-len(b) + 1, len(a))
        return lags, corr

    @staticmethod
    def normality_test(y: np.ndarray) -> dict:
        """Test for normality. Returns dict with test results."""
        valid = y[np.isfinite(y)]
        if len(valid) < 8:
            return {'shapiro_stat': 0, 'shapiro_p': 0, 'p_value': 0,
                    'is_normal': False, 'test': 'insufficient_data'}
        try:
            from scipy.stats import shapiro
            stat, p = shapiro(valid[:5000])  # Shapiro limit
            return {'shapiro_stat': float(stat), 'shapiro_p': float(p),
                    'p_value': float(p), 'is_normal': p > 0.05, 'test': 'shapiro'}
        except ImportError:
            # Simple heuristic: check skewness and kurtosis
            mean = np.mean(valid)
            std = np.std(valid)
            if std < 1e-12:
                return {'shapiro_stat': 0, 'shapiro_p': 0,
                        'is_normal': False, 'test': 'heuristic'}
            skew = float(np.mean(((valid - mean) / std) ** 3))
            kurt = float(np.mean(((valid - mean) / std) ** 4) - 3)
            is_normal = abs(skew) < 1.0 and abs(kurt) < 2.0
            return {'shapiro_stat': 0, 'shapiro_p': 0, 'p_value': 0,
                    'is_normal': is_normal, 'test': 'heuristic',
                    'skewness': skew, 'kurtosis': kurt}

    # ================================================================
    # GAIT PARAMETERS
    # ================================================================

    @staticmethod
    def estimate_sample_rate(df: pd.DataFrame) -> float:
        # Check millisecond time columns first
        for col in ['Time_ms', 'time_ms']:
            if col in df.columns:
                t = df[col].values.astype(np.float64)
                valid = t[np.isfinite(t)]
                if len(valid) > 1:
                    dt_ms = np.median(np.diff(valid))
                    if dt_ms > 0:
                        return 1000.0 / dt_ms
        # Check second-based time columns
        for col in ['Time', 'time', 'Time_s', 'Timestamp']:
            if col in df.columns:
                t = df[col].values.astype(np.float64)
                valid = t[np.isfinite(t)]
                if len(valid) > 1:
                    dt = np.median(np.diff(valid))
                    if dt > 0:
                        return 1.0 / dt
        return 111.0  # Teensy default

    @classmethod
    def compute_gait_params(cls, df: pd.DataFrame) -> dict:
        """Compute gait parameters for both sides."""
        p = {}
        sample_rate = cls.estimate_sample_rate(df)

        for side, prefix in [('L', 'l'), ('R', 'r')]:
            gcp_col = f'{side}_GCP'
            force_col = f'{side}_ActForce_N'

            if gcp_col not in df.columns:
                cls._fill_empty_gait(p, prefix)
                continue

            gcp = df[gcp_col].values.astype(np.float64) if gcp_col in df.columns else np.zeros(len(df))

            # HS detection: use firmware Event column (primary), GCP drop (fallback)
            event_col = f'{side}_Event'
            hs_idx = np.array([], dtype=int)

            if event_col in df.columns:
                events = df[event_col].values.astype(np.float64)
                hs_idx = np.where(np.diff(events) > 0.5)[0] + 1  # rising edge = HS

            if len(hs_idx) < 2:
                # Fallback: detect HS from GCP sawtooth drop
                gcp_range = np.ptp(gcp[np.isfinite(gcp)]) if np.any(np.isfinite(gcp)) else 0
                if gcp_range < 0.3:
                    p[f'{prefix}_no_data'] = True
                    cls._fill_empty_gait(p, prefix)
                    continue
                # Normalize GCP to 0-1
                gcp_max = np.nanmax(gcp)
                if gcp_max > 10:
                    gcp = gcp / 100.0
                elif gcp_max > 1.5:
                    gcp = gcp / gcp_max
                hs_threshold = -max(0.1, np.ptp(gcp[np.isfinite(gcp)]) * 0.15)
                diffs = np.diff(gcp)
                raw_hs = np.where(diffs < hs_threshold)[0] + 1
                if len(raw_hs) > 1:
                    gaps = np.diff(raw_hs)
                    keep = np.concatenate([[True], gaps > max(20, sample_rate * 0.3)])
                    hs_idx = raw_hs[keep]
                else:
                    hs_idx = raw_hs

            if len(hs_idx) < 2:
                p[f'{prefix}_no_data'] = True
                cls._fill_empty_gait(p, prefix)
                continue
            n_strides = max(0, len(hs_idx) - 1)

            p[f'{prefix}_hs_count'] = len(hs_idx)
            p[f'{prefix}_stride_count'] = n_strides

            # HO count (computed after stride filtering below)
            p[f'{prefix}_ho_count'] = 0  # placeholder, updated after filtering

            # Stride times
            stride_times_raw = np.array(
                [(hs_idx[i + 1] - hs_idx[i]) / sample_rate for i in range(n_strides)]
            ) if n_strides > 0 else np.array([])

            # Filter outlier strides using IQR method
            if len(stride_times_raw) >= 4:
                q1 = np.percentile(stride_times_raw, 25)
                q3 = np.percentile(stride_times_raw, 75)
                iqr = q3 - q1
                lower = q1 - 2.0 * iqr
                upper = q3 + 2.0 * iqr
                # Also apply absolute bounds (0.3s - 5.0s for walking)
                lower = max(lower, 0.3)
                upper = min(upper, 5.0)
                valid_mask = (stride_times_raw >= lower) & (stride_times_raw <= upper)
                stride_times = stride_times_raw[valid_mask]
            else:
                stride_times = stride_times_raw
                valid_mask = np.ones(len(stride_times_raw), dtype=bool)

            p[f'{prefix}_stride_times'] = stride_times
            p[f'{prefix}_stride_times_raw'] = stride_times_raw
            p[f'{prefix}_stride_count'] = len(stride_times)  # update to filtered count

            # HO count (using valid strides only)
            ho_count = 0
            for i in range(n_strides):
                if not valid_mask[i]:
                    continue
                s, e = hs_idx[i], hs_idx[i + 1]
                if np.any(gcp[s:e] > 0.6):
                    ho_count += 1
            p[f'{prefix}_ho_count'] = ho_count
            p[f'{prefix}_stride_time_mean'] = float(np.mean(stride_times)) if len(stride_times) else 0
            p[f'{prefix}_stride_time_std'] = float(np.std(stride_times)) if len(stride_times) else 0
            p[f'{prefix}_step_time_mean'] = p[f'{prefix}_stride_time_mean'] / 2
            p[f'{prefix}_step_time_std'] = p[f'{prefix}_stride_time_std'] / 2
            p[f'{prefix}_cadence'] = (60.0 / p[f'{prefix}_stride_time_mean'] * 2
                                       if p[f'{prefix}_stride_time_mean'] > 0 else 0)

            # Stance / Swing (only for valid strides)
            stance_ratios, swing_ratios = [], []
            phase_col = f'{side}_Phase'
            for i in range(n_strides):
                if not valid_mask[i]:
                    continue
                s, e = hs_idx[i], hs_idx[i + 1]
                if e - s < 5:
                    continue
                if phase_col in df.columns and df[phase_col].nunique() > 1:
                    # Use Phase column: 0=stance, 1=swing
                    phase_data = df[phase_col].values[s:e].astype(np.float64)
                    n_stance = np.sum(phase_data < 0.5)
                else:
                    stride_gcp = gcp[s:e]
                    n_stance = np.sum(stride_gcp < 0.6)
                stance_ratios.append(n_stance / (e - s) * 100)
                swing_ratios.append(((e - s) - n_stance) / (e - s) * 100)

            p[f'{prefix}_stance_mean'] = float(np.mean(stance_ratios)) if stance_ratios else 0
            p[f'{prefix}_stance_std'] = float(np.std(stance_ratios)) if stance_ratios else 0
            p[f'{prefix}_swing_mean'] = float(np.mean(swing_ratios)) if swing_ratios else 0
            p[f'{prefix}_swing_std'] = float(np.std(swing_ratios)) if swing_ratios else 0

            # Force per stride
            if force_col in df.columns:
                force = df[force_col].values.astype(np.float64)
                peak_forces, mean_forces, strides_data = [], [], []
                for i in range(n_strides):
                    if not valid_mask[i]:
                        continue
                    s, e = hs_idx[i], hs_idx[i + 1]
                    if e - s < 10:
                        continue
                    stride_f = force[s:e]
                    if np.all(np.isnan(stride_f)):
                        continue
                    peak_forces.append(float(np.nanmax(stride_f)))
                    mean_forces.append(float(np.nanmean(stride_f)))
                    # Fill NaN before resampling
                    sf_clean = stride_f.copy()
                    nan_mask = np.isnan(sf_clean)
                    if np.any(nan_mask):
                        valid_idx = np.where(~nan_mask)[0]
                        if len(valid_idx) >= 2:
                            sf_clean[nan_mask] = np.interp(
                                np.where(nan_mask)[0], valid_idx, sf_clean[valid_idx])
                        else:
                            sf_clean = np.nan_to_num(sf_clean, nan=0.0)
                    x_orig = np.linspace(0, 100, len(sf_clean))
                    strides_data.append(np.interp(np.linspace(0, 100, 101), x_orig, sf_clean))

                p[f'{prefix}_peak_force_mean'] = float(np.mean(peak_forces)) if peak_forces else 0
                p[f'{prefix}_peak_force_std'] = float(np.std(peak_forces)) if peak_forces else 0
                p[f'{prefix}_mean_force_mean'] = float(np.mean(mean_forces)) if mean_forces else 0
                p[f'{prefix}_mean_force_std'] = float(np.std(mean_forces)) if mean_forces else 0
                p[f'{prefix}_force_strides'] = np.array(strides_data) if strides_data else None
            else:
                p[f'{prefix}_peak_force_mean'] = 0
                p[f'{prefix}_peak_force_std'] = 0
                p[f'{prefix}_mean_force_mean'] = 0
                p[f'{prefix}_mean_force_std'] = 0
                p[f'{prefix}_force_strides'] = None

        # Symmetry indices (multiple metrics)
        l_st = p.get('l_stride_time_mean', 0)
        r_st = p.get('r_stride_time_mean', 0)
        p['symmetry_index'] = abs(l_st - r_st) / ((l_st + r_st) / 2) * 100 if (l_st + r_st) > 0 else 0
        p['total_strides'] = p.get('l_stride_count', 0) + p.get('r_stride_count', 0)
        p['avg_cadence'] = ((p.get('l_cadence', 0) + p.get('r_cadence', 0)) / 2
                            if (p.get('l_cadence', 0) + p.get('r_cadence', 0)) > 0 else 0)

        # Force symmetry
        l_pf = p.get('l_peak_force_mean', 0)
        r_pf = p.get('r_peak_force_mean', 0)
        p['force_symmetry'] = abs(l_pf - r_pf) / ((l_pf + r_pf) / 2) * 100 if (l_pf + r_pf) > 0 else 0

        # Stance symmetry
        l_stance = p.get('l_stance_mean', 0)
        r_stance = p.get('r_stance_mean', 0)
        p['stance_symmetry'] = abs(l_stance - r_stance) / ((l_stance + r_stance) / 2) * 100 if (l_stance + r_stance) > 0 else 0

        # Cadence symmetry
        l_cad = p.get('l_cadence', 0)
        r_cad = p.get('r_cadence', 0)
        p['cadence_symmetry'] = abs(l_cad - r_cad) / ((l_cad + r_cad) / 2) * 100 if (l_cad + r_cad) > 0 else 0

        # Stride time variability (CV = coefficient of variation)
        p['l_stride_cv'] = (p.get('l_stride_time_std', 0) / p.get('l_stride_time_mean', 1) * 100
                             if p.get('l_stride_time_mean', 0) > 0 else 0)
        p['r_stride_cv'] = (p.get('r_stride_time_std', 0) / p.get('r_stride_time_mean', 1) * 100
                             if p.get('r_stride_time_mean', 0) > 0 else 0)

        # Duration & recording info
        total_samples = len(df)
        p['total_samples'] = total_samples
        p['duration_s'] = total_samples / sample_rate
        p['sample_rate'] = sample_rate

        # Fatigue trend: compare first-half vs second-half stride times
        for prefix in ['l', 'r']:
            stride_t = p.get(f'{prefix}_stride_times', np.array([]))
            if not isinstance(stride_t, np.ndarray):
                stride_t = np.array(stride_t) if stride_t is not None else np.array([])
            if len(stride_t) < 4:
                p[f'{prefix}_fatigue_ratio'] = 0
                continue
            mid = len(stride_t) // 2
            first_half = np.mean(stride_t[:mid])
            second_half = np.mean(stride_t[mid:])
            p[f'{prefix}_fatigue_ratio'] = (second_half / first_half * 100 - 100
                                             if first_half > 0 else 0)

        return p

    @staticmethod
    def _fill_empty_gait(p: dict, prefix: str):
        for key in ['hs_count', 'stride_count', 'ho_count',
                     'stride_time_mean', 'stride_time_std',
                     'step_time_mean', 'step_time_std', 'cadence',
                     'stance_mean', 'stance_std', 'swing_mean', 'swing_std',
                     'peak_force_mean', 'peak_force_std',
                     'mean_force_mean', 'mean_force_std',
                     'fatigue_ratio', 'stride_cv']:
            p[f'{prefix}_{key}'] = 0
        p[f'{prefix}_force_strides'] = None
        p[f'{prefix}_stride_times'] = np.array([])

    # ================================================================
    # SESSION SAVE / LOAD
    # ================================================================

    def save_session(self, path: str, extra: dict = None):
        """Save current session (file paths + settings) to JSON."""
        data = {
            'files': [f.path for f in self.files],
            'extra': extra or {},
        }
        with open(path, 'w') as fp:
            json.dump(data, fp, indent=2)

    def load_session(self, path: str) -> dict:
        """Load session from JSON. Returns extra settings dict."""
        with open(path, 'r') as fp:
            data = json.load(fp)
        self.files.clear()
        for fpath in data.get('files', []):
            if os.path.exists(fpath):
                self.load_csv(fpath)
        return data.get('extra', {})
