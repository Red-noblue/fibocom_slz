"""验证飞前等效风特征转换。"""

from __future__ import annotations

import math

import pandas as pd

from uav_energy_engine.planned_equivalent_features import (
    add_planned_equivalent_wind_features,
    compute_equivalent_airspeed,
)


def test_compute_equivalent_airspeed_combines_headwind_and_crosswind():
    """等效空速应由计划地速、逆风和侧风向量合成。"""

    assert math.isclose(compute_equivalent_airspeed(10.0, 4.0, 0.0), 14.0, rel_tol=1e-6)
    assert math.isclose(compute_equivalent_airspeed(10.0, -3.0, 0.0), 7.0, rel_tol=1e-6)
    assert math.isclose(compute_equivalent_airspeed(10.0, 0.0, 4.0), math.sqrt(116.0), rel_tol=1e-6)


def test_add_planned_equivalent_wind_features_uses_speed_alias():
    """只有旧 speed_mps 时也应生成计划地速和等效风特征。"""

    frame = pd.DataFrame(
        {
            "speed_mps": [10.0, 10.0],
            "headwind_mps": [4.0, -3.0],
            "crosswind_mps": [0.0, 4.0],
        }
    )

    out = add_planned_equivalent_wind_features(frame)

    assert out["planned_ground_speed_mps"].tolist() == [10.0, 10.0]
    assert round(float(out["equivalent_airspeed_mps"].iloc[0]), 6) == 14.0
    assert round(float(out["tailwind_mps"].iloc[1]), 6) == 3.0
    assert round(float(out["crosswind_ratio"].iloc[1]), 6) == 0.4
    assert set(out["equivalent_wind_feature_source"]) == {
        "planned_equivalent:planned_ground_speed+headwind+crosswind"
    }
