"""验证多来源训练表构建会保留数据源角色。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from uav_energy_engine.multi_source_training import build_multi_source_training_tables


def _write_minimal_flights(path: Path, source_dataset: str | None = None) -> None:
    """写出可分段的最小逐时刻飞行日志。"""

    rows = []
    for flight_id, lon_base in [(1, 116.0), (2, 116.01)]:
        for time_s, lon_offset in [(0.0, 0.0), (20.0, 0.001)]:
            row = {
                "flight": flight_id,
                "time": time_s,
                "wind_speed": 2.0,
                "wind_angle": 90.0,
                "battery_voltage": 10.0,
                "battery_current": 10.0,
                "position_x": lon_base + lon_offset,
                "position_y": 39.0,
                "position_z": 10.0 + time_s / 20.0,
                "speed": 8.0,
                "payload": 200.0 if source_dataset != "wemuav" else 0.0,
                "altitude": 50.0,
                "date": "2021-01-01",
                "route": "R1" if source_dataset != "wemuav" else "Hover",
                "hist_wind_speed_mps": 2.0,
                "hist_wind_dir_deg": 90.0,
                "hist_temperature_c": 20.0,
                "hist_pressure_hpa": 1013.0,
                "hist_relative_humidity_pct": 50.0,
            }
            if source_dataset is not None:
                row["source_dataset"] = source_dataset
                row["source_data_type"] = "unit"
                row["wind_speed_source"] = "external_weather"
                row["wind_angle_source"] = "external_weather"
            rows.append(row)
    pd.DataFrame(rows).to_csv(path, index=False)


def test_build_multi_source_training_tables_outputs_combined_table(tmp_path: Path):
    """多来源构建应输出分源表、合并表和审计摘要。"""

    m100_csv = tmp_path / "m100.csv"
    wemuav_csv = tmp_path / "wemuav.csv"
    output_dir = tmp_path / "out"
    _write_minimal_flights(m100_csv)
    _write_minimal_flights(wemuav_csv, source_dataset="wemuav")

    summary = build_multi_source_training_tables(
        output_dir=output_dir,
        m100_input_csv=m100_csv,
        wemuav_input_csv=wemuav_csv,
        segment_seconds=30.0,
        min_duration_s=1.0,
        m100_min_distance_m=1.0,
        wemuav_min_distance_m=1.0,
    )

    combined = pd.read_csv(output_dir / "combined_power_preflight.csv")

    assert (output_dir / "summary.json").exists()
    assert set(combined["source_dataset"]) == {"m100", "wemuav"}
    assert {"segment_energy_wh", "segment_wh_per_s", "mean_power_w"}.issubset(combined.columns)
    assert summary["source_counts"]["m100"] == 2
    assert summary["source_counts"]["wemuav"] == 2
    assert summary["rows"]["combined_power_preflight"] == 4
