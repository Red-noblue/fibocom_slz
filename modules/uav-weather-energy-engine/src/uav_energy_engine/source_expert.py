# 按数据源训练专家模型，避免不同无人机数据集被粗暴压进同一个回归器。
"""按数据源分发的专家模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Sequence

import numpy as np
import pandas as pd

from .model import _fit_model


@dataclass
class SourceExpertModel:
    """按 source_dataset 等字段选择专家模型，缺失时回退到全局模型。"""

    fallback_model: object
    expert_col: str = "source_dataset"
    experts: Dict[str, object] = field(default_factory=dict)
    expert_counts: Dict[str, int] = field(default_factory=dict)
    method: str = "source_expert"

    @property
    def feature_cols(self):
        """复用全局模型的特征列。"""

        return list(self.fallback_model.feature_cols)

    @property
    def target_cols(self):
        """复用全局模型的目标列。"""

        return list(getattr(self.fallback_model, "target_cols", []))

    @property
    def target(self) -> str:
        """兼容旧接口返回首个目标列。"""

        targets = self.target_cols
        return targets[0] if targets else ""

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        """根据数据源选择专家模型预测。"""

        predictions = np.asarray(self.fallback_model.predict(frame), dtype=float).reshape(-1)
        if self.expert_col not in frame.columns or not self.experts:
            return predictions

        sources = frame[self.expert_col].fillna("__nan__").astype(str)
        for source, expert in self.experts.items():
            mask = sources == str(source)
            if not mask.any():
                continue
            predictions[mask.to_numpy()] = np.asarray(expert.predict(frame.loc[mask]), dtype=float).reshape(-1)
        return predictions


def fit_source_expert_model(
    train_frame: pd.DataFrame,
    target: str,
    feature_cols: Sequence[str],
    method: str,
    random_state: int = 42,
    expert_col: str = "source_dataset",
    min_expert_rows: int = 20,
    base_cols: Optional[Sequence[str]] = None,
    sample_weight=None,
) -> SourceExpertModel:
    """训练全局回退模型和按数据源划分的专家模型。"""

    features = list(feature_cols)
    x_train = train_frame[features].copy()
    y_train = pd.to_numeric(train_frame[target], errors="coerce")
    weights = pd.to_numeric(pd.Series(sample_weight, index=train_frame.index), errors="coerce") if sample_weight is not None else None
    fallback = _fit_model(
        x_train=x_train,
        y_train=y_train,
        feature_cols=features,
        method=method,
        random_state=random_state,
        base_cols=base_cols,
        sample_weight=weights,
    )

    experts: Dict[str, object] = {}
    expert_counts: Dict[str, int] = {}
    if expert_col not in train_frame.columns:
        return SourceExpertModel(
            fallback_model=fallback,
            expert_col=expert_col,
            experts=experts,
            expert_counts=expert_counts,
        )

    for source, group in train_frame.groupby(expert_col, sort=False):
        source_name = str(source)
        clean_group = group.dropna(subset=features + [target]).copy()
        expert_counts[source_name] = int(len(clean_group.index))
        if len(clean_group.index) < int(min_expert_rows):
            continue
        expert = _fit_model(
            x_train=clean_group[features].copy(),
            y_train=pd.to_numeric(clean_group[target], errors="coerce"),
            feature_cols=features,
            method=method,
            random_state=random_state,
            base_cols=base_cols,
            sample_weight=weights.loc[clean_group.index] if weights is not None else None,
        )
        experts[source_name] = expert

    return SourceExpertModel(
        fallback_model=fallback,
        expert_col=expert_col,
        experts=experts,
        expert_counts=expert_counts,
    )
