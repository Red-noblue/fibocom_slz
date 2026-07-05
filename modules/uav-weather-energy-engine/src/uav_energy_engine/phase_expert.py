# 按飞行阶段训练专家模型，避免把数据集来源误当成专家划分依据。
"""飞行阶段专家模型。"""

from __future__ import annotations

from typing import Optional, Sequence

import pandas as pd

from .source_expert import SourceExpertModel, fit_source_expert_model


def fit_phase_expert_model(
    train_frame: pd.DataFrame,
    target: str,
    feature_cols: Sequence[str],
    method: str,
    random_state: int = 42,
    phase_col: str = "phase_label",
    min_expert_rows: int = 20,
    base_cols: Optional[Sequence[str]] = None,
    sample_weight=None,
) -> SourceExpertModel:
    """训练全局回退模型和按飞行阶段划分的专家模型。"""

    model = fit_source_expert_model(
        train_frame=train_frame,
        target=target,
        feature_cols=feature_cols,
        method=method,
        random_state=random_state,
        expert_col=phase_col,
        min_expert_rows=min_expert_rows,
        base_cols=base_cols,
        sample_weight=sample_weight,
    )
    model.method = "phase_expert"
    return model
