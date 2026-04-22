"""Shared fixtures for backend tests.

Creates a realistic 500-row H-Walker CSV at 111 Hz (≈4.5 s of data).
Covers ~4 complete gait cycles per side.
"""
import numpy as np
import pandas as pd
import pytest
import tempfile
import os


def make_hwalker_csv(n_rows: int = 500) -> pd.DataFrame:
    """Generate a realistic H-Walker log DataFrame."""
    rng = np.random.default_rng(42)
    t = np.linspace(0, n_rows / 111.0, n_rows)

    # Gait cycle % — sawtooth 0→100 with ~111 samples/stride (1 Hz gait)
    gait_freq = 1.0  # Hz
    L_GCP = (t * gait_freq * 100) % 100
    R_GCP = ((t * gait_freq + 0.5) * 100) % 100  # R is 50% offset

    # Forces: sin-wave shaped, 0-60 N, with noise
    L_ActForce_N = np.clip(
        40 * np.abs(np.sin(np.pi * t * gait_freq)) + rng.normal(0, 2, n_rows),
        0, 70
    )
    R_ActForce_N = np.clip(
        38 * np.abs(np.sin(np.pi * (t * gait_freq + 0.5))) + rng.normal(0, 2, n_rows),
        0, 70
    )
    L_DesForce_N = L_ActForce_N + rng.normal(0, 1, n_rows)
    R_DesForce_N = R_ActForce_N + rng.normal(0, 1, n_rows)

    # IMU angles (degrees)
    L_Pitch = 5 * np.sin(2 * np.pi * t * gait_freq) + rng.normal(0, 0.5, n_rows)
    R_Pitch = 5 * np.sin(2 * np.pi * (t * gait_freq + 0.5)) + rng.normal(0, 0.5, n_rows)
    L_Roll  = 2 * np.sin(2 * np.pi * t * gait_freq * 2) + rng.normal(0, 0.3, n_rows)
    R_Roll  = 2 * np.sin(2 * np.pi * (t * gait_freq * 2 + 0.5)) + rng.normal(0, 0.3, n_rows)
    L_Yaw   = rng.normal(0, 0.5, n_rows)
    R_Yaw   = rng.normal(0, 0.5, n_rows)

    # Gait phase (0-3) and events (0/1)
    L_Phase = (L_GCP / 25).astype(int) % 4
    R_Phase = (R_GCP / 25).astype(int) % 4
    L_Event = (np.diff(L_GCP, prepend=L_GCP[0]) < -50).astype(int)
    R_Event = (np.diff(R_GCP, prepend=R_GCP[0]) < -50).astype(int)

    # Additional columns
    L_Vel = 0.5 * np.sin(2 * np.pi * t * gait_freq) + rng.normal(0, 0.05, n_rows)
    R_Vel = 0.5 * np.sin(2 * np.pi * (t * gait_freq + 0.5)) + rng.normal(0, 0.05, n_rows)
    L_Pos = np.cumsum(L_Vel) * (1 / 111.0)
    R_Pos = np.cumsum(R_Vel) * (1 / 111.0)
    L_Current = 2.0 * L_ActForce_N / 70.0 + rng.normal(0, 0.1, n_rows)
    R_Current = 2.0 * R_ActForce_N / 70.0 + rng.normal(0, 0.1, n_rows)
    L_FF = L_DesForce_N * 0.9
    R_FF = R_DesForce_N * 0.9
    L_GyroX = rng.normal(0, 1, n_rows)
    R_GyroX = rng.normal(0, 1, n_rows)
    L_GyroY = rng.normal(0, 1, n_rows)
    R_GyroY = rng.normal(0, 1, n_rows)
    L_GyroZ = rng.normal(0, 1, n_rows)
    R_GyroZ = rng.normal(0, 1, n_rows)
    L_AccX = rng.normal(0, 0.5, n_rows)
    R_AccX = rng.normal(0, 0.5, n_rows)
    L_AccY = rng.normal(0, 0.5, n_rows)
    R_AccY = rng.normal(0, 0.5, n_rows)
    L_AccZ = 9.81 + rng.normal(0, 0.3, n_rows)
    R_AccZ = 9.81 + rng.normal(0, 0.3, n_rows)
    timestamp = np.arange(n_rows) * (1 / 111.0)

    df = pd.DataFrame({
        "timestamp": timestamp,
        "L_ActForce_N": L_ActForce_N,
        "R_ActForce_N": R_ActForce_N,
        "L_DesForce_N": L_DesForce_N,
        "R_DesForce_N": R_DesForce_N,
        "L_GCP": L_GCP,
        "R_GCP": R_GCP,
        "L_Pitch": L_Pitch,
        "R_Pitch": R_Pitch,
        "L_Roll": L_Roll,
        "R_Roll": R_Roll,
        "L_Yaw": L_Yaw,
        "R_Yaw": R_Yaw,
        "L_Phase": L_Phase,
        "R_Phase": R_Phase,
        "L_Event": L_Event,
        "R_Event": R_Event,
        "L_Vel": L_Vel,
        "R_Vel": R_Vel,
        "L_Pos": L_Pos,
        "R_Pos": R_Pos,
        "L_Current": L_Current,
        "R_Current": R_Current,
        "L_FF": L_FF,
        "R_FF": R_FF,
        "L_GyroX": L_GyroX,
        "R_GyroX": R_GyroX,
        "L_GyroY": L_GyroY,
        "R_GyroY": R_GyroY,
        "L_GyroZ": L_GyroZ,
        "R_GyroZ": R_GyroZ,
        "L_AccX": L_AccX,
        "R_AccX": R_AccX,
        "L_AccY": L_AccY,
        "R_AccY": R_AccY,
        "L_AccZ": L_AccZ,
        "R_AccZ": R_AccZ,
    })
    return df


@pytest.fixture
def sample_csv(tmp_path) -> str:
    """Write a 500-row H-Walker CSV and return the file path."""
    df = make_hwalker_csv(500)
    path = str(tmp_path / "trial_001.csv")
    df.to_csv(path, index=False)
    return path


@pytest.fixture
def sample_csv_path_and_df(tmp_path):
    """Return both (path, df) for tests that need the original DataFrame."""
    df = make_hwalker_csv(500)
    path = str(tmp_path / "trial_001.csv")
    df.to_csv(path, index=False)
    return path, df


@pytest.fixture
def two_csv_paths(tmp_path):
    """Two distinct CSV files for multi-file tests."""
    rng = np.random.default_rng(99)
    paths = []
    for i in range(2):
        df = make_hwalker_csv(500)
        # Shift forces slightly to make files distinguishable
        df["L_ActForce_N"] += rng.normal(i * 3, 0.5, 500)
        path = str(tmp_path / f"trial_{i:03d}.csv")
        df.to_csv(path, index=False)
        paths.append(path)
    return paths
