# 验证飞行阶段专家模型按阶段分发预测。
"""验证飞行阶段专家模型。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from uav_energy_engine.phase_expert import fit_phase_expert_model


def test_phase_expert_model_dispatches_by_phase_label():
    """阶段专家模型应按 phase_label 使用不同专家。"""

    train = pd.DataFrame(
        {
            "speed_mps": [1.0, 2.0, 1.0, 2.0, 1.0, 2.0],
            "phase_label": ["cruise", "cruise", "cruise", "hover_or_slow", "hover_or_slow", "hover_or_slow"],
            "mean_power_w": [110.0, 120.0, 110.0, 220.0, 210.0, 220.0],
        }
    )

    model = fit_phase_expert_model(
        train_frame=train,
        target="mean_power_w",
        feature_cols=["speed_mps"],
        method="linear",
        min_expert_rows=2,
    )
    test = pd.DataFrame(
        {
            "speed_mps": [1.0, 1.0],
            "phase_label": ["cruise", "hover_or_slow"],
        }
    )

    pred = model.predict(test)

    assert model.method == "phase_expert"
    assert model.expert_col == "phase_label"
    assert set(model.experts) == {"cruise", "hover_or_slow"}
    assert np.asarray(pred).shape == (2,)
    assert float(pred[1]) > float(pred[0])
