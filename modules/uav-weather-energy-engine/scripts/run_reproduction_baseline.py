"""执行目标论文复现实验基线流程的命令行入口。"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / ".vendor"
SRC = ROOT / "src"
if VENDOR.exists() and str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_energy_engine.config import load_config
from uav_energy_engine.dataset import (
    build_research_feature_table,
    build_training_dataset,
    prepare_m100_dataset,
)
from uav_energy_engine.model import train_energy_model, train_target_suite
from uav_energy_engine.predict import (
    load_defaults_from_features,
    parse_departure,
    predict_fixed_route_energy,
    write_prediction_outputs,
)
from uav_energy_engine.wemuav_dataset import prepare_wemuav_dataset
from uav_energy_engine.schema import BatterySpec, GeoPoint, MissionSpec, VehicleSpec

import pandas as pd


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="执行目标论文复现实验的基础训练与预测流程。")
    parser.add_argument(
        "--experiment-config",
        default="experiments/engappai_2025_weather_aware_energy/config.yaml",
        help="实验配置文件",
    )
    parser.add_argument(
        "--base-config",
        default="configs/base.yaml",
        help="基础任务配置",
    )
    parser.add_argument(
        "--departure",
        required=True,
        help="起飞时间",
    )
    parser.add_argument(
        "--skip-train",
        action="store_true",
        help="跳过训练，只执行预测",
    )
    parser.add_argument(
        "--train-suite",
        action="store_true",
        help="额外训练论文复现候选模型套件",
    )
    parser.add_argument(
        "--prepare-m100",
        action="store_true",
        help="若缺少 flights.csv，则尝试用配置中的 M100 数据集根目录自动整理",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    exp_cfg = load_config(args.experiment_config)
    base_cfg = load_config(args.base_config)

    flights_csv = Path(exp_cfg["data"]["flights_csv"])
    features_csv = Path(exp_cfg["data"]["features_csv"])
    research_features_csv = Path(exp_cfg["data"].get("research_features_csv", "outputs/reproduction/research_features.csv"))
    m100_root = exp_cfg["data"].get("m100_root")
    model_out = Path(exp_cfg["model"]["output_model"])
    metrics_out = Path(exp_cfg["model"]["output_metrics"])
    suite_model_dir = Path(exp_cfg["model"].get("output_suite_dir", "outputs/reproduction/model_suite"))
    suite_metrics_out = Path(exp_cfg["model"].get("output_suite_metrics", "outputs/reproduction/model_suite.json"))
    predict_output_dir = Path(exp_cfg["prediction"]["output_dir"])
    route_filter = exp_cfg["data"].get("route_filter")
    source_datasets = exp_cfg["data"].get("source_datasets")
    feature_cols = exp_cfg["model"].get("features")
    target = str(exp_cfg["model"].get("target", "energy_wh_per_km"))
    targets = exp_cfg["model"].get("targets") or [target]
    candidate_methods = exp_cfg["model"].get("candidate_methods") or ["linear_residual_gb"]

    if not args.skip_train:
        if source_datasets:
            flights_csv.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="uav_energy_sources_") as temp_dir:
                temp_dir_path = Path(temp_dir)
                frames = []
                for idx, source in enumerate(source_datasets):
                    kind = str(source.get("kind", "")).strip().lower()
                    source_root = source.get("root")
                    if not source_root:
                        raise FileNotFoundError("source_datasets 中缺少 root。")
                    flight_id_offset = int(source.get("flight_id_offset", idx * 1_000_000))
                    temp_output = temp_dir_path / f"{kind}_{idx}.csv"
                    if kind == "m100":
                        frames.append(
                            prepare_m100_dataset(
                                dataset_root=source_root,
                                output_csv=temp_output,
                                flights_zip=source.get("flights_zip"),
                                parameters_csv=source.get("parameters_csv"),
                                flight_id_offset=flight_id_offset,
                            )
                        )
                    elif kind == "wemuav":
                        frames.append(
                            prepare_wemuav_dataset(
                                dataset_root=source_root,
                                output_csv=temp_output,
                                overview_csv=source.get("overview_csv"),
                                flight_id_offset=flight_id_offset,
                                max_cases=source.get("max_cases"),
                            )
                        )
                    else:
                        raise ValueError(f"不支持的数据源类型: {kind}")
                combined = pd.concat(frames, ignore_index=True, sort=False)
                combined.to_csv(flights_csv, index=False)
        elif not flights_csv.exists() and args.prepare_m100:
            if not m100_root:
                raise FileNotFoundError("缺少 flights.csv，且实验配置未提供 data.m100_root。")
            prepare_m100_dataset(dataset_root=m100_root, output_csv=flights_csv)
        if not flights_csv.exists():
            raise FileNotFoundError(
                f"未找到复现实验输入数据: {flights_csv}。请先把 flights.csv 放到该位置。"
            )
        build_training_dataset(flights_csv, features_csv, route_filter)
        build_research_feature_table(flights_csv, research_features_csv, route_filter)
        train_energy_model(
            features_csv=features_csv,
            model_out=model_out,
            metrics_out=metrics_out,
            method=str(candidate_methods[0]),
            target=target,
            feature_cols=feature_cols,
        )
        if args.train_suite:
            train_target_suite(
                features_csv=research_features_csv,
                model_dir=suite_model_dir,
                metrics_out=suite_metrics_out,
                methods=candidate_methods,
                targets=targets,
                feature_cols=feature_cols,
            )

    if not features_csv.exists():
        raise FileNotFoundError(f"未找到训练样本文件: {features_csv}")
    if not model_out.exists():
        raise FileNotFoundError(f"未找到模型文件: {model_out}")

    defaults = load_defaults_from_features(features_csv)
    mission = MissionSpec(
        route_name=str(exp_cfg["prediction"]["route_name"]),
        start=GeoPoint(lat=float(base_cfg["start"]["lat"]), lon=float(base_cfg["start"]["lon"])),
        end=GeoPoint(lat=float(base_cfg["end"]["lat"]), lon=float(base_cfg["end"]["lon"])),
        departure_time=parse_departure(args.departure),
        step_minutes=int(exp_cfg["prediction"]["step_minutes"]),
    )
    vehicle = VehicleSpec(
        name=str(base_cfg["vehicle"]["name"]),
        payload_g=defaults["payload_g"],
        cruise_speed_mps=defaults["speed_mps"],
        altitude_m=defaults["altitude_m"],
    )
    battery = BatterySpec(
        capacity_wh=float(base_cfg["battery"]["capacity_wh"]),
        nominal_voltage_v=float(base_cfg["battery"]["nominal_voltage_v"]),
    )
    bundle = predict_fixed_route_energy(
        model_path=model_out,
        weather_config=exp_cfg["weather"]["adapter_config"],
        mission=mission,
        vehicle=vehicle,
        battery=battery,
    )
    summary_path, timeseries_path = write_prediction_outputs(bundle, predict_output_dir)
    print(
        json.dumps(
            {
                "summary_path": str(summary_path),
                "timeseries_path": str(timeseries_path),
                "summary": bundle.summary,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
