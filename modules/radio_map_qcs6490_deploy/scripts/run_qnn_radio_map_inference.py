#!/usr/bin/env python3
# 中文说明：该脚本用于运行 radio-map 的 QNN .so 模型，支持真实 M2 样本、QNN CPU/GPU/DSP runtime 和 dBm 误差统计。

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
from fiboaisdk.api_aisdk_py import api_infer_py


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def build_parser() -> argparse.ArgumentParser:
    root = repo_root()
    parser = argparse.ArgumentParser(description="使用 Fibo AI Stack QNN 后端执行 radio-map .so 推理")
    parser.add_argument(
        "--model",
        default=str(
            root
            / "modules/fiboaistack_229_env/outputs/qnn_htp_rewrite_pad_constant_int8/host_build/libs/aarch64-ubuntu-gcc9.4/libradio_map_liteunet_pad_constant_int8_qnn.so"
        ),
        help="QNN .so 模型路径",
    )
    parser.add_argument(
        "--features-dir",
        default=str(root / "modules/radio-map-estimation-workbench/modules/m2/runs/datas/features/v1_base_256_k1_landuse3"),
        help="M2 特征目录",
    )
    parser.add_argument("--sample-id", default="166_k0", help="样本 ID")
    parser.add_argument("--runtime", default="DSP", help="QNN runtime：CPU/GPU/DSP")
    parser.add_argument("--mode", type=int, default=5, help="Fibo AI Stack profile/mode")
    parser.add_argument("--log-level", default="ERROR", help="Fibo AI Stack 日志级别")
    parser.add_argument("--warmup", type=int, default=1, help="预热次数")
    parser.add_argument("--repeat", type=int, default=3, help="计时次数")
    parser.add_argument("--input-name", default="input", help="输入张量名")
    parser.add_argument("--output-name", default="output", help="输出张量名")
    parser.add_argument("--qnn-json", default="", help="QNN converter 生成的 *_qnn_net.json，留空时从 model 路径推断")
    parser.add_argument("--execute-dtype", default="auto", choices=["auto", "float", "uint8"], help="输入执行类型")
    parser.add_argument("--fetch-dtype", default="auto", choices=["auto", "float", "uint8"], help="输出获取类型")
    parser.add_argument(
        "--output-dir",
        default=str(root / "modules/radio_map_qcs6490_deploy/outputs/qnn_radio_map_inference"),
        help="输出目录",
    )
    return parser


def infer_qnn_json_path(model_path: Path) -> Path:
    model_name = model_path.name
    if model_name.startswith("lib"):
        model_name = model_name[3:]
    if model_name.endswith(".so"):
        model_name = model_name[:-3]
    output_root = model_path.parents[3]
    return output_root / f"{model_name}_net.json"


def load_sample(features_dir: Path, sample_id: str) -> Tuple[np.ndarray, Dict[str, object]]:
    sample_path = features_dir / f"{sample_id}.npz"
    if not sample_path.is_file():
        raise FileNotFoundError(f"未找到样本文件：{sample_path}")
    with np.load(sample_path) as data:
        x_chw = data["X"].astype(np.float32)
    x_nhwc = np.transpose(x_chw, (1, 2, 0))[None, ...].astype(np.float32)
    return x_nhwc, {"sample_path": str(sample_path.resolve()), "x_shape_nhwc": list(x_nhwc.shape)}


def load_label_norm(features_dir: Path) -> Tuple[float, float]:
    stats_path = features_dir / "stats.json"
    stats = json.loads(stats_path.read_text(encoding="utf-8"))
    ystats = stats["label_y_dbm"]
    return float(ystats["mean"]), float(ystats["std"])


def label_metrics(features_dir: Path, sample_id: str, pred_norm: np.ndarray) -> Dict[str, object]:
    sample_path = features_dir / f"{sample_id}.npz"
    y_mean, y_std = load_label_norm(features_dir)
    with np.load(sample_path) as data:
        y = data["y"].astype(np.float32).reshape(256, 256)
        mask = data["valid_mask"].astype(bool).reshape(256, 256)
    pred_dbm = pred_norm.reshape(256, 256) * y_std + y_mean
    diff = pred_dbm[mask] - y[mask]
    mse = float(np.mean(diff * diff))
    return {
        "rmse_db": float(np.sqrt(mse)),
        "mae_db": float(np.mean(np.abs(diff))),
        "pred_dbm_mean": float(pred_dbm[mask].mean()),
        "label_dbm_mean": float(y[mask].mean()),
        "valid_pixels": int(mask.sum()),
    }


def load_tensor_quant(args: argparse.Namespace, tensor_name: str) -> Dict[str, object]:
    qnn_json = Path(args.qnn_json) if args.qnn_json else infer_qnn_json_path(Path(args.model).resolve())
    if not qnn_json.is_file():
        return {"ok": False, "qnn_json": str(qnn_json)}
    obj = json.loads(qnn_json.read_text(encoding="utf-8"))
    tensor = ((obj.get("graph") or {}).get("tensors") or {}).get(tensor_name) or {}
    params = tensor.get("quant_params") or {}
    scale_offset = params.get("scale_offset") or {}
    scale = scale_offset.get("scale")
    offset = scale_offset.get("offset")
    return {
        "ok": scale is not None and offset is not None,
        "qnn_json": str(qnn_json),
        "data_type": tensor.get("data_type"),
        "dims": tensor.get("dims"),
        "scale": None if scale is None else float(scale),
        "offset": None if offset is None else int(offset),
    }


