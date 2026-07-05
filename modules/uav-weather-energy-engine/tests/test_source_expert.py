"""验证按数据源分发的专家模型。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from uav_energy_engine.source_expert import fit_source_expert_model


def test_source_expert_model_dispatches_by_source_dataset():
    """源域专家模型应按 source_dataset 使用不同专家。"""

    train = pd.DataFrame(
        {
            "speed_mps": [1.0, 2.0, 1.0, 2.0, 1.0, 2.0],
            "source_dataset": ["m100", "m100", "m100", "wemuav", "wemuav", "wemuav"],
            "mean_power_w": [110.0, 120.0, 110.0, 220.0, 210.0, 220.0],
        }
    )
    model = fit_source_expert_model(
        train_frame=train,
        target="mean_power_w",
        feature_cols=["speed_mps"],
        method="linear",
        expert_col="source_dataset",
        min_expert_rows=2,
    )
    test = pd.DataFrame(
        {
            "speed_mps": [1.0, 1.0],
            "source_dataset": ["m100", "wemuav"],
        }
    )

    pred = model.predict(test)

    assert set(model.experts) == {"m100", "wemuav"}
    assert np.asarray(pred).shape == (2,)
    assert float(pred[1]) > float(pred[0])
