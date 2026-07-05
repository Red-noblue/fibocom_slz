from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_virtual_validation.artifacts.io import read_csv, write_csv, write_json
from uav_virtual_validation.validation.metrics import compare_energy_curves


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="对比预测能耗曲线与虚拟仿真能耗曲线。")
    parser.add_argument("--prediction-timeseries", required=True)
    parser.add_argument("--sim-timeseries", required=True)
    parser.add_argument("--output-dir", default=str(ROOT / "outputs/validation"))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    pred_rows = read_csv(args.prediction_timeseries)
    sim_rows = read_csv(args.sim_timeseries)
    result = compare_energy_curves(pred_rows, sim_rows)
    out = Path(args.output_dir)
    write_json(result["metrics"], out / "validation_metrics.json")
    write_csv(result["comparison"], out / "validation_comparison.csv")
    print(f"validation metrics: {out / 'validation_metrics.json'}")
    print(f"validation comparison: {out / 'validation_comparison.csv'}")
