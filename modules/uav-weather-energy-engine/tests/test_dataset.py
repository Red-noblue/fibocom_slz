"""验证数据集整理入口的基础行为。"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd

from uav_energy_engine.dataset import build_segment_dataset, filter_segment_outliers, prepare_m100_dataset


def test_prepare_m100_dataset_from_zip(tmp_path: Path):
    """M100 数据集整理应输出统一 flights.csv。"""

    dataset_root = tmp_path / "m100"
    dataset_root.mkdir()

    parameters = pd.DataFrame(
        [
            {
                "flight": 1,
                "payload_g": 250.0,
                "speed_mps": 8.0,
                "altitude_m": 60.0,
                "route": "R1",
                "date": "2021-01-01",
            }
        ]
    )
    parameters.to_csv(dataset_root / "parameters.csv", index=False)

    flight_csv = tmp_path / "1.csv"
    pd.DataFrame(
        [
            {
                "time": 0.0,
                "wind_speed": 3.2,
                "wind_direction": 45.0,
                "voltage": 15.5,
                "current": 12.0,
                "longitude": 116.1,
                "latitude": 39.9,
                "position_z": 312.4,
                "speed": 8.1,
                "altitude": 60.2,
                "heading": 92.0,
            },
            {
                "time": 1.0,
                "wind_speed": 3.4,
                "wind_direction": 47.0,
                "voltage": 15.4,
                "current": 12.2,
                "longitude": 116.1001,
                "latitude": 39.9001,
                "position_z": 312.6,
                "speed": 8.0,
                "altitude": 60.3,
                "heading": 93.0,
            },
        ]
    ).to_csv(flight_csv, index=False)

    zip_path = dataset_root / "flights.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.write(flight_csv, arcname="1.csv")

    output_csv = dataset_root / "flights.csv"
    out = prepare_m100_dataset(dataset_root=dataset_root, output_csv=output_csv)

    assert output_csv.exists()
    assert list(out["flight"].unique()) == [1]
    assert "battery_voltage" in out.columns
    assert "battery_current" in out.columns
    assert "position_x" in out.columns
    assert "position_y" in out.columns
    assert "position_z" in out.columns
    assert out["route"].iloc[0] == "R1"


def test_build_segment_dataset_preserves_energy_sum(tmp_path: Path):
    """分段样本能耗求和应接近原始日志积分能耗。"""

    input_csv = tmp_path / "flights.csv"
    output_csv = tmp_path / "segments.csv"
    pd.DataFrame(
        [
            {
                "flight": 1,
                "time": 0.0,
                "wind_speed": 2.0,
                "wind_angle": 90.0,
                "battery_voltage": 10.0,
                "battery_current": 10.0,
                "position_x": 116.0,
                "position_y": 39.0,
                "position_z": 0.0,
                "speed": 8.0,
                "payload": 200.0,
                "altitude": 50.0,
                "date": "2021-01-01",
                "route": "R1",
                "source_dataset": "unit",
                "source_data_type": "datconv4",
                "hist_wind_speed_mps": 2.1,
                "hist_wind_dir_deg": 90.0,
                "hist_temperature_c": 20.0,
                "hist_pressure_hpa": 1013.0,
            },
            {
                "flight": 1,
                "time": 10.0,
                "wind_speed": 2.2,
                "wind_angle": 91.0,
                "battery_voltage": 10.0,
                "battery_current": 10.0,
                "position_x": 116.0001,
                "position_y": 39.0001,
                "position_z": 5.0,
                "speed": 8.0,
                "payload": 200.0,
                "altitude": 50.0,
                "date": "2021-01-01",
                "route": "R1",
                "source_dataset": "unit",
                "source_data_type": "datconv4",
                "hist_wind_speed_mps": 2.2,
                "hist_wind_dir_deg": 91.0,
                "hist_temperature_c": 20.0,
                "hist_pressure_hpa": 1013.0,
            },
            {
                "flight": 1,
                "time": 20.0,
                "wind_speed": 2.4,
                "wind_angle": 92.0,
                "battery_voltage": 10.0,
                "battery_current": 10.0,
                "position_x": 116.0002,
                "position_y": 39.0002,
                "position_z": 10.0,
                "speed": 8.0,
                "payload": 200.0,
                "altitude": 50.0,
                "date": "2021-01-01",
                "route": "R1",
                "source_dataset": "unit",
                "source_data_type": "datconv4",
                "hist_wind_speed_mps": 2.3,
                "hist_wind_dir_deg": 92.0,
                "hist_temperature_c": 20.0,
                "hist_pressure_hpa": 1013.0,
            },
        ]
    ).to_csv(input_csv, index=False)

    out = build_segment_dataset(
        input_csv=input_csv,
        output_csv=output_csv,
        route="R1",
        segment_seconds=30.0,
        min_distance_m=1.0,
        min_duration_s=1.0,
    )

    assert output_csv.exists()
    assert len(out) == 1
    assert "segment_wh_per_km" in out.columns
    assert "segment_wh_per_s" in out.columns
    assert "mean_power_w" in out.columns
    assert out["source_dataset"].iloc[0] == "unit"
    assert out["source_data_type"].iloc[0] == "datconv4"
    assert "climb_ratio" in out.columns
    assert "vertical_speed_mean_mps" in out.columns
    assert float(out["climb_ratio"].iloc[0]) == 1.0
    assert round(float(out["vertical_speed_mean_mps"].iloc[0]), 6) == 0.5
    assert round(float(out["segment_energy_wh"].sum()), 6) == round(2000.0 / 3600.0, 6)
    assert round(float(out["segment_wh_per_s"].iloc[0]), 6) == round((2000.0 / 3600.0) / 20.0, 6)
    assert round(float(out["mean_power_w"].iloc[0]), 6) == 100.0


def test_filter_segment_outliers_by_target_range():
    """分段异常过滤应按目标范围删除长尾样本。"""

    frame = pd.DataFrame(
        {
            "segment_wh_per_km": [20.0, 30.0, 400.0],
            "segment_energy_wh": [1.0, 1.2, 4.0],
        }
    )
    filtered, meta = filter_segment_outliers(frame, max_target=100.0)

    assert len(filtered) == 2
    assert meta["rows_removed"] == 1
    assert meta["max_target"] == 100.0
