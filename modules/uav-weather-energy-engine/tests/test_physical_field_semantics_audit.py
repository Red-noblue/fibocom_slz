# 验证高度、风和功率字段口径审计脚本的关键规则。
"""验证物理字段语义审计脚本。"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_physical_field_semantics as audit


def test_power_consistency_accepts_energy_duration_power():
    """mean_power_w 与 Wh/s 和 Wh/duration 反算一致时应为低风险。"""

    frame = pd.DataFrame(
        {
            "source_dataset": ["m100", "m100"],
            "mean_power_w": [360.0, 720.0],
            "segment_wh_per_s": [0.1, 0.2],
            "segment_energy_wh": [6.0, 12.0],
            "duration_s": [60.0, 60.0],
        }
    )

    out = audit.build_power_consistency(frame)

    assert out["risk_level"].tolist() == ["low"]
    assert float(out["p95_abs_pct_diff_whps_to_power"].iloc[0]) == 0.0


def test_wind_semantics_flags_flight_log_feature_used_by_baseline():
    """当前最佳特征使用 flight_log 风字段时必须标记高风险。"""

    frame = pd.DataFrame(
        {
            "source_dataset": ["wemuav", "wemuav"],
            "wind_speed_mps": [1.0, 2.0],
            "wind_speed_source": ["flight_log:AirSpeed:windSpeed", "flight_log:AirSpeed:windSpeed"],
        }
    )

    out = audit.build_wind_semantics(frame, baseline_features=["wind_speed_mps"])
    row = out.loc[out["field"].eq("wind_speed_mps")].iloc[0]

    assert row["risk_level"] == "high"
    assert "飞行前部署不可直接获得" in row["finding"]


def test_wind_semantics_accepts_height_weather_profile():
    """高度层天气风口径覆盖同名字段后，不应继续按 flight_log 风误报。"""

    frame = pd.DataFrame(
        {
            "source_dataset": ["wemuav", "wemuav"],
            "heading_deg": [0.0, 90.0],
            "wind_speed_mps": [1.0, 2.0],
            "wind_speed_source": ["flight_log:AirSpeed:windSpeed", "flight_log:AirSpeed:windSpeed"],
            "hist_height_wind_speed_mps": [3.0, 4.0],
            "hist_height_wind_dir_deg": [0.0, 180.0],
        }
    )

    profiled, meta = audit.apply_wind_profile(frame, "height_weather")
    out = audit.build_wind_semantics(profiled, baseline_features=["wind_speed_mps"])
    row = out.loc[out["field"].eq("wind_speed_mps")].iloc[0]

    assert meta["changed"] is True
    assert row["risk_level"] == "low"
    assert "flight_log" not in row["source_value_counts"]


def test_altitude_semantics_accepts_planned_level_profile():
    """固定高度计划口径下，高度动态特征不应继续按实飞轨迹缺口报警。"""

    frame = pd.DataFrame(
        {
            "source_dataset": ["m100", "m100"],
            "altitude_m": [50.0, 60.0],
            "altitude_start_m": [300.0, 310.0],
            "altitude_end_m": [305.0, 315.0],
            "altitude_delta_m": [5.0, 5.0],
            "vertical_speed_mean_mps": [0.1, 0.1],
            "altitude_source": ["programmed_altitude", "programmed_altitude"],
        }
    )

    profiled, meta = audit.apply_altitude_profile(frame, "planned_level")
    out = audit.build_altitude_semantics(
        profiled,
        baseline_features=["altitude_m", "altitude_delta_m", "vertical_speed_mean_mps"],
    )

    assert meta["changed"] is True
    assert set(out["risk_level"]) == {"low"}


def test_model_feature_semantics_propagates_wind_risk():
    """模型特征语义表应继承字段审计风险。"""

    wind = pd.DataFrame(
        {
            "field": ["wind_speed_mps"],
            "field_group": ["wind"],
            "risk_level": ["high"],
            "finding": ["风险"],
            "recommended_action": ["处理"],
        }
    )
    altitude = pd.DataFrame()

    out = audit.build_model_feature_semantics(["wind_speed_mps", "speed_mps"], wind, altitude)

    assert out.loc[out["feature"].eq("wind_speed_mps"), "risk_level"].iloc[0] == "high"
    assert out.loc[out["feature"].eq("speed_mps"), "risk_level"].iloc[0] == "low"
