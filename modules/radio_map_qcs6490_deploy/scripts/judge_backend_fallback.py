#!/usr/bin/env python3
# 中文说明：该脚本汇总 Fibo AI Stack 推理日志、JSON 结果和设备侧计数，给出后端是否疑似 CPU fallback 的硬性判据。

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


ERROR_PATTERNS = (
    "MODEL_GRAPH_OP_VALIDATION_ERROR",
    "QnnBackend_validateOpConfig failed",
    "Failed to validate op",
    "GPU_ERROR_INVALID_TYPE",
    "GPU_ERROR_OP_PACKAGE_FAILED",
    "OpConfig validation failed",
    "Failed to initialize QNN runtime",
)

NON_FATAL_PATTERNS = (
    "GPU_ERROR_UNSUPPORTED(10018) - Setting context priority after context initialization not supported",
    "QnnContext_setConfig() failed",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="判断 Fibo AI Stack 后端是否疑似 CPU fallback")
    parser.add_argument("--run-dir", required=True, help="包含 *.json / *.raw.log / *.summary 的运行目录")
    parser.add_argument("--cpu-key", default="CPU", help="CPU baseline 文件名关键字")
    parser.add_argument("--runtime-key", required=True, help="目标 runtime 文件名关键字，例如 GPU/DSP/NPU")
    parser.add_argument("--min-speedup", type=float, default=1.5, help="认为硬件加速成立的最低加速比")
    parser.add_argument("--max-output-mean-diff", type=float, default=1e-6, help="输出均值完全一致的判断阈值")
    parser.add_argument("--output", default="", help="可选：保存判定 JSON 的路径")
    return parser


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def load_json_with_log_prefix(path: Path) -> Optional[Dict[str, Any]]:
    text = read_text(path)
    if not text:
        return None
    match = re.search(r"(?m)^\{", text)
    if not match:
        return None
    try:
        decoder = json.JSONDecoder()
        data, _ = decoder.raw_decode(text[match.start():])
        return data
    except json.JSONDecodeError:
        return None


def find_case_files(run_dir: Path, key: str) -> List[Path]:
    return sorted(path for path in run_dir.glob(f"*_{key}.json") if not path.name.startswith("fallback_judgement"))


def related_texts(json_path: Path) -> str:
    stem = json_path.name[:-5]
    parts = [read_text(json_path)]
    for suffix in (".raw.log", ".summary"):
        parts.append(read_text(json_path.with_name(stem + suffix)))
    return "\n".join(parts)


def load_runtime_result(json_path: Path) -> Optional[Dict[str, Any]]:
    data = load_json_with_log_prefix(json_path)
    if data and "parse_error" not in data:
        return data
    raw_path = json_path.with_name(json_path.name[:-5] + ".raw.log")
    raw_data = load_json_with_log_prefix(raw_path)
    if raw_data:
        return raw_data
    return data


def contains_any(text: str, patterns: Iterable[str]) -> List[str]:
    return [pattern for pattern in patterns if pattern in text]


def parse_first_ints(raw: Any) -> List[int]:
    if raw is None:
        return []
    return [int(part) for part in re.findall(r"-?\d+", str(raw))]


def int_counter_delta(before: Dict[str, Any], after: Dict[str, Any], key: str) -> Optional[int]:
    before_vals = parse_first_ints(before.get(key))
    after_vals = parse_first_ints(after.get(key))
    if not before_vals or not after_vals:
        return None
    return after_vals[0] - before_vals[0]


def pair_counter_delta(before: Dict[str, Any], after: Dict[str, Any], key: str) -> Optional[List[int]]:
    before_vals = parse_first_ints(before.get(key))
    after_vals = parse_first_ints(after.get(key))
    if len(before_vals) < 2 or len(after_vals) < 2:
        return None
    return [after_vals[0] - before_vals[0], after_vals[1] - before_vals[1]]


def build_device_evidence(target: Dict[str, Any]) -> Dict[str, Any]:
    before = target.get("device_before_execute") or {}
    after = target.get("device_after_execute") or {}
    if not isinstance(before, dict) or not isinstance(after, dict):
        return {
            "has_device_snapshots": False,
            "kgsl_gpu_activity": False,
            "fastrpc_activity": False,
        }

    kgsl_gpubusy_delta = pair_counter_delta(before, after, "kgsl_gpubusy")
    kgsl_busy_pct_after = parse_first_ints(after.get("kgsl_gpu_busy_percentage"))
    kgsl_gpuclk_after = parse_first_ints(after.get("kgsl_gpuclk"))
    devfreq_cur_freq_after = parse_first_ints(after.get("devfreq_cur_freq"))
    kgsl_gpu_activity = bool(
        (kgsl_gpubusy_delta and (kgsl_gpubusy_delta[0] > 0 or kgsl_gpubusy_delta[1] > 0))
        or (kgsl_busy_pct_after and kgsl_busy_pct_after[0] > 0)
    )

    fastrpc_keys = (
        "fastrpc_adsprpc_wakeup_count",
        "fastrpc_adsprpc_event_count",
        "fastrpc_adsprpc_secure_wakeup_count",
        "fastrpc_adsprpc_secure_event_count",
    )
    fastrpc_deltas = {
        key: int_counter_delta(before, after, key)
        for key in fastrpc_keys
        if int_counter_delta(before, after, key) is not None
    }
    fastrpc_activity = any(delta > 0 for delta in fastrpc_deltas.values())

    return {
        "has_device_snapshots": True,
        "kgsl_gpu_activity": kgsl_gpu_activity,
        "kgsl_gpubusy_delta": kgsl_gpubusy_delta,
        "kgsl_gpu_busy_percentage_after": kgsl_busy_pct_after[0] if kgsl_busy_pct_after else None,
        "kgsl_gpuclk_after": kgsl_gpuclk_after[0] if kgsl_gpuclk_after else None,
        "devfreq_cur_freq_after": devfreq_cur_freq_after[0] if devfreq_cur_freq_after else None,
        "fastrpc_activity": fastrpc_activity,
        "fastrpc_deltas": fastrpc_deltas,
    }


