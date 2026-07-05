# 生成飞前计划航线可计算的等效风特征，统一训练端和部署端的风输入口径。
"""飞前等效风特征转换。"""

from __future__ import annotations

from typing import Mapping

import numpy as np
import pandas as pd

from .features import ensure_planned_ground_speed


PLANNED_EQUIVALENT_WIND_FEATURE_COLUMNS = [
    "equivalent_airspeed_mps",
    "equivalent_along_track_airspeed_mps",
    "equivalent_cross_track_airspeed_mps",
    "equivalent_crosswind_abs_mps",
    "headwind_ratio",
    "crosswind_ratio",
    "tailwind_mps",
]


def compute_equivalent_airspeed(
    planned_ground_speed_mps: float,
    headwind_mps: float,
    crosswind_mps: float,
) -> float:
    """由计划地速、逆风和侧风计算维持计划航迹所需的等效空速。"""

    ground_speed = float(planned_ground_speed_mps)
    headwind = float(headwind_mps)
    crosswind = float(crosswind_mps)
    return float(np.hypot(ground_speed + headwind, crosswind))


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    """安全读取数值列。"""

    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan)


def add_planned_equivalent_wind_features(frame: pd.DataFrame) -> pd.DataFrame:
    """把环境风和计划地速转换为部署前可生成的等效相对风特征。"""

    out = ensure_planned_ground_speed(frame)
    planned_speed = _numeric(out, "planned_ground_speed_mps")
    headwind = _numeric(out, "headwind_mps")
    crosswind = _numeric(out, "crosswind_mps")

    along_track = planned_speed + headwind
    equivalent_airspeed = np.hypot(along_track, crosswind)
    speed_denom = planned_speed.abs().where(planned_speed.abs() > 1e-9, np.nan)

    out["equivalent_airspeed_mps"] = equivalent_airspeed
    out["equivalent_along_track_airspeed_mps"] = along_track
    out["equivalent_cross_track_airspeed_mps"] = crosswind
    out["equivalent_crosswind_abs_mps"] = crosswind.abs()
    out["headwind_ratio"] = headwind / speed_denom
    out["crosswind_ratio"] = crosswind.abs() / speed_denom
    out["tailwind_mps"] = (-headwind).clip(lower=0.0)

    valid = planned_speed.notna() & headwind.notna() & crosswind.notna()
    out["equivalent_wind_feature_source"] = "planned_equivalent:planned_ground_speed+headwind+crosswind"
    out.loc[~valid, "equivalent_wind_feature_source"] = "planned_equivalent:missing_inputs"
    return out


def add_planned_equivalent_wind_features_to_row(row: Mapping[str, object]) -> dict:
    """为单行预测输入补充等效风特征。"""

    frame = add_planned_equivalent_wind_features(pd.DataFrame([dict(row)]))
    return frame.iloc[0].to_dict()
