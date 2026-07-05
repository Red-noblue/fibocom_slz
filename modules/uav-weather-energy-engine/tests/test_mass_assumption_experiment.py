# 验证质量输入假设实验不会把数据源标签当成模型特征。
"""验证质量输入假设实验脚本。"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import run_mass_assumption_experiment as experiment


def test_apply_assumed_empty_mass_builds_takeoff_mass_without_source_feature():
    """已知空机质量假设应生成起飞质量，但特征中不能包含数据源标签。"""

    frame = pd.DataFrame(
        {
            "source_dataset": ["m100", "wemuav"],
            "payload_kg": [0.5, 0.0],
        }
    )

    out, mass_cols, meta = experiment.apply_mass_assumption(
        frame,
        assumption="payload_plus_assumed_empty_mass",
        assumed_empty_mass_by_source={"m100": 2.355, "wemuav": 1.388},
    )

    assert mass_cols == ["payload_kg", "assumed_empty_mass_kg", "assumed_takeoff_mass_kg"]
    assert round(float(out["assumed_takeoff_mass_kg"].iloc[0]), 6) == 2.855
    assert round(float(out["assumed_takeoff_mass_kg"].iloc[1]), 6) == 1.388
    assert meta["uses_source_dataset_as_feature"] is False
    experiment.assert_no_source_features(mass_cols)


def test_source_features_are_rejected():
    """数据源标签和数据源 one-hot 都必须被拦截。"""

    with pytest.raises(ValueError):
        experiment.assert_no_source_features(["speed_mps", "source_dataset"])
    with pytest.raises(ValueError):
        experiment.assert_no_source_features(["speed_mps", "source_is_m100"])


def test_feature_columns_for_assumption_excludes_source_flags():
    """部署特征生成只能返回物理量、阶段量和质量量。"""

    frame = pd.DataFrame(
        {
            "planned_ground_speed_mps": [5.0, 6.0],
            "speed_mps": [5.0, 6.0],
            "payload_kg": [0.0, 0.5],
            "assumed_empty_mass_kg": [2.355, 2.355],
            "assumed_takeoff_mass_kg": [2.355, 2.855],
            "source_is_m100": [1.0, 1.0],
            "source_dataset": ["m100", "m100"],
        }
    )

    cols = experiment.feature_columns_for_assumption(
        frame,
        ["payload_kg", "assumed_empty_mass_kg", "assumed_takeoff_mass_kg"],
    )

    assert "planned_ground_speed_mps" in cols
    assert "speed_mps" not in cols
    assert "equivalent_airspeed_mps" not in cols
    assert "assumed_takeoff_mass_kg" in cols
    assert "source_dataset" not in cols
    assert "source_is_m100" not in cols


def test_feature_columns_for_assumption_can_exclude_risky_fields():
    """字段干预实验应能显式排除高风险输入列。"""

    frame = experiment.add_planned_equivalent_wind_features(
        pd.DataFrame(
            {
                "planned_ground_speed_mps": [5.0, 6.0],
                "speed_mps": [5.0, 6.0],
                "wind_speed_mps": [1.0, 1.1],
                "headwind_mps": [1.0, 1.1],
                "crosswind_mps": [0.0, 0.0],
                "payload_kg": [0.0, 0.5],
            }
        )
    )

    cols = experiment.feature_columns_for_assumption(
        frame,
        ["payload_kg"],
        exclude_features=["wind_speed_mps"],
        equivalent_wind_feature_set="airspeed",
    )

    assert "planned_ground_speed_mps" in cols
    assert "equivalent_airspeed_mps" in cols
    assert "payload_kg" in cols
    assert "wind_speed_mps" not in cols


def test_mass_proxy_audit_flags_source_separable_empty_mass():
    """当空机质量在数据源之间完全分离时，应标记来源代理风险。"""

    frame = pd.DataFrame(
        {
            "source_dataset": ["m100", "m100", "wemuav", "wemuav"],
            "payload_kg": [0.0, 0.5, 0.0, 0.0],
            "assumed_empty_mass_kg": [2.355, 2.355, 1.388, 1.388],
            "assumed_takeoff_mass_kg": [2.355, 2.855, 1.388, 1.388],
        }
    )

    audit = experiment.audit_mass_source_proxy_risk(
        frame,
        ["payload_kg", "assumed_empty_mass_kg", "assumed_takeoff_mass_kg"],
    )

    assert audit["mass_source_proxy_risk"] == "high"
    assert "assumed_empty_mass_kg" in audit["mass_source_proxy_columns"]


def test_source_balanced_sample_weight_upweights_small_source():
    """源域均衡权重应提高小样本数据源的训练权重。"""

    frame = pd.DataFrame(
        {
            "source_dataset": ["m100", "m100", "m100", "wemuav"],
        }
    )

    weights = experiment.compute_sample_weight(frame, "source_balanced")

    assert weights is not None
    assert round(float(weights.mean()), 6) == 1.0
    assert float(weights.iloc[3]) > float(weights.iloc[0])


def test_apply_weather_basic_wind_profile_recomputes_components():
    """基础天气风口径应覆盖同名风字段并重算逆风侧风。"""

    frame = pd.DataFrame(
        {
            "heading_deg": [0.0, 90.0],
            "wind_speed_mps": [99.0, 99.0],
            "wind_dir_deg": [99.0, 99.0],
            "hist_wind_speed_mps": [2.0, 3.0],
            "hist_wind_dir_deg": [0.0, 180.0],
            "headwind_mps": [99.0, 99.0],
            "crosswind_mps": [99.0, 99.0],
        }
    )

    out, meta = experiment.apply_wind_profile(frame, "weather_basic")

    assert meta["changed"] is True
    assert out["wind_speed_mps"].tolist() == [2.0, 3.0]
    assert out["wind_dir_deg"].tolist() == [0.0, 180.0]
    assert round(float(out["headwind_mps"].iloc[0]), 6) == 2.0
    assert round(float(out["crosswind_mps"].iloc[0]), 6) == 0.0
    assert round(float(out["headwind_mps"].iloc[1]), 6) == 0.0
    assert round(float(out["crosswind_mps"].iloc[1]), 6) == 3.0


def test_apply_height_weather_prefers_height_layer_columns():
    """高度层天气风口径应优先使用 hist_height_* 字段。"""

    frame = pd.DataFrame(
        {
            "heading_deg": [0.0],
            "hist_wind_speed_mps": [1.0],
            "hist_wind_dir_deg": [0.0],
            "hist_height_wind_speed_mps": [4.0],
            "hist_height_wind_dir_deg": [90.0],
        }
    )

    out, meta = experiment.apply_wind_profile(frame, "height_weather")

    assert meta["source_speed_column"] == "hist_height_wind_speed_mps"
    assert meta["source_dir_column"] == "hist_height_wind_dir_deg"
    assert round(float(out["wind_speed_mps"].iloc[0]), 6) == 4.0
    assert round(float(out["headwind_mps"].iloc[0]), 6) == 0.0
    assert round(float(out["crosswind_mps"].iloc[0]), 6) == 4.0


def test_deployment_selection_score_balances_task_error_and_proxy_risk():
    """部署候选评分不应被单一段级 RMSE 牵着走。"""

    comparison = pd.DataFrame(
        [
            {
                "variant": "low_rmse_high_task_error",
                "segment_rmse": 24.0,
                "flight_mean_abs_energy_error_pct": 3.5,
                "range_mean_abs_error_pct": 3.5,
                "worst_source_abs_target_error_pct": 4.5,
                "max_abs_source_phase_bias_w": 7.0,
                "mass_source_proxy_risk": "high",
            },
            {
                "variant": "balanced_deployment_candidate",
                "segment_rmse": 25.0,
                "flight_mean_abs_energy_error_pct": 2.8,
                "range_mean_abs_error_pct": 2.8,
                "worst_source_abs_target_error_pct": 4.0,
                "max_abs_source_phase_bias_w": 13.0,
                "mass_source_proxy_risk": "medium",
            },
        ]
    )

    scored = experiment.add_deployment_selection_score(comparison)
    best = scored.sort_values("deployment_selection_score").iloc[0]

    assert best["variant"] == "balanced_deployment_candidate"
    assert "deployment_selection_score_note" in scored.columns
