# 验证模型训练在按分组切分时的基础行为，避免天气实验因日期泄漏而失真。
"""验证模型训练入口的基础行为。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from uav_energy_engine.model import _fit_model, save_model_object, train_energy_model, WeatherEnergyModel
from uav_energy_engine.phase_residual import PhaseResidualCorrectedModel, PhaseResidualCorrection


def test_train_energy_model_supports_group_split(tmp_path: Path):
    """按日期分组切分时应返回分组切分元信息。"""

    features_csv = tmp_path / "features.csv"
    pd.DataFrame(
        [
            {"speed_mps": 8.0, "payload_g": 200.0, "altitude_m": 50.0, "energy_wh_per_km": 30.0, "date": "2021-01-01"},
            {"speed_mps": 8.2, "payload_g": 200.0, "altitude_m": 50.0, "energy_wh_per_km": 31.0, "date": "2021-01-01"},
            {"speed_mps": 9.0, "payload_g": 250.0, "altitude_m": 60.0, "energy_wh_per_km": 35.0, "date": "2021-01-02"},
            {"speed_mps": 9.1, "payload_g": 250.0, "altitude_m": 60.0, "energy_wh_per_km": 36.0, "date": "2021-01-02"},
            {"speed_mps": 10.0, "payload_g": 300.0, "altitude_m": 70.0, "energy_wh_per_km": 40.0, "date": "2021-01-03"},
            {"speed_mps": 10.2, "payload_g": 300.0, "altitude_m": 70.0, "energy_wh_per_km": 41.0, "date": "2021-01-03"},
        ]
    ).to_csv(features_csv, index=False)

    model_out = tmp_path / "model.pkl"
    metrics_out = tmp_path / "metrics.json"
    metrics = train_energy_model(
        features_csv=features_csv,
        model_out=model_out,
        metrics_out=metrics_out,
        method="linear",
        feature_cols=["speed_mps", "payload_kg", "altitude_m"],
        group_col="date",
        test_size=0.34,
        random_state=7,
    )

    assert model_out.exists()
    assert metrics_out.exists()
    assert metrics["split_strategy"] == "group"
    assert metrics["group_col"] == "date"
    assert metrics["total_group_count"] == 3
    assert metrics["train_group_count"] >= 1
    assert metrics["test_group_count"] >= 1


def test_train_energy_model_supports_robust_linear_methods(tmp_path: Path):
    """稳健线性模型应可用于小样本能耗训练。"""

    features_csv = tmp_path / "features.csv"
    pd.DataFrame(
        [
            {"speed_mps": 4.0, "payload_g": 200.0, "altitude_m": 25.0, "segment_energy_wh": 10.0},
            {"speed_mps": 5.0, "payload_g": 220.0, "altitude_m": 30.0, "segment_energy_wh": 11.0},
            {"speed_mps": 6.0, "payload_g": 240.0, "altitude_m": 35.0, "segment_energy_wh": 12.0},
            {"speed_mps": 7.0, "payload_g": 260.0, "altitude_m": 40.0, "segment_energy_wh": 13.0},
            {"speed_mps": 8.0, "payload_g": 280.0, "altitude_m": 45.0, "segment_energy_wh": 14.0},
            {"speed_mps": 9.0, "payload_g": 300.0, "altitude_m": 50.0, "segment_energy_wh": 15.0},
        ]
    ).to_csv(features_csv, index=False)

    for method in ["huber", "elastic_net"]:
        metrics = train_energy_model(
            features_csv=features_csv,
            model_out=tmp_path / f"{method}.pkl",
            metrics_out=None,
            method=method,
            target="segment_energy_wh",
            feature_cols=["speed_mps", "payload_kg", "altitude_m"],
            test_size=0.34,
            random_state=7,
        )

        assert metrics["method"] == method
        assert metrics["test"]["count"] > 0


def test_fit_model_accepts_sample_weight():
    """底层训练函数应支持样本权重，供多来源误差实验使用。"""

    x_train = pd.DataFrame(
        {
            "speed_mps": [2.0, 3.0, 4.0, 5.0, 6.0],
            "altitude_m": [20.0, 25.0, 30.0, 35.0, 40.0],
        }
    )
    y_train = pd.Series([100.0, 120.0, 140.0, 160.0, 180.0], name="mean_power_w")
    sample_weight = pd.Series([1.0, 1.0, 2.0, 2.0, 3.0], index=x_train.index)

    model = _fit_model(
        x_train=x_train,
        y_train=y_train,
        feature_cols=["speed_mps", "altitude_m"],
        method="gradient_boosting",
        random_state=7,
        sample_weight=sample_weight,
    )

    prediction = model.predict(x_train)

    assert prediction.shape == (5,)


def test_save_model_object_supports_wrapped_models(tmp_path: Path):
    """通用模型保存应兼容带阶段修正的包装模型。"""

    x_train = pd.DataFrame(
        {
            "speed_mps": [2.0, 3.0, 4.0, 5.0],
            "altitude_m": [20.0, 25.0, 30.0, 35.0],
            "phase_label": ["climb", "climb", "level", "level"],
        }
    )
    y_train = pd.Series([100.0, 120.0, 140.0, 160.0], name="mean_power_w")
    base_model = _fit_model(
        x_train=x_train[["speed_mps", "altitude_m"]],
        y_train=y_train,
        feature_cols=["speed_mps", "altitude_m"],
        method="linear",
        random_state=7,
    )
    wrapped = PhaseResidualCorrectedModel(
        base_model=base_model,
        correction=PhaseResidualCorrection(
            phase_col="phase_label",
            offsets={"climb": 1.0, "level": -1.0},
            counts={"climb": 2, "level": 2},
        ),
    )

    model_out = tmp_path / "wrapped_model.pkl"
    save_model_object(wrapped, model_out)
    loaded = WeatherEnergyModel.load(model_out)

    prediction = loaded.predict(x_train)
    assert model_out.exists()
    assert prediction.shape == (4,)
