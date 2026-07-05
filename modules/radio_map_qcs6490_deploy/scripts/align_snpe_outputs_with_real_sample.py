#!/usr/bin/env python3
# 中文说明：该脚本使用真实 M2 特征样本分别执行 SNPE CPU/GPU 推理，并统计二者输出差异，用于确认 GPU 路线的数值对齐情况。

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def build_parser() -> argparse.ArgumentParser:
    root = repo_root()
    parser = argparse.ArgumentParser(description="对齐真实样本上的 SNPE CPU/GPU 输出")
    parser.add_argument("--sample-id", default="166_k0", help="样本 ID")
    parser.add_argument("--features-dir", default=str(root / "modules/radio-map-estimation-workbench/modules/m2/runs/datas/features/v1_base_256_k1_landuse3"), help="M2 特征目录")
    parser.add_argument("--model", default=str(root / "modules/fiboaistack_229_env/outputs/radio_map_liteunet.dlc"), help="DLC 模型路径")
    parser.add_argument("--output-dir", default=str(root / "modules/radio_map_qcs6490_deploy/outputs/snpe_alignment"), help="输出目录")
    parser.add_argument("--mode", type=int, default=5, help="Fibo AI Stack profile/mode")
    parser.add_argument("--warmup", type=int, default=1, help="预热次数")
    parser.add_argument("--repeat", type=int, default=3, help="计时推理次数")
    return parser


def run_one(args: argparse.Namespace, runtime: str, output_dir: Path) -> Dict[str, object]:
    script = Path(__file__).resolve().parent / "run_snpe_gpu_inference.py"
    cmd = [
        sys.executable,
        str(script),
        "--model",
        args.model,
        "--features-dir",
        args.features_dir,
        "--sample-id",
        args.sample_id,
        "--runtime",
        runtime,
        "--mode",
        str(args.mode),
        "--warmup",
        str(args.warmup),
        "--repeat",
        str(args.repeat),
        "--output-dir",
        str(output_dir),
    ]
    proc = subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(f"{runtime} 推理失败，returncode={proc.returncode}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    summary_path = output_dir / f"{args.sample_id}_{runtime.lower()}_snpe_summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"{runtime} 推理完成但未找到 summary：{summary_path}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
    return json.loads(summary_path.read_text(encoding="utf-8"))


def diff_stats(cpu_path: Path, gpu_path: Path) -> Dict[str, object]:
    cpu = np.load(cpu_path).astype(np.float32)
    gpu = np.load(gpu_path).astype(np.float32)
    if cpu.shape != gpu.shape:
        raise ValueError(f"CPU/GPU 输出形状不一致：{cpu.shape} vs {gpu.shape}")
    diff = gpu - cpu
    abs_diff = np.abs(diff)
    return {
        "shape": list(cpu.shape),
        "cpu_min": float(cpu.min()),
        "cpu_max": float(cpu.max()),
        "cpu_mean": float(cpu.mean()),
        "gpu_min": float(gpu.min()),
        "gpu_max": float(gpu.max()),
        "gpu_mean": float(gpu.mean()),
        "diff_mean": float(diff.mean()),
        "abs_diff_mean": float(abs_diff.mean()),
        "abs_diff_max": float(abs_diff.max()),
        "rmse": float(np.sqrt(np.mean(diff * diff))),
    }


def load_label_norm(features_dir: Path) -> Optional[Tuple[float, float]]:
    stats_path = features_dir / "stats.json"
    if not stats_path.is_file():
        return None
    obj = json.loads(stats_path.read_text(encoding="utf-8"))
    ystats = obj.get("label_y_dbm") or {}
    if "mean" not in ystats or "std" not in ystats:
        return None
    std = float(ystats["std"])
    if std <= 0:
        return None
    return float(ystats["mean"]), std


def masked_metrics(pred_dbm: np.ndarray, y_dbm: np.ndarray, valid_mask: np.ndarray) -> Dict[str, object]:
    mask = valid_mask.astype(bool)
    if pred_dbm.shape != y_dbm.shape:
        raise ValueError(f"预测和标签形状不一致：{pred_dbm.shape} vs {y_dbm.shape}")
    if mask.shape != pred_dbm.shape:
        raise ValueError(f"mask 和预测形状不一致：{mask.shape} vs {pred_dbm.shape}")
    diff = pred_dbm[mask] - y_dbm[mask]
    mse = float(np.mean(diff * diff))
    mae = float(np.mean(np.abs(diff)))
    rmse = float(np.sqrt(mse))
    peak = float(np.max(y_dbm[mask]) - np.min(y_dbm[mask]))
    psnr = float("inf") if mse == 0 else float(20.0 * np.log10(peak / np.sqrt(mse))) if peak > 0 else float("nan")
    return {
        "valid_pixels": int(mask.sum()),
        "rmse_db": rmse,
        "mae_db": mae,
        "psnr_db": psnr,
        "pred_dbm_min": float(pred_dbm[mask].min()),
        "pred_dbm_max": float(pred_dbm[mask].max()),
        "pred_dbm_mean": float(pred_dbm[mask].mean()),
        "label_dbm_min": float(y_dbm[mask].min()),
        "label_dbm_max": float(y_dbm[mask].max()),
        "label_dbm_mean": float(y_dbm[mask].mean()),
    }


def real_sample_metrics(args: argparse.Namespace, cpu_path: Path, gpu_path: Path) -> Dict[str, object]:
    features_dir = Path(args.features_dir)
    sample_path = features_dir / f"{args.sample_id}.npz"
    label_norm = load_label_norm(features_dir)
    if label_norm is None:
        return {"ok": False, "reason": f"未找到可用标签归一化参数：{features_dir / 'stats.json'}"}
    y_mean, y_std = label_norm
    with np.load(sample_path) as data:
        y = data["y"].astype(np.float32).reshape(256, 256)
        valid_mask = data["valid_mask"].astype(bool).reshape(256, 256)

    cpu_norm = np.load(cpu_path).astype(np.float32).reshape(256, 256)
    gpu_norm = np.load(gpu_path).astype(np.float32).reshape(256, 256)
    cpu_dbm = cpu_norm * y_std + y_mean
    gpu_dbm = gpu_norm * y_std + y_mean

    return {
        "ok": True,
        "label_norm": {"type": "standard", "y_mean": y_mean, "y_std": y_std},
        "cpu_vs_label": masked_metrics(cpu_dbm, y, valid_mask),
        "gpu_vs_label": masked_metrics(gpu_dbm, y, valid_mask),
        "cpu_gpu_dbm_diff": {
            "abs_diff_mean_db": float(np.abs(gpu_dbm - cpu_dbm).mean()),
            "abs_diff_max_db": float(np.abs(gpu_dbm - cpu_dbm).max()),
            "rmse_db": float(np.sqrt(np.mean((gpu_dbm - cpu_dbm) ** 2))),
        },
    }


def main() -> int:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cpu_summary = run_one(args, "CPU", output_dir)
    gpu_summary = run_one(args, "GPU", output_dir)
    cpu_path = Path(cpu_summary["output_npy"])
    gpu_path = Path(gpu_summary["output_npy"])
    summary = {
        "sample_id": args.sample_id,
        "cpu": cpu_summary,
        "gpu": gpu_summary,
        "diff": diff_stats(cpu_path, gpu_path),
        "real_sample_metrics": real_sample_metrics(args, cpu_path, gpu_path),
    }
    out_path = output_dir / f"{args.sample_id}_snpe_cpu_gpu_alignment.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
