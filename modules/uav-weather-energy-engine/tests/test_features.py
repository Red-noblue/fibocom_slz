"""验证核心特征工程函数的基础行为。"""

from __future__ import annotations

import math

from uav_energy_engine.evaluate import naive_rmse
from uav_energy_engine.features import (
    compute_air_density,
    compute_derived_gps_distance,
    compute_normalized_timestamp,
    compute_weather_factor,
    compute_wind_components,
    build_model_feature_row,
    ensure_planned_ground_speed,
)


def test_compute_air_density_positive():
    """空气密度应为正数。"""

    density = compute_air_density(temperature_c=20.0, pressure_hpa=1013.25)
    assert density > 0.0


def test_compute_wind_components_simple_case():
    """同向风下逆风分量应接近风速本身。"""

    headwind, crosswind = compute_wind_components(5.0, 90.0, 90.0)
    assert math.isclose(headwind, 5.0, rel_tol=1e-6)
    assert math.isclose(crosswind, 0.0, abs_tol=1e-6)


def test_ensure_planned_ground_speed_adds_explicit_alias():
    """计划地速字段应从旧 speed_mps 兼容生成。"""

    import pandas as pd

    frame = pd.DataFrame({"speed_mps": [5.0, 6.0]})

    out = ensure_planned_ground_speed(frame)

    assert out["planned_ground_speed_mps"].tolist() == [5.0, 6.0]
    assert out["speed_mps"].tolist() == [5.0, 6.0]


def test_build_model_feature_row_includes_equivalent_wind():
    """单次预测输入也应包含等效空速字段。"""

    row = build_model_feature_row(
        speed_mps=10.0,
        payload_g=500.0,
        altitude_m=50.0,
        wind_speed_mps=4.0,
        wind_dir_deg=90.0,
        heading_deg=90.0,
    )

    assert round(float(row["equivalent_airspeed_mps"]), 6) == 14.0
    assert round(float(row["headwind_ratio"]), 6) == 0.4
    assert round(float(row["wind_dir_deg"]), 6) == 90.0
    assert round(float(row["phase_is_level"]), 6) == 1.0
    assert round(float(row["phase_is_cruise"]), 6) == 1.0


def test_weather_factor_not_less_than_lower_clip():
    """天气因子应遵守下限裁剪。"""

    factor = compute_weather_factor(
        temperature_c=22.0,
        relative_humidity_pct=40.0,
        pressure_hpa=1013.25,
        precipitation_mm=0.0,
        visibility_km=20.0,
        uv_index=1.0,
        air_quality_index=20.0,
    )
    assert factor >= 0.85


def test_compute_normalized_timestamp_bounds():
    """归一化时间戳应落在 0 到 1 之间。"""

    values = compute_normalized_timestamp([10.0, 20.0, 30.0])
    assert math.isclose(values[0], 0.0, abs_tol=1e-9)
    assert math.isclose(values[-1], 1.0, abs_tol=1e-9)


def test_compute_derived_gps_distance_starts_at_zero():
    """派生 GPS 距离的首项应为零。"""

    distances = compute_derived_gps_distance(
        lat_values=[39.0, 39.0001],
        lon_values=[116.0, 116.0001],
        alt_values=[50.0, 50.0],
    )
    assert math.isclose(distances[0], 0.0, abs_tol=1e-9)
    assert distances[1] > 0.0


def test_naive_rmse_positive_for_varying_series():
    """变化序列的 Naive RMSE 应为正。"""

    metric = naive_rmse([1.0, 2.0, 4.0, 7.0])
    assert metric > 0.0
