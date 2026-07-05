#!/usr/bin/env python3
# 中文说明：该脚本用于在当前 QCS6490 设备上固定使用 Fibo AI Stack 的 SNPE GPU 路线执行单样本推理，并保存输出结果。

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


def default_model_path() -> Path:
    return repo_root() / "modules/fiboaistack_229_env/outputs/radio_map_liteunet.dlc"


def default_features_dir() -> Path:
    return repo_root() / "modules/radio-map-estimation-workbench/modules/m2/runs/datas/features/v1_base_256_k1_landuse3"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="使用 SNPE GPU 执行 radio map DLC 单样本推理")
    parser.add_argument("--model", default=str(default_model_path()), help="DLC 模型路径")
    parser.add_argument("--features-dir", default=str(default_features_dir()), help="M2 特征目录")
    parser.add_argument("--sample-id", default="166_k0", help="样本 ID，对应 features-dir 下的 <sample-id>.npz")
    parser.add_argument("--input-npz", default="", help="显式指定 npz 样本路径，优先于 sample-id")
    parser.add_argument("--output-dir", default=str(repo_root() / "modules/radio_map_qcs6490_deploy/outputs/snpe_gpu"), help="输出目录")
    parser.add_argument("--input-name", default="input", help="DLC 输入张量名")
    parser.add_argument("--output-name", default="output", help="DLC 输出张量名")
    parser.add_argument("--runtime", default="GPU", help="Fibo AI Stack runtime，默认固定 GPU")
    parser.add_argument("--mode", type=int, default=5, help="Fibo AI Stack profile/mode，默认 5(burst)")
    parser.add_argument("--log-level", default="ERROR", help="Fibo AI Stack 日志级别")
    parser.add_argument("--warmup", type=int, default=2, help="预热次数")
    parser.add_argument("--repeat", type=int, default=5, help="计时推理次数")
    return parser


def load_sample(args: argparse.Namespace) -> Tuple[str, np.ndarray, Dict[str, object]]:
    if args.input_npz:
        sample_path = Path(args.input_npz)
        sample_id = sample_path.stem
    else:
        sample_id = args.sample_id
        sample_path = Path(args.features_dir) / f"{sample_id}.npz"
    if not sample_path.is_file():
        raise FileNotFoundError(f"未找到样本文件：{sample_path}")

    with np.load(sample_path) as data:
        x_chw = data["X"].astype(np.float32)
        meta: Dict[str, object] = {
            "sample_path": str(sample_path.resolve()),
            "x_shape_chw": list(x_chw.shape),
            "has_y": "y" in data.files,
            "has_valid_mask": "valid_mask" in data.files,
        }
    if x_chw.ndim != 3:
        raise ValueError(f"样本 X 应为 [C,H,W]，实际为 {x_chw.shape}")
    x_nhwc = np.transpose(x_chw, (1, 2, 0))[None, ...].astype(np.float32)
    meta["x_shape_nhwc"] = list(x_nhwc.shape)
    return sample_id, x_nhwc, meta


def run_inference(args: argparse.Namespace, x_nhwc: np.ndarray) -> Dict[str, object]:
    model_path = str(Path(args.model).resolve())
    infer = api_infer_py.InferAPI()
    result: Dict[str, object] = {
        "model": model_path,
        "framework": "snpe",
        "runtime": args.runtime,
        "mode": args.mode,
        "input_name": args.input_name,
        "output_name": args.output_name,
        "warmup": args.warmup,
        "repeat": args.repeat,
    }
    try:
        params = api_infer_py.InferParams(
            model_path,
            "qualcomm",
            "snpe",
            args.runtime,
            args.log_level,
            args.mode,
        )
        t0 = time.perf_counter()
        init_code = infer.Init(params)
        result["init_ms"] = (time.perf_counter() - t0) * 1000.0
        result["init_code"] = init_code
        if init_code != 0:
            result["ok"] = False
            return result

        feed = {args.input_name: x_nhwc.reshape(-1).astype(np.float32).tolist()}
        for _ in range(max(args.warmup, 0)):
            rc = infer.Execute_float(feed)
            if rc != 0:
                result["ok"] = False
                result["warmup_execute_code"] = rc
                return result

        execute_ms = []
        fetch_ms = []
        output = None
        for _ in range(max(args.repeat, 1)):
            t1 = time.perf_counter()
            rc = infer.Execute_float(feed)
            execute_ms.append((time.perf_counter() - t1) * 1000.0)
            if rc != 0:
                result["ok"] = False
                result["execute_code"] = rc
                return result

            t2 = time.perf_counter()
            outputs = infer.FetchOutputs_float([args.output_name])
            fetch_ms.append((time.perf_counter() - t2) * 1000.0)
            output = np.asarray(outputs[args.output_name], dtype=np.float32)

        if output is None:
            raise RuntimeError("未获取到输出")
        result.update(
            {
                "ok": True,
                "execute_ms": execute_ms,
                "fetch_ms": fetch_ms,
                "execute_ms_avg": statistics.mean(execute_ms),
                "execute_ms_min": min(execute_ms),
                "execute_ms_max": max(execute_ms),
                "fetch_ms_avg": statistics.mean(fetch_ms),
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
    sample_id, x_nhwc, sample_meta = load_sample(args)
    result = run_inference(args, x_nhwc)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = result.pop("output", None)
    if isinstance(output, np.ndarray):
        if output.size == 256 * 256:
            output_to_save = output.reshape(256, 256)
        else:
            output_to_save = output
        np.save(output_dir / f"{sample_id}_{args.runtime.lower()}_snpe.npy", output_to_save.astype(np.float32))
        result["output_npy"] = str((output_dir / f"{sample_id}_{args.runtime.lower()}_snpe.npy").resolve())

    result["sample_id"] = sample_id
    result["sample"] = sample_meta
    result_path = output_dir / f"{sample_id}_{args.runtime.lower()}_snpe_summary.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
