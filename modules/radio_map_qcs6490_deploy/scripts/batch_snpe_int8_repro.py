#!/usr/bin/env python3
# 中文说明：该脚本批量运行真实 M2 test 样本的 FP32 GPU、INT8 GPU 和 INT8 DSP 推理，并汇总速度、标签误差和后端输出差异。

import argparse
import csv
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_features_dir() -> Path:
    return repo_root() / "modules/radio-map-estimation-workbench/modules/m2/runs/datas/features/v1_base_256_k1_landuse3"


def default_fp32_model() -> Path:
    return repo_root() / "modules/fiboaistack_229_env/outputs/radio_map_liteunet.dlc"


def default_int8_model() -> Path:
    return repo_root() / "modules/fiboaistack_229_env/outputs/snpe_quant_qemu82_full_20260703_075537/radio_map_liteunet_quantized.dlc"


def build_parser() -> argparse.ArgumentParser:
    root = repo_root()
    parser = argparse.ArgumentParser(description="批量复现 SNPE INT8 GPU/DSP 部署实验")
    parser.add_argument("--features-dir", default=str(default_features_dir()), help="M2 特征目录")
    parser.add_argument("--fp32-model", default=str(default_fp32_model()), help="FP32 DLC 模型路径")
    parser.add_argument("--int8-model", default=str(default_int8_model()), help="INT8 DLC 模型路径")
    parser.add_argument("--split", default="test", help="样本 split，默认 test")
    parser.add_argument("--limit", type=int, default=50, help="最多运行样本数")
    parser.add_argument("--warmup", type=int, default=1, help="每个后端的预热次数")
    parser.add_argument("--repeat", type=int, default=1, help="每个后端的计时次数")
    parser.add_argument("--mode", type=int, default=5, help="Fibo AI Stack profile/mode")
    parser.add_argument(
        "--cases",
        default="fp32_gpu,int8_gpu,int8_dsp",
        help="逗号分隔的实验项，可选 fp32_gpu,int8_gpu,int8_dsp",
    )
    parser.add_argument(
        "--output-dir",
        default=str(root / "modules/radio_map_qcs6490_deploy/outputs/int8_repro_test50"),
        help="输出目录",
    )
    return parser


