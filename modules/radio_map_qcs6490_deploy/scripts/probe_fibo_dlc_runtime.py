#!/usr/bin/env python3
# 中文说明：该脚本用于在当前 QCS6490 设备上用 Fibo AI Stack 测试模型在指定运行时的可用性、推理耗时和部分设备侧计数器变化。

import argparse
import json
import os
import statistics
import time
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from fiboaisdk.api_aisdk_py import api_infer_py


def build_parser() -> argparse.ArgumentParser:
    repo_root = Path(__file__).resolve().parents[3]
    default_model = repo_root / "modules/fiboaistack_229_env/outputs/radio_map_liteunet.dlc"
    parser = argparse.ArgumentParser(description="测试 Fibo AI Stack DLC 运行时可用性和推理耗时")
    parser.add_argument("--model", default=str(default_model), help="DLC 模型路径")
    parser.add_argument("--runtime", default="CPU", help="运行时：CPU/GPU/DSP/NPU")
    parser.add_argument("--framework", default="snpe", help="推理框架：snpe/qnn")
    parser.add_argument("--warmup", type=int, default=1, help="预热次数")
    parser.add_argument("--repeat", type=int, default=5, help="计时推理次数")
    parser.add_argument("--input-name", default="input", help="DLC 输入张量名")
    parser.add_argument("--input-shape", default="1,256,256,7", help="输入张量形状，逗号分隔，例如 1,256,256,7")
    parser.add_argument("--output-name", default="output", help="DLC 输出张量名")
    parser.add_argument("--seed", type=int, default=17, help="随机输入种子")
    parser.add_argument("--log-level", default="ERROR", help="Fibo AI Stack 日志级别")
    parser.add_argument("--mode", type=int, default=0, help="Fibo AI Stack profile/mode 参数")
    parser.add_argument("--sample-device", action="store_true", help="采样 KGSL/FASTRPC 等设备侧状态，辅助判断是否真的触发硬件后端")
    return parser


def parse_shape(raw_shape: str) -> Tuple[int, ...]:
    try:
        shape = tuple(int(part.strip()) for part in raw_shape.split(",") if part.strip())
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"非法输入形状：{raw_shape}") from exc
    if not shape or any(dim <= 0 for dim in shape):
        raise argparse.ArgumentTypeError(f"输入形状必须是正整数列表：{raw_shape}")
    return shape


def make_input(seed: int, shape: Tuple[int, ...]) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.standard_normal(shape, dtype=np.float32)


def read_text(path: str) -> Optional[str]:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None


def read_counter_snapshot() -> dict:
    paths = {
        "kgsl_gpu_model": "/sys/class/kgsl/kgsl-3d0/gpu_model",
        "kgsl_gpuclk": "/sys/class/kgsl/kgsl-3d0/gpuclk",
        "kgsl_clock_mhz": "/sys/class/kgsl/kgsl-3d0/clock_mhz",
        "kgsl_gpu_busy_percentage": "/sys/class/kgsl/kgsl-3d0/gpu_busy_percentage",
        "kgsl_gpubusy": "/sys/class/kgsl/kgsl-3d0/gpubusy",
        "kgsl_reset_count": "/sys/class/kgsl/kgsl-3d0/reset_count",
        "devfreq_cur_freq": "/sys/class/devfreq/3d00000.qcom,kgsl-3d0/cur_freq",
        "devfreq_trans_stat": "/sys/class/devfreq/3d00000.qcom,kgsl-3d0/trans_stat",
        "fastrpc_adsprpc_wakeup_count": "/sys/class/fastrpc/adsprpc-smd/wakeup11/wakeup_count",
        "fastrpc_adsprpc_event_count": "/sys/class/fastrpc/adsprpc-smd/wakeup11/event_count",
        "fastrpc_adsprpc_secure_wakeup_count": "/sys/class/fastrpc/adsprpc-smd-secure/wakeup12/wakeup_count",
        "fastrpc_adsprpc_secure_event_count": "/sys/class/fastrpc/adsprpc-smd-secure/wakeup12/event_count",
    }
    return {name: value for name, path in paths.items() if (value := read_text(path)) is not None}


