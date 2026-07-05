# 验证保守可达性校准和应用逻辑。
"""验证 P50/P90/P95 保守能耗与航程输出。"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from uav_energy_engine.predict import build_risk_alerts
from uav_energy_engine.reachability import (
    apply_conservative_reachability,
    build_reachability_safety_profile,
    load_reachability_safety_profile,
    save_reachability_safety_profile,
)


def test_build_reachability_safety_profile_uses_underprediction_multiplier():
    """安全校准应使用实际能耗与预测能耗的倍率分布。"""

    flight_errors = pd.DataFrame(
        {
            "actual_total_energy_wh": [90.0, 110.0, 140.0],
            "predicted_total_energy_wh": [100.0, 100.0, 100.0],
        }
    )

    profile = build_reachability_safety_profile(flight_errors, quantiles=[0.5, 0.9, 0.95], source_name="unit")

    assert profile["valid_count"] == 3
    assert profile["diagnostics"]["underprediction_count"] == 2
    assert round(float(profile["quantiles"]["p50"]["energy_multiplier"]), 6) == 1.1
    assert float(profile["quantiles"]["p95"]["energy_multiplier"]) > 1.3
    assert profile["quantiles"]["p95"]["empirical_coverage_rate"] >= 2.0 / 3.0


def test_apply_conservative_reachability_flags_p95_infeasible():
    """P95 保守能耗超过电池容量时应标记高风险。"""

    profile = {
        "profile_type": "flight_energy_safety_multiplier",
        "calibration_source": "unit",
        "valid_count": 3,
        "quantiles": {
            "p50": {"level": 0.5, "energy_multiplier": 1.0, "energy_margin_pct": 0.0},
            "p90": {"level": 0.9, "energy_multiplier": 1.1, "energy_margin_pct": 10.0},
            "p95": {"level": 0.95, "energy_multiplier": 1.4, "energy_margin_pct": 40.0},
        },
    }
    summary = {
        "predicted_total_energy_wh": 100.0,
        "route_length_km": 2.0,
        "battery_wh": 120.0,
        "predicted_range_km": 2.4,
    }

    conservative = apply_conservative_reachability(summary, profile)

    assert conservative["risk_level"] == "high"
    assert conservative["quantiles"]["p95"]["estimated_total_energy_wh"] == 140.0
    assert conservative["quantiles"]["p95"]["route_feasible"] is False

    summary["conservative_reachability"] = conservative
    alerts = build_risk_alerts(summary)
    assert any("P95" in alert for alert in alerts)


def test_reachability_safety_profile_round_trip(tmp_path: Path):
    """安全校准文件应可保存和加载。"""

    profile = build_reachability_safety_profile(
        pd.DataFrame(
            {
                "actual_total_energy_wh": [10.0, 12.0],
                "predicted_total_energy_wh": [10.0, 10.0],
            }
        )
    )
    output = save_reachability_safety_profile(profile, tmp_path / "profile.json")
    loaded = load_reachability_safety_profile(output)

    assert json.loads(output.read_text(encoding="utf-8"))["profile_type"] == "flight_energy_safety_multiplier"
    assert loaded["valid_count"] == 2
