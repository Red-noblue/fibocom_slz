# 负责模型训练、保存、加载与单次推理，并支持按日期等分组切分训练集。
"""负责模型训练、保存、加载与单次推理。"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import ElasticNet, HuberRegressor, Lasso, LinearRegression, Ridge
from sklearn.model_selection import GroupShuffleSplit, train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures, StandardScaler

from .evaluate import regression_metrics, save_summary
from .features import ROUTE_FEATURE_COLUMNS, ensure_planned_ground_speed
from .planned_equivalent_features import add_planned_equivalent_wind_features


SUPPORTED_METHODS = [
    "linear_residual_gb",
    "linear",
    "polynomial",
    "ridge",
    "huber",
    "elastic_net",
    "lasso",
    "random_forest",
    "gradient_boosting",
    "mlp",
    "xgboost",
]


@dataclass
class WeatherEnergyModel:
    """包装天气驱动能耗模型。"""

    feature_cols: List[str]
    target_cols: List[str]
    method: str
    estimator: Optional[object] = None
    base_cols: List[str] = field(default_factory=list)
    baseline: Optional[LinearRegression] = None
    residual: Optional[GradientBoostingRegressor] = None

    @property
    def target(self) -> str:
        """兼容旧接口返回首个目标列。"""

        return self.target_cols[0]

    def predict(self, frame: pd.DataFrame) -> np.ndarray:
        """对输入特征表执行预测。"""

        features = frame[self.feature_cols]
        if self.method == "linear_residual_gb":
            if self.baseline is None or self.residual is None:
                raise ValueError("线性残差模型缺少已训练子模型。")
            baseline_pred = self.baseline.predict(frame[self.base_cols])
            residual_pred = self.residual.predict(features)
            return np.asarray(baseline_pred + residual_pred, dtype=float).reshape(-1)

        if self.estimator is None:
            raise ValueError("模型缺少可用的 estimator。")
        prediction = self.estimator.predict(features)
        return np.asarray(prediction, dtype=float)

    def save(self, model_out: Union[str, Path]) -> None:
        """保存模型。"""

        save_model_object(self, model_out)

    @classmethod
    def load(cls, model_path: Union[str, Path]) -> "WeatherEnergyModel":
        """加载模型。"""

        payload = joblib.load(model_path)
        if isinstance(payload, cls):
            return payload
        if isinstance(payload, dict) and payload.get("kind") == "generic_model":
            return payload["model"]
        target_cols = payload.get("target_cols")
        if not target_cols and payload.get("target"):
            target_cols = [str(payload["target"])]
        return cls(
            feature_cols=list(payload["feature_cols"]),
            target_cols=list(target_cols or []),
            method=str(payload.get("method", "linear_residual_gb")),
            estimator=payload.get("estimator"),
            base_cols=list(payload.get("base_cols", [])),
            baseline=payload.get("baseline"),
            residual=payload.get("residual"),
        )


def save_model_object(model: object, model_out: Union[str, Path]) -> None:
    """保存通用模型对象，兼容基础模型与带修正包装模型。"""

    Path(model_out).parent.mkdir(parents=True, exist_ok=True)
    if isinstance(model, WeatherEnergyModel):
        payload = {
            "method": model.method,
            "feature_cols": model.feature_cols,
            "target_cols": model.target_cols,
            "estimator": model.estimator,
            "base_cols": model.base_cols,
            "baseline": model.baseline,
            "residual": model.residual,
        }
    else:
        payload = {"kind": "generic_model", "model": model}
    joblib.dump(payload, model_out)


def _default_feature_columns(frame: pd.DataFrame, target_cols: Sequence[str]) -> List[str]:
    """优先使用核心路线特征，缺失时回退到数值列。"""

    default_cols = []
    for column in ROUTE_FEATURE_COLUMNS:
        if column == "speed_mps" and "planned_ground_speed_mps" in frame.columns:
            continue
        if column in frame.columns:
            default_cols.append(column)
    if default_cols:
        return default_cols

    ignored = set(target_cols) | {"flight", "route", "date"}
    numeric_cols = [
        column
        for column in frame.columns
        if column not in ignored and pd.api.types.is_numeric_dtype(frame[column])
    ]
    if not numeric_cols:
        raise ValueError("没有可用于训练的数值特征列。")
    return numeric_cols


def _build_estimator(method: str, random_state: int):
    """构造指定方法对应的回归器。"""

    if method == "linear":
        return LinearRegression()
    if method == "polynomial":
        return Pipeline(
            steps=[
                ("poly", PolynomialFeatures(degree=2, include_bias=False)),
                ("linear", LinearRegression()),
            ]
        )
    if method == "ridge":
        return Pipeline(
            steps=[
                ("scale", StandardScaler()),
                ("ridge", Ridge(alpha=1.0)),
            ]
        )
    if method == "huber":
        return Pipeline(
            steps=[
                ("scale", StandardScaler()),
                ("huber", HuberRegressor(epsilon=1.35, alpha=0.001, max_iter=1000)),
            ]
        )
    if method == "elastic_net":
        return Pipeline(
            steps=[
                ("scale", StandardScaler()),
                (
                    "elastic_net",
                    ElasticNet(alpha=0.03, l1_ratio=0.2, max_iter=50000, random_state=random_state),
                ),
            ]
        )
    if method == "lasso":
        return Pipeline(
            steps=[
                ("scale", StandardScaler()),
                (
                    "lasso",
                    Lasso(alpha=0.01, max_iter=10000, selection="random", random_state=random_state),
                ),
            ]
        )
    if method == "random_forest":
        return RandomForestRegressor(
            n_estimators=300,
            min_samples_leaf=2,
            random_state=random_state,
            n_jobs=-1,
        )
    if method == "gradient_boosting":
        return GradientBoostingRegressor(random_state=random_state)
    if method == "mlp":
        return Pipeline(
            steps=[
                ("scale", StandardScaler()),
                (
                    "mlp",
                    MLPRegressor(
                        hidden_layer_sizes=(64, 64),
                        activation="relu",
                        solver="adam",
                        learning_rate_init=0.001,
                        max_iter=1000,
                        random_state=random_state,
                    ),
                ),
            ]
        )
    if method == "xgboost":
        try:
            from xgboost import XGBRegressor
        except ImportError as exc:
            raise ImportError("当前环境未安装 xgboost，无法训练 xgboost 模型。") from exc
        return XGBRegressor(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="reg:squarederror",
            random_state=random_state,
            n_jobs=4,
        )
    raise ValueError(f"不支持的训练方法: {method}")


def _normalise_sample_weight(sample_weight, index: pd.Index) -> Optional[np.ndarray]:
    """把样本权重整理为和训练集对齐的数值数组。"""

    if sample_weight is None:
        return None
    if isinstance(sample_weight, pd.Series):
        weights = pd.to_numeric(sample_weight.reindex(index), errors="coerce")
    else:
        weights = pd.Series(sample_weight, index=index, dtype=float)
    weights = weights.replace([np.inf, -np.inf], np.nan)
    if weights.notna().sum() == 0:
        return None
    weights = weights.fillna(float(weights.median())).clip(lower=1e-6)
    return weights.to_numpy(dtype=float)


def _fit_estimator_with_optional_weight(estimator, x_train: pd.DataFrame, y_train: pd.Series, sample_weight=None) -> None:
    """训练 estimator，支持时透传样本权重，不支持时退回普通训练。"""

    if sample_weight is None:
        estimator.fit(x_train, y_train)
        return

    weights = np.asarray(sample_weight, dtype=float).reshape(-1)
    if isinstance(estimator, Pipeline):
        final_step_name = estimator.steps[-1][0]
        try:
            estimator.fit(x_train, y_train, **{f"{final_step_name}__sample_weight": weights})
            return
        except (TypeError, ValueError):
            estimator.fit(x_train, y_train)
            return

    try:
        estimator.fit(x_train, y_train, sample_weight=weights)
    except (TypeError, ValueError):
        estimator.fit(x_train, y_train)


def _fit_model(
    x_train: pd.DataFrame,
    y_train: pd.Series,
    feature_cols: Sequence[str],
    method: str,
    random_state: int,
    base_cols: Optional[Sequence[str]] = None,
    sample_weight=None,
) -> WeatherEnergyModel:
    """训练一个单目标回归模型。"""

    weights = _normalise_sample_weight(sample_weight, x_train.index)
    if method == "linear_residual_gb":
        base_columns = list(
            base_cols
            or [
                column
                for column in ["planned_ground_speed_mps", "speed_mps", "payload_kg", "altitude_m"]
                if column in x_train and not (column == "speed_mps" and "planned_ground_speed_mps" in x_train)
            ]
        )
        if not base_columns:
            raise ValueError("linear_residual_gb 至少需要基础特征列。")
        baseline = LinearRegression()
        _fit_estimator_with_optional_weight(baseline, x_train[base_columns], y_train, sample_weight=weights)
        residual_target = y_train - baseline.predict(x_train[base_columns])
        residual = GradientBoostingRegressor(random_state=random_state)
        _fit_estimator_with_optional_weight(residual, x_train[list(feature_cols)], residual_target, sample_weight=weights)
        return WeatherEnergyModel(
            feature_cols=list(feature_cols),
            target_cols=[str(y_train.name)],
            method=method,
            base_cols=base_columns,
            baseline=baseline,
            residual=residual,
        )

    estimator = _build_estimator(method, random_state=random_state)
    _fit_estimator_with_optional_weight(estimator, x_train[list(feature_cols)], y_train, sample_weight=weights)
    return WeatherEnergyModel(
        feature_cols=list(feature_cols),
        target_cols=[str(y_train.name)],
        method=method,
        estimator=estimator,
    )


def _resolve_feature_columns(frame: pd.DataFrame, requested_feature_cols: Optional[Sequence[str]], target_cols: Sequence[str]) -> List[str]:
    """解析最终使用的特征列，允许配置特征与样本列做交集。"""

    if not requested_feature_cols:
        requested_feature_cols = _default_feature_columns(frame, target_cols)

    resolved = []
    for column in requested_feature_cols:
        if column not in frame.columns:
            continue
        series = frame[column]
        if series.replace([np.inf, -np.inf], np.nan).notna().sum() == 0:
            continue
        resolved.append(column)
    if not resolved:
        raise ValueError("配置中的特征列在训练数据中全部缺失。")
    return resolved


def _prepare_training_frame(
    features_csv: Union[str, Path],
    target_cols: Sequence[str],
    feature_cols: Optional[Sequence[str]],
) -> Tuple[pd.DataFrame, List[str]]:
    """读取并清洗训练数据。"""

    df = pd.read_csv(features_csv)
    df = ensure_planned_ground_speed(df)
    df = add_planned_equivalent_wind_features(df)
    if "payload_kg" not in df.columns and "payload_g" in df.columns:
        df["payload_kg"] = pd.to_numeric(df["payload_g"], errors="coerce") / 1000.0

    target_columns = list(target_cols)
    feature_columns = _resolve_feature_columns(df, feature_cols, target_columns)
    required_columns = feature_columns + target_columns

    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError("训练数据缺少必要列: {}".format(", ".join(missing_columns)))

    cleaned = df.replace([np.inf, -np.inf], np.nan).dropna(subset=required_columns)
    if cleaned.empty:
        raise ValueError("训练数据经过清洗后为空。")
    return cleaned, feature_columns


def _split_training_frame(
    df: pd.DataFrame,
    feature_cols: Sequence[str],
    target: str,
    test_size: float,
    random_state: int,
    group_col: Optional[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, Dict]:
    """按随机或分组方式切分训练集与测试集。"""

    x = df[list(feature_cols)].copy()
    y = pd.to_numeric(df[target], errors="coerce")
    split_meta: Dict[str, object] = {
        "split_strategy": "random",
        "group_col": group_col,
    }

    if group_col and group_col in df.columns:
        groups = df[group_col].fillna("__nan__").astype(str)
        total_group_count = int(groups.nunique(dropna=False))
        if total_group_count >= 2:
            splitter = GroupShuffleSplit(
                n_splits=1,
                test_size=test_size,
                random_state=random_state,
            )
            train_idx, test_idx = next(splitter.split(x, y, groups=groups))
            split_meta.update(
                {
                    "split_strategy": "group",
                    "total_group_count": total_group_count,
                    "train_group_count": int(groups.iloc[train_idx].nunique(dropna=False)),
                    "test_group_count": int(groups.iloc[test_idx].nunique(dropna=False)),
                }
            )
            return (
                x.iloc[train_idx].copy(),
                x.iloc[test_idx].copy(),
                y.iloc[train_idx].copy(),
                y.iloc[test_idx].copy(),
                split_meta,
            )

        split_meta.update(
            {
                "split_strategy": "random_fallback",
                "fallback_reason": "group_count_lt_2",
                "total_group_count": total_group_count,
            }
        )

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=test_size,
        random_state=random_state,
    )
    return x_train, x_test, y_train, y_test, split_meta


def train_energy_model(
    features_csv: Union[str, Path],
    model_out: Union[str, Path],
    metrics_out: Optional[Union[str, Path]],
    random_state: int = 42,
    method: str = "linear_residual_gb",
    target: str = "energy_wh_per_km",
    feature_cols: Optional[Sequence[str]] = None,
    base_cols: Optional[Sequence[str]] = None,
    test_size: float = 0.2,
    group_col: Optional[str] = None,
) -> Dict:
    """训练天气驱动能耗模型并保存。"""

    if method not in SUPPORTED_METHODS:
        raise ValueError("不支持的训练方法: {}。可选值: {}".format(method, ", ".join(SUPPORTED_METHODS)))

    df, selected_feature_cols = _prepare_training_frame(features_csv, [target], feature_cols)
    x_train, x_test, y_train, y_test, split_meta = _split_training_frame(
        df=df,
        feature_cols=selected_feature_cols,
        target=target,
        test_size=test_size,
        random_state=random_state,
        group_col=group_col,
    )

    model = _fit_model(
        x_train=x_train,
        y_train=y_train,
        feature_cols=selected_feature_cols,
        method=method,
        random_state=random_state,
        base_cols=base_cols,
    )

    y_pred_train = np.asarray(model.predict(x_train), dtype=float).reshape(-1)
    y_pred_test = np.asarray(model.predict(x_test), dtype=float).reshape(-1)
    train_metrics = regression_metrics(y_train.to_numpy(dtype=float), y_pred_train)
    test_metrics = regression_metrics(y_test.to_numpy(dtype=float), y_pred_test)

    metrics = {
        "method": method,
        "train": {"count": int(len(x_train)), **train_metrics},
        "test": {"count": int(len(x_test)), **test_metrics},
        "features": selected_feature_cols,
        "base_features": list(model.base_cols),
        "target": target,
        "rows_total": int(len(df)),
        "supported_methods": SUPPORTED_METHODS,
        **split_meta,
    }

    model.save(model_out)
    if metrics_out is not None:
        save_summary(metrics, metrics_out)
    return metrics


def train_target_suite(
    features_csv: Union[str, Path],
    model_dir: Union[str, Path],
    metrics_out: Union[str, Path],
    methods: Sequence[str],
    targets: Sequence[str],
    random_state: int = 42,
    feature_cols: Optional[Sequence[str]] = None,
    test_size: float = 0.2,
    group_col: Optional[str] = None,
) -> Dict:
    """按论文复现思路训练多目标、多方法候选模型。"""

    suite_rows = []
    best_by_target = {}
    model_root = Path(model_dir)
    available_columns = set(pd.read_csv(features_csv, nrows=0).columns.tolist())

    for target in targets:
        if target not in available_columns:
            suite_rows.append(
                {
                    "target": target,
                    "method": None,
                    "status": "skipped_target_missing",
                    "error": "训练数据中缺少目标列: {}".format(target),
                }
            )
            continue
        target_best = None
        for method in methods:
            model_path = model_root / target / "{}.pkl".format(method)
            one_metrics_path = model_root / target / "{}.metrics.json".format(method)
            try:
                metrics = train_energy_model(
                    features_csv=features_csv,
                    model_out=model_path,
                    metrics_out=one_metrics_path,
                    random_state=random_state,
                    method=method,
                    target=target,
                    feature_cols=feature_cols,
                    test_size=test_size,
                    group_col=group_col,
                )
                row = {
                    "target": target,
                    "method": method,
                    "status": "trained",
                    "model_path": str(model_path),
                    "test_rmse": metrics["test"]["rmse"],
                    "test_mae": metrics["test"]["mae"],
                    "test_r2": metrics["test"]["r2"],
                    "test_naive_rmse": metrics["test"]["naive_rmse"],
                }
                if target_best is None or row["test_rmse"] < target_best["test_rmse"]:
                    target_best = row
            except Exception as exc:
                row = {
                    "target": target,
                    "method": method,
                    "status": "error",
                    "error": str(exc),
                }
            suite_rows.append(row)

        if target_best is not None:
            best_by_target[target] = target_best

    payload = {
        "methods": list(methods),
        "targets": list(targets),
        "results": suite_rows,
        "best_by_target": best_by_target,
    }
    save_summary(payload, metrics_out)
    return payload
