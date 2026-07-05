# 批量回放 M100 任务级输入，评估部署口径下的任务误差。
"""执行 M100 任务回放评估。"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / ".vendor"
SRC = ROOT / "src"
for path in (VENDOR, SRC):
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))

import numpy as np
import pandas as pd

from uav_energy_engine.evaluate import save_summary


def _resolve_path(value: str) -> Path:
    """解析相对项目根目录的路径。"""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="执行 M100 任务级回放评估。")
    parser.add_argument(
        "--manifest",
        default="outputs/m100_task_replay_inputs/manifest.csv",
        help="M100 任务清单",
    )
    parser.add_argument(
        "--model",
        default="outputs/deployment_model_default_smoke",
        help="模型文件路径，或包含 model.pkl 的模型目录",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/m100_task_replay_benchmark",
        help="评估输出目录",
    )
    parser.add_argument("--limit", type=int, default=None, help="可选：限制回放任务数")
    return parser.parse_args()


def _relative_error_pct(predicted: float, actual: float) -> float:
    """计算相对误差百分比。"""

    if not np.isfinite(actual) or abs(actual) <= 1e-9:
        return float("nan")
    return (predicted - actual) / actual * 100.0


def main() -> None:
    """执行回放评估。"""

    args = parse_args()
    manifest_path = _resolve_path(args.manifest)
    output_dir = _resolve_path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    replay_dir = output_dir / "replays"
    replay_dir.mkdir(parents=True, exist_ok=True)

    manifest = pd.read_csv(manifest_path)
    if args.limit is not None:
        manifest = manifest.head(int(args.limit)).copy()

    rows = []
    for row in manifest.to_dict(orient="records"):
        flight_id = int(row["flight"])
        task_mode = str(row.get("task_mode", "unknown"))
        flight_output_dir = replay_dir / f"flight_{flight_id}__{task_mode}"
        cmd = [
            "python3",
            str((ROOT / "scripts" / "run_task_predict.py").resolve()),
            "--model",
            str(_resolve_path(args.model)),
            "--task-config",
            str(row["task_config"]),
            "--weather-frame",
            str(row["weather_frame"]),
            "--output-dir",
            str(flight_output_dir),
        ]
        env = dict(os.environ)
        env["PYTHONPATH"] = f"{VENDOR}:{SRC}"
        subprocess.run(cmd, check=True, cwd=str(ROOT), env=env, stdout=subprocess.DEVNULL)
        summary = json.loads((flight_output_dir / "summary.json").read_text(encoding="utf-8"))
        predicted_total_energy_wh = float(summary["predicted_total_energy_wh"])
        actual_total_energy_wh = float(row["actual_total_energy_wh"])
        actual_total_distance_km = float(row["actual_total_distance_m"]) / 1000.0
        predicted_range_km = float(summary["predicted_range_km"])
        actual_wh_per_km = actual_total_energy_wh / actual_total_distance_km if actual_total_distance_km > 1e-9 else float("nan")
        actual_range_km = 130.0 / actual_wh_per_km if np.isfinite(actual_wh_per_km) and actual_wh_per_km > 1e-9 else float("nan")
        rows.append(
            {
                "flight": flight_id,
                "task_mode": task_mode,
                "route": row["route"],
                "segment_count": int(row["segment_count"]),
                "actual_total_distance_km": actual_total_distance_km,
                "predicted_total_energy_wh": predicted_total_energy_wh,
                "actual_total_energy_wh": actual_total_energy_wh,
                "energy_error_wh": predicted_total_energy_wh - actual_total_energy_wh,
                "abs_energy_error_wh": abs(predicted_total_energy_wh - actual_total_energy_wh),
                "energy_error_pct": _relative_error_pct(predicted_total_energy_wh, actual_total_energy_wh),
                "predicted_range_km": predicted_range_km,
                "actual_range_km": actual_range_km,
                "range_error_km": predicted_range_km - actual_range_km if np.isfinite(actual_range_km) else float("nan"),
                "range_error_pct": _relative_error_pct(predicted_range_km, actual_range_km),
                "risk_alert_count": int(len(summary.get("risk_alerts") or [])),
                "replay_summary": str((flight_output_dir / "summary.json").resolve()),
                "replay_timeseries": str((flight_output_dir / "timeseries.csv").resolve()),
            }
        )

    result = pd.DataFrame(rows)
    result.to_csv(output_dir / "task_replay_errors.csv", index=False)
    summary = {
        "manifest": str(manifest_path.resolve()),
        "model": str(_resolve_path(args.model).resolve()),
        "row_count": int(len(result.index)),
        "mean_abs_energy_error_wh": float(pd.to_numeric(result["abs_energy_error_wh"], errors="coerce").mean()),
        "mean_abs_energy_error_pct": float(pd.to_numeric(result["energy_error_pct"], errors="coerce").abs().mean()),
        "p95_abs_energy_error_pct": float(pd.to_numeric(result["energy_error_pct"], errors="coerce").abs().quantile(0.95)),
        "mean_abs_range_error_pct": float(pd.to_numeric(result["range_error_pct"], errors="coerce").abs().mean()),
        "p95_abs_range_error_pct": float(pd.to_numeric(result["range_error_pct"], errors="coerce").abs().quantile(0.95)),
        "outputs": {
            "task_replay_errors": str((output_dir / "task_replay_errors.csv").resolve()),
            "summary": str((output_dir / "summary.json").resolve()),
        },
    }
    save_summary(summary, output_dir / "summary.json")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
