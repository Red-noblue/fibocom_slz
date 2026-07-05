"""验证部署模型误差分析的基础行为。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from uav_energy_engine.error_analysis import (
    build_flight_error_table,
    build_phase_error_table,
    build_segment_error_table,
    build_segment_error_table_from_frame,
    build_slice_error_table,
    summarize_error_tables,
)


class _MeanLikeModel:
    """测试用模型：按速度生成一个稳定预测值。"""

    feature_cols = ["speed_mps", "distance_m"]

    def predict(self, frame: pd.DataFrame):
        """返回可重复的预测。"""

        return np.asarray(30.0 + pd.to_numeric(frame["speed_mps"], errors="coerce"), dtype=float)


class _EnergyLikeModel:
    """测试用模型：直接输出分段总耗电。"""

    feature_cols = ["speed_mps", "distance_m"]

    def predict(self, frame: pd.DataFrame):
        """返回分段 Wh 预测值。"""

        return np.asarray(5.0 + pd.to_numeric(frame["speed_mps"], errors="coerce"), dtype=float)


class _ConstantTargetModel:
    """测试用模型：按指定常数输出目标值。"""

    feature_cols = ["speed_mps", "distance_m", "duration_s"]

    def __init__(self, value: float):
        self.value = value

    def predict(self, frame: pd.DataFrame):
        """返回固定目标值。"""

        return np.full(len(frame.index), self.value, dtype=float)


def test_build_segment_error_table_outputs_energy_errors(tmp_path: Path):
    """分段误差表应包含每公里误差和分段能耗误差。"""

    features_csv = tmp_path / "features.csv"
    pd.DataFrame(
        {
            "flight": [1, 1, 2, 2, 3, 3],
            "speed_mps": [4.0, 5.0, 6.0, 7.0, 8.0, 9.0],
            "distance_m": [100.0, 120.0, 130.0, 140.0, 150.0, 160.0],
            "segment_wh_per_km": [35.0, 36.0, 37.0, 38.0, 39.0, 40.0],
        }
    ).to_csv(features_csv, index=False)

    segment_errors, meta = build_segment_error_table(
        model=_MeanLikeModel(),
        features_csv=features_csv,
        test_size=0.5,
        random_state=1,
        group_col=None,
    )

    assert not segment_errors.empty
    assert "predicted_wh_per_km" in segment_errors.columns
    assert "segment_energy_error_wh" in segment_errors.columns
    assert "abs_wh_per_km_error_pct" in segment_errors.columns
    assert "segment_energy_error_pct" in segment_errors.columns
    assert meta["rows_evaluated"] == len(segment_errors)


def test_build_segment_error_table_supports_segment_energy_target(tmp_path: Path):
    """直接预测分段耗电时不应再次按距离换算。"""

    features_csv = tmp_path / "energy_features.csv"
    pd.DataFrame(
        {
            "flight": [1, 1, 2, 2, 3, 3],
            "speed_mps": [4.0, 5.0, 6.0, 7.0, 8.0, 9.0],
            "distance_m": [100.0, 200.0, 250.0, 300.0, 400.0, 500.0],
            "segment_energy_wh": [8.0, 9.0, 12.0, 15.0, 18.0, 20.0],
        }
    ).to_csv(features_csv, index=False)

    segment_errors, meta = build_segment_error_table(
        model=_EnergyLikeModel(),
        features_csv=features_csv,
        target="segment_energy_wh",
        test_size=0.5,
        random_state=1,
        group_col=None,
    )

    distance_km = pd.to_numeric(segment_errors["distance_m"], errors="coerce") / 1000.0
    expected_energy = 5.0 + pd.to_numeric(segment_errors["speed_mps"], errors="coerce")
    expected_rate = expected_energy / distance_km

    assert meta["target_mode"] == "segment_energy_wh"
    np.testing.assert_allclose(segment_errors["predicted_segment_energy_wh"], expected_energy)
    np.testing.assert_allclose(segment_errors["predicted_wh_per_km"], expected_rate)
    np.testing.assert_allclose(segment_errors["predicted_target_value"], expected_energy)


def test_build_segment_error_table_from_frame_uses_explicit_test_rows():
    """指定测试集误差表不应重新随机切分。"""

    frame = pd.DataFrame(
        {
            "flight": [10, 11],
            "speed_mps": [4.0, 5.0],
            "distance_m": [100.0, 200.0],
            "segment_energy_wh": [8.0, 9.0],
        }
    )

    segment_errors, meta = build_segment_error_table_from_frame(
        model=_EnergyLikeModel(),
        test_frame=frame,
        target="segment_energy_wh",
        segment_meta={"split_strategy": "explicit"},
    )

    assert list(segment_errors["flight"]) == [10, 11]
    assert meta["split_strategy"] == "explicit"
    assert meta["rows_evaluated"] == 2


def test_build_segment_error_table_supports_time_rate_targets(tmp_path: Path):
    """Wh/s 和平均功率 W 目标应按时长换算为分段耗电。"""

    features_csv = tmp_path / "time_rate_features.csv"
    pd.DataFrame(
        {
            "flight": [1, 1, 2, 2, 3, 3],
            "speed_mps": [4.0, 5.0, 6.0, 7.0, 8.0, 9.0],
            "distance_m": [100.0, 200.0, 250.0, 300.0, 400.0, 500.0],
            "duration_s": [60.0, 60.0, 120.0, 120.0, 180.0, 180.0],
            "segment_wh_per_s": [0.10, 0.12, 0.11, 0.13, 0.09, 0.14],
            "mean_power_w": [360.0, 420.0, 390.0, 450.0, 330.0, 480.0],
        }
    ).to_csv(features_csv, index=False)

    wh_per_s_errors, wh_per_s_meta = build_segment_error_table(
        model=_ConstantTargetModel(0.1),
        features_csv=features_csv,
        target="segment_wh_per_s",
        test_size=0.5,
        random_state=1,
        group_col=None,
    )
    power_errors, power_meta = build_segment_error_table(
        model=_ConstantTargetModel(360.0),
        features_csv=features_csv,
        target="mean_power_w",
        test_size=0.5,
        random_state=1,
        group_col=None,
    )

    np.testing.assert_allclose(
        wh_per_s_errors["predicted_segment_energy_wh"],
        wh_per_s_errors["duration_s"] * 0.1,
    )
    np.testing.assert_allclose(
        power_errors["predicted_segment_energy_wh"],
        power_errors["duration_s"] * 360.0 / 3600.0,
    )
    assert wh_per_s_meta["target_mode"] == "wh_per_s"
    assert power_meta["target_mode"] == "power_w"


def test_flight_and_slice_error_tables_are_summarized():
    """飞行级误差和切片误差应能汇总为部署风险指标。"""

    segment_errors = pd.DataFrame(
        {
            "flight": [1, 1, 2, 2],
            "distance_m": [100.0, 100.0, 200.0, 200.0],
            "wind_speed_mps": [2.0, 3.0, 6.0, 7.0],
            "actual_wh_per_km": [30.0, 30.0, 40.0, 40.0],
            "predicted_wh_per_km": [32.0, 29.0, 42.0, 37.0],
            "residual_wh_per_km": [2.0, -1.0, 2.0, -3.0],
            "abs_error_wh_per_km": [2.0, 1.0, 2.0, 3.0],
            "wh_per_km_error_pct": [6.6667, -3.3333, 5.0, -7.5],
            "abs_wh_per_km_error_pct": [6.6667, 3.3333, 5.0, 7.5],
            "actual_segment_energy_wh": [3.0, 3.0, 8.0, 8.0],
            "predicted_segment_energy_wh": [3.2, 2.9, 8.4, 7.4],
            "segment_energy_error_wh": [0.2, -0.1, 0.4, -0.6],
            "abs_segment_energy_error_wh": [0.2, 0.1, 0.4, 0.6],
            "segment_energy_error_pct": [6.6667, -3.3333, 5.0, -7.5],
            "abs_segment_energy_error_pct": [6.6667, 3.3333, 5.0, 7.5],
        }
    )
    flight_errors = build_flight_error_table(segment_errors, battery_wh=20.0)
    slice_errors = build_slice_error_table(segment_errors, slice_columns=["wind_speed_mps"], bins=2)
    summary = summarize_error_tables(
        segment_errors=segment_errors,
        flight_errors=flight_errors,
        segment_meta={"segment_metrics": {"mae": 2.0, "rmse": 2.2, "r2": 0.5, "naive_rmse": 1.0}},
        battery_wh=20.0,
    )

    assert len(flight_errors) == 2
    assert "actual_range_km" in flight_errors.columns
    assert "range_error_pct" in flight_errors.columns
    assert not slice_errors.empty
    assert summary["flight"]["count"] == 2
    assert "mean_abs_range_error_pct" in summary["flight"]
    assert "risk" in summary


def test_build_phase_error_table_summarizes_dominant_and_ratio_gate():
    """阶段误差表应同时支持主导阶段和比例门控视图。"""

    segment_errors = pd.DataFrame(
        {
            "flight": [1, 1, 2, 2],
            "phase_label": ["climb", "cruise", "cruise", "descent"],
            "climb_ratio": [0.8, 0.0, 0.0, 0.0],
            "descent_ratio": [0.0, 0.0, 0.0, 0.7],
            "cruise_ratio": [0.2, 1.0, 0.9, 0.3],
            "distance_m": [100.0, 100.0, 200.0, 200.0],
            "duration_s": [60.0, 60.0, 120.0, 120.0],
            "actual_segment_energy_wh": [6.0, 5.0, 8.0, 7.0],
            "predicted_segment_energy_wh": [7.0, 5.2, 7.6, 8.4],
            "abs_segment_energy_error_wh": [1.0, 0.2, 0.4, 1.4],
            "segment_energy_error_pct": [16.6667, 4.0, -5.0, 20.0],
            "abs_segment_energy_error_pct": [16.6667, 4.0, 5.0, 20.0],
            "abs_target_error_pct": [16.6667, 4.0, 5.0, 20.0],
            "abs_wh_per_km_error_pct": [16.6667, 4.0, 5.0, 20.0],
        }
    )

    phase_errors = build_phase_error_table(segment_errors, active_threshold=0.5)

    assert {"dominant_phase", "ratio_gate"}.issubset(set(phase_errors["view"]))
    assert "climb" in set(phase_errors["phase"])
    climb_gate = phase_errors[(phase_errors["view"] == "ratio_gate") & (phase_errors["phase"] == "climb")]
    assert int(climb_gate["count"].iloc[0]) == 1
    assert float(climb_gate["mean_phase_ratio"].iloc[0]) == 0.8
