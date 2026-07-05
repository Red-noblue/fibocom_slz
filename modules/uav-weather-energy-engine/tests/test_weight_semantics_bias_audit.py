# 验证重量语义与常量偏差审计脚本的关键判断逻辑。
"""验证训练侧重量语义与常量偏差审计。"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_weight_semantics_and_constant_bias as audit


def test_estimate_linear_sensitivity_fits_simple_payload_power_line():
    """线性敏感度应能识别载荷增加带来的功率增加。"""

    frame = pd.DataFrame(
        {
            "payload_kg": [0.0, 1.0, 2.0, 3.0],
            "actual_target_value": [100.0, 110.0, 120.0, 130.0],
        }
    )

    sensitivity = audit.estimate_linear_sensitivity(frame, "payload_kg", "actual_target_value")

    assert round(float(sensitivity["slope"]), 6) == 10.0
    assert round(float(sensitivity["intercept"]), 6) == 100.0
    assert round(float(sensitivity["r2"]), 6) == 1.0
    assert int(sensitivity["unique_x_count"]) == 4


def test_payload_sensitivity_status_rejects_negative_or_weak_slope():
    """斜率方向错误或解释力太弱时，不允许反推等效缺失重量。"""

    assert audit._payload_sensitivity_status(-5.0, 0.90, 5, 5) == "non_positive_slope"
    assert audit._payload_sensitivity_status(5.0, 0.10, 5, 5, min_r2=0.30) == "low_r2"
    assert audit._payload_sensitivity_status(5.0, 0.80, 5, 5, min_r2=0.30) == "reliable"


def test_build_bias_table_does_not_infer_mass_from_unreliable_payload_slope():
    """不可靠载荷斜率下应保留常量偏差，但不输出等效重量解释。"""

    frame = pd.DataFrame(
        {
            "variant": ["demo"] * 4,
            "source_dataset": ["m100"] * 4,
            "phase_label": ["climb"] * 4,
            "target_error": [-10.0] * 4,
            "actual_target_value": [130.0, 120.0, 110.0, 100.0],
            "predicted_target_value": [120.0, 110.0, 100.0, 90.0],
            "abs_target_error_pct": [8.0, 8.5, 9.0, 10.0],
            "segment_energy_error_pct": [8.0, 8.5, 9.0, 10.0],
            "payload_kg": [0.0, 0.5, 1.0, 1.5],
            "speed_mps": [5.0] * 4,
            "altitude_m": [30.0] * 4,
            "duration_s": [60.0] * 4,
            "distance_m": [300.0] * 4,
            "random_state": [1] * 4,
        }
    )

    bias_table = audit.build_bias_table(frame, min_payload_slope_r2=0.30)
    source_phase = bias_table.loc[bias_table["group_type"] == "source_phase"].iloc[0]

    assert source_phase["payload_sensitivity_status"] == "non_positive_slope"
    assert bool(source_phase["payload_sensitivity_reliable"]) is False
    assert np.isnan(float(source_phase["equivalent_payload_shift_kg"]))
    assert round(float(source_phase["prediction_bias_w"]), 6) == -10.0