def dequantize_uint8_output(values: object, quant: Dict[str, object]) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float32)
    scale = float(quant["scale"])
    offset = float(quant["offset"])
    return (arr + offset) * scale


def quantize_uint8_input(x_nhwc: np.ndarray, quant: Dict[str, object]) -> np.ndarray:
    scale = float(quant["scale"])
    offset = float(quant["offset"])
    return np.clip(np.rint(x_nhwc / scale - offset), 0, 255).astype(np.uint8)


def run_inference(args: argparse.Namespace, x_nhwc: np.ndarray) -> Dict[str, object]:
    infer = api_infer_py.InferAPI()
    result: Dict[str, object] = {
        "model": str(Path(args.model).resolve()),
        "platform": "qualcomm",
        "framework": "qnn",
        "runtime": args.runtime,
        "mode": args.mode,
        "warmup": args.warmup,
        "repeat": args.repeat,
    }
    try:
        params = api_infer_py.InferParams(
            result["model"],
            "qualcomm",
            "qnn",
            args.runtime,
            args.log_level,
            args.mode,
        )
        t0 = time.perf_counter()
        result["init_code"] = infer.Init(params)
        result["init_ms"] = (time.perf_counter() - t0) * 1000.0
        if result["init_code"] != 0:
            result["ok"] = False
            return result

        input_quant = load_tensor_quant(args, args.input_name)
        output_quant = load_tensor_quant(args, args.output_name)
        execute_dtype = args.execute_dtype
        if execute_dtype == "auto":
            execute_dtype = "uint8" if input_quant.get("ok") and input_quant.get("data_type") != 562 else "float"
        if execute_dtype == "uint8":
            input_data = quantize_uint8_input(x_nhwc, input_quant).reshape(-1).astype(np.uint8).tolist()
        else:
            input_data = x_nhwc.reshape(-1).astype(np.float32).tolist()
        feed = {args.input_name: input_data}
        for _ in range(max(args.warmup, 0)):
            rc = infer.Execute_uint8(feed) if execute_dtype == "uint8" else infer.Execute_float(feed)
            if rc != 0:
                result["ok"] = False
                result["warmup_execute_code"] = rc
                return result

        output = None
        fetch_dtype = args.fetch_dtype
        if fetch_dtype == "auto":
            fetch_dtype = "uint8" if output_quant.get("ok") and output_quant.get("data_type") != 562 else "float"
        execute_ms = []
        fetch_ms = []
        for _ in range(max(args.repeat, 1)):
            t1 = time.perf_counter()
            rc = infer.Execute_uint8(feed) if execute_dtype == "uint8" else infer.Execute_float(feed)
            execute_ms.append((time.perf_counter() - t1) * 1000.0)
            if rc != 0:
                result["ok"] = False
                result["execute_code"] = rc
                return result
            t2 = time.perf_counter()
            if fetch_dtype == "uint8":
                outputs = infer.FetchOutputs_uint8([args.output_name])
            else:
                outputs = infer.FetchOutputs_float([args.output_name])
            fetch_ms.append((time.perf_counter() - t2) * 1000.0)
            if fetch_dtype == "uint8":
                output = dequantize_uint8_output(outputs[args.output_name], output_quant)
            else:
                output = np.asarray(outputs[args.output_name], dtype=np.float32)
        if output is None:
            raise RuntimeError("未获取到 QNN 输出")
        result.update(
            {
                "ok": True,
                "execute_ms": execute_ms,
                "execute_ms_avg": statistics.mean(execute_ms),
                "execute_ms_min": min(execute_ms),
                "execute_ms_max": max(execute_ms),
                "fetch_ms_avg": statistics.mean(fetch_ms),
                "execute_dtype": execute_dtype,
                "input_quant": input_quant,
                "fetch_dtype": fetch_dtype,
                "output_quant": output_quant,
                "output_len": int(output.size),
                "output_min": float(output.min()),
                "output_max": float(output.max()),
                "output_mean": float(output.mean()),
                "output": output,
            }
        )
        return result
    finally:
        try:
            result["release_code"] = infer.Release()
        except Exception:
            pass


def main() -> int:
    args = build_parser().parse_args()
    features_dir = Path(args.features_dir)
    x_nhwc, sample_meta = load_sample(features_dir, args.sample_id)
    result = run_inference(args, x_nhwc)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = result.pop("output", None)
    if isinstance(output, np.ndarray):
        if output.size == 256 * 256:
            pred = output.reshape(256, 256).astype(np.float32)
        else:
            side = int(np.sqrt(output.size))
            pred = output.reshape(side, side).astype(np.float32) if side * side == output.size else output.astype(np.float32)
        npy_path = output_dir / f"{args.sample_id}_{args.runtime.lower()}_qnn.npy"
        np.save(npy_path, pred)
        result["output_npy"] = str(npy_path.resolve())
        result["saved_output_shape"] = list(pred.shape)
        if pred.shape == (256, 256):
            result["label_metrics"] = label_metrics(features_dir, args.sample_id, pred)
        else:
            result["label_metrics"] = {
                "ok": False,
                "reason": f"输出形状不是 256x256，无法直接和标签对齐：{pred.shape}",
            }

    result["sample_id"] = args.sample_id
    result["sample"] = sample_meta
    summary_path = output_dir / f"{args.sample_id}_{args.runtime.lower()}_qnn_summary.json"
    summary_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
