#!/usr/bin/env python3
# 中文说明：该脚本批量运行真实 M2 样本的 SNPE CPU/GPU 对齐实验，并生成可复现实验的 CSV/JSON 汇总。

import argparse
import csv
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def build_parser() -> argparse.ArgumentParser:
    root = repo_root()
    parser = argparse.ArgumentParser(description="批量复现 SNPE GPU 真实样本部署实验")
    parser.add_argument("--features-dir", default=str(root / "modules/radio-map-estimation-workbench/modules/m2/runs/datas/features/v1_base_256_k1_landuse3"), help="M2 特征目录")
    parser.add_argument("--model", default=str(root / "modules/fiboaistack_229_env/outputs/radio_map_liteunet.dlc"), help="DLC 模型路径")
    parser.add_argument("--split", default="test", help="样本 split，默认 test")
    parser.add_argument("--limit", type=int, default=20, help="最多运行样本数")
    parser.add_argument("--warmup", type=int, default=1, help="每个 runtime 的预热次数")
    parser.add_argument("--repeat", type=int, default=1, help="每个 runtime 的计时次数")
    parser.add_argument("--mode", type=int, default=5, help="Fibo AI Stack profile/mode")
    parser.add_argument("--output-dir", default=str(root / "modules/radio_map_qcs6490_deploy/outputs/snpe_gpu_repro_test20"), help="输出目录")
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


def run_alignment(args: argparse.Namespace, sample_id: str, sample_output_dir: Path) -> Dict[str, object]:
    script = Path(__file__).resolve().parent / "align_snpe_outputs_with_real_sample.py"
    cmd = [
        sys.executable,
        str(script),
        "--sample-id",
        sample_id,
        "--features-dir",
        args.features_dir,
        "--model",
        args.model,
        "--output-dir",
        str(sample_output_dir),
        "--mode",
        str(args.mode),
        "--warmup",
        str(args.warmup),
        "--repeat",
        str(args.repeat),
    ]
    proc = subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result_path = sample_output_dir / f"{sample_id}_snpe_cpu_gpu_alignment.json"
    if proc.returncode != 0 or not result_path.is_file():
        return {
            "sample_id": sample_id,
            "ok": False,
            "returncode": proc.returncode,
            "stdout_tail": proc.stdout[-2000:],
            "stderr_tail": proc.stderr[-2000:],
        }
    result = json.loads(result_path.read_text(encoding="utf-8"))
    result["ok"] = True
    return result


def flatten_row(item: Dict[str, object]) -> Dict[str, object]:
    if not item.get("ok"):
        return {
            "sample_id": item.get("sample_id"),
            "ok": False,
            "error": item.get("stderr_tail") or item.get("stdout_tail") or item.get("returncode"),
        }
    metrics = item.get("real_sample_metrics") or {}
    diff = item.get("diff") or {}
    cpu = item.get("cpu") or {}
    gpu = item.get("gpu") or {}
    cpu_vs_label = metrics.get("cpu_vs_label") or {}
    gpu_vs_label = metrics.get("gpu_vs_label") or {}
    cpu_gpu_dbm = metrics.get("cpu_gpu_dbm_diff") or {}
    return {
        "sample_id": item.get("sample_id"),
        "ok": True,
        "cpu_execute_ms_avg": cpu.get("execute_ms_avg"),
        "gpu_execute_ms_avg": gpu.get("execute_ms_avg"),
        "speedup_cpu_over_gpu": (float(cpu["execute_ms_avg"]) / float(gpu["execute_ms_avg"])) if cpu.get("execute_ms_avg") and gpu.get("execute_ms_avg") else None,
        "norm_cpu_gpu_rmse": diff.get("rmse"),
        "norm_cpu_gpu_abs_diff_mean": diff.get("abs_diff_mean"),
        "norm_cpu_gpu_abs_diff_max": diff.get("abs_diff_max"),
        "dbm_cpu_gpu_rmse": cpu_gpu_dbm.get("rmse_db"),
        "dbm_cpu_gpu_abs_diff_mean": cpu_gpu_dbm.get("abs_diff_mean_db"),
        "dbm_cpu_gpu_abs_diff_max": cpu_gpu_dbm.get("abs_diff_max_db"),
        "gpu_rmse_db": gpu_vs_label.get("rmse_db"),
        "gpu_mae_db": gpu_vs_label.get("mae_db"),
        "gpu_psnr_db": gpu_vs_label.get("psnr_db"),
        "cpu_rmse_db": cpu_vs_label.get("rmse_db"),
        "cpu_mae_db": cpu_vs_label.get("mae_db"),
        "cpu_psnr_db": cpu_vs_label.get("psnr_db"),
    }


def summarize(rows: List[Dict[str, object]], args: argparse.Namespace) -> Dict[str, object]:
    ok_rows = [row for row in rows if row.get("ok")]
    def mean_of(key: str):
        vals = [float(row[key]) for row in ok_rows if row.get(key) is not None]
        return statistics.mean(vals) if vals else None

    return {
        "features_dir": str(Path(args.features_dir).resolve()),
        "model": str(Path(args.model).resolve()),
        "split": args.split,
        "limit": args.limit,
        "warmup": args.warmup,
        "repeat": args.repeat,
        "mode": args.mode,
        "num_samples": len(rows),
        "num_ok": len(ok_rows),
        "num_failed": len(rows) - len(ok_rows),
        "mean_cpu_execute_ms": mean_of("cpu_execute_ms_avg"),
        "mean_gpu_execute_ms": mean_of("gpu_execute_ms_avg"),
        "mean_speedup_cpu_over_gpu": mean_of("speedup_cpu_over_gpu"),
        "mean_dbm_cpu_gpu_rmse": mean_of("dbm_cpu_gpu_rmse"),
        "mean_dbm_cpu_gpu_abs_diff_mean": mean_of("dbm_cpu_gpu_abs_diff_mean"),
        "mean_gpu_rmse_db": mean_of("gpu_rmse_db"),
        "mean_gpu_mae_db": mean_of("gpu_mae_db"),
    }


def main() -> int:
    args = build_parser().parse_args()
    output_dir = Path(args.output_dir)
    samples_dir = output_dir / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)
    sample_ids = load_sample_ids(Path(args.features_dir), args.split, args.limit)

    started = time.time()
    rows: List[Dict[str, object]] = []
    raw_results: List[Dict[str, object]] = []
    for idx, sample_id in enumerate(sample_ids, start=1):
        print(f"[{idx}/{len(sample_ids)}] 运行样本 {sample_id}", flush=True)
        result = run_alignment(args, sample_id, samples_dir)
        raw_results.append(result)
        rows.append(flatten_row(result))

    fieldnames = list(rows[0].keys())
    csv_path = output_dir / "summary.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize(rows, args)
    summary["elapsed_sec"] = time.time() - started
    summary["summary_csv"] = str(csv_path.resolve())
    summary["raw_results_json"] = str((output_dir / "raw_results.json").resolve())
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "raw_results.json").write_text(json.dumps(raw_results, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if summary["num_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
