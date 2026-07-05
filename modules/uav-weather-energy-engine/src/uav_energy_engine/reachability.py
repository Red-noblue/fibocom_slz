# 根据泛化误差校准保守能耗与航程可达性输出。
"""保守可达性校准与预测结果扩展。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Sequence, Union

import numpy as np
import pandas as pd


DEFAULT_REACHABILITY_QUANTILES = (0.5, 0.9, 0.95)


def _quantile_name(level: float) -> str:
    """把分位数转换为稳定字段名。"""

    return "p{:02d}".format(int(round(float(level) * 100.0)))


def _read_frame(value: Union[str, Path, pd.DataFrame]) -> pd.DataFrame:
    """读取 DataFrame 或 CSV 路径。"""

    if isinstance(value, pd.DataFrame):
        return value.copy()
    return pd.read_csv(value)


def _finite_positive(series: pd.Series) -> pd.Series:
    """保留有限正数。"""

    numeric = pd.to_numeric(series, errors="coerce")
    return numeric[numeric.notna() & np.isfinite(numeric) & (numeric > 1e-9)]


def build_reachability_safety_profile(
    flight_errors: Union[str, Path, pd.DataFrame],
    quantiles: Sequence[float] = DEFAULT_REACHABILITY_QUANTILES,
    source_name: str | None = None,
) -> dict:
    """从飞行级误差表生成能耗保守放大系数。"""

    frame = _read_frame(flight_errors)
    required = {"actual_total_energy_wh", "predicted_total_energy_wh"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError("飞行级误差表缺少必要列: {}".format(", ".join(missing)))

    actual = _finite_positive(frame["actual_total_energy_wh"])
    predicted = _finite_positive(frame["predicted_total_energy_wh"])
    aligned = pd.concat([actual.rename("actual"), predicted.rename("predicted")], axis=1).dropna()
    if aligned.empty:
        raise ValueError("飞行级误差表没有可用的正能耗样本。")

    raw_multiplier = aligned["actual"] / aligned["predicted"]
    safety_multiplier = raw_multiplier.clip(lower=1.0)
    underprediction_mask = raw_multiplier > 1.0
    error_pct_pred_base = (aligned["actual"] - aligned["predicted"]) / aligned["predicted"] * 100.0

    quantile_payload = {}
    for level in quantiles:
        numeric_level = float(level)
        if numeric_level <= 0.0 or numeric_level >= 1.0:
            raise ValueError("分位数必须位于 0 到 1 之间: {}".format(level))
        name = _quantile_name(numeric_level)
        empirical_multiplier = float(raw_multiplier.quantile(numeric_level))
        energy_multiplier = float(max(1.0, safety_multiplier.quantile(numeric_level)))
        exceedance_count = int((raw_multiplier > energy_multiplier).sum())
        quantile_payload[name] = {
            "level": numeric_level,
            "empirical_energy_multiplier": empirical_multiplier,
            "energy_multiplier": energy_multiplier,
            "energy_margin_pct": (energy_multiplier - 1.0) * 100.0,
            "range_multiplier": 1.0 / energy_multiplier if energy_multiplier > 1e-9 else float("nan"),
            "exceedance_count": exceedance_count,
            "empirical_coverage_rate": 1.0 - exceedance_count / float(len(raw_multiplier.index)),
        }

    profile = {
        "profile_type": "flight_energy_safety_multiplier",
        "calibration_source": source_name or "",
        "row_count": int(len(frame.index)),
        "valid_count": int(len(aligned.index)),
        "quantiles": quantile_payload,
        "diagnostics": {
            "underprediction_count": int(underprediction_mask.sum()),
            "underprediction_rate": float(underprediction_mask.mean()),
            "mean_energy_error_pct_pred_base": float(error_pct_pred_base.mean()),
            "p95_abs_energy_error_pct_pred_base": float(error_pct_pred_base.abs().quantile(0.95)),
            "max_energy_multiplier": float(raw_multiplier.max()),
            "min_energy_multiplier": float(raw_multiplier.min()),
        },
    }
    return profile


def save_reachability_safety_profile(profile: Mapping, output_path: Union[str, Path]) -> Path:
    """保存保守可达性校准文件。"""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(dict(profile), fh, indent=2, ensure_ascii=False)
    return path


def load_reachability_safety_profile(value: Union[str, Path, Mapping]) -> dict:
    """加载保守可达性校准文件。"""

    if isinstance(value, Mapping):
        return dict(value)
    with Path(value).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def apply_conservative_reachability(summary: Mapping, profile: Mapping) -> dict:
    """把保守能耗分位数应用到单次任务预测摘要。"""

    predicted_energy_wh = float(summary["predicted_total_energy_wh"])
    route_length_km = float(summary["route_length_km"])
    battery_wh = float(summary["battery_wh"])
    predicted_rate_wh_per_km = predicted_energy_wh / route_length_km if route_length_km > 1e-9 else float("nan")

    quantile_outputs = {}
    for name, spec in dict(profile.get("quantiles", {})).items():
        multiplier = float(spec["energy_multiplier"])
        conservative_energy_wh = predicted_energy_wh * multiplier
        conservative_rate_wh_per_km = predicted_rate_wh_per_km * multiplier
        conservative_range_km = (
            battery_wh / conservative_rate_wh_per_km
            if np.isfinite(conservative_rate_wh_per_km) and conservative_rate_wh_per_km > 1e-9
            else float("nan")
        )
        remaining_wh = battery_wh - conservative_energy_wh
        quantile_outputs[name] = {
            "level": float(spec.get("level", float("nan"))),
            "energy_multiplier": multiplier,
            "energy_margin_pct": float(spec.get("energy_margin_pct", (multiplier - 1.0) * 100.0)),
            "estimated_total_energy_wh": conservative_energy_wh,
            "estimated_remaining_battery_wh": remaining_wh,
            "estimated_range_km": conservative_range_km,
            "route_feasible": bool(conservative_energy_wh <= battery_wh and conservative_range_km >= route_length_km),
        }

    risk_level = "unknown"
    recommended = quantile_outputs.get("p95") or quantile_outputs.get("p90") or quantile_outputs.get("p50")
    if recommended:
        if not recommended["route_feasible"]:
            risk_level = "high"
        elif "p90" in quantile_outputs and not quantile_outputs["p90"]["route_feasible"]:
            risk_level = "medium"
        else:
            risk_level = "low"

    return {
        "profile_type": profile.get("profile_type", "flight_energy_safety_multiplier"),
        "calibration_source": profile.get("calibration_source", ""),
        "calibration_valid_count": int(profile.get("valid_count", 0)),
        "point_prediction": {
            "predicted_total_energy_wh": predicted_energy_wh,
            "predicted_rate_wh_per_km": predicted_rate_wh_per_km,
            "predicted_range_km": float(summary.get("predicted_range_km", float("nan"))),
        },
        "quantiles": quantile_outputs,
        "recommended_quantile": "p95" if "p95" in quantile_outputs else ("p90" if "p90" in quantile_outputs else "p50"),
        "risk_level": risk_level,
    }
