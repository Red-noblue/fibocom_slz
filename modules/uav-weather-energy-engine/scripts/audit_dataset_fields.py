# 审计无人机数据集字段语义，输出机器可读风险报告。
"""审计无人机数据集字段语义。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / ".vendor"
SRC = ROOT / "src"
if VENDOR.exists() and str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_energy_engine.field_semantics import audit_csv_semantics, summarize_audits


DEFAULT_INPUTS = [
    ("m100_raw", "m100", ROOT / "data/raw/m100/flights.csv"),
    ("m100_historical", "m100", ROOT / "data/processed/flights_with_historical_weather_100m.csv"),
    ("wemuav_flights", "wemuav", ROOT / "outputs/wemuav_dataset/wemuav_flights.csv"),
    ("wemuav_segments", "wemuav", ROOT / "outputs/wemuav_dataset/wemuav_segments_60s.csv"),
]


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""

    parser = argparse.ArgumentParser(description="审计无人机数据集字段语义。")
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        help="输入项，格式为 label:dataset:path。例如 m100_raw:m100:data/raw/m100/flights.csv",
    )
    parser.add_argument("--output", default="outputs/field_semantics_audit/summary.json", help="审计报告 JSON 输出路径")
    parser.add_argument("--skip-missing", action="store_true", help="跳过不存在的默认输入")
    return parser.parse_args()


def _resolve_path(value: str) -> Path:
    """解析相对项目根目录的路径。"""

    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def _parse_input_item(value: str) -> tuple[str, str, Path]:
    """解析单个输入项。"""

    parts = value.split(":", 2)
    if len(parts) != 3:
        raise ValueError("--input 必须使用 label:dataset:path 格式。")
    label, dataset, path_text = parts
    return label, dataset, _resolve_path(path_text)


if __name__ == "__main__":
    args = parse_args()
    inputs = [_parse_input_item(item) for item in args.input] if args.input else DEFAULT_INPUTS
    audits = []
    for label, dataset, path in inputs:
        if not path.exists() and args.skip_missing:
            continue
        audits.append(audit_csv_semantics(path, dataset=dataset, label=label))

    summary = summarize_audits(audits)
    output_path = _resolve_path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(output_path),
                "audits": len(audits),
                "warning_count": summary["warning_count"],
                "high_risk_count": summary["high_risk_count"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
