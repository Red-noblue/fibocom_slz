# 验证阶段残差修正能学习并应用阶段性偏差。
"""验证阶段残差修正包装器的基础行为。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from uav_energy_engine.phase_residual import (
    fit_categorical_residual_correction,
    fit_phase_residual_correction,
    wrap_with_categorical_residual_corrections,
    wrap_with_phase_residual_correction,
)


class _LinearPhaseModel:
    """测试用基础模型：按速度输出稳定基线。"""

    feature_cols = ["speed_mps"]
    target_cols = ["segment_wh_per_s"]

    def predict(self, frame: pd.DataFrame):
        """返回可重复的基线预测。"""

        return np.asarray(10.0 + pd.to_numeric(frame["speed_mps"], errors="coerce"), dtype=float)


def test_fit_phase_residual_correction_learns_phase_offsets():
    """阶段残差应能学习到不同阶段的系统性偏差。"""

    train_frame = pd.DataFrame(
        {
            "speed_mps": [1.0, 1.0, 1.0, 1.0],
            "segment_wh_per_s": [12.0, 12.0, 15.0, 15.0],
            "phase_label": ["cruise", "cruise", "climb", "climb"],
        }
    )

    correction = fit_phase_residual_correction(
        base_model=_LinearPhaseModel(),
        train_frame=train_frame,
        target="segment_wh_per_s",
        phase_col="phase_label",
        min_phase_rows=2,
        shrinkage_rows=0.0,
    )

    assert round(float(correction.default_offset), 6) == 2.5
    assert round(float(correction.offsets["cruise"]), 6) == 1.0
    assert round(float(correction.offsets["climb"]), 6) == 4.0


def test_wrap_with_phase_residual_correction_applies_offsets():
    """包装后的模型应把阶段修正加回预测值。"""

    train_frame = pd.DataFrame(
        {
            "speed_mps": [1.0, 1.0, 1.0, 1.0],
            "segment_wh_per_s": [12.0, 12.0, 15.0, 15.0],
            "phase_label": ["cruise", "cruise", "climb", "climb"],
        }
    )
    model = wrap_with_phase_residual_correction(
        base_model=_LinearPhaseModel(),
        train_frame=train_frame,
        target="segment_wh_per_s",
        phase_col="phase_label",
        min_phase_rows=2,
        shrinkage_rows=0.0,
    )

    test_frame = pd.DataFrame(
        {
            "speed_mps": [1.0, 1.0],
            "phase_label": ["cruise", "climb"],
        }
    )

    predictions = model.predict(test_frame)

    assert round(float(predictions[0]), 6) == 12.0
    assert round(float(predictions[1]), 6) == 15.0


def test_fit_categorical_residual_correction_supports_source_groups():
    """通用分类残差应能按数据源学习偏差。"""

    train_frame = pd.DataFrame(
        {
            "speed_mps": [1.0, 1.0, 1.0, 1.0],
            "mean_power_w": [111.0, 111.0, 121.0, 121.0],
            "source_dataset": ["m100", "m100", "wemuav", "wemuav"],
        }
    )

    correction = fit_categorical_residual_correction(
        base_model=_LinearPhaseModel(),
        train_frame=train_frame,
        target="mean_power_w",
        group_cols=["source_dataset"],
        min_group_rows=2,
        shrinkage_rows=0.0,
    )

    assert round(float(correction.offsets["m100"]), 6) == 100.0
    assert round(float(correction.offsets["wemuav"]), 6) == 110.0


def test_wrap_with_categorical_residual_corrections_applies_sequential_offsets():
    """多组分类残差应按顺序修正源域和阶段偏差。"""

    train_frame = pd.DataFrame(
        {
            "speed_mps": [1.0, 1.0, 1.0, 1.0],
            "mean_power_w": [111.0, 113.0, 121.0, 123.0],
            "source_dataset": ["m100", "m100", "wemuav", "wemuav"],
            "phase_label": ["cruise", "climb", "cruise", "climb"],
        }
    )
    model = wrap_with_categorical_residual_corrections(
        base_model=_LinearPhaseModel(),
        train_frame=train_frame,
        target="mean_power_w",
        correction_groups=[["source_dataset"], ["phase_label"]],
        min_group_rows=2,
        shrinkage_rows=0.0,
    )
    test_frame = pd.DataFrame(
        {
            "speed_mps": [1.0, 1.0],
            "source_dataset": ["m100", "wemuav"],
            "phase_label": ["cruise", "climb"],
        }
    )

    predictions = model.predict(test_frame)

    assert round(float(predictions[0]), 6) == 111.0
    assert round(float(predictions[1]), 6) == 123.0