def build_backend_evidence(args: argparse.Namespace) -> dict:
    sdk_root = Path("/usr/local/lib/python3.8/dist-packages/fiboaisdk")
    return {
        "platform": "qualcomm",
        "framework": args.framework.lower(),
        "requested_runtime": args.runtime,
        "public_python_params": [
            "model_path",
            "platform",
            "framework",
            "device_unit(runtime)",
            "log_level",
            "mode(profile_level)",
        ],
        "runtime_lib_paths": os.environ.get("RUNTIME_LIB_PATHS"),
        "adsp_library_path": os.environ.get("ADSP_LIBRARY_PATH"),
        "htp_config_exists": (sdk_root / "htp_backend_ext_config.json").exists(),
        "htp_config_path": str(sdk_root / "htp_backend_ext_config.json"),
    }


def main() -> int:
    args = build_parser().parse_args()
    model_path = str(Path(args.model).resolve())
    input_shape = parse_shape(args.input_shape)
    input_data = make_input(args.seed, input_shape)
    input_feed = {args.input_name: input_data.reshape(-1).astype(np.float32).tolist()}

    result = {
        "runtime": args.runtime,
        "framework": args.framework,
        "model": model_path,
        "input_name": args.input_name,
        "output_name": args.output_name,
        "input_shape": list(input_data.shape),
        "warmup": args.warmup,
        "repeat": args.repeat,
        "ok": False,
        "backend_evidence": build_backend_evidence(args),
    }

    infer = api_infer_py.InferAPI()
    try:
        params = api_infer_py.InferParams(
            model_path,
            "qualcomm",
            args.framework,
            args.runtime,
            args.log_level,
            args.mode,
        )
        result["params"] = {
            "model_path": params.get_model_path(),
            "platform": params.get_platform(),
            "framework": params.get_framework(),
            "device_unit": params.get_device_unit(),
            "log_level": params.get_log_level(),
            "mode": params.get_mode(),
        }

        if args.sample_device:
            result["device_before_init"] = read_counter_snapshot()

        t0 = time.perf_counter()
        init_code = infer.Init(params)
        result["init_code"] = init_code
        result["init_ms"] = (time.perf_counter() - t0) * 1000.0
        if args.sample_device:
            result["device_after_init"] = read_counter_snapshot()
        if init_code != 0:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 10

        for _ in range(max(args.warmup, 0)):
            rc = infer.Execute_float(input_feed)
            if rc != 0:
                result["warmup_execute_code"] = rc
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 11

        execute_ms = []
        fetch_ms = []
        output_len = None
        output_min = None
        output_max = None
        output_mean = None
        if args.sample_device:
            result["device_before_execute"] = read_counter_snapshot()

        for _ in range(max(args.repeat, 1)):
            t1 = time.perf_counter()
            rc = infer.Execute_float(input_feed)
            execute_ms.append((time.perf_counter() - t1) * 1000.0)
            if rc != 0:
                result["execute_code"] = rc
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 12

            t2 = time.perf_counter()
            outputs = infer.FetchOutputs_float([args.output_name])
            fetch_ms.append((time.perf_counter() - t2) * 1000.0)
            output = np.asarray(outputs[args.output_name], dtype=np.float32)
            output_len = int(output.size)
            output_min = float(output.min()) if output.size else None
            output_max = float(output.max()) if output.size else None
            output_mean = float(output.mean()) if output.size else None

        if args.sample_device:
            result["device_after_execute"] = read_counter_snapshot()

        result.update(
            {
                "ok": True,
                "execute_ms": execute_ms,
                "fetch_ms": fetch_ms,
                "execute_ms_avg": statistics.mean(execute_ms),
                "execute_ms_min": min(execute_ms),
                "execute_ms_max": max(execute_ms),
                "fetch_ms_avg": statistics.mean(fetch_ms),
                "output_len": output_len,
                "output_min": output_min,
                "output_max": output_max,
                "output_mean": output_mean,
            }
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        result["error"] = str(exc)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 20
    finally:
        try:
            result["release_code"] = infer.Release()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
