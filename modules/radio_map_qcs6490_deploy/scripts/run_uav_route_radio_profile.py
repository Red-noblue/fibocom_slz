#!/usr/bin/env python3
# 中文说明：该脚本用于把 UAV 航线局部 radio-map 输入批量送入 Fibo AI Stack / SNPE 模型，并输出航线级信号画像 JSON 与完整预测图。

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from fiboaisdk.api_aisdk_py import api_infer_py


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_input_dir() -> Path:
    return repo_root() / "modules/uav_virtual_validation/outputs/radio_route_inputs/wuhan_central_urban_default"


def default_model_path() -> Path:
    return repo_root() / "modules/fiboaistack_229_env/outputs/snpe_quant_qemu82_full_20260703_075537/radio_map_liteunet_quantized.dlc"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="批量运行 UAV 航线 radio-map 输入并生成 route_radio_profile.json")
    parser.add_argument("--input-dir", default=str(default_input_dir()), help="包含 manifest.json 和 route npz 的输入目录")
    parser.add_argument("--manifest", default="manifest.json", help="相对 input-dir 的 manifest 文件名")
    parser.add_argument("--model", default=str(default_model_path()), help="SNPE DLC 模型路径")
    parser.add_argument("--runtime", default="GPU", help="Fibo AI Stack runtime，建议 GPU 或 DSP")
    parser.add_argument("--mode", type=int, default=5, help="Fibo AI Stack profile/mode")
    parser.add_argument("--log-level", default="ERROR", help="Fibo AI Stack 日志级别")
    parser.add_argument("--warmup", type=int, default=1, help="首个样本预热次数")
    parser.add_argument("--repeat", type=int, default=1, help="每个样本计时推理次数，保存最后一次输出")
    parser.add_argument("--input-name", default="input", help="模型输入张量名")
    parser.add_argument("--output-name", default="output", help="模型输出张量名")
    parser.add_argument("--output-dir", default="", help="输出目录，默认写回 input-dir")
    parser.add_argument("--profile-name", default="route_radio_profile.json", help="输出画像 JSON 文件名")
    parser.add_argument("--predictions-name", default="predictions.npz", help="输出完整预测图 npz 文件名")
    parser.add_argument("--write-per-sample-npy", action="store_true", help="同时输出 <sample_id>_pred.npy")
    return parser