def load_sample_ids(features_dir: Path, split: str, limit: int) -> List[str]:
    samples_csv = features_dir / "samples.csv"
    if not samples_csv.is_file():
        raise FileNotFoundError(f"未找到 samples.csv：{samples_csv}")

    sample_ids: List[str] = []
    with samples_csv.open("r", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("split") != split:
                continue
            sample_id = str(row.get("sample_id") or "").strip()
            if sample_id and (features_dir / f"{sample_id}.npz").is_file():
                sample_ids.append(sample_id)
            if limit > 0 and len(sample_ids) >= limit:
                break
    if not sample_ids:
        raise RuntimeError(f"没有找到 split={split} 的可用样本")
    return sample_ids


def load_label_norm(features_dir: Path) -> Dict[str, float]:
    stats_path = features_dir / "stats.json"
    obj = json.loads(stats_path.read_text(encoding="utf-8"))
    ystats = obj.get("label_y_dbm") or {}
    return {"mean": float(ystats["mean"]), "std": float(ystats["std"])}


def masked_label_metrics(pred_npy: Path, sample_npz: Path, norm: Dict[str, float]) -> Dict[str, float]:
    pred_norm = np.load(pred_npy).astype(np.float32).reshape(256, 256)
    pred_dbm = pred_norm * norm["std"] + norm["mean"]
    with np.load(sample_npz) as data:
        y = data["y"].astype(np.float32).reshape(256, 256)
        mask = data["valid_mask"].astype(bool).reshape(256, 256)
    diff = pred_dbm[mask] - y[mask]
    mse = float(np.mean(diff * diff))
    return {
        "rmse_db": float(np.sqrt(mse)),
        "mae_db": float(np.mean(np.abs(diff))),
        "pred_dbm_mean": float(pred_dbm[mask].mean()),
    }


def diff_metrics(lhs_npy: Path, rhs_npy: Path, norm: Dict[str, float]) -> Dict[str, float]:
    lhs = np.load(lhs_npy).astype(np.float32).reshape(256, 256) * norm["std"] + norm["mean"]
    rhs = np.load(rhs_npy).astype(np.float32).reshape(256, 256) * norm["std"] + norm["mean"]
    diff = rhs - lhs
    abs_diff = np.abs(diff)
    return {
        "rmse_db": float(np.sqrt(np.mean(diff * diff))),
        "mae_db": float(np.mean(abs_diff)),
        "max_abs_db": float(abs_diff.max()),
    }


def mean_of(rows: Iterable[Dict[str, object]], key: str) -> Optional[float]:
    vals = [float(row[key]) for row in rows if row.get(key) is not None]
    return statistics.mean(vals) if vals else None


def run_one(args: argparse.Namespace, sample_id: str, case: str, case_dir: Path) -> Dict[str, object]:
    script = Path(__file__).resolve().parent / "run_snpe_gpu_inference.py"
    runtime = "DSP" if case == "int8_dsp" else "GPU"
    model = args.fp32_model if case == "fp32_gpu" else args.int8_model
    cmd = [
        sys.executable,
        str(script),
        "--model",
        model,
        "--features-dir",
        args.features_dir,
        "--sample-id",
        sample_id,
        "--runtime",
        runtime,
        "--mode",
        str(args.mode),
        "--warmup",
        str(args.warmup),
        "--repeat",
        str(args.repeat),
        "--output-dir",
        str(case_dir),
    ]
    proc = subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout_path = case_dir / f"{sample_id}.{case}.stdout.log"
    stderr_path = case_dir / f"{sample_id}.{case}.stderr.log"
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")
    summary_path = case_dir / f"{sample_id}_{runtime.lower()}_snpe_summary.json"
    if proc.returncode != 0 or not summary_path.is_file():
        return {
            "ok": False,
            "case": case,
            "returncode": proc.returncode,
            "stdout_log": str(stdout_path),
            "stderr_log": str(stderr_path),
        }
    obj = json.loads(summary_path.read_text(encoding="utf-8"))
    obj["ok"] = bool(obj.get("ok"))
    obj["case"] = case
    return obj


def main() -> int:
    args = build_parser().parse_args()
    features_dir = Path(args.features_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cases = [item.strip() for item in args.cases.split(",") if item.strip()]
    allowed_cases = {"fp32_gpu", "int8_gpu", "int8_dsp"}
    unknown = sorted(set(cases) - allowed_cases)
    if unknown:
        raise ValueError(f"未知实验项：{unknown}")

    sample_ids = load_sample_ids(features_dir, args.split, args.limit)
    norm = load_label_norm(features_dir)
    started = time.time()
    rows: List[Dict[str, object]] = []
    raw: Dict[str, Dict[str, Dict[str, object]]] = {}

    for idx, sample_id in enumerate(sample_ids, start=1):
        print(f"[{idx}/{len(sample_ids)}] 运行样本 {sample_id}", flush=True)
        raw[sample_id] = {}
        row: Dict[str, object] = {"sample_id": sample_id, "ok": True}
        npy_by_case: Dict[str, Path] = {}
        for case in cases:
            case_dir = output_dir / case
            case_dir.mkdir(parents=True, exist_ok=True)
            result = run_one(args, sample_id, case, case_dir)
            raw[sample_id][case] = result
            if not result.get("ok"):
                row["ok"] = False
                row[f"{case}_error"] = result.get("stderr_log") or result.get("returncode")
                continue
            output_npy = Path(str(result["output_npy"]))
            npy_by_case[case] = output_npy
            label = masked_label_metrics(output_npy, features_dir / f"{sample_id}.npz", norm)
            row[f"{case}_ms_avg"] = result.get("execute_ms_avg")
            row[f"{case}_ms_min"] = result.get("execute_ms_min")
            row[f"{case}_ms_max"] = result.get("execute_ms_max")
            row[f"{case}_rmse_db"] = label["rmse_db"]
            row[f"{case}_mae_db"] = label["mae_db"]

        if "fp32_gpu" in npy_by_case and "int8_gpu" in npy_by_case:
            diff = diff_metrics(npy_by_case["fp32_gpu"], npy_by_case["int8_gpu"], norm)
            row["int8_gpu_vs_fp32_rmse_db"] = diff["rmse_db"]
            row["int8_gpu_vs_fp32_mae_db"] = diff["mae_db"]
            row["int8_gpu_vs_fp32_max_abs_db"] = diff["max_abs_db"]
        if "fp32_gpu" in npy_by_case and "int8_dsp" in npy_by_case:
            diff = diff_metrics(npy_by_case["fp32_gpu"], npy_by_case["int8_dsp"], norm)
            row["int8_dsp_vs_fp32_rmse_db"] = diff["rmse_db"]
            row["int8_dsp_vs_fp32_mae_db"] = diff["mae_db"]
            row["int8_dsp_vs_fp32_max_abs_db"] = diff["max_abs_db"]
        if "int8_gpu" in npy_by_case and "int8_dsp" in npy_by_case:
            diff = diff_metrics(npy_by_case["int8_gpu"], npy_by_case["int8_dsp"], norm)
            row["int8_dsp_vs_gpu_rmse_db"] = diff["rmse_db"]
            row["int8_dsp_vs_gpu_mae_db"] = diff["mae_db"]
            row["int8_dsp_vs_gpu_max_abs_db"] = diff["max_abs_db"]
        if row.get("int8_gpu_ms_avg") and row.get("int8_dsp_ms_avg"):
            row["int8_dsp_speedup_vs_int8_gpu"] = float(row["int8_gpu_ms_avg"]) / float(row["int8_dsp_ms_avg"])
        if row.get("fp32_gpu_ms_avg") and row.get("int8_dsp_ms_avg"):
            row["int8_dsp_speedup_vs_fp32_gpu"] = float(row["fp32_gpu_ms_avg"]) / float(row["int8_dsp_ms_avg"])
        rows.append(row)

    fieldnames = sorted({key for row in rows for key in row.keys()})
    fieldnames = ["sample_id", "ok"] + [key for key in fieldnames if key not in {"sample_id", "ok"}]
    summary_csv = output_dir / "summary.csv"
    with summary_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    ok_rows = [row for row in rows if row.get("ok")]
    summary = {
        "run_dir": str(output_dir),
        "features_dir": str(features_dir.resolve()),
        "fp32_model": str(Path(args.fp32_model).resolve()),
        "int8_model": str(Path(args.int8_model).resolve()),
        "split": args.split,
        "limit": args.limit,
        "warmup": args.warmup,
        "repeat": args.repeat,
        "mode": args.mode,
        "cases": cases,
        "num_samples": len(rows),
        "num_ok": len(ok_rows),
        "num_failed": len(rows) - len(ok_rows),
        "elapsed_sec": time.time() - started,
        "summary_csv": str(summary_csv.resolve()),
    }
    for key in fieldnames:
        if key not in {"sample_id", "ok"}:
            summary[f"mean_{key}"] = mean_of(ok_rows, key)
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "raw_results.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "sample_ids.txt").write_text("\n".join(sample_ids) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["num_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
