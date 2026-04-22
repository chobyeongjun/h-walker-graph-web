from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AnalysisType(str, Enum):
    force = "force"
    velocity = "velocity"
    position = "position"
    current = "current"
    imu = "imu"
    gyro = "gyro"
    accel = "accel"
    gait = "gait"
    gcp = "gcp"
    feedforward = "feedforward"
    compare = "compare"


# H-Walker firmware column names (67 cols, 111Hz)
COLUMN_GROUPS: dict[AnalysisType, list[str]] = {
    AnalysisType.force: [
        "L_ActForce_N", "R_ActForce_N",
        "L_DesForce_N", "R_DesForce_N",
    ],
    AnalysisType.velocity: [
        "L_ActVel_mps", "R_ActVel_mps",
        "L_DesVel_mps", "R_DesVel_mps",
    ],
    AnalysisType.position: [
        "L_ActPos_deg", "R_ActPos_deg",
        "L_DesPos_deg", "R_DesPos_deg",
    ],
    AnalysisType.current: [
        "L_ActCurr_A", "R_ActCurr_A",
        "L_DesCurr_A", "R_DesCurr_A",
    ],
    AnalysisType.imu: [
        "L_Pitch", "R_Pitch",
        "L_Roll", "R_Roll",
        "L_Yaw", "R_Yaw",
    ],
    AnalysisType.gyro: [
        "L_Gx", "L_Gy", "L_Gz",
        "R_Gx", "R_Gy", "R_Gz",
    ],
    AnalysisType.accel: [
        "L_Ax", "L_Ay", "L_Az",
        "R_Ax", "R_Ay", "R_Az",
    ],
    AnalysisType.gait: [
        "L_GCP", "R_GCP",
        "L_ActForce_N", "R_ActForce_N",
        "L_Phase", "R_Phase",
        "L_Event", "R_Event",
    ],
    AnalysisType.gcp: [
        "L_GCP", "R_GCP",
    ],
    AnalysisType.feedforward: [
        "L_MotionFF_mps", "R_MotionFF_mps",
        "L_TreadmillFF_mps", "R_TreadmillFF_mps",
        "TFF_Gain", "FF_Gain_F",
    ],
    AnalysisType.compare: [
        "L_ActForce_N", "R_ActForce_N",
        "L_DesForce_N", "R_DesForce_N",
    ],
}


class AnalysisRequest(BaseModel):
    analysis_type: AnalysisType
    columns: Optional[list[str]] = None
    sides: list[str] = Field(default=["both"])
    normalize_gcp: bool = False
    compare_mode: bool = False
    file_paths: list[str] = Field(default_factory=list)
    statistics: bool = False

    def resolve_columns(self) -> list[str]:
        """Return columns to plot.

        If columns is explicitly set, return unchanged (explicit wins over side filtering).
        Otherwise take COLUMN_GROUPS default and filter by sides.
        """
        if self.columns is not None:
            return self.columns

        default = COLUMN_GROUPS.get(self.analysis_type, [])

        if "both" in self.sides:
            return list(default)

        filtered: list[str] = []
        for col in default:
            if "left" in self.sides and col.startswith("L_"):
                filtered.append(col)
            if "right" in self.sides and col.startswith("R_"):
                filtered.append(col)
            # include non-sided columns (TFF_Gain, FF_Gain_F, etc.)
            if not col.startswith("L_") and not col.startswith("R_"):
                filtered.append(col)
        return filtered


class GraphSpec(BaseModel):
    request: AnalysisRequest
    csv_paths: list[str]


class StatsResult(BaseModel):
    column: str
    file: str
    mean: float
    std: float
    max_val: float
    min_val: float


class PlotlyTrace(BaseModel):
    x: list
    y: list
    name: str
    mode: str
    line: dict


class PlotlyResponse(BaseModel):
    data: list[dict]
    layout: dict
