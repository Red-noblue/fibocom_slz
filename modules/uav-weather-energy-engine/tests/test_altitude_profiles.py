# 验证高度字段口径转换，避免把实飞海拔和计划巡航高度混成同一类输入。
"""验证高度字段口径转换工具。"""

from __future__ import annotations

import pandas as pd

from uav_energy_engine.altitude_profiles import apply_altitude_profile


def test_planned_level_profile_uses_altitude_m_and_clears_vertical_dynamics():
    """固定高度计划口径应使用 altitude_m 并清零爬降动态量。"""

    frame = pd.DataFrame(
        {
            "altitude_m": [50.0, 60.0],
            "altitude_start_m": [300.0, 305.0],
            "altitude_end_m": [310.0, 295.0],
            "altitude_delta_m": [10.0, -10.0],
            "altitude_gain_m": [20.0, 12.0],
            "altitude_loss_m": [3.0, 18.0],
            "vertical_speed_abs_mean_mps": [0.8, 1.2],
            "climb_ratio": [0.4, 0.1],
            "descent_ratio": [0.2, 0.5],
            "level_ratio": [0.4, 0.4],
            "phase_label": ["climb", "turn"],
            "altitude_source": ["programmed_altitude", "flight_log_position_z"],
        }
    )

    out, meta = apply_altitude_profile(frame, "planned_level")

    assert meta["changed"] is True
    assert out["altitude_start_m"].tolist() == [50.0, 60.0]
    assert out["altitude_end_m"].tolist() == [50.0, 60.0]
    assert out["altitude_delta_m"].tolist() == [0.0, 0.0]
    assert out["altitude_gain_m"].tolist() == [0.0, 0.0]
    assert out["altitude_loss_m"].tolist() == [0.0, 0.0]
    assert out["vertical_speed_abs_mean_mps"].tolist() == [0.0, 0.0]
    assert out["climb_ratio"].tolist() == [0.0, 0.0]
    assert out["descent_ratio"].tolist() == [0.0, 0.0]
    assert out["level_ratio"].tolist() == [1.0, 1.0]
    assert out["phase_label"].tolist() == ["level", "turn"]
    assert set(out["altitude_source"]) == {"altitude_profile:planned_level:altitude_m"}


def test_route_3d_profile_uses_segment_endpoints_without_jitter_gain_loss():
    """3D 航线口径应只按起终点高度计算垂直动态量。"""

    frame = pd.DataFrame(
        {
            "altitude_m": [50.0, 60.0, 70.0],
            "altitude_start_m": [50.0, 60.0, 70.0],
            "altitude_end_m": [56.0, 54.0, 71.0],
            "duration_s": [10.0, 20.0, 10.0],
            "altitude_gain_m": [100.0, 100.0, 100.0],
            "altitude_loss_m": [100.0, 100.0, 100.0],
            "vertical_speed_mean_mps": [9.0, 9.0, 9.0],
            "vertical_speed_abs_mean_mps": [9.0, 9.0, 9.0],
            "climb_ratio": [0.0, 0.0, 0.0],
            "descent_ratio": [0.0, 0.0, 0.0],
            "level_ratio": [1.0, 1.0, 1.0],
            "phase_label": ["cruise", "cruise", "descent"],
            "altitude_source": ["flight_log_position_z"] * 3,
        }
    )

    out, meta = apply_altitude_profile(frame, "route_3d")

    assert meta["changed"] is True
    assert out["altitude_delta_m"].tolist() == [6.0, -6.0, 1.0]
    assert out["altitude_gain_m"].tolist() == [6.0, 0.0, 1.0]
    assert out["altitude_loss_m"].tolist() == [-0.0, 6.0, -0.0]
    assert out["vertical_speed_mean_mps"].tolist() == [0.6, -0.3, 0.1]
    assert out["climb_ratio"].tolist() == [0.0, 0.0, 0.0]
    assert out["descent_ratio"].tolist() == [0.0, 0.0, 0.0]
    assert out["level_ratio"].tolist() == [1.0, 1.0, 1.0]
    assert out["phase_label"].tolist() == ["cruise", "cruise", "level"]
