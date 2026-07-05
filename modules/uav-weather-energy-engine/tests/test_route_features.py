"""验证飞行前天气到路线时序特征的适配逻辑。"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from uav_energy_engine.route_features import (
    ROUTE_GEOMETRY_FEATURE_COLUMNS,
    ROUTE_TIME_MODEL_FEATURE_COLUMNS,
    WeatherToFlightFeatureAdapter,
    add_route_geometry_features,
    build_preflight_training_feature_view,
    build_route_time_feature_frame,
)
from uav_energy_engine.schema import GeoPoint, MissionSpec, VehicleSpec


def _demo_weather_frame() -> pd.DataFrame:
    """构造带 10m/100m 风的逐小时天气样例。"""

    return pd.DataFrame(
        {
            "wind_speed_mps": [2.0, 2.0],
            "wind_dir_deg": [90.0, 90.0],
            "wind_speed_100m_mps": [6.0, 6.0],
            "wind_dir_100m_deg": [90.0, 90.0],
            "wind_gust_mps": [7.0, 7.0],
            "temperature_c": [20.0, 20.0],
            "relative_humidity_pct": [60.0, 60.0],
            "pressure_hpa": [1013.25, 1013.25],
            "precipitation_mm": [0.0, 0.0],
        },
        index=pd.DatetimeIndex(["2026-05-13 10:00:00", "2026-05-13 11:00:00"]),
    )


def test_build_route_time_feature_frame_uses_height_aware_weather():
    """路线时序特征应把天气按飞行高度转换为模型输入。"""

    mission = MissionSpec(
        route_name="eastbound",
        start=GeoPoint(lat=39.0, lon=116.0),
        end=GeoPoint(lat=39.0, lon=116.01),
        departure_time=datetime(2026, 5, 13, 10, 0, 0),
        step_minutes=1,
    )
    vehicle = VehicleSpec(
        name="demo",
        payload_g=500.0,
        cruise_speed_mps=10.0,
        altitude_m=55.0,
    )

    frame = build_route_time_feature_frame(mission, vehicle, _demo_weather_frame())

    assert not frame.empty
    for column in ROUTE_TIME_MODEL_FEATURE_COLUMNS:
        assert column in frame.columns
    assert round(float(frame["payload_kg"].iloc[0]), 6) == 0.5
    assert round(float(frame["planned_ground_speed_mps"].iloc[0]), 6) == 10.0
    assert round(float(frame["speed_mps"].iloc[0]), 6) == 10.0
    assert round(float(frame["wind_speed_mps"].iloc[0]), 6) == 4.0
    assert float(frame["headwind_mps"].iloc[0]) > 3.9
    assert abs(float(frame["crosswind_mps"].iloc[0])) < 0.1
    assert round(float(frame["equivalent_airspeed_mps"].iloc[0]), 6) == 14.0
    assert float(frame["air_density_kgm3"].iloc[0]) > 1.0


def test_weather_to_flight_feature_adapter_marks_sources():
    """适配器应记录天气来源和特征来源，便于训练/运行误差分析。"""

    mission = MissionSpec(
        route_name="short",
        start=GeoPoint(lat=39.0, lon=116.0),
        end=GeoPoint(lat=39.001, lon=116.0),
        departure_time=datetime(2026, 5, 13, 10, 0, 0),
    )
    vehicle = VehicleSpec(name="demo", payload_g=100.0, cruise_speed_mps=8.0, altitude_m=10.0)
    adapter = WeatherToFlightFeatureAdapter(weather_source="era5_forecast", feature_source="preflight_adapter")

    frame = adapter.transform(mission, vehicle, _demo_weather_frame())

    assert set(frame["weather_source"]) == {"era5_forecast"}
    assert set(frame["feature_source"]) == {"preflight_adapter"}


def test_build_preflight_training_feature_view_uses_historical_weather_names():
    """部署口径训练视图应把历史天气映射为运行时同名字段。"""

    segment_frame = pd.DataFrame(
        {
            "speed_mps": [8.0],
            "payload_g": [500.0],
            "altitude_m": [55.0],
            "distance_m": [120.0],
            "duration_s": [15.0],
            "heading_deg": [90.0],
            "wind_speed_mps": [99.0],
            "hist_height_wind_speed_mps": [4.0],
            "hist_height_wind_dir_deg": [90.0],
            "hist_headwind_mps": [4.0],
            "hist_crosswind_mps": [0.0],
            "hist_wind_gust_mps": [6.0],
            "hist_temperature_c": [21.0],
            "hist_relative_humidity_pct": [55.0],
            "hist_pressure_hpa": [1010.0],
            "hist_precipitation_mm": [0.1],
            "hist_air_density_kgm3": [1.2],
            "segment_wh_per_km": [35.0],
        }
    )

    view = build_preflight_training_feature_view(segment_frame)

    assert round(float(view["payload_kg"].iloc[0]), 6) == 0.5
    assert round(float(view["planned_ground_speed_mps"].iloc[0]), 6) == 8.0
    assert round(float(view["wind_speed_mps"].iloc[0]), 6) == 4.0
    assert round(float(view["headwind_mps"].iloc[0]), 6) == 4.0
    assert round(float(view["equivalent_airspeed_mps"].iloc[0]), 6) == 12.0
    assert round(float(view["temperature_c"].iloc[0]), 6) == 21.0
    assert set(view["feature_source"]) == {"preflight_training_view"}


def test_add_route_geometry_features_describes_route_without_route_id():
    """路线几何特征应描述路径形态，而不是依赖路线编号。"""

    frame = pd.DataFrame(
        {
            "flight": [1, 1],
            "start_lat": [40.0, 40.001],
            "start_lon": [116.0, 116.0],
            "end_lat": [40.001, 40.001],
            "end_lon": [116.0, 116.001],
            "heading_deg": [0.0, 90.0],
            "distance_m": [100.0, 120.0],
            "altitude_start_m": [10.0, 20.0],
            "altitude_end_m": [20.0, 15.0],
            "altitude_gain_m": [10.0, 0.0],
            "altitude_loss_m": [0.0, 5.0],
        }
    )

    out = add_route_geometry_features(frame)

    for column in ROUTE_GEOMETRY_FEATURE_COLUMNS:
        assert column in out.columns
    assert round(float(out["route_total_distance_m"].iloc[0]), 6) == 220.0
    assert int(out["route_segment_count"].iloc[0]) == 2
    assert float(out["route_tortuosity"].iloc[0]) > 1.0
    assert round(float(out["segment_heading_change_deg"].iloc[1]), 6) == 90.0
    assert round(float(out["route_total_altitude_gain_m"].iloc[0]), 6) == 10.0
    assert round(float(out["route_total_altitude_loss_m"].iloc[0]), 6) == 5.0


def test_build_route_time_feature_frame_includes_route_geometry():
    """运行时航线特征也应带上路线几何字段。"""

    mission = MissionSpec(
        route_name="turning",
        start=GeoPoint(lat=39.0, lon=116.0),
        end=GeoPoint(lat=39.0, lon=116.01),
        route_points=[
            GeoPoint(lat=39.0, lon=116.0, alt_m=30.0),
            GeoPoint(lat=39.001, lon=116.0, alt_m=40.0),
            GeoPoint(lat=39.001, lon=116.001, alt_m=35.0),
        ],
        departure_time=datetime(2026, 5, 13, 10, 0, 0),
        step_minutes=1,
    )
    vehicle = VehicleSpec(name="demo", payload_g=500.0, cruise_speed_mps=10.0, altitude_m=55.0)

    frame = build_route_time_feature_frame(mission, vehicle, _demo_weather_frame())

    assert not frame.empty
    assert "route_total_distance_m" in frame.columns
    assert "segment_heading_change_deg" in frame.columns
    assert round(float(frame["altitude_start_m"].iloc[0]), 6) == 30.0
    assert round(float(frame["altitude_end_m"].iloc[0]), 6) == 40.0
    assert round(float(frame["altitude_gain_m"].iloc[0]), 6) == 10.0
    assert round(float(frame["altitude_loss_m"].iloc[1]), 6) == 5.0
    assert int(frame["route_segment_count"].iloc[0]) == 2
    assert float(frame["segment_heading_change_deg"].iloc[1]) > 1.0
