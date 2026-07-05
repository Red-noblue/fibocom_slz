"""验证统一任务配置输入解析。"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from uav_energy_engine.task_io import load_task_bundle


def test_load_task_bundle_reads_polyline_and_defaults(tmp_path: Path):
    """任务配置应能读取折线航线，并从训练表补默认参数。"""

    features_csv = tmp_path / "train_frame.csv"
    pd.DataFrame(
        {
            "planned_ground_speed_mps": [8.0, 9.0, 10.0],
            "payload_kg": [0.2, 0.25, 0.3],
            "altitude_m": [50.0, 60.0, 70.0],
            "duration_s": [120.0, 120.0, 120.0],
        }
    ).to_csv(features_csv, index=False)

    task_json = tmp_path / "task.json"
    task_json.write_text(
        json.dumps(
            {
                "route_name": "polyline_task",
                "departure_time": "2026-05-16T08:00:00",
                "route_points": [
                    {"lat": 39.0, "lon": 116.0, "alt_m": 30.0},
                    {"lat": 39.001, "lon": 116.0, "alt_m": 40.0},
                    {"lat": 39.001, "lon": 116.001, "alt_m": 35.0},
                ],
                "battery": {"capacity_wh": 150.0},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    mission, vehicle, battery, task_cfg = load_task_bundle(task_json, features_csv)

    assert mission.route_name == "polyline_task"
    assert len(mission.route_points) == 3
    assert round(float(vehicle.payload_g), 6) == 250.0
    assert round(float(vehicle.cruise_speed_mps), 6) == 9.0
    assert round(float(vehicle.altitude_m), 6) == 60.0
    assert vehicle.hover_power_w is None
    assert round(float(battery.capacity_wh), 6) == 150.0
    assert task_cfg["route_name"] == "polyline_task"


def test_load_task_bundle_reads_hover_power_w(tmp_path: Path):
    """任务配置中的悬停功率校准应能进入载具对象。"""

    features_csv = tmp_path / "train_frame.csv"
    pd.DataFrame(
        {
            "planned_ground_speed_mps": [8.0],
            "payload_kg": [0.2],
            "altitude_m": [20.0],
            "duration_s": [60.0],
        }
    ).to_csv(features_csv, index=False)

    task_json = tmp_path / "task_hover.json"
    task_json.write_text(
        json.dumps(
            {
                "route_name": "hover_task",
                "departure_time": "2026-05-16T08:00:00",
                "start": {"lat": 39.0, "lon": 116.0, "alt_m": 20.0},
                "end": {"lat": 39.0, "lon": 116.0, "alt_m": 20.0},
                "vehicle": {
                    "name": "demo",
                    "payload_g": 0.0,
                    "cruise_speed_mps": 0.0,
                    "altitude_m": 20.0,
                    "hover_power_w": 420.0,
                },
                "battery": {"capacity_wh": 100.0},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    _, vehicle, _, _ = load_task_bundle(task_json, features_csv)

    assert round(float(vehicle.hover_power_w), 6) == 420.0
