# 统一定义能耗预测目标的单位口径，并负责换算为分段总耗电。
"""能耗预测目标单位口径与换算工具。"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd


TargetMode = Literal["segment_energy_wh", "wh_per_km", "wh_per_s", "power_w"]


def infer_target_mode(target: str) -> TargetMode:
    """根据目标列名判断模型输出的物理单位。"""

    normalized = str(target or "").strip().lower()
    if normalized in {"segment_energy_wh", "energy_wh"} or normalized.endswith("_energy_wh"):
        return "segment_energy_wh"
    if normalized in {"segment_wh_per_s", "energy_wh_per_s", "wh_per_s"} or normalized.endswith("_wh_per_s"):
        return "wh_per_s"
    if normalized in {"mean_power_w", "avg_power_w", "average_power_w", "power_w"} or normalized.endswith("_power_w"):
        return "power_w"
    return "wh_per_km"


def is_segment_energy_target(target: str) -> bool:
    """判断目标列是否表示分段总耗电。"""

    return infer_target_mode(target) == "segment_energy_wh"


def distance_km(frame: pd.DataFrame) -> pd.Series:
    """读取分段距离并转换为公里。"""

    if "distance_m" not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame["distance_m"], errors="coerce") / 1000.0


def duration_s(frame: pd.DataFrame) -> pd.Series:
    """读取分段时长，单位秒。"""

    if "duration_s" not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame["duration_s"], errors="coerce")


def safe_rate_from_energy(energy_wh: pd.Series, distance_km_values: pd.Series) -> pd.Series:
    """用分段耗电和距离反算每公里耗电。"""

    out = pd.Series(np.nan, index=energy_wh.index, dtype=float)
    valid = (
        energy_wh.notna()
        & distance_km_values.notna()
        & np.isfinite(energy_wh)
        & np.isfinite(distance_km_values)
        & (distance_km_values > 1e-9)
    )
    out.loc[valid] = energy_wh.loc[valid] / distance_km_values.loc[valid]
    return out


def segment_energy_from_target_values(
    values,
    frame: pd.DataFrame,
    target: str,
) -> tuple[pd.Series, TargetMode]:
    """把不同目标单位统一换算为分段总耗电 Wh。"""

    mode = infer_target_mode(target)
    target_values = pd.Series(values, index=frame.index, dtype=float)
    if mode == "segment_energy_wh":
        return target_values, mode
    if mode == "wh_per_s":
        return target_values * duration_s(frame), mode
    if mode == "power_w":
        return target_values * duration_s(frame) / 3600.0, mode
    return target_values * distance_km(frame), mode


def segment_energy_from_single_prediction(
    model_output: float,
    target: str,
    segment_distance_km: float,
    segment_duration_s: float,
    multiplier: float = 1.0,
) -> float:
    """把单次模型输出换算为分段总耗电 Wh。"""

    mode = infer_target_mode(target)
    value = float(model_output) * float(multiplier)
    if mode == "segment_energy_wh":
        return value
    if mode == "wh_per_s":
        return value * float(segment_duration_s)
    if mode == "power_w":
        return value * float(segment_duration_s) / 3600.0
    return value * float(segment_distance_km)
