# 构建多来源无人机能耗训练表，并保留数据源角色与字段语义风险。
"""多来源训练表构建工具。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd

from .dataset import build_segment_dataset
from .field_semantics import audit_field_semantics, summarize_audits
from .route_features import build_preflight_training_feature_view
from .utils import ensure_dir


POWER_TARGET_COLUMNS = ["segment_energy_wh", "segment_wh_per_s", "mean_power_w"]
WEATHER_COMPLETE_COLUMNS = [
    "wind_speed_mps",
    "wind_dir_deg",
    "temperature_c",
    "pressure_hpa",
    "relative_humidity_pct",
]


def _resolve_optional_path(value: Optional[Union[str, Path]]) -> Optional[Path]:
    """解析可选路径。"""

    if value is None:
        return None
    return Path(value)


def _add_source_columns(frame: pd.DataFrame, dataset: str, role: str, source_data_type: str) -> pd.DataFrame:
    """补充数据源、训练角色和简单 one-hot 特征。"""

    out = frame.copy()
    if "source_dataset" not in out.columns:
        out["source_dataset"] = dataset
    else:
        out["source_dataset"] = out["source_dataset"].fillna(dataset).astype(str)
    if "source_data_type" not in out.columns:
        out["source_data_type"] = source_data_type
    else:
        out["source_data_type"] = out["source_data_type"].fillna(source_data_type).astype(str)
    out["training_role"] = role
    out["source_is_m100"] = (out["source_dataset"].astype(str) == "m100").astype(float)
    out["source_is_wemuav"] = (out["source_dataset"].astype(str) == "wemuav").astype(float)
    out["role_is_route_calibration"] = (out["training_role"].astype(str) == "route_calibration").astype(float)
    out["role_is_wind_phase_power_auxiliary"] = (
        out["training_role"].astype(str) == "wind_phase_power_auxiliary"
    ).astype(float)
    if "wind_speed_mps" in out.columns and "wind_speed_source" not in out.columns:
        out["wind_speed_source"] = (
            "historical_weather:hist_height_wind_speed_mps"
            if dataset == "m100"
            else "external_weather_or_flight_log"
        )
    if "wind_dir_deg" in out.columns and "wind_angle_source" not in out.columns:
        out["wind_angle_source"] = (
            "historical_weather:hist_height_wind_dir_deg"
            if dataset == "m100"
            else "external_weather_or_flight_log"
        )
    if "altitude_m" in out.columns and "altitude_source" not in out.columns:
        out["altitude_source"] = "programmed_altitude" if dataset == "m100" else "flight_log_position_z"
    return out


def _target_coverage(frame: pd.DataFrame) -> dict[str, float]:
    """统计关键训练目标覆盖率。"""

    coverage = {}
    for column in POWER_TARGET_COLUMNS + ["segment_wh_per_km"]:
        if column in frame.columns:
            coverage[column] = float(pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan).notna().mean())
    return coverage


def _weather_complete(frame: pd.DataFrame) -> pd.DataFrame:
    """抽取天气字段完整的训练子集。"""

    required = [column for column in WEATHER_COMPLETE_COLUMNS if column in frame.columns]
    if not required:
        return frame.iloc[0:0].copy()
    return frame.dropna(subset=required).copy()


def _write_frame(frame: pd.DataFrame, path: Path) -> Path:
    """写出 CSV，并确保父目录存在。"""

    ensure_dir(path.parent)
    frame.to_csv(path, index=False)
    return path


def _value_counts_dict(frame: pd.DataFrame, column: str) -> dict[str, int]:
    """返回 JSON 友好的计数字典。"""

    if column not in frame.columns:
        return {}
    counts = frame[column].value_counts(dropna=False)
    return {str(key): int(value) for key, value in counts.items()}


def build_multi_source_training_tables(
    output_dir: Union[str, Path],
    m100_input_csv: Optional[Union[str, Path]] = None,
    wemuav_input_csv: Optional[Union[str, Path]] = None,
    segment_seconds: float = 60.0,
    min_duration_s: float = 10.0,
    m100_min_distance_m: float = 50.0,
    wemuav_min_distance_m: float = 0.1,
    m100_route: Optional[str] = None,
    wemuav_route: Optional[str] = None,
) -> dict:
    """从可用来源构建分源训练表和合并训练表。"""

    output_root = Path(output_dir)
    ensure_dir(output_root)
    frames = []
    outputs: dict[str, str] = {}
    audits = []

    m100_path = _resolve_optional_path(m100_input_csv)
    if m100_path is not None and m100_path.exists():
        m100_segments = build_segment_dataset(
            input_csv=m100_path,
            output_csv=output_root / "m100_route_segments.csv",
            route=m100_route,
            segment_seconds=segment_seconds,
            min_distance_m=m100_min_distance_m,
            min_duration_s=min_duration_s,
        )
        m100_segments = _add_source_columns(
            m100_segments,
            dataset="m100",
            role="route_calibration",
            source_data_type="m100_processed",
        )
        _write_frame(m100_segments, output_root / "m100_route_segments.csv")
        m100_preflight = build_preflight_training_feature_view(m100_segments)
        m100_preflight = _add_source_columns(
            m100_preflight,
            dataset="m100",
            role="route_calibration",
            source_data_type="m100_processed",
        )
        _write_frame(m100_preflight, output_root / "m100_route_preflight.csv")
        frames.append(m100_preflight)
        outputs["m100_route_segments"] = str(output_root / "m100_route_segments.csv")
        outputs["m100_route_preflight"] = str(output_root / "m100_route_preflight.csv")
        audits.append(audit_field_semantics(m100_preflight, dataset="m100", label="m100_route_preflight"))

    wemuav_path = _resolve_optional_path(wemuav_input_csv)
    if wemuav_path is not None and wemuav_path.exists():
        wemuav_segments = build_segment_dataset(
            input_csv=wemuav_path,
            output_csv=output_root / "wemuav_power_segments.csv",
            route=wemuav_route,
            segment_seconds=segment_seconds,
            min_distance_m=wemuav_min_distance_m,
            min_duration_s=min_duration_s,
        )
        wemuav_segments = _add_source_columns(
            wemuav_segments,
            dataset="wemuav",
            role="wind_phase_power_auxiliary",
            source_data_type="wemuav_datcon",
        )
        _write_frame(wemuav_segments, output_root / "wemuav_power_segments.csv")
        wemuav_preflight = build_preflight_training_feature_view(wemuav_segments)
        wemuav_preflight = _add_source_columns(
            wemuav_preflight,
            dataset="wemuav",
            role="wind_phase_power_auxiliary",
            source_data_type="wemuav_datcon",
        )
        _write_frame(wemuav_preflight, output_root / "wemuav_power_preflight.csv")
        frames.append(wemuav_preflight)
        outputs["wemuav_power_segments"] = str(output_root / "wemuav_power_segments.csv")
        outputs["wemuav_power_preflight"] = str(output_root / "wemuav_power_preflight.csv")
        audits.append(audit_field_semantics(wemuav_preflight, dataset="wemuav", label="wemuav_power_preflight"))

    if not frames:
        raise ValueError("没有可用数据源用于构建训练表。")

    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined_path = _write_frame(combined, output_root / "combined_power_preflight.csv")
    outputs["combined_power_preflight"] = str(combined_path)

    weather_complete = _weather_complete(combined)
    weather_complete_path = _write_frame(weather_complete, output_root / "combined_power_preflight_weather_complete.csv")
    outputs["combined_power_preflight_weather_complete"] = str(weather_complete_path)

    summary = {
        "outputs": outputs,
        "segment_seconds": float(segment_seconds),
        "min_duration_s": float(min_duration_s),
        "rows": {
            "combined_power_preflight": int(len(combined.index)),
            "combined_power_preflight_weather_complete": int(len(weather_complete.index)),
        },
        "source_counts": _value_counts_dict(combined, "source_dataset"),
        "role_counts": _value_counts_dict(combined, "training_role"),
        "target_coverage": _target_coverage(combined),
        "weather_complete_target_coverage": _target_coverage(weather_complete),
        "semantic_audit": summarize_audits(audits),
        "recommended_training_targets": [
            {
                "target": "segment_energy_wh",
                "reason": "同时适配路线飞行和悬停/垂直工况，不受水平距离接近 0 的 Wh/km 爆炸影响。",
            },
            {
                "target": "mean_power_w",
                "reason": "适合 WEMUAV 这类风场/阶段实验数据，也适合后续时序模型。",
            },
            {
                "target": "segment_wh_per_km",
                "reason": "仅建议用于 M100 路线飞行校准，不建议直接纳入 WEMUAV 悬停段。",
            },
        ],
    }
    (output_root / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary
