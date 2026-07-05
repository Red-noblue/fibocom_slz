from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split


def train_energy_model(
    features_csv: str | Path,
    model_out: str | Path,
    metrics_out: str | Path,
    random_state: int = 42,
) -> None:
    df = pd.read_csv(features_csv)
    df["payload_kg"] = df["payload_g"] / 1000.0

    base_cols = ["speed_mps", "payload_kg", "altitude_m"]
    feature_cols = base_cols + ["wind_speed_mps", "headwind_mps", "crosswind_mps"]
    target = "energy_wh_per_km"

    df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=feature_cols + [target])
    if df.empty:
        raise ValueError("Training dataset is empty after dropping invalid feature rows.")

    x = df[feature_cols]
    y = df[target]

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=random_state,
    )

    baseline = LinearRegression()
    baseline.fit(x_train[base_cols], y_train)

    y_train_resid = y_train - baseline.predict(x_train[base_cols])
    residual_model = GradientBoostingRegressor(random_state=random_state)
    residual_model.fit(x_train, y_train_resid)

    def predict(batch: pd.DataFrame) -> np.ndarray:
        return baseline.predict(batch[base_cols]) + residual_model.predict(batch)

    y_pred_train = predict(x_train)
    y_pred_test = predict(x_test)

    train_mse = mean_squared_error(y_train, y_pred_train)
    test_mse = mean_squared_error(y_test, y_pred_test)

    metrics = {
        "train": {
            "count": int(len(x_train)),
            "mae": float(mean_absolute_error(y_train, y_pred_train)),
            "rmse": float(np.sqrt(train_mse)),
            "r2": float(r2_score(y_train, y_pred_train)),
        },
        "test": {
            "count": int(len(x_test)),
            "mae": float(mean_absolute_error(y_test, y_pred_test)),
            "rmse": float(np.sqrt(test_mse)),
            "r2": float(r2_score(y_test, y_pred_test)),
        },
        "features": feature_cols,
        "base_features": base_cols,
        "target": target,
        "rows_total": int(len(df)),
    }

    model_path = Path(model_out)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "baseline": baseline,
            "residual": residual_model,
            "feature_cols": feature_cols,
            "base_cols": base_cols,
            "target": target,
        },
        model_path,
    )

    metrics_path = Path(metrics_out)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with metrics_path.open("w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2, ensure_ascii=False)