def classify_backend(cpu: Dict[str, Any], target: Dict[str, Any], target_text: str, args: argparse.Namespace) -> Dict[str, Any]:
    cpu_ms = cpu.get("execute_ms_avg")
    target_ms = target.get("execute_ms_avg")
    speedup = (cpu_ms / target_ms) if isinstance(cpu_ms, (int, float)) and isinstance(target_ms, (int, float)) and target_ms > 0 else None
    cpu_mean = cpu.get("output_mean")
    target_mean = target.get("output_mean")
    output_mean_diff = (
        abs(float(cpu_mean) - float(target_mean))
        if isinstance(cpu_mean, (int, float)) and isinstance(target_mean, (int, float))
        else None
    )
    errors = contains_any(target_text, ERROR_PATTERNS)
    non_fatal_markers = contains_any(target_text, NON_FATAL_PATTERNS)
    requested_runtime = str(target.get("runtime") or target.get("params", {}).get("device_unit") or "").upper()
    framework = str(target.get("framework") or target.get("backend_evidence", {}).get("framework") or "").lower()
    ok = bool(target.get("ok")) and target.get("init_code") == 0

    hard_fail = bool(errors) or target.get("init_code") not in (0, None) or bool(target.get("error"))
    speed_evidence = speedup is not None and speedup >= args.min_speedup
    identical_output = output_mean_diff is not None and output_mean_diff <= args.max_output_mean_diff
    gpu_log_evidence = any(token in target_text for token in ("gpu_float32_16_hybrid", "QNN_GPU", "GPU ERROR", "requested_runtime\": \"GPU"))
    dsp_log_evidence = any(token in target_text for token in ("libQnnHtp", "libSnpeHtp", "cdsprpc", "adsprpc-smd", "QnnBackend_validateOpConfig", "dsp_fixed8_tf"))
    device_evidence = build_device_evidence(target)

    backend_log_evidence = gpu_log_evidence if requested_runtime == "GPU" else dsp_log_evidence
    backend_device_evidence = (
        device_evidence["kgsl_gpu_activity"]
        if requested_runtime == "GPU"
        else device_evidence["fastrpc_activity"]
    )

    if hard_fail:
        verdict = "backend_failed_not_fallback_success"
    elif requested_runtime == "GPU" and ok and speed_evidence and gpu_log_evidence and backend_device_evidence:
        verdict = "hardware_backend_confirmed"
    elif requested_runtime == "GPU" and ok and speed_evidence and gpu_log_evidence:
        verdict = "hardware_backend_likely_missing_device_counter"
    elif requested_runtime in {"DSP", "NPU", "HTP"} and ok and speed_evidence and dsp_log_evidence and backend_device_evidence:
        verdict = "hardware_backend_likely"
    elif requested_runtime in {"DSP", "NPU", "HTP"} and ok and speed_evidence and dsp_log_evidence:
        verdict = "hardware_backend_likely_missing_device_counter"
    elif ok and backend_log_evidence and not speed_evidence:
        verdict = "backend_loaded_no_acceleration_evidence"
    elif ok and not backend_log_evidence and not speed_evidence and identical_output:
        verdict = "suspected_cpu_fallback"
    elif ok and not speed_evidence:
        verdict = "no_acceleration_evidence"
    else:
        verdict = "inconclusive"

    return {
        "framework": framework,
        "requested_runtime": requested_runtime,
        "ok": ok,
        "init_code": target.get("init_code"),
        "cpu_execute_ms_avg": cpu_ms,
        "target_execute_ms_avg": target_ms,
        "speedup_cpu_over_target": speedup,
        "output_mean_diff": output_mean_diff,
        "error_markers": errors,
        "non_fatal_markers": non_fatal_markers,
        "gpu_log_evidence": gpu_log_evidence,
        "dsp_log_evidence": dsp_log_evidence,
        "backend_log_evidence": backend_log_evidence,
        "backend_device_evidence": backend_device_evidence,
        "device_evidence": device_evidence,
        "verdict": verdict,
    }


def main() -> int:
    args = build_parser().parse_args()
    run_dir = Path(args.run_dir)
    cpu_files = find_case_files(run_dir, args.cpu_key)
    target_files = find_case_files(run_dir, args.runtime_key)
    if not cpu_files or not target_files:
        print(json.dumps({"ok": False, "error": "未找到 CPU 或目标 runtime JSON", "run_dir": str(run_dir)}, ensure_ascii=False, indent=2))
        return 2

    cpu_by_case: Dict[str, Dict[str, Any]] = {}
    for path in cpu_files:
        case = path.name[: -len(f"_{args.cpu_key}.json")]
        data = load_runtime_result(path)
        if data:
            cpu_by_case[case] = data

    results = []
    for target_path in target_files:
        case = target_path.name[: -len(f"_{args.runtime_key}.json")]
        cpu = cpu_by_case.get(case)
        target = load_runtime_result(target_path)
        if not cpu or not target:
            results.append({"case": case, "verdict": "missing_or_unparseable_json"})
            continue
        item = classify_backend(cpu, target, related_texts(target_path), args)
        item["case"] = case
        item["target_json"] = str(target_path)
        results.append(item)

    summary: Dict[str, int] = {}
    for item in results:
        summary[item["verdict"]] = summary.get(item["verdict"], 0) + 1
    payload = {"ok": True, "run_dir": str(run_dir), "runtime_key": args.runtime_key, "summary": summary, "results": results}
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
