# 训练天气驱动能耗模型的命令行入口，支持按日期等分组切分。
"""训练天气驱动能耗模型的命令行入口。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / ".vendor"
SRC = ROOT / "src"
if VENDOR.exists() and str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_energy_engine.config import load_config
from uav_energy_engine.model import SUPPORTED_METHODS, train_energy_model, train_target_suite


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="训练天气驱动无人机能耗模型。")
    parser.add_argument("--features", default="outputs/features.csv", help="训练样本 CSV")
    parser.add_argument("--model-out", default="outputs/model.pkl", help="模型输出路径")
    parser.add_argument("--metrics-out", default="outputs/metrics.json", help="指标输出路径")
    parser.add_argument(
        "--config",
        default=None,
        help="可选模型配置文件，若提供则从其中读取 target/features/candidate_methods",
    )
    parser.add_argument(
        "--method",
        default="linear_residual_gb",
        choices=SUPPORTED_METHODS,
        help="单模型训练方法",
    )
    parser.add_argument("--target", default="energy_wh_per_km", help="单模型训练目标列")
    parser.add_argument(
        "--suite",
        action="store_true",
        help="按配置中的 candidate_methods 和 targets 训练整套候选模型",
    )
    parser.add_argument("--group-col", default=None, help="可选分组列，例如 date")
    parser.add_argument("--random-state", type=int, default=42, help="随机种子")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    cfg = load_config(args.config) if args.config else {}
    feature_cols = cfg.get("features")
    targets = cfg.get("targets")
    candidate_methods = cfg.get("candidate_methods")
    method = str(cfg.get("method", args.method))
    target = str(cfg.get("target", args.target))
    test_size = float(cfg.get("test_size", 0.2))
    group_col = cfg.get("group_col", args.group_col)

    if args.suite:
        train_target_suite(
            features_csv=args.features,
            model_dir=args.model_out,
            metrics_out=args.metrics_out,
            methods=candidate_methods or [method],
            targets=targets or [target],
            random_state=args.random_state,
            feature_cols=feature_cols,
            test_size=test_size,
            group_col=group_col,
        )
    else:
        train_energy_model(
            features_csv=args.features,
            model_out=args.model_out,
            metrics_out=args.metrics_out,
            random_state=args.random_state,
            method=method,
            target=target,
            feature_cols=feature_cols,
            test_size=test_size,
            group_col=group_col,
        )
