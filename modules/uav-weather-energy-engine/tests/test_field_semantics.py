"""验证字段语义审计能识别高风险字段。"""

from __future__ import annotations

import pandas as pd

from uav_energy_engine.field_semantics import audit_field_semantics, dataset_semantic_catalog


def test_audit_m100_flags_onboard_wind_and_altitude_semantics():
    """M100 机载风和高度双语义应被标记为风险。"""

    frame = pd.DataFrame(
        {
            "flight": [1, 1],
            "time": [0.0, 1.0],
            "wind_speed": [2.0, 2.1],
            "wind_angle": [90.0, 91.0],
            "payload": [250.0, 250.0],
            "altitude": [50.0, 50.0],
            "position_z": [312.0, 312.5],
            "battery_voltage": [15.5, 15.4],
            "battery_current": [12.0, 12.1],
        }
    )

    audit = audit_field_semantics(frame, dataset="m100", label="unit_m100")
    high_columns = {warning["column"] for warning in audit["warnings"] if warning["level"] == "high"}

    assert audit["dataset"] == "m100"
    assert "wind_speed" in high_columns
    assert "payload" in high_columns
    assert "position_z" in high_columns
    assert "altitude/position_z" in {warning["column"] for warning in audit["warnings"]}


def test_audit_wemuav_requires_wind_source_and_reports_catalog():
    """WEMUAV 风字段缺少来源列时应提示风险。"""

    frame = pd.DataFrame(
        {
            "flight": [1001, 1001],
            "time": [0.0, 1.0],
            "wind_speed": [1.5, 1.6],
            "payload": [0.0, 0.0],
            "hist_wind_speed_mps": [1.4, None],
            "hist_temperature_c": [10.0, None],
            "hist_pressure_hpa": [1000.0, None],
            "hist_relative_humidity_pct": [60.0, None],
        }
    )

    audit = audit_field_semantics(frame, dataset="wemuav", label="unit_wemuav")
    messages = " ".join(warning["message"] for warning in audit["warnings"])
    catalog = dataset_semantic_catalog()

    assert audit["dataset"] == "wemuav"
    assert "来源列" in messages
    assert "wemuav" in catalog
