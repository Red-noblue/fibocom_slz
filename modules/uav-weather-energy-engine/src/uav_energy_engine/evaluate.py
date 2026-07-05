"""提供评估指标与实验结果汇总函数。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Union

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def naive_rmse(y_true) -> float:
    """计算论文中使用的 Naive RMSE 基线。"""

    series = np.asarray(y_true, dtype=float).reshape(-1)
    if series.size < 2:
        return float("nan")
    diffs = np.diff(series)
    return float(np.sqrt(np.mean(np.square(diffs))))


def regression_metrics(y_true, y_pred) -> dict:
    """计算标准回归指标。"""

    y_true_arr = np.asarray(y_true, dtype=float).reshape(-1)
    y_pred_arr = np.asarray(y_pred, dtype=float).reshape(-1)
    mse = mean_squared_error(y_true_arr, y_pred_arr)
    return {
        "mae": float(mean_absolute_error(y_true_arr, y_pred_arr)),
        "rmse": float(np.sqrt(mse)),
        "r2": float(r2_score(y_true_arr, y_pred_arr)),
        "naive_rmse": naive_rmse(y_true_arr),
    }


def save_ablation_results(rows: List[dict], output_path: Union[str, Path]) -> pd.DataFrame:
    """保存消融实验结果表。"""

    frame = pd.DataFrame(rows)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False)
    return frame


def save_summary(payload: dict, output_path: Union[str, Path]) -> None:
    """保存 JSON 汇总结果。"""

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with Path(output_path).open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
