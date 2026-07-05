# 审计高度、风和功率字段物理口径，避免模型把字段混用误差学成规律。
"""训练侧物理字段语义审计。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Sequence


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / ".vendor"
SRC = ROOT / "src"
for path in (VENDOR, SRC):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

import numpy as np
import pandas as pd

from uav_energy_engine.altitude_profiles import ALTITUDE_PROFILES, apply_altitude_profile
from uav_energy_engine.evaluate import save_summary
from uav_energy_engine.wind_profiles import WIND_PROFILES, apply_wind_profile


DEFAULT_FEATURES = "outputs/multi_source_training/combined_power_preflight_weather_complete.csv"
DEFAULT_BASELINE_SUMMARY = "outputs/multi_source_training/mass_assumption_experiment_phase_balanced/summary.json"
DEFAULT_OUTPUT_DIR = "outputs/multi_source_training/physical_field_semantics_audit"

WIND_FEATURES = {
    "wind_speed_mps",
    "wind_dir_deg",
    "headwind_mps",
    "crosswind_mps",
    "wind_gust_mps",
}
ALTITUDE_FEATURES = {
    "altitude_m",
    "altitude_delta_m",
    "altitude_range_m",
    "altitude_gain_m",
    "altitude_loss_m",
    "vertical_speed_mean_mps",
    "vertical_speed_abs_mean_mps",
    "vertical_speed_abs_p95_mps",
}
POWER_COLUMNS = [
    "mean_power_w",
    "segment_wh_per_s",
    "segment_energy_wh",
    "duration_s",
]


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="审计高度、风和功率字段物理口径。")
    parser.add_argument("--features", default=DEFAULT_FEATURES, help="多来源训练特征表 CSV")
    parser.add_argument("--baseline-summary", default=DEFAULT_BASELINE_SUMMARY, help="当前最佳基线 summary.json")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="审计输出目录")
    parser.add_argument("--wind-profile", default="current", choices=WIND_PROFILES, help="审计前应用的风字段口径")
    parser.add_argument("--altitude-profile", default="current", choices=ALTITUDE_PROFILES, help="审计前应用的高度字段口径")
    return parser.parse_args()


def _resolve_path(value: str) -> Path:
    """解析相对项目根目录的路径。"""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    """安全读取数值列。"""

    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").replace([np.inf, -np.inf], np.nan)


def _coverage(frame: pd.DataFrame, column: str) -> float:
    """计算列覆盖率。"""

    if column not in frame.columns or frame.empty:
        return 0.0
    return float(frame[column].replace([np.inf, -np.inf], np.nan).notna().mean())


def _safe_float(value) -> Optional[float]:
    """把数值转换成可 JSON 序列化的 float。"""

    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if np.isfinite(out) else None


def _source_groups(frame: pd.DataFrame):
    """按数据源分组；没有数据源列时退回 all。"""

    if "source_dataset" not in frame.columns:
        yield "all", frame
        return
    for source, group in frame.groupby(frame["source_dataset"].fillna("unknown").astype(str), sort=True):
        yield str(source), group


def _source_value_counts(group: pd.DataFrame, column: str) -> str:
    """把来源列的取值统计压成可读字符串。"""

    if column not in group.columns:
        return ""
    counts = group[column].fillna("__nan__").astype(str).value_counts().head(10)
    return "; ".join(f"{key}:{int(value)}" for key, value in counts.items())


def _median_abs_diff_pct(actual: pd.Series, predicted: pd.Series) -> tuple[float, float, float]:
    """计算绝对差和相对差统计。"""

    valid = actual.notna() & predicted.notna() & (actual.abs() > 1e-9)
    if not valid.any():
        return float("nan"), float("nan"), float("nan")
    diff = (predicted.loc[valid] - actual.loc[valid]).abs()
    pct = diff / actual.loc[valid].abs() * 100.0
    return float(diff.median()), float(diff.quantile(0.95)), float(pct.quantile(0.95))


def load_baseline_summary(path: Path) -> dict:
    """读取当前最佳基线摘要。"""

    if not path.exists():
        return {"path": str(path), "features": [], "best": {}, "missing": True}
    payload = json.loads(path.read_text(encoding="utf-8"))
    best = payload.get("best_by_segment_rmse") or {}
    features = []
    if best.get("features"):
        features = [item.strip() for item in str(best["features"]).split(",") if item.strip()]
    return {
        "path": str(path),
        "features": features,
        "best": best,
        "missing": False,
    }


def build_power_consistency(frame: pd.DataFrame) -> pd.DataFrame:
    """检查 mean_power_w 是否和能量/时长口径一致。"""

    rows = []
    for source, group in _source_groups(frame):
        actual = _numeric(group, "mean_power_w")
        wh_per_s = _numeric(group, "segment_wh_per_s")
        energy_wh = _numeric(group, "segment_energy_wh")
        duration_s = _numeric(group, "duration_s")
        derived_from_whps = wh_per_s * 3600.0
        derived_from_energy_duration = energy_wh / duration_s.replace(0.0, np.nan) * 3600.0

        whps_median, whps_p95, whps_pct95 = _median_abs_diff_pct(actual, derived_from_whps)
        energy_median, energy_p95, energy_pct95 = _median_abs_diff_pct(actual, derived_from_energy_duration)
        risk = "low"
        reason = "mean_power_w 与 segment_wh_per_s/segment_energy_wh 反算功率一致。"
        if any(np.isfinite(value) and value > 1.0 for value in [whps_p95, energy_p95]):
            risk = "high"
            reason = "mean_power_w 与能量/时长反算功率存在明显差异，目标口径可能不一致。"
        elif any(np.isfinite(value) and value > 0.1 for value in [whps_p95, energy_p95]):
            risk = "medium"
            reason = "mean_power_w 与能量/时长反算功率存在轻微差异，需要确认单位和聚合方式。"

        rows.append(
            {
                "source_dataset": source,
                "rows": int(len(group.index)),
                "mean_power_coverage": _coverage(group, "mean_power_w"),
                "segment_wh_per_s_coverage": _coverage(group, "segment_wh_per_s"),
                "segment_energy_wh_coverage": _coverage(group, "segment_energy_wh"),
                "duration_s_coverage": _coverage(group, "duration_s"),
                "median_abs_diff_whps_to_power_w": whps_median,
                "p95_abs_diff_whps_to_power_w": whps_p95,
                "p95_abs_pct_diff_whps_to_power": whps_pct95,
                "median_abs_diff_energy_duration_to_power_w": energy_median,
                "p95_abs_diff_energy_duration_to_power_w": energy_p95,
                "p95_abs_pct_diff_energy_duration_to_power": energy_pct95,
                "risk_level": risk,
                "finding": reason,
                "recommended_action": "低风险时可继续用 mean_power_w；高风险时必须先统一目标列口径再训练。",
            }
        )
    return pd.DataFrame(rows)


def _wind_source_column(feature: str) -> str:
    """返回风特征对应的来源列。"""

    if feature in {"wind_dir_deg"}:
        return "wind_angle_source"
    if feature in {"wind_speed_mps", "headwind_mps", "crosswind_mps"}:
        return "wind_speed_source"
    return "weather_source"


def build_wind_semantics(frame: pd.DataFrame, baseline_features: Sequence[str]) -> pd.DataFrame:
    """审计风字段是否为部署可获得口径。"""

    rows = []
    baseline_set = set(baseline_features)
    wind_columns = sorted(column for column in WIND_FEATURES if column in frame.columns)
    alias_pairs = [
        ("wind_speed_mps", "hist_wind_speed_mps"),
        ("wind_speed_mps", "hist_height_wind_speed_mps"),
        ("headwind_mps", "hist_headwind_mps"),
        ("crosswind_mps", "hist_crosswind_mps"),
    ]
    for source, group in _source_groups(frame):
        for feature in wind_columns:
            values = _numeric(group, feature)
            source_col = _wind_source_column(feature)
            source_counts = _source_value_counts(group, source_col)
            in_baseline = feature in baseline_set
            has_flight_log_source = "flight_log" in source_counts.lower()
            coverage = _coverage(group, feature)
            risk = "low"
            finding = "风字段来源看起来可作为当前训练输入。"
            action = "保持来源列，后续按部署可获得字段生成同名特征。"
            if in_baseline and has_flight_log_source:
                risk = "high"
                finding = "当前最佳模型使用该风字段，但该数据源来自 flight_log/机载日志，飞行前部署不可直接获得。"
                action = "用历史天气/预报天气转换模块生成同名风特征，或在部署模型中禁用该字段做对照实验。"
            elif in_baseline and coverage < 0.95:
                risk = "medium"
                finding = "当前最佳模型使用该风字段，但覆盖率不足，训练清洗会丢样本或引入样本偏置。"
                action = "补齐天气字段，或加入缺失指示并比较禁用该字段的结果。"

            rows.append(
                {
                    "source_dataset": source,
                    "field": feature,
                    "field_group": "wind",
                    "in_current_best_features": bool(in_baseline),
                    "coverage": coverage,
                    "min": _safe_float(values.min()),
                    "median": _safe_float(values.median()),
                    "max": _safe_float(values.max()),
                    "source_column": source_col,
                    "source_value_counts": source_counts,
                    "risk_level": risk,
                    "finding": finding,
                    "recommended_action": action,
                }
            )

        for left, right in alias_pairs:
            if left not in group.columns or right not in group.columns:
                continue
            left_values = _numeric(group, left)
            right_values = _numeric(group, right)
            valid = left_values.notna() & right_values.notna()
            if not valid.any():
                continue
            abs_diff = (left_values.loc[valid] - right_values.loc[valid]).abs()
            rows.append(
                {
                    "source_dataset": source,
                    "field": f"{left} vs {right}",
                    "field_group": "wind_alias_check",
                    "in_current_best_features": bool(left in baseline_set or right in baseline_set),
                    "coverage": float(valid.mean()),
                    "min": _safe_float(abs_diff.min()),
                    "median": _safe_float(abs_diff.median()),
                    "max": _safe_float(abs_diff.max()),
                    "source_column": "",
                    "source_value_counts": "",
                    "risk_level": "low" if float(abs_diff.quantile(0.95)) < 1e-9 else "medium",
                    "finding": "检查统一风字段与 hist_* 风字段是否等价。",
                    "recommended_action": "若不等价，需要明确训练使用机载风还是环境天气风。",
                }
            )
    return pd.DataFrame(rows)


def build_altitude_semantics(frame: pd.DataFrame, baseline_features: Sequence[str]) -> pd.DataFrame:
    """审计高度字段是否混用设定高度、相对高度和海拔高度。"""

    rows = []
    baseline_set = set(baseline_features)
    altitude_columns = sorted(column for column in ALTITUDE_FEATURES if column in frame.columns)
    for source, group in _source_groups(frame):
        altitude_source = _source_value_counts(group, "altitude_source")
        is_deployable_altitude_profile = (
            "altitude_profile:planned_level" in altitude_source
            or "altitude_profile:route_3d" in altitude_source
        )
        start = _numeric(group, "altitude_start_m")
        end = _numeric(group, "altitude_end_m")
        mid = (start + end) / 2.0
        altitude = _numeric(group, "altitude_m")
        valid_mid = altitude.notna() & mid.notna()
        median_abs_mid_diff = float((altitude.loc[valid_mid] - mid.loc[valid_mid]).abs().median()) if valid_mid.any() else float("nan")
        for feature in altitude_columns:
            values = _numeric(group, feature)
            in_baseline = feature in baseline_set
            risk = "low"
            finding = "高度字段可作为当前训练输入。"
            action = "保持字段血缘，部署时由计划航线 3D 几何生成。"
            if in_baseline and is_deployable_altitude_profile:
                risk = "low"
                finding = "该高度字段已转换为飞行前计划航线口径，不直接依赖逐时刻实飞高度日志。"
                action = "保持该口径；固定高度用 planned_level，三维航线用 route_3d。"
            elif feature == "altitude_m" and in_baseline and "programmed_altitude" in altitude_source:
                risk = "medium"
                finding = "altitude_m 在该数据源是任务设定高度，不是逐时刻真实高度；它和 altitude_start/end 不同口径。"
                action = "部署时用计划巡航高度生成 altitude_m；阶段动态特征不要由该列替代。"
            elif feature == "altitude_m" and in_baseline and "relativeheight" in altitude_source.lower():
                risk = "medium"
                finding = "altitude_m 在该数据源来自相对高度日志，部署时必须由计划高度或地形高度转换得到。"
                action = "明确 altitude_m 是相对起飞点高度还是海拔高度，后续加入 AGL/MSL 标识。"
            elif feature in ALTITUDE_FEATURES and feature != "altitude_m" and in_baseline:
                risk = "medium"
                finding = "该高度动态特征通常由实际飞行轨迹或计划 3D 航线计算，不能只靠起终点高度直接给出。"
                action = "部署侧必须由 3D 航线采样器生成同口径特征。"

            rows.append(
                {
                    "source_dataset": source,
                    "field": feature,
                    "field_group": "altitude",
                    "in_current_best_features": bool(in_baseline),
                    "coverage": _coverage(group, feature),
                    "min": _safe_float(values.min()),
                    "median": _safe_float(values.median()),
                    "max": _safe_float(values.max()),
                    "altitude_source_counts": altitude_source,
                    "median_abs_altitude_m_to_segment_mid_m": _safe_float(median_abs_mid_diff),
                    "risk_level": risk,
                    "finding": finding,
                    "recommended_action": action,
                }
            )
    return pd.DataFrame(rows)


def _feature_group(feature: str) -> str:
    """粗分模型特征类别。"""

    if feature in WIND_FEATURES:
        return "wind"
    if feature in ALTITUDE_FEATURES:
        return "altitude"
    if feature.startswith("phase_is_") or feature.endswith("_ratio"):
        return "phase"
    if feature in {"payload_kg"}:
        return "mass"
    if feature in {"temperature_c", "pressure_hpa", "relative_humidity_pct", "air_density_kgm3"}:
        return "weather"
    if feature.startswith("source_") or feature.startswith("role_"):
        return "source_label"
    return "physical"


def build_model_feature_semantics(
    baseline_features: Sequence[str],
    wind_semantics: pd.DataFrame,
    altitude_semantics: pd.DataFrame,
) -> pd.DataFrame:
    """把字段审计接回当前最佳模型特征。"""

    risk_priority = {"low": 0, "medium": 1, "high": 2}
    rows = []
    combined = pd.concat([wind_semantics, altitude_semantics], ignore_index=True, sort=False)
    for feature in baseline_features:
        feature_rows = combined.loc[combined["field"].eq(feature)].copy() if not combined.empty else pd.DataFrame()
        if feature_rows.empty:
            group = _feature_group(feature)
            risk = "high" if group == "source_label" else "low"
            finding = "该特征未触发专门语义风险。"
            action = "继续保留，并在后续消融中验证贡献。"
        else:
            group = str(feature_rows["field_group"].iloc[0])
            risk = max(feature_rows["risk_level"].fillna("low"), key=lambda item: risk_priority.get(str(item), 0))
            finding = "；".join(str(item) for item in feature_rows["finding"].dropna().unique()[:3])
            action = "；".join(str(item) for item in feature_rows["recommended_action"].dropna().unique()[:3])
        rows.append(
            {
                "feature": feature,
                "feature_group": group,
                "risk_level": risk,
                "finding": finding,
                "recommended_action": action,
            }
        )
    return pd.DataFrame(rows)


def _risk_counts(*frames: pd.DataFrame) -> dict:
    """统计风险等级数量。"""

    counts = {"high": 0, "medium": 0, "low": 0}
    for frame in frames:
        if frame.empty or "risk_level" not in frame.columns:
            continue
        for risk, value in frame["risk_level"].fillna("low").value_counts().items():
            counts[str(risk)] = counts.get(str(risk), 0) + int(value)
    return counts


def main() -> None:
    """执行物理字段语义审计。"""

    args = parse_args()
    features_path = _resolve_path(args.features)
    baseline_path = _resolve_path(args.baseline_summary)
    output_dir = _resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frame = pd.read_csv(features_path)
    frame, wind_profile_meta = apply_wind_profile(frame, args.wind_profile)
    frame, altitude_profile_meta = apply_altitude_profile(frame, args.altitude_profile)
    baseline = load_baseline_summary(baseline_path)
    baseline_features = baseline["features"]

    power = build_power_consistency(frame)
    wind = build_wind_semantics(frame, baseline_features)
    altitude = build_altitude_semantics(frame, baseline_features)
    model_features = build_model_feature_semantics(baseline_features, wind, altitude)

    power_path = output_dir / "power_consistency.csv"
    wind_path = output_dir / "wind_semantics.csv"
    altitude_path = output_dir / "altitude_semantics.csv"
    model_feature_path = output_dir / "model_feature_semantics.csv"
    power.to_csv(power_path, index=False)
    wind.to_csv(wind_path, index=False)
    altitude.to_csv(altitude_path, index=False)
    model_features.to_csv(model_feature_path, index=False)

    high_risk_features = model_features.loc[model_features["risk_level"].eq("high"), "feature"].tolist()
    medium_risk_features = model_features.loc[model_features["risk_level"].eq("medium"), "feature"].tolist()
    payload = {
        "features": str(features_path),
        "baseline_summary": str(baseline_path),
        "wind_profile": args.wind_profile,
        "wind_profile_meta": wind_profile_meta,
        "altitude_profile": args.altitude_profile,
        "altitude_profile_meta": altitude_profile_meta,
        "baseline_best": baseline.get("best", {}),
        "row_counts": {
            "features": int(len(frame.index)),
            "baseline_features": int(len(baseline_features)),
            "power_rows": int(len(power.index)),
            "wind_rows": int(len(wind.index)),
            "altitude_rows": int(len(altitude.index)),
            "model_feature_rows": int(len(model_features.index)),
        },
        "risk_counts": _risk_counts(power, wind, altitude, model_features),
        "high_risk_current_features": high_risk_features,
        "medium_risk_current_features": medium_risk_features,
        "top_power_findings": power.to_dict(orient="records"),
        "top_model_feature_findings": model_features.head(80).to_dict(orient="records"),
        "outputs": {
            "power_consistency": str(power_path.resolve()),
            "wind_semantics": str(wind_path.resolve()),
            "altitude_semantics": str(altitude_path.resolve()),
            "model_feature_semantics": str(model_feature_path.resolve()),
            "summary": str((output_dir / "summary.json").resolve()),
        },
    }
    save_summary(payload, output_dir / "summary.json")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
