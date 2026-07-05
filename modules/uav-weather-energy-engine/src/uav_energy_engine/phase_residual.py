# 对不同飞行阶段的系统性预测偏差进行轻量残差修正。
"""阶段残差修正，用于在不拆复杂 MoE 的前提下降低阶段性偏差。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Sequence

import numpy as np
import pandas as pd


@dataclass
class PhaseResidualCorrection:
    """保存按阶段学习到的残差修正量。"""

    phase_col: str = "phase_label"
    offsets: Dict[str, float] = field(default_factory=dict)
    counts: Dict[str, int] = field(default_factory=dict)
    default_offset: float = 0.0
    shrinkage_rows: float = 20.0

    def apply(self, frame: pd.DataFrame, predictions) -> np.ndarray:
        """把阶段残差修正加到基础预测上。"""

        base = np.asarray(predictions, dtype=float).reshape(-1)
        if self.phase_col not in frame.columns or not self.offsets:
            return base + float(self.default_offset)

        phases = frame[self.phase_col].fillna("__nan__").astype(str)
        offsets = phases.map(self.offsets).fillna(float(self.default_offset)).to_numpy(dtype=float)
        return base + offsets


@dataclass
class PhaseResidualCorrectedModel:
    """包装基础模型，并在预测时追加阶段残差修正。"""

    base_model: object
    correction: PhaseResidualCorrection
    method: str = "phase_residual"

    @property
    def feature_cols(self):
        """复用基础模型的特征列。"""

        return list(self.base_model.feature_cols)

    @property
    def target_cols(self):
        """复用基础模型的目标列。"""

        return list(getattr(self.base_model, "target_cols", []))

    @property
    def target(self) -> str:
        """兼容旧接口返回首个目标列。"""

        targets = self.target_cols
        return targets[0] if targets else ""

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        """执行基础预测后追加阶段残差修正。"""

        base_predictions = self.base_model.predict(frame)
        return self.correction.apply(frame, base_predictions)


@dataclass
class CategoricalResidualCorrection:
    """保存按一个或多个分类字段学习到的残差修正量。"""

    group_cols: list[str] = field(default_factory=list)
    offsets: Dict[str, float] = field(default_factory=dict)
    counts: Dict[str, int] = field(default_factory=dict)
    default_offset: float = 0.0
    shrinkage_rows: float = 20.0

    def apply(self, frame: pd.DataFrame, predictions) -> np.ndarray:
        """把分类残差修正加到基础预测上。"""

        base = np.asarray(predictions, dtype=float).reshape(-1)
        if not self.group_cols or not self.offsets:
            return base + float(self.default_offset)
        if not set(self.group_cols).issubset(frame.columns):
            return base + float(self.default_offset)

        keys = _categorical_group_key(frame, self.group_cols)
        offsets = keys.map(self.offsets).fillna(float(self.default_offset)).to_numpy(dtype=float)
        return base + offsets


@dataclass
class ResidualCorrectedModel:
    """包装基础模型，并按多组分类字段顺序追加残差修正。"""

    base_model: object
    corrections: list[CategoricalResidualCorrection] = field(default_factory=list)
    method: str = "categorical_residual"

    @property
    def feature_cols(self):
        """复用基础模型的特征列。"""

        return list(self.base_model.feature_cols)

    @property
    def target_cols(self):
        """复用基础模型的目标列。"""

        return list(getattr(self.base_model, "target_cols", []))

    @property
    def target(self) -> str:
        """兼容旧接口返回首个目标列。"""

        targets = self.target_cols
        return targets[0] if targets else ""

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        """执行基础预测后按顺序追加残差修正。"""

        predictions = np.asarray(self.base_model.predict(frame), dtype=float).reshape(-1)
        for correction in self.corrections:
            predictions = correction.apply(frame, predictions)
        return predictions


def _categorical_group_key(frame: pd.DataFrame, group_cols: Sequence[str]) -> pd.Series:
    """把一个或多个分类列组合成稳定 key。"""

    key = pd.Series([""] * len(frame.index), index=frame.index, dtype=object)
    for idx, column in enumerate(group_cols):
        values = frame[column].fillna("__nan__").astype(str) if column in frame.columns else "__missing__"
        if idx == 0:
            key = values
        else:
            key = key + "|" + values
    return key


def fit_categorical_residual_correction(
    base_model: object,
    train_frame: pd.DataFrame,
    target: str,
    group_cols: Sequence[str],
    min_group_rows: int = 5,
    shrinkage_rows: float = 20.0,
    baseline_predictions=None,
) -> CategoricalResidualCorrection:
    """从训练集残差中估计一组分类字段的偏差修正量。"""

    columns = [str(column) for column in group_cols if str(column)]
    if not columns or not set(columns).issubset(train_frame.columns):
        return CategoricalResidualCorrection(group_cols=columns, shrinkage_rows=shrinkage_rows)

    required = list(base_model.feature_cols) + [target] + columns
    cleaned = train_frame.replace([np.inf, -np.inf], np.nan).dropna(subset=required).copy()
    if cleaned.empty:
        return CategoricalResidualCorrection(group_cols=columns, shrinkage_rows=shrinkage_rows)

    actual = pd.to_numeric(cleaned[target], errors="coerce")
    if baseline_predictions is None:
        predicted = pd.Series(np.asarray(base_model.predict(cleaned), dtype=float).reshape(-1), index=cleaned.index)
    else:
        predicted = pd.Series(np.asarray(baseline_predictions, dtype=float).reshape(-1), index=train_frame.index)
        predicted = predicted.loc[cleaned.index]
    residual = actual - predicted
    valid = residual.replace([np.inf, -np.inf], np.nan).dropna()
    if valid.empty:
        return CategoricalResidualCorrection(group_cols=columns, shrinkage_rows=shrinkage_rows)

    keys = _categorical_group_key(cleaned.loc[valid.index], columns)
    default_offset = float(valid.mean())
    offsets: Dict[str, float] = {}
    counts: Dict[str, int] = {}
    shrink = max(float(shrinkage_rows), 0.0)
    for key, group_residual in valid.groupby(keys, sort=False):
        count = int(len(group_residual.index))
        counts[str(key)] = count
        if count < int(min_group_rows):
            continue
        group_mean = float(group_residual.mean())
        weight = count / (count + shrink) if shrink > 0.0 else 1.0
        offsets[str(key)] = default_offset * (1.0 - weight) + group_mean * weight

    return CategoricalResidualCorrection(
        group_cols=columns,
        offsets=offsets,
        counts=counts,
        default_offset=default_offset,
        shrinkage_rows=shrink,
    )


def fit_phase_residual_correction(
    base_model: object,
    train_frame: pd.DataFrame,
    target: str,
    phase_col: str = "phase_label",
    min_phase_rows: int = 5,
    shrinkage_rows: float = 20.0,
) -> PhaseResidualCorrection:
    """从训练集残差中估计各飞行阶段的偏差修正量。"""

    if phase_col not in train_frame.columns:
        return PhaseResidualCorrection(phase_col=phase_col, shrinkage_rows=shrinkage_rows)

    required = list(base_model.feature_cols) + [target, phase_col]
    cleaned = train_frame.replace([np.inf, -np.inf], np.nan).dropna(subset=required).copy()
    if cleaned.empty:
        return PhaseResidualCorrection(phase_col=phase_col, shrinkage_rows=shrinkage_rows)

    actual = pd.to_numeric(cleaned[target], errors="coerce")
    predicted = pd.Series(np.asarray(base_model.predict(cleaned), dtype=float).reshape(-1), index=cleaned.index)
    residual = actual - predicted
    valid = residual.replace([np.inf, -np.inf], np.nan).dropna()
    if valid.empty:
        return PhaseResidualCorrection(phase_col=phase_col, shrinkage_rows=shrinkage_rows)

    phases = cleaned.loc[valid.index, phase_col].fillna("__nan__").astype(str)
    default_offset = float(valid.mean())
    offsets: Dict[str, float] = {}
    counts: Dict[str, int] = {}
    shrink = max(float(shrinkage_rows), 0.0)
    for phase, group_residual in valid.groupby(phases, sort=False):
        count = int(len(group_residual.index))
        counts[str(phase)] = count
        if count < int(min_phase_rows):
            continue
        phase_mean = float(group_residual.mean())
        weight = count / (count + shrink) if shrink > 0.0 else 1.0
        offsets[str(phase)] = default_offset * (1.0 - weight) + phase_mean * weight

    return PhaseResidualCorrection(
        phase_col=phase_col,
        offsets=offsets,
        counts=counts,
        default_offset=default_offset,
        shrinkage_rows=shrink,
    )


def wrap_with_phase_residual_correction(
    base_model: object,
    train_frame: pd.DataFrame,
    target: str,
    phase_col: str = "phase_label",
    min_phase_rows: int = 5,
    shrinkage_rows: float = 20.0,
) -> PhaseResidualCorrectedModel:
    """构造带阶段残差修正的模型包装器。"""

    correction = fit_phase_residual_correction(
        base_model=base_model,
        train_frame=train_frame,
        target=target,
        phase_col=phase_col,
        min_phase_rows=min_phase_rows,
        shrinkage_rows=shrinkage_rows,
    )
    return PhaseResidualCorrectedModel(base_model=base_model, correction=correction)


def wrap_with_categorical_residual_corrections(
    base_model: object,
    train_frame: pd.DataFrame,
    target: str,
    correction_groups: Sequence[Sequence[str]],
    min_group_rows: int = 5,
    shrinkage_rows: float = 20.0,
) -> ResidualCorrectedModel:
    """按多组分类字段顺序构造残差修正包装器。"""

    corrections: list[CategoricalResidualCorrection] = []
    current_predictions = np.asarray(base_model.predict(train_frame), dtype=float).reshape(-1)
    for group_cols in correction_groups:
        correction = fit_categorical_residual_correction(
            base_model=base_model,
            train_frame=train_frame,
            target=target,
            group_cols=group_cols,
            min_group_rows=min_group_rows,
            shrinkage_rows=shrinkage_rows,
            baseline_predictions=current_predictions,
        )
        corrections.append(correction)
        current_predictions = correction.apply(train_frame, current_predictions)

    return ResidualCorrectedModel(base_model=base_model, corrections=corrections)
