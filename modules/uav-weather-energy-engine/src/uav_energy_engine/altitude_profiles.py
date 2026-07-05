# 统一管理训练、审计和部署对照使用的高度字段口径，避免计划高度、海拔高度和相对高度混用。
"""高度字段口径转换工具。"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd


ALTITUDE_PROFILES = [
    "current",
    "planned_level",
    "route_3d",
]

ALTITUDE_LEVEL_COLUMNS = [
    "altitude_delta_m",
    "altitude_range_m",
    "altitude_gain_m",
    "altitude_loss_m",
    "vertical_speed_mean_mps",
    "vertical_speed_abs_mean_mps",
    "vertical_speed_abs_p95_mps",
]

VERTICAL_PHASE_ZERO_COLUMNS = [
    "climb_ratio",
    "descent_ratio",
    "phase_is_climb",
    "phase_is_descent",
]

VERTICAL_PHASE_LEVEL_COLUMNS = [
    "level_ratio",
    "phase_is_level",
]

CLIMB_THRESHOLD_MPS = 0.3


def _numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    """安全读取数值列。"""

    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan)


def _set_existing_columns(frame: pd.DataFrame, columns: Sequence[str], value: float) -> list[str]:
    """仅覆盖已存在的列，并返回被修改列名。"""

    changed = []
    for column in columns:
        if column in frame.columns:
            frame[column] = float(value)
            changed.append(column)
    return changed


def _apply_planned_level(out: pd.DataFrame) -> tuple[pd.DataFrame, list[str], pd.Series]:
    """应用固定高度计划口径。"""

    changed_columns: list[str] = []
    altitude = _numeric_series(out, "altitude_m")
    if altitude.notna().any():
        for column in ["altitude_start_m", "altitude_end_m"]:
            if column in out.columns:
                out[column] = altitude
                changed_columns.append(column)

    changed_columns.extend(_set_existing_columns(out, ALTITUDE_LEVEL_COLUMNS, 0.0))
    changed_columns.extend(_set_existing_columns(out, VERTICAL_PHASE_ZERO_COLUMNS, 0.0))
    changed_columns.extend(_set_existing_columns(out, VERTICAL_PHASE_LEVEL_COLUMNS, 1.0))
    if "phase_label" in out.columns:
        phases = out["phase_label"].fillna("unknown").astype(str)
        out["phase_label"] = phases.where(~phases.isin({"climb", "descent"}), "level")
        changed_columns.append("phase_label")
    return out, changed_columns, altitude


def _apply_route_3d(out: pd.DataFrame) -> tuple[pd.DataFrame, list[str], pd.Series]:
    """应用计划 3D 航线口径，仅用分段起终点高度计算垂直动态量。"""

    changed_columns: list[str] = []
    altitude = _numeric_series(out, "altitude_m")
    start = _numeric_series(out, "altitude_start_m").fillna(altitude)
    end = _numeric_series(out, "altitude_end_m").fillna(altitude)
    duration = _numeric_series(out, "duration_s")
    valid_duration = duration > 1e-9
    delta = end - start
    vertical_speed = pd.Series(np.nan, index=out.index, dtype=float)
    vertical_speed.loc[valid_duration] = delta.loc[valid_duration] / duration.loc[valid_duration]
    abs_vertical_speed = vertical_speed.abs()

    route_values = {
        "altitude_start_m": start,
        "altitude_end_m": end,
        "altitude_delta_m": delta,
        "altitude_range_m": delta.abs(),
        "altitude_gain_m": delta.clip(lower=0.0),
        "altitude_loss_m": (-delta.clip(upper=0.0)),
        "vertical_speed_mean_mps": vertical_speed,
        "vertical_speed_abs_mean_mps": abs_vertical_speed,
        "vertical_speed_abs_p95_mps": abs_vertical_speed,
    }
    for column, value in route_values.items():
        out[column] = value
        changed_columns.append(column)

    vertical_active = abs_vertical_speed > CLIMB_THRESHOLD_MPS
    vertical_inactive = vertical_speed.notna() & ~vertical_active
    phase_values = {
        "climb_ratio": 0.0,
        "descent_ratio": 0.0,
        "phase_is_climb": 0.0,
        "phase_is_descent": 0.0,
    }
    for column, value in phase_values.items():
        if column in out.columns:
            out.loc[vertical_inactive, column] = value
            changed_columns.append(column)
    for column in ["level_ratio", "phase_is_level"]:
        if column in out.columns:
            out.loc[vertical_inactive, column] = 1.0
            changed_columns.append(column)
    if "phase_label" in out.columns:
        phases = out["phase_label"].fillna("unknown").astype(str).copy()
        phases.loc[vertical_inactive & phases.isin({"climb", "descent"})] = "level"
        out["phase_label"] = phases
        changed_columns.append("phase_label")
    return out, changed_columns, altitude


def apply_altitude_profile(frame: pd.DataFrame, altitude_profile: str) -> tuple[pd.DataFrame, dict]:
    """把高度字段转换为指定训练/部署口径。"""

    if altitude_profile not in ALTITUDE_PROFILES:
        raise ValueError(f"不支持的高度字段口径: {altitude_profile}")
    out = frame.copy()
    if altitude_profile == "current":
        return out, {
            "altitude_profile": altitude_profile,
            "changed": False,
            "changed_columns": [],
            "note": "保持输入表中的当前高度字段。",
        }

    if altitude_profile == "planned_level":
        out, changed_columns, altitude = _apply_planned_level(out)
        note = "使用计划巡航高度模拟固定高度飞行前输入，并清零实飞高度动态量。"
    else:
        out, changed_columns, altitude = _apply_route_3d(out)
        note = "使用计划 3D 航线分段起终点高度生成垂直动态量，不使用逐时刻实飞高度抖动。"
    if "altitude_source" in out.columns:
        source_detail = "altitude_m" if altitude_profile == "planned_level" else "altitude_start_end_m"
        out["altitude_source"] = f"altitude_profile:{altitude_profile}:{source_detail}"
        changed_columns.append("altitude_source")

    changed_columns = sorted(set(changed_columns))
    out["altitude_profile"] = altitude_profile
    return out, {
        "altitude_profile": altitude_profile,
        "changed": bool(changed_columns),
        "changed_columns": changed_columns,
        "altitude_m_coverage": float(altitude.notna().mean()) if len(out.index) else 0.0,
        "note": note,
    }
