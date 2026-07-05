# 验证预测入口从训练特征中读取默认飞行参数和分段步长。
"""验证预测默认参数加载逻辑。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import json

from uav_energy_engine.predict import (
    add_planned_phase_defaults,
    add_planned_route_geometry_defaults,
    add_segment_altitude_defaults,
    apply_hover_power_prior,
    load_defaults_from_features,
    mission_route_points,
    mission_segment_specs,
    resample_route_points,
    route_total_distance_m,
    segment_boundary_time_index,
    predict_fixed_route_energy_with_weather_frame,
    write_prediction_outputs,
)
from uav_energy_engine.schema import BatterySpec, GeoPoint, MissionSpec, RouteSegmentSpec, VehicleSpec
from datetime import datetime


def test_load_defaults_from_features_infers_step_minutes(tmp_path: Path):
    """训练特征包含分段时长时，应推断对应的预测步长。"""

    features_csv = tmp_path / "features.csv"
    pd.DataFrame(
        {
            "speed_mps": [7.0, 8.0, 9.0],
            "payload_g": [200.0, 250.0, 300.0],
            "altitude_m": [50.0, 60.0, 70.0],
            "duration_s": [120.0, 120.0, 120.0],
        }
    ).to_csv(features_csv, index=False)

    defaults = load_defaults_from_features(features_csv)

    assert defaults["speed_mps"] == 8.0
    assert defaults["payload_g"] == 250.0
    assert defaults["altitude_m"] == 60.0
    assert defaults["segment_duration_s"] == 120.0
    assert defaults["step_minutes"] == 2


def test_load_defaults_from_features_supports_payload_kg(tmp_path: Path):
    """只有 payload_kg 时也应推断默认载荷。"""

    features_csv = tmp_path / "features_payload_kg.csv"
    pd.DataFrame(
        {
            "planned_ground_speed_mps": [7.0, 8.0, 9.0],
            "payload_kg": [0.2, 0.25, 0.3],
            "altitude_m": [50.0, 60.0, 70.0],
            "duration_s": [60.0, 60.0, 60.0],
        }
    ).to_csv(features_csv, index=False)

    defaults = load_defaults_from_features(features_csv)

    assert defaults["payload_g"] == 250.0
    assert defaults["payload_kg"] == 0.25


def test_add_planned_phase_defaults_sets_cruise_features():
    """固定航速固定高度规划段应补充巡航阶段默认特征。"""

    row = add_planned_phase_defaults({}, segment_distance_km=0.24, segment_duration_s=60.0)

    assert row["level_ratio"] == 1.0
    assert row["cruise_ratio"] == 1.0
    assert row["climb_ratio"] == 0.0
    assert row["vertical_speed_mean_mps"] == 0.0
    assert row["horizontal_speed_mean_mps"] == 4.0


def test_add_planned_route_geometry_defaults_sets_validated_features():
    """固定路线推理应补齐验证模型需要的路线几何字段。"""

    row = add_planned_route_geometry_defaults(
        {},
        route_distance_m=1000.0,
        segment_distance_m=100.0,
        segment_start_distance_m=200.0,
        route_heading_deg=90.0,
        route_segment_count=10,
    )

    assert round(float(row["heading_sin"]), 6) == 1.0
    assert round(float(row["heading_cos"]), 6) == 0.0
    assert row["route_total_distance_m"] == 1000.0
    assert row["route_tortuosity"] == 1.0
    assert row["route_segment_count"] == 10
    assert round(float(row["route_progress_ratio"]), 6) == 0.25
    assert row["route_remaining_distance_m"] == 750.0
    assert row["segment_route_alignment"] == 1.0


def test_route_total_distance_uses_polyline_not_just_endpoint():
    """折线航线总长应按逐段累加，而不是偷懒用起终点直线。"""

    points = [
        GeoPoint(lat=39.0, lon=116.0),
        GeoPoint(lat=39.001, lon=116.0),
        GeoPoint(lat=39.001, lon=116.001),
    ]

    total_distance = route_total_distance_m(points)

    assert total_distance > 150.0


def test_resample_route_points_preserves_polyline_endpoints():
    """折线航线重采样后应保留起终点。"""

    points = [
        GeoPoint(lat=39.0, lon=116.0, alt_m=30.0),
        GeoPoint(lat=39.001, lon=116.0, alt_m=40.0),
        GeoPoint(lat=39.001, lon=116.001, alt_m=35.0),
    ]

    sampled = resample_route_points(points, 5)

    assert len(sampled) == 5
    assert round(float(sampled[0].lat), 6) == 39.0
    assert round(float(sampled[0].lon), 6) == 116.0
    assert round(float(sampled[-1].lat), 6) == 39.001
    assert round(float(sampled[-1].lon), 6) == 116.001


def test_mission_route_points_prefers_explicit_route_points():
    """任务显式给出折线航点时，预测入口应优先使用这些点。"""

    mission = MissionSpec(
        route_name="polyline",
        start=GeoPoint(lat=39.0, lon=116.0),
        end=GeoPoint(lat=39.002, lon=116.002),
        departure_time=datetime(2026, 5, 16, 8, 0, 0),
        route_points=[
            GeoPoint(lat=39.0, lon=116.0),
            GeoPoint(lat=39.001, lon=116.0),
            GeoPoint(lat=39.001, lon=116.001),
        ],
    )

    points = mission_route_points(mission, 10)

    assert len(points) == 3
    assert round(float(points[1].lat), 6) == 39.001
    assert round(float(points[1].lon), 6) == 116.0


def test_segment_boundary_time_index_respects_variable_segment_duration():
    """显式分段任务应按真实累计时长取天气，而不是粗暴均匀切片。"""

    mission = MissionSpec(
        route_name="variable_duration",
        start=GeoPoint(lat=39.0, lon=116.0, alt_m=20.0),
        end=GeoPoint(lat=39.002, lon=116.002, alt_m=20.0),
        departure_time=datetime(2026, 5, 16, 8, 0, 0),
        route_segments=[
            RouteSegmentSpec(
                start=GeoPoint(lat=39.0, lon=116.0, alt_m=20.0),
                end=GeoPoint(lat=39.001, lon=116.0, alt_m=30.0),
                duration_s=45.0,
                distance_m=120.0,
                segment_id=0,
            ),
            RouteSegmentSpec(
                start=GeoPoint(lat=39.001, lon=116.0, alt_m=30.0),
                end=GeoPoint(lat=39.002, lon=116.002, alt_m=20.0),
                duration_s=135.0,
                distance_m=280.0,
                segment_id=1,
            ),
        ],
    )
    vehicle = VehicleSpec(name="demo", payload_g=200.0, cruise_speed_mps=8.0, altitude_m=30.0)

    specs = mission_segment_specs(mission, vehicle)
    time_index = segment_boundary_time_index(mission, specs)

    assert len(time_index) == 3
    assert time_index[0].isoformat() == "2026-05-16T08:00:00"
    assert time_index[1].isoformat() == "2026-05-16T08:00:45"
    assert time_index[2].isoformat() == "2026-05-16T08:03:00"


def test_add_segment_altitude_defaults_falls_back_to_route_altitude_when_point_alt_missing():
    """分段起终点高度缺失时，应回退到任务巡航高度，不能把整串垂直特征变成 NaN。"""

    row = {"altitude_m": 55.0}
    out = add_segment_altitude_defaults(
        feature_row=row,
        start_point=GeoPoint(lat=39.0, lon=116.0, alt_m=float("nan")),
        end_point=GeoPoint(lat=39.001, lon=116.001, alt_m=float("nan")),
        segment_duration_s=60.0,
    )

    assert out["altitude_start_m"] == 55.0
    assert out["altitude_end_m"] == 55.0
    assert out["altitude_delta_m"] == 0.0
    assert out["vertical_speed_mean_mps"] == 0.0


def test_predict_uses_segment_ground_speed_for_explicit_route_segments(tmp_path: Path):
    """显式分段任务应使用分段真实地速，而不是整条任务的统一 cruise_speed_mps。"""
    captured_frames = []

    class DummyModel:
        target = "segment_energy_wh"
        feature_cols = ["planned_ground_speed_mps"]

        def predict(self, frame):
            captured_frames.append(frame.copy())
            return [1.0]

    from uav_energy_engine import predict as predict_module

    original_loader = predict_module.WeatherEnergyModel.load
    predict_module.WeatherEnergyModel.load = staticmethod(lambda _: DummyModel())

    mission = MissionSpec(
        route_name="seg_speed",
        start=GeoPoint(lat=39.0, lon=116.0, alt_m=10.0),
        end=GeoPoint(lat=39.002, lon=116.0, alt_m=10.0),
        departure_time=datetime(2026, 5, 16, 8, 0, 0),
        route_segments=[
            RouteSegmentSpec(
                start=GeoPoint(lat=39.0, lon=116.0, alt_m=10.0),
                end=GeoPoint(lat=39.001, lon=116.0, alt_m=10.0),
                duration_s=50.0,
                distance_m=100.0,
                segment_id=0,
            ),
            RouteSegmentSpec(
                start=GeoPoint(lat=39.001, lon=116.0, alt_m=10.0),
                end=GeoPoint(lat=39.002, lon=116.0, alt_m=10.0),
                duration_s=50.0,
                distance_m=200.0,
                segment_id=1,
            ),
        ],
    )
    vehicle = VehicleSpec(name="demo", payload_g=0.0, cruise_speed_mps=0.0, altitude_m=10.0)
    battery = BatterySpec(capacity_wh=100.0, nominal_voltage_v=15.2)
    weather_csv = tmp_path / "weather.csv"
    pd.DataFrame(
        {
            "time": ["2026-05-16T08:00:00", "2026-05-16T08:00:50", "2026-05-16T08:01:40"],
            "wind_speed_mps": [0.0, 0.0, 0.0],
            "wind_dir_deg": [0.0, 0.0, 0.0],
            "wind_speed_100m_mps": [0.0, 0.0, 0.0],
            "wind_dir_100m_deg": [0.0, 0.0, 0.0],
            "wind_gust_mps": [0.0, 0.0, 0.0],
            "temperature_c": [20.0, 20.0, 20.0],
            "relative_humidity_pct": [50.0, 50.0, 50.0],
            "pressure_hpa": [1013.25, 1013.25, 1013.25],
            "precipitation_mm": [0.0, 0.0, 0.0],
            "air_density_kgm3": [1.2, 1.2, 1.2],
        }
    ).to_csv(weather_csv, index=False)

    try:
        predict_fixed_route_energy_with_weather_frame(
            model_path=tmp_path / "dummy.pkl",
            weather_frame=weather_csv,
            mission=mission,
            vehicle=vehicle,
            battery=battery,
        )
    finally:
        predict_module.WeatherEnergyModel.load = original_loader

    assert len(captured_frames) == 2
    first_speed = float(captured_frames[0]["planned_ground_speed_mps"].iloc[0])
    second_speed = float(captured_frames[1]["planned_ground_speed_mps"].iloc[0])
    assert first_speed == 2.0
    assert second_speed == 4.0


def test_apply_hover_power_prior_raises_hover_segment_floor():
    """悬停校准功率应为悬停段提供能耗下限。"""

    vehicle = VehicleSpec(
        name="demo",
        payload_g=0.0,
        cruise_speed_mps=0.0,
        altitude_m=10.0,
        hover_power_w=420.0,
    )

    adjusted = apply_hover_power_prior(
        vehicle=vehicle,
        feature_row={"phase_is_hover_or_slow": 1.0},
        segment_duration_s=60.0,
        segment_ground_speed_mps=0.05,
        segment_energy_wh=3.0,
    )

    assert round(float(adjusted), 6) == 7.0
