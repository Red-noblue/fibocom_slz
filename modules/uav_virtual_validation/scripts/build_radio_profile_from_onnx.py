#!/usr/bin/env python3
"""中文说明：使用 ONNXRuntime 从 UAV 航线输入重建无线电画像与前端热力点云资产。"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MODEL = REPO_ROOT / "modules/fiboaistack_229_env/inputs/qnn_htp_rewrite/radio_map_liteunet_pad_constant.onnx"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从 ONNX 模型重建 UAV 航线无线电画像。")
    parser.add_argument("--input-dir", required=True, help="包含 manifest.json 和样本 npz 的输入目录。")
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="ONNX 模型路径。")
    parser.add_argument("--manifest", default="manifest.json", help="输入 manifest 文件名。")
    parser.add_argument("--profile-name", default="route_radio_profile.json", help="画像 JSON 输出文件名。")
    parser.add_argument("--predictions-name", default="predictions.npz", help="完整预测矩阵输出文件名。")
    parser.add_argument("--heatmap-dir", default="heatmaps", help="前端热力点云输出子目录。")
    parser.add_argument("--grid-steps", default="32,16,8,4,2", help="点云抽样步长，逗号分隔。")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def compute_radio_score(pred_center_dbm: float, coverage_ratio: float, weak_ratio: float) -> int:
    coverage_score = coverage_ratio * 100.0
    weak_score = (1.0 - weak_ratio) * 100.0
    center_score = clamp((pred_center_dbm + 110.0) / 25.0, 0.0, 1.0) * 100.0
    score = 0.45 * coverage_score + 0.35 * weak_score + 0.20 * center_score
    return int(round(clamp(score, 0.0, 100.0)))


def recommendation(score: int, pred_center_dbm: float, coverage_ratio: float, weak_ratio: float) -> str:
    if score >= 80 and coverage_ratio >= 0.70 and weak_ratio <= 0.10:
        return "高码率上传"
    if score >= 65 and coverage_ratio >= 0.45:
        return "常规上传"
    if score >= 45:
        return "降码率保守传输"
    if pred_center_dbm > -95.0:
        return "中心点可通信，建议低码率并监控"
    return "弱覆盖，建议切换链路或调整航线"


def meters_to_latlon(origin_lat: float, origin_lon: float, north_m: float, east_m: float) -> tuple[float, float]:
    earth_radius_m = 6_371_000.0
    lat = origin_lat + math.degrees(north_m / earth_radius_m)
    lon = origin_lon + math.degrees(east_m / (earth_radius_m * math.cos(math.radians(origin_lat))))
    return lat, lon


def run_model(session: ort.InferenceSession, sample_path: Path) -> tuple[np.ndarray, np.ndarray]:
    with np.load(sample_path) as data:
        x_chw = data["X"].astype(np.float32)
        valid_mask = data["valid_mask"].astype(bool)
    if x_chw.shape != (7, 256, 256):
        raise ValueError(f"{sample_path.name} 的 X shape 应为 (7,256,256)，实际为 {x_chw.shape}")
    x = x_chw[None, :, :, :]
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    pred = session.run([output_name], {input_name: x})[0]
    return pred.reshape(256, 256).astype(np.float32), valid_mask


def profile_row(sample: dict[str, Any], pred_dbm: np.ndarray, valid_mask: np.ndarray, elapsed_ms: float) -> dict[str, Any]:
    valid_values = pred_dbm[valid_mask]
    tx_x, tx_y = [int(v) for v in sample.get("tx_pixel_xy", [128, 128])]
    tx_x = int(clamp(tx_x, 0, 255))
    tx_y = int(clamp(tx_y, 0, 255))
    pred_center_dbm = float(pred_dbm[tx_y, tx_x])
    coverage_ratio = float(np.mean(valid_values > -90.0))
    weak_ratio = float(np.mean(valid_values < -100.0))
    score = compute_radio_score(pred_center_dbm, coverage_ratio, weak_ratio)
    return {
        "sample_id": str(sample["sample_id"]),
        "lon": float(sample["lon"]),
        "lat": float(sample["lat"]),
        "altitude_m": float(sample["altitude_m"]),
        "distance_along_route_m": float(sample["distance_along_route_m"]),
        "pred_center_dbm": pred_center_dbm,
        "coverage_ratio_gt_minus90": coverage_ratio,
        "weak_ratio_lt_minus100": weak_ratio,
        "radio_score": score,
        "recommendation": recommendation(score, pred_center_dbm, coverage_ratio, weak_ratio),
        "tx_pixel_xy": [tx_x, tx_y],
        "pred_mean_dbm": float(valid_values.mean()),
        "pred_min_dbm": float(valid_values.min()),
        "pred_max_dbm": float(valid_values.max()),
        "pred_p10_dbm": float(np.percentile(valid_values, 10)),
        "pred_p50_dbm": float(np.percentile(valid_values, 50)),
        "pred_p90_dbm": float(np.percentile(valid_values, 90)),
        "execute_ms_avg": elapsed_ms,
        "fetch_ms_avg": 0.0,
    }


def build_point_cloud(
    manifest: dict[str, Any],
    predictions: dict[str, np.ndarray],
    rows: list[dict[str, Any]],
    step: int,
) -> dict[str, Any]:
    sampling = manifest.get("sampling") or {}
    pixel_size_m = float(sampling.get("pixel_size_m") or 1.0)
    points: list[dict[str, Any]] = []
    all_values = np.concatenate([pred.reshape(-1) for pred in predictions.values()])
    min_dbm = float(np.percentile(all_values, 1))
    max_dbm = float(np.percentile(all_values, 99))
    denom = max(1e-6, max_dbm - min_dbm)
    row_by_id = {row["sample_id"]: row for row in rows}
    for sample in manifest.get("samples") or []:
        sample_id = str(sample["sample_id"])
        pred = predictions[sample_id]
        row = row_by_id[sample_id]
        origin_lat = float(sample["lat"])
        origin_lon = float(sample["lon"])
        altitude = float(sample["altitude_m"]) + 8.0
        for y in range(0, 256, step):
            north_m = (128 - y) * pixel_size_m
            for x in range(0, 256, step):
                east_m = (x - 128) * pixel_size_m
                lat, lon = meters_to_latlon(origin_lat, origin_lon, north_m, east_m)
                dbm = float(pred[y, x])
                points.append({
                    "sample_id": sample_id,
                    "lon": round(lon, 7),
                    "lat": round(lat, 7),
                    "altitude_m": round(altitude, 2),
                    "dbm": round(dbm, 3),
                    "norm": round(clamp((dbm - min_dbm) / denom, 0.0, 1.0), 5),
                    "distance_along_route_m": row["distance_along_route_m"],
                })
    return {
        "schema": "uav_route_radio_point_cloud_v1",
        "city": manifest.get("city"),
        "unit": "dBm",
        "sampling": {
            "grid_step_px": step,
            "points_per_sample_max": (256 // step) * (256 // step),
            "pixel_size_m": pixel_size_m,
            "source_grid": [256, 256],
        },
        "normalization": {
            "method": "global_p01_p99",
            "min_dbm": min_dbm,
            "max_dbm": max_dbm,
        },
        "points": points,
    }


def main() -> int:
    args = parse_args()
    input_dir = Path(args.input_dir)
    manifest = read_json(input_dir / args.manifest)
    y_norm = manifest.get("feature_contract", {}).get("label_y_dbm", {})
    y_mean = float(y_norm.get("mean", 0.0))
    y_std = float(y_norm.get("std", 1.0))
    session = ort.InferenceSession(str(Path(args.model)), providers=["CPUExecutionProvider"])

    predictions: dict[str, np.ndarray] = {}
    rows: list[dict[str, Any]] = []
    started = time.time()
    for sample in manifest.get("samples") or []:
        sample_id = str(sample["sample_id"])
        t0 = time.perf_counter()
        pred_norm, valid_mask = run_model(session, input_dir / str(sample["npz"]))
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        pred_dbm = (pred_norm * y_std + y_mean).astype(np.float32)
        predictions[sample_id] = pred_dbm
        rows.append(profile_row(sample, pred_dbm, valid_mask, elapsed_ms))

    np.savez_compressed(input_dir / args.predictions_name, **predictions)
    profile = {
        "schema": "uav_route_radio_profile_v1",
        "input_manifest": args.manifest,
        "unit": "dBm",
        "normalized": False,
        "sampling": manifest.get("sampling"),
        "point_scale_test": manifest.get("point_scale_test"),
        "building_height_filter": manifest.get("building_height_filter"),
        "road_channel_policy": manifest.get("road_channel_policy"),
        "label_norm": {"mean": y_mean, "std": y_std},
        "model": str(Path(args.model).resolve()),
        "framework": "onnxruntime",
        "runtime": "CPU",
        "prediction_file": args.predictions_name,
        "score_method": "round(clamp(0.45*coverage_gt_-90 + 0.35*(1-weak_lt_-100) + 0.20*center_strength, 0, 100))",
        "num_samples": len(rows),
        "elapsed_sec": time.time() - started,
        "samples": rows,
    }
    write_json(profile, input_dir / args.profile_name)

    heatmap_dir = input_dir / args.heatmap_dir
    steps = [int(item.strip()) for item in args.grid_steps.split(",") if item.strip()]
    for step in steps:
        cloud = build_point_cloud(manifest, predictions, rows, step)
        write_json(cloud, heatmap_dir / f"radio_point_cloud_step{step}.json")
    write_json({"schema": "uav_route_radio_texture_tiles_v1", "items": []}, heatmap_dir / "texture_tile_index.json")

    print(json.dumps({
        "ok": True,
        "input_dir": str(input_dir),
        "profile": str(input_dir / args.profile_name),
        "predictions": str(input_dir / args.predictions_name),
        "samples": len(rows),
        "heatmap_steps": steps,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
