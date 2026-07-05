# 统一管理训练和审计使用的风字段口径转换，避免部署可用天气风与机载日志风混用。
"""风字段口径转换工具。"""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np
import pandas as pd

from .features import compute_wind_components


WIND_PROFILES = [
    "current",
    "weather_basic",
    "height_weather",
]


def numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    """安全读取数值列。"""

    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan)


def first_existing_column(frame: pd.DataFrame, candidates: Sequence[str]) -> Optional[str]:
    """返回第一个存在且至少有一个有效值的候选列。"""

    for column in candidates:
        if column in frame.columns and numeric_series(frame, column).notna().any():
            return column
    return None


def compute_wind_component_series(
    wind_speed: pd.Series,
    wind_dir: pd.Series,
    heading: pd.Series,
) -> tuple[pd.Series, pd.Series]:
    """按特征生成公式计算逆风和侧风序列。"""

    headwind = pd.Series(np.nan, index=wind_speed.index, dtype=float)
    crosswind = pd.Series(np.nan, index=wind_speed.index, dtype=float)
    valid = wind_speed.notna() & wind_dir.notna() & heading.notna()
    if not valid.any():
        return headwind, crosswind
    for idx in wind_speed.loc[valid].index:
        one_headwind, one_crosswind = compute_wind_components(
            float(wind_speed.loc[idx]),
            float(wind_dir.loc[idx]),
            float(heading.loc[idx]),
        )
        headwind.loc[idx] = one_headwind
        crosswind.loc[idx] = one_crosswind
    return headwind, crosswind


def apply_wind_profile(frame: pd.DataFrame, wind_profile: str) -> tuple[pd.DataFrame, dict]:
    """把历史/高度层天气风转换成模型同名风特征。"""

    if wind_profile not in WIND_PROFILES:
        raise ValueError(f"不支持的风字段口径: {wind_profile}")
    out = frame.copy()
    if wind_profile == "current":
        return out, {
            "wind_profile": wind_profile,
            "changed": False,
            "source_speed_column": "wind_speed_mps",
            "source_dir_column": "wind_dir_deg",
            "note": "保持输入表中的当前风字段。",
        }

    if wind_profile == "weather_basic":
        speed_col = first_existing_column(out, ["hist_wind_speed_mps"])
        dir_col = first_existing_column(out, ["hist_wind_dir_deg"])
    else:
        speed_col = first_existing_column(
            out,
            ["hist_height_wind_speed_mps", "hist_wind_speed_100m_mps", "hist_wind_speed_mps"],
        )
        dir_col = first_existing_column(
            out,
            ["hist_height_wind_dir_deg", "hist_wind_dir_100m_deg", "hist_wind_dir_deg"],
        )

    meta = {
        "wind_profile": wind_profile,
        "changed": False,
        "source_speed_column": speed_col,
        "source_dir_column": dir_col,
        "note": "使用天气风覆盖模型同名风特征，并按 heading_deg 重算逆风/侧风。",
    }
    if not speed_col or not dir_col:
        meta["note"] = "缺少可用天气风速或风向列，保持当前风字段。"
        return out, meta

    speed = numeric_series(out, speed_col)
    direction = numeric_series(out, dir_col)
    out["wind_speed_mps"] = speed
    out["wind_dir_deg"] = direction
    if "heading_deg" in out.columns:
        headwind, crosswind = compute_wind_component_series(speed, direction, numeric_series(out, "heading_deg"))
        out["headwind_mps"] = headwind
        out["crosswind_mps"] = crosswind
    if "hist_wind_gust_mps" in out.columns:
        out["wind_gust_mps"] = numeric_series(out, "hist_wind_gust_mps")
    out["wind_speed_source"] = f"wind_profile:{wind_profile}:{speed_col}"
    out["wind_angle_source"] = f"wind_profile:{wind_profile}:{dir_col}"
    meta["changed"] = True
    meta["wind_speed_coverage"] = float(out["wind_speed_mps"].notna().mean())
    meta["wind_dir_coverage"] = float(out["wind_dir_deg"].notna().mean())
    meta["headwind_coverage"] = float(out["headwind_mps"].notna().mean()) if "headwind_mps" in out.columns else 0.0
    meta["crosswind_coverage"] = float(out["crosswind_mps"].notna().mean()) if "crosswind_mps" in out.columns else 0.0
    return out, meta