def load_manifest(input_dir: Path, manifest_name: str) -> Dict[str, object]:
    manifest_path = input_dir / manifest_name
    if not manifest_path.is_file():
        raise FileNotFoundError(f"未找到 manifest：{manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "uav_route_radio_inputs_v1":
        raise ValueError(f"manifest schema 不匹配：{manifest.get('schema')}")
    return manifest


def load_label_norm(manifest: Dict[str, object]) -> Tuple[float, float]:
    contract = manifest.get("feature_contract") or {}
    label = contract.get("label_y_dbm") or {}
    return float(label["mean"]), float(label["std"])


def load_route_sample(input_dir: Path, sample: Dict[str, object]) -> Tuple[np.ndarray, np.ndarray]:
    npz_name = str(sample["npz"])
    sample_path = input_dir / npz_name
    if not sample_path.is_file():
        raise FileNotFoundError(f"未找到 route 样本：{sample_path}")
    with np.load(sample_path) as data:
        x_chw = data["X"].astype(np.float32)
        valid_mask = data["valid_mask"].astype(bool)
    if x_chw.shape != (7, 256, 256):
        raise ValueError(f"{npz_name} 的 X shape 应为 (7,256,256)，实际为 {x_chw.shape}")
    if valid_mask.shape != (256, 256):
        raise ValueError(f"{npz_name} 的 valid_mask shape 应为 (256,256)，实际为 {valid_mask.shape}")
    x_nhwc = np.transpose(x_chw, (1, 2, 0))[None, ...].astype(np.float32)
    return x_nhwc, valid_mask


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


def init_infer(args: argparse.Namespace) -> api_infer_py.InferAPI:
    infer = api_infer_py.InferAPI()
    params = api_infer_py.InferParams(
        str(Path(args.model).resolve()),
        "qualcomm",
        "snpe",
        args.runtime,
        args.log_level,
        args.mode,
    )
    init_code = infer.Init(params)
    if init_code != 0:
        raise RuntimeError(f"Fibo AI Stack 初始化失败，init_code={init_code}")
    return infer


def execute_sample(
    infer: api_infer_py.InferAPI,
    args: argparse.Namespace,
    x_nhwc: np.ndarray,
) -> Tuple[np.ndarray, List[float], List[float]]:
    feed = {args.input_name: x_nhwc.reshape(-1).astype(np.float32).tolist()}
    execute_ms: List[float] = []
    fetch_ms: List[float] = []
    output = None
    for _ in range(max(args.repeat, 1)):
        t0 = time.perf_counter()
        execute_code = infer.Execute_float(feed)
        execute_ms.append((time.perf_counter() - t0) * 1000.0)
        if execute_code != 0:
            raise RuntimeError(f"Execute_float 失败，execute_code={execute_code}")
        t1 = time.perf_counter()
        outputs = infer.FetchOutputs_float([args.output_name])
        fetch_ms.append((time.perf_counter() - t1) * 1000.0)
        output = np.asarray(outputs[args.output_name], dtype=np.float32)
    if output is None or output.size != 256 * 256:
        raise RuntimeError(f"模型输出应为 65536 个元素，实际为 {None if output is None else output.size}")
    return output.reshape(256, 256), execute_ms, fetch_ms


def make_profile_row(
    sample: Dict[str, object],
    pred_dbm: np.ndarray,
    valid_mask: np.ndarray,
    execute_ms: List[float],
    fetch_ms: List[float],
) -> Dict[str, object]:
    valid_values = pred_dbm[valid_mask]
    tx_pixel_xy = sample.get("tx_pixel_xy") or [128, 128]
    tx_x = int(clamp(float(tx_pixel_xy[0]), 0.0, 255.0))
    tx_y = int(clamp(float(tx_pixel_xy[1]), 0.0, 255.0))
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
        "execute_ms_avg": float(statistics.mean(execute_ms)),
        "fetch_ms_avg": float(statistics.mean(fetch_ms)),
    }


def main() -> int:
    args = build_parser().parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir) if args.output_dir else input_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest(input_dir, args.manifest)
    y_mean, y_std = load_label_norm(manifest)
    samples = list(manifest.get("samples") or [])
    if not samples:
        raise RuntimeError("manifest 中没有 samples")

    infer = init_infer(args)
    predictions: Dict[str, np.ndarray] = {}
    rows: List[Dict[str, object]] = []
    started = time.time()
    try:
        if args.warmup > 0:
            first_x, _ = load_route_sample(input_dir, samples[0])
            feed = {args.input_name: first_x.reshape(-1).astype(np.float32).tolist()}
            for _ in range(args.warmup):
                code = infer.Execute_float(feed)
                if code != 0:
                    raise RuntimeError(f"预热 Execute_float 失败，execute_code={code}")

        for index, sample in enumerate(samples, start=1):
            sample_id = str(sample["sample_id"])
            print(f"[{index}/{len(samples)}] 推理 {sample_id}", flush=True)
            x_nhwc, valid_mask = load_route_sample(input_dir, sample)
            pred_norm, execute_ms, fetch_ms = execute_sample(infer, args, x_nhwc)
            pred_dbm = (pred_norm * y_std + y_mean).astype(np.float32)
            predictions[sample_id] = pred_dbm
            rows.append(make_profile_row(sample, pred_dbm, valid_mask, execute_ms, fetch_ms))
            if args.write_per_sample_npy:
                np.save(output_dir / f"{sample_id}_pred.npy", pred_dbm)
    finally:
        try:
            infer.Release()
        except Exception:
            pass

    predictions_path = output_dir / args.predictions_name
    np.savez_compressed(predictions_path, **predictions)

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
        "framework": "snpe",
        "runtime": args.runtime,
        "mode": args.mode,
        "prediction_file": args.predictions_name,
        "score_method": "round(clamp(0.45*coverage_gt_-90 + 0.35*(1-weak_lt_-100) + 0.20*center_strength, 0, 100))",
        "num_samples": len(rows),
        "elapsed_sec": time.time() - started,
        "samples": rows,
    }
    profile_path = output_dir / args.profile_name
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"profile": str(profile_path.resolve()), "predictions": str(predictions_path.resolve()), "num_samples": len(rows)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
