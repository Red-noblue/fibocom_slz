# 分析部署模型在分段、整次飞行和不同天气场景下的预测误差。
"""分析部署模型的分段误差、飞行级误差和场景切片误差。"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence, Union

import numpy as np
import pandas as pd

from .evaluate import regression_metrics
from .model import WeatherEnergyModel, _prepare_training_frame, _split_training_frame
from .target_modes import (
    distance_km,
    infer_target_mode,
    safe_rate_from_energy,
    segment_energy_from_target_values,
)


DEFAULT_SLICE_COLUMNS = [
    "planned_ground_speed_mps",
    "altitude_m",
    "distance_m",
    "duration_s",
    "wind_speed_mps",
    "headwind_mps",
    "crosswind_mps",
    "temperature_c",
    "pressure_hpa",
]

DEFAULT_PHASE_RATIO_COLUMNS = {
    "climb": "climb_ratio",
    "descent": "descent_ratio",
    "level": "level_ratio",
    "turn": "turn_ratio",
    "hover_or_slow": "hover_or_slow_ratio",
    "cruise": "cruise_ratio",
}


def _relative_error_pct(predicted, actual) -> pd.Series:
    """计算相对误差百分比，实际值为分母。"""

    pred = pd.to_numeric(pd.Series(predicted), errors="coerce")
    act = pd.to_numeric(pd.Series(actual), errors="coerce")
    out = pd.Series(np.nan, index=pred.index, dtype=float)
    valid = pred.notna() & act.notna() & np.isfinite(pred) & np.isfinite(act) & (np.abs(act) > 1e-9)
    out.loc[valid] = (pred.loc[valid] - act.loc[valid]) / act.loc[valid] * 100.0
    return out


def build_segment_error_table(
    model: WeatherEnergyModel,
    features_csv: Union[str, Path],
    target: str = "segment_wh_per_km",
    test_size: float = 0.2,
    random_state: int = 42,
    group_col: Optional[str] = "flight",
) -> tuple[pd.DataFrame, dict]:
    """复现训练切分并生成测试集分段误差表。"""

    cleaned, _ = _prepare_training_frame(features_csv, [target], model.feature_cols)
    _, x_test, _, y_test, split_meta = _split_training_frame(
        df=cleaned,
        feature_cols=model.feature_cols,
        target=target,
        test_size=test_size,
        random_state=random_state,
        group_col=group_col,
    )
    test_frame = cleaned.loc[x_test.index].copy()
    return build_segment_error_table_from_frame(
        model=model,
        test_frame=test_frame,
        target=target,
        segment_meta=split_meta,
    )


def build_segment_error_table_from_frame(
    model: WeatherEnergyModel,
    test_frame: pd.DataFrame,
    target: str = "segment_wh_per_km",
    segment_meta: Optional[dict] = None,
) -> tuple[pd.DataFrame, dict]:
    """使用指定测试集生成分段误差表。"""

    required_columns = list(model.feature_cols) + [target]
    cleaned = test_frame.replace([np.inf, -np.inf], np.nan).dropna(subset=required_columns).copy()
    if cleaned.empty:
        raise ValueError("指定测试集经过清洗后为空。")

    predictions = np.asarray(model.predict(cleaned), dtype=float).reshape(-1)
    actual = pd.to_numeric(cleaned[target], errors="coerce").to_numpy(dtype=float).reshape(-1)

    out = cleaned.copy()
    target_mode = infer_target_mode(target)
    distance_km_values = distance_km(out)
    actual_target = pd.Series(actual, index=out.index, dtype=float)
    predicted_target = pd.Series(predictions, index=out.index, dtype=float)

    actual_segment_energy_wh, _ = segment_energy_from_target_values(actual_target, out, target)
    predicted_segment_energy_wh, _ = segment_energy_from_target_values(predicted_target, out, target)

    if target_mode == "wh_per_km":
        actual_wh_per_km = actual_target
        predicted_wh_per_km = predicted_target
    else:
        actual_wh_per_km = safe_rate_from_energy(actual_segment_energy_wh, distance_km_values)
        predicted_wh_per_km = safe_rate_from_energy(predicted_segment_energy_wh, distance_km_values)

    out["actual_target_value"] = actual_target
    out["predicted_target_value"] = predicted_target
    out["target_error"] = out["predicted_target_value"] - out["actual_target_value"]
    out["abs_target_error"] = out["target_error"].abs()
    out["target_error_pct"] = _relative_error_pct(out["predicted_target_value"], out["actual_target_value"])
    out["abs_target_error_pct"] = out["target_error_pct"].abs()
    out["actual_wh_per_km"] = actual_wh_per_km
    out["predicted_wh_per_km"] = predicted_wh_per_km
    out["residual_wh_per_km"] = out["predicted_wh_per_km"] - out["actual_wh_per_km"]
    out["abs_error_wh_per_km"] = out["residual_wh_per_km"].abs()
    out["wh_per_km_error_pct"] = _relative_error_pct(out["predicted_wh_per_km"], out["actual_wh_per_km"])
    out["abs_wh_per_km_error_pct"] = out["wh_per_km_error_pct"].abs()
    out["pct_error"] = out["target_error_pct"]
    out["actual_segment_energy_wh"] = actual_segment_energy_wh
    out["predicted_segment_energy_wh"] = predicted_segment_energy_wh
    out["segment_energy_error_wh"] = out["predicted_segment_energy_wh"] - out["actual_segment_energy_wh"]
    out["abs_segment_energy_error_wh"] = out["segment_energy_error_wh"].abs()
    out["segment_energy_error_pct"] = _relative_error_pct(
        out["predicted_segment_energy_wh"], out["actual_segment_energy_wh"]
    )
    out["abs_segment_energy_error_pct"] = out["segment_energy_error_pct"].abs()

    metrics = {
        "target": target,
        "target_mode": target_mode,
        "rows_evaluated": int(len(out.index)),
        "features": list(model.feature_cols),
        "segment_metrics": regression_metrics(actual, predictions),
        **(segment_meta or {}),
    }
    return out, metrics


def build_flight_error_table(
    segment_errors: pd.DataFrame,
    battery_wh: Optional[float] = None,
    group_col: str = "flight",
) -> pd.DataFrame:
    """把分段误差聚合为整次飞行能耗误差。"""

    frame = segment_errors.copy()
    if group_col not in frame.columns:
        frame[group_col] = "all"
    if "distance_m" not in frame.columns:
        frame["distance_m"] = np.nan

    rows = []
    for group_value, group in frame.groupby(group_col, sort=False):
        distance_km = float(pd.to_numeric(group["distance_m"], errors="coerce").sum() / 1000.0)
        actual_energy_wh = float(pd.to_numeric(group["actual_segment_energy_wh"], errors="coerce").sum())
        predicted_energy_wh = float(pd.to_numeric(group["predicted_segment_energy_wh"], errors="coerce").sum())
        energy_error_wh = predicted_energy_wh - actual_energy_wh
        actual_wh_per_km = actual_energy_wh / distance_km if distance_km > 0 else np.nan
        predicted_wh_per_km = predicted_energy_wh / distance_km if distance_km > 0 else np.nan
        row = {
            group_col: group_value,
            "segment_count": int(len(group.index)),
            "distance_km": distance_km,
            "actual_total_energy_wh": actual_energy_wh,
            "predicted_total_energy_wh": predicted_energy_wh,
            "energy_error_wh": energy_error_wh,
            "abs_energy_error_wh": abs(energy_error_wh),
            "energy_error_pct": ((predicted_energy_wh - actual_energy_wh) / actual_energy_wh * 100.0)
            if actual_energy_wh > 1e-9
            else np.nan,
            "actual_wh_per_km": actual_wh_per_km,
            "predicted_wh_per_km": predicted_wh_per_km,
            "wh_per_km_error": predicted_wh_per_km - actual_wh_per_km if np.isfinite(actual_wh_per_km) else np.nan,
            "wh_per_km_error_pct": ((predicted_wh_per_km - actual_wh_per_km) / actual_wh_per_km * 100.0)
            if np.isfinite(actual_wh_per_km) and abs(actual_wh_per_km) > 1e-9
            else np.nan,
        }
        if battery_wh is not None:
            actual_remaining_wh = float(battery_wh) - actual_energy_wh
            predicted_remaining_wh = float(battery_wh) - predicted_energy_wh
            actual_range_km = float(battery_wh) / actual_wh_per_km if np.isfinite(actual_wh_per_km) and actual_wh_per_km > 1e-9 else np.nan
            predicted_range_km = (
                float(battery_wh) / predicted_wh_per_km
                if np.isfinite(predicted_wh_per_km) and predicted_wh_per_km > 1e-9
                else np.nan
            )
            row.update(
                {
                    "battery_wh": float(battery_wh),
                    "actual_remaining_wh": actual_remaining_wh,
                    "predicted_remaining_wh": predicted_remaining_wh,
                    "remaining_error_wh": predicted_remaining_wh - actual_remaining_wh,
                    "remaining_error_pct": (
                        (predicted_remaining_wh - actual_remaining_wh) / actual_remaining_wh * 100.0
                        if abs(actual_remaining_wh) > 1e-9
                        else np.nan
                    ),
                    "actual_range_km": actual_range_km,
                    "predicted_range_km": predicted_range_km,
                    "range_error_km": predicted_range_km - actual_range_km if np.isfinite(actual_range_km) else np.nan,
                    "range_error_pct": (
                        (predicted_range_km - actual_range_km) / actual_range_km * 100.0
                        if np.isfinite(actual_range_km) and abs(actual_range_km) > 1e-9
                        else np.nan
                    ),
                    "range_ratio": predicted_range_km / actual_range_km if np.isfinite(actual_range_km) and actual_range_km > 1e-9 and np.isfinite(predicted_range_km) else np.nan,
                    "actual_feasible": actual_energy_wh <= float(battery_wh),
                    "predicted_feasible": predicted_energy_wh <= float(battery_wh),
                    "feasibility_mismatch": (actual_energy_wh <= float(battery_wh)) != (predicted_energy_wh <= float(battery_wh)),
                }
            )
        rows.append(row)
    return pd.DataFrame(rows)


def _rmse(values: pd.Series) -> float:
    """计算一组误差的 RMSE。"""

    arr = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    if arr.size == 0:
        return float("nan")
    return float(np.sqrt(np.mean(np.square(arr))))


def build_slice_error_table(
    segment_errors: pd.DataFrame,
    slice_columns: Optional[Sequence[str]] = None,
    bins: int = 3,
) -> pd.DataFrame:
    """按风、距离、温度等场景切片统计误差。"""

    columns = list(slice_columns or DEFAULT_SLICE_COLUMNS)
    rows = []
    for column in columns:
        if column not in segment_errors.columns:
            continue
        series = pd.to_numeric(segment_errors[column], errors="coerce")
        valid = segment_errors.loc[series.notna()].copy()
        if valid.empty or series.nunique(dropna=True) < 2:
            continue
        try:
            buckets = pd.qcut(
                pd.to_numeric(valid[column], errors="coerce"),
                q=min(bins, int(series.nunique(dropna=True))),
                duplicates="drop",
            )
        except ValueError:
            continue
        valid = valid.assign(_bucket=buckets.astype(str))
        for bucket, group in valid.groupby("_bucket", sort=True):
            residual = pd.to_numeric(group["residual_wh_per_km"], errors="coerce")
            abs_error = pd.to_numeric(group["abs_error_wh_per_km"], errors="coerce")
            abs_pct_error = pd.to_numeric(group["abs_wh_per_km_error_pct"], errors="coerce")
            rows.append(
                {
                    "feature": column,
                    "bucket": bucket,
                    "count": int(len(group.index)),
                    "feature_mean": float(pd.to_numeric(group[column], errors="coerce").mean()),
                    "bias_wh_per_km": float(residual.mean()),
                    "mae_wh_per_km": float(abs_error.mean()),
                    "rmse_wh_per_km": _rmse(residual),
                    "mean_abs_wh_per_km_error_pct": float(abs_pct_error.mean()),
                    "mean_abs_segment_energy_error_wh": float(
                        pd.to_numeric(group["abs_segment_energy_error_wh"], errors="coerce").mean()
                    ),
                }
            )
    return pd.DataFrame(rows)


def _dominant_phase_series(
    frame: pd.DataFrame,
    phase_ratio_columns: Optional[dict[str, str]] = None,
) -> pd.Series:
    """读取或推断每个分段的主导阶段。"""

    if "phase_label" in frame.columns:
        labels = frame["phase_label"].fillna("unknown").astype(str)
        if labels.ne("unknown").any():
            return labels

    columns = dict(phase_ratio_columns or DEFAULT_PHASE_RATIO_COLUMNS)
    available = {phase: column for phase, column in columns.items() if column in frame.columns}
    if not available:
        return pd.Series(["unknown"] * len(frame.index), index=frame.index)

    ratio_frame = pd.DataFrame(
        {
            phase: pd.to_numeric(frame[column], errors="coerce")
            for phase, column in available.items()
        },
        index=frame.index,
    )
    return ratio_frame.idxmax(axis=1).fillna("unknown").astype(str)


def _phase_error_row(
    group: pd.DataFrame,
    view: str,
    phase: str,
    total_count: int,
    ratio_column: Optional[str] = None,
    active_threshold: Optional[float] = None,
) -> dict:
    """汇总一个阶段子集的误差指标。"""

    actual_energy = pd.to_numeric(group.get("actual_segment_energy_wh", pd.Series(dtype=float)), errors="coerce")
    predicted_energy = pd.to_numeric(group.get("predicted_segment_energy_wh", pd.Series(dtype=float)), errors="coerce")
    energy_error = predicted_energy.sum() - actual_energy.sum()
    abs_energy_pct = pd.to_numeric(group.get("abs_segment_energy_error_pct", pd.Series(dtype=float)), errors="coerce")
    abs_target_pct = pd.to_numeric(group.get("abs_target_error_pct", pd.Series(dtype=float)), errors="coerce")
    abs_wh_per_km_pct = pd.to_numeric(group.get("abs_wh_per_km_error_pct", pd.Series(dtype=float)), errors="coerce")
    ratio_mean = (
        float(pd.to_numeric(group[ratio_column], errors="coerce").mean())
        if ratio_column and ratio_column in group.columns
        else float("nan")
    )
    return {
        "view": view,
        "phase": phase,
        "ratio_column": ratio_column,
        "active_threshold": active_threshold,
        "count": int(len(group.index)),
        "segment_share": float(len(group.index) / total_count) if total_count else float("nan"),
        "flight_count": int(group["flight"].nunique()) if "flight" in group.columns else None,
        "mean_phase_ratio": ratio_mean,
        "actual_energy_wh": float(actual_energy.sum()),
        "predicted_energy_wh": float(predicted_energy.sum()),
        "energy_error_wh": float(energy_error),
        "energy_error_pct": float(energy_error / actual_energy.sum() * 100.0)
        if abs(float(actual_energy.sum())) > 1e-9
        else float("nan"),
        "mean_abs_segment_energy_error_wh": float(
            pd.to_numeric(group.get("abs_segment_energy_error_wh", pd.Series(dtype=float)), errors="coerce").mean()
        ),
        "p95_abs_segment_energy_error_wh": float(
            pd.to_numeric(group.get("abs_segment_energy_error_wh", pd.Series(dtype=float)), errors="coerce").quantile(0.95)
        ),
        "mean_abs_segment_energy_error_pct": float(abs_energy_pct.mean()),
        "p95_abs_segment_energy_error_pct": float(abs_energy_pct.quantile(0.95)),
        "mean_abs_target_error_pct": float(abs_target_pct.mean()),
        "p95_abs_target_error_pct": float(abs_target_pct.quantile(0.95)),
        "mean_abs_wh_per_km_error_pct": float(abs_wh_per_km_pct.mean()),
        "p95_abs_wh_per_km_error_pct": float(abs_wh_per_km_pct.quantile(0.95)),
        "mean_distance_m": float(pd.to_numeric(group.get("distance_m", pd.Series(dtype=float)), errors="coerce").mean()),
        "mean_duration_s": float(pd.to_numeric(group.get("duration_s", pd.Series(dtype=float)), errors="coerce").mean()),
    }


def build_phase_error_table(
    segment_errors: pd.DataFrame,
    phase_ratio_columns: Optional[dict[str, str]] = None,
    active_threshold: float = 0.2,
) -> pd.DataFrame:
    """按主导阶段和阶段比例门控统计误差。"""

    if segment_errors.empty:
        return pd.DataFrame()

    columns = dict(phase_ratio_columns or DEFAULT_PHASE_RATIO_COLUMNS)
    total_count = int(len(segment_errors.index))
    frame = segment_errors.copy()
    frame["_dominant_phase"] = _dominant_phase_series(frame, columns)

    rows = []
    for phase, group in frame.groupby("_dominant_phase", sort=True):
        rows.append(
            _phase_error_row(
                group=group,
                view="dominant_phase",
                phase=str(phase),
                total_count=total_count,
            )
        )

    for phase, column in columns.items():
        if column not in frame.columns:
            continue
        ratio = pd.to_numeric(frame[column], errors="coerce")
        group = frame.loc[ratio >= active_threshold].copy()
        if group.empty:
            continue
        rows.append(
            _phase_error_row(
                group=group,
                view="ratio_gate",
                phase=phase,
                total_count=total_count,
                ratio_column=column,
                active_threshold=float(active_threshold),
            )
        )
    return pd.DataFrame(rows)


def summarize_error_tables(
    segment_errors: pd.DataFrame,
    flight_errors: pd.DataFrame,
    segment_meta: dict,
    battery_wh: Optional[float] = None,
) -> dict:
    """汇总分段、飞行级和可达性风险指标。"""

    abs_energy = pd.to_numeric(flight_errors.get("abs_energy_error_wh", pd.Series(dtype=float)), errors="coerce")
    energy_error = pd.to_numeric(flight_errors.get("energy_error_wh", pd.Series(dtype=float)), errors="coerce")
    distance_km = pd.to_numeric(flight_errors.get("distance_km", pd.Series(dtype=float)), errors="coerce")
    segment_abs = pd.to_numeric(segment_errors["abs_error_wh_per_km"], errors="coerce")
    target_abs = pd.to_numeric(segment_errors.get("abs_target_error", pd.Series(dtype=float)), errors="coerce")
    target_abs_pct = pd.to_numeric(segment_errors.get("abs_target_error_pct", pd.Series(dtype=float)), errors="coerce")
    summary = {
        "segment": {
            **segment_meta["segment_metrics"],
            "target": segment_meta.get("target"),
            "target_mode": segment_meta.get("target_mode"),
            "count": int(len(segment_errors.index)),
            "mean_abs_target_error": float(target_abs.mean()),
            "p90_abs_target_error": float(target_abs.quantile(0.90)),
            "p95_abs_target_error": float(target_abs.quantile(0.95)),
            "mean_abs_target_error_pct": float(target_abs_pct.mean()),
            "p90_abs_target_error_pct": float(target_abs_pct.quantile(0.90)),
            "p95_abs_target_error_pct": float(target_abs_pct.quantile(0.95)),
            "mean_abs_error_wh_per_km": float(segment_abs.mean()),
            "p90_abs_error_wh_per_km": float(segment_abs.quantile(0.90)),
            "p95_abs_error_wh_per_km": float(segment_abs.quantile(0.95)),
            "mean_abs_error_wh_per_km_pct": float(
                pd.to_numeric(segment_errors.get("abs_wh_per_km_error_pct", pd.Series(dtype=float)), errors="coerce").mean()
            ),
            "p90_abs_error_wh_per_km_pct": float(
                pd.to_numeric(segment_errors.get("abs_wh_per_km_error_pct", pd.Series(dtype=float)), errors="coerce").quantile(0.90)
            ),
            "p95_abs_error_wh_per_km_pct": float(
                pd.to_numeric(segment_errors.get("abs_wh_per_km_error_pct", pd.Series(dtype=float)), errors="coerce").quantile(0.95)
            ),
        },
        "flight": {
            "count": int(len(flight_errors.index)),
            "mean_distance_km": float(distance_km.mean()) if not distance_km.empty else float("nan"),
            "p95_distance_km": float(distance_km.quantile(0.95)) if not distance_km.empty else float("nan"),
            "mean_energy_error_wh": float(energy_error.mean()) if not energy_error.empty else float("nan"),
            "mean_abs_energy_error_wh": float(abs_energy.mean()) if not abs_energy.empty else float("nan"),
            "p90_abs_energy_error_wh": float(abs_energy.quantile(0.90)) if not abs_energy.empty else float("nan"),
            "p95_abs_energy_error_wh": float(abs_energy.quantile(0.95)) if not abs_energy.empty else float("nan"),
            "mean_energy_error_pct": float(
                pd.to_numeric(flight_errors.get("energy_error_pct", pd.Series(dtype=float)), errors="coerce").mean()
            ),
            "mean_abs_energy_error_pct": float(
                pd.to_numeric(flight_errors.get("energy_error_pct", pd.Series(dtype=float)), errors="coerce").abs().mean()
            ),
            "p90_abs_energy_error_pct": float(
                pd.to_numeric(flight_errors.get("energy_error_pct", pd.Series(dtype=float)), errors="coerce").abs().quantile(0.90)
            ),
            "p95_abs_energy_error_pct": float(
                pd.to_numeric(flight_errors.get("energy_error_pct", pd.Series(dtype=float)), errors="coerce").abs().quantile(0.95)
            ),
            "mean_range_error_km": float(
                pd.to_numeric(flight_errors.get("range_error_km", pd.Series(dtype=float)), errors="coerce").mean()
            ),
            "mean_abs_range_error_km": float(
                pd.to_numeric(flight_errors.get("range_error_km", pd.Series(dtype=float)), errors="coerce").abs().mean()
            ),
            "p90_abs_range_error_km": float(
                pd.to_numeric(flight_errors.get("range_error_km", pd.Series(dtype=float)), errors="coerce").abs().quantile(0.90)
            ),
            "p95_abs_range_error_km": float(
                pd.to_numeric(flight_errors.get("range_error_km", pd.Series(dtype=float)), errors="coerce").abs().quantile(0.95)
            ),
            "mean_range_error_pct": float(
                pd.to_numeric(flight_errors.get("range_error_pct", pd.Series(dtype=float)), errors="coerce").mean()
            ),
            "mean_abs_range_error_pct": float(
                pd.to_numeric(flight_errors.get("range_error_pct", pd.Series(dtype=float)), errors="coerce").abs().mean()
            ),
            "p90_abs_range_error_pct": float(
                pd.to_numeric(flight_errors.get("range_error_pct", pd.Series(dtype=float)), errors="coerce").abs().quantile(0.90)
            ),
            "p95_abs_range_error_pct": float(
                pd.to_numeric(flight_errors.get("range_error_pct", pd.Series(dtype=float)), errors="coerce").abs().quantile(0.95)
            ),
        },
        "split": {
            key: value
            for key, value in segment_meta.items()
            if key not in {"segment_metrics", "features"}
        },
        "features": segment_meta.get("features", []),
    }
    if battery_wh is not None and "feasibility_mismatch" in flight_errors.columns:
        mismatch = flight_errors["feasibility_mismatch"].astype(bool)
        range_pct = pd.to_numeric(flight_errors.get("range_error_pct", pd.Series(dtype=float)), errors="coerce")
        energy_pct = pd.to_numeric(flight_errors.get("energy_error_pct", pd.Series(dtype=float)), errors="coerce")
        summary["risk"] = {
            "battery_wh": float(battery_wh),
            "feasibility_mismatch_count": int(mismatch.sum()),
            "feasibility_mismatch_rate": float(mismatch.mean()) if len(mismatch.index) else float("nan"),
            "range_overprediction_gt_25pct_count": int((range_pct > 25.0).sum()),
            "range_overprediction_gt_50pct_count": int((range_pct > 50.0).sum()),
            "range_overprediction_gt_100pct_count": int((range_pct > 100.0).sum()),
            "range_overprediction_gt_25pct_rate": float((range_pct > 25.0).mean()) if len(range_pct.index) else float("nan"),
            "range_overprediction_gt_50pct_rate": float((range_pct > 50.0).mean()) if len(range_pct.index) else float("nan"),
            "range_overprediction_gt_100pct_rate": float((range_pct > 100.0).mean()) if len(range_pct.index) else float("nan"),
            "energy_underprediction_gt_25pct_count": int((energy_pct < -25.0).sum()),
            "energy_underprediction_gt_50pct_count": int((energy_pct < -50.0).sum()),
            "energy_underprediction_gt_25pct_rate": float((energy_pct < -25.0).mean()) if len(energy_pct.index) else float("nan"),
            "energy_underprediction_gt_50pct_rate": float((energy_pct < -50.0).mean()) if len(energy_pct.index) else float("nan"),
        }
    return summary
