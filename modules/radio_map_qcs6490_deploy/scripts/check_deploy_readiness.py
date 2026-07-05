#!/usr/bin/env python3
# 中文说明：本脚本只做只读检查，用于确认当前设备是否具备 radio map SNPE GPU 主线部署条件。

import argparse
import importlib.util
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_paths(root: Path) -> Dict[str, Path]:
    deploy = root / "modules/radio_map_qcs6490_deploy"
    fibo_env = root / "modules/fiboaistack_229_env"
    features = root / "modules/radio-map-estimation-workbench/modules/m2/runs/datas/features/v1_base_256_k1_landuse3"
    return {
        "deploy": deploy,
        "fibo_env": fibo_env,
        "dlc": fibo_env / "outputs/radio_map_liteunet.dlc",
        "onnx": fibo_env / "inputs/radio_map_liteunet.onnx",
        "features": features,
        "samples_csv": features / "samples.csv",
        "stats_json": features / "stats.json",
        "snpe100_summary": deploy / "outputs/snpe_gpu_repro_test100/summary.json",
        "fallback_gpu": deploy / "outputs/snpe_backend_judgement_20260703_044730/fallback_judgement_GPU.json",
        "fallback_dsp": deploy / "outputs/snpe_backend_judgement_20260703_044730/fallback_judgement_DSP.json",
        "fallback_npu": deploy / "outputs/snpe_backend_judgement_20260703_044730/fallback_judgement_NPU.json",
        "qemu_check": fibo_env / "scripts/check_qemu_x86_64.sh",
        "qemu_register": fibo_env / "scripts/register_qemu82_binfmt.sh",
    }


def status(ok: bool, detail: str = "", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    item: Dict[str, Any] = {"ok": bool(ok), "detail": detail}
    if data:
        item.update(data)
    return item


def file_status(path: Path, min_size: int = 1) -> Dict[str, Any]:
    if not path.exists():
        return status(False, f"missing: {path}")
    if not path.is_file():
        return status(False, f"not a file: {path}")
    size = path.stat().st_size
    return status(size >= min_size, str(path), {"size": size})


def dir_status(path: Path) -> Dict[str, Any]:
    return status(path.is_dir(), str(path))


def load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def run_cmd(args: List[str], timeout: int = 5) -> Dict[str, Any]:
    try:
        proc = subprocess.run(args, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"returncode": None, "stdout": "", "stderr": str(exc)}
    return {"returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}


def check_python_sdk() -> Dict[str, Any]:
    spec = importlib.util.find_spec("fiboaisdk")
    api_ok = False
    api_error = ""
    try:
        from fiboaisdk.api_aisdk_py import api_infer_py  # type: ignore

        api_ok = hasattr(api_infer_py, "InferAPI") and hasattr(api_infer_py, "InferParams")
    except Exception as exc:  # noqa: BLE001 - readiness check should report import failures.
        api_error = f"{type(exc).__name__}: {exc}"
    return status(
        spec is not None and api_ok and sys.version_info[:2] == (3, 8),
        "system python3 should expose fiboaisdk under CPython 3.8",
        {
            "python": sys.version,
            "executable": sys.executable,
            "machine": platform.machine(),
            "fiboaisdk_found": spec is not None,
            "fiboaisdk_api_ok": api_ok,
            "fiboaisdk_api_error": api_error,
        },
    )


def check_devices() -> Dict[str, Any]:
    kgsl_dev = Path("/dev/kgsl-3d0")
    kgsl_sys = Path("/sys/class/kgsl/kgsl-3d0")
    gpu_model = kgsl_sys / "gpu_model"
    fastrpc_nodes = [Path("/dev/adsprpc-smd"), Path("/dev/adsprpc-smd-secure"), Path("/usr/lib/libcdsprpc.so")]
    model = ""
    try:
        model = gpu_model.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        pass
    return status(
        kgsl_dev.exists() and kgsl_sys.exists(),
        "KGSL is required for SNPE GPU evidence",
        {
            "kgsl_dev": str(kgsl_dev),
            "kgsl_dev_exists": kgsl_dev.exists(),
            "kgsl_sys_exists": kgsl_sys.exists(),
            "gpu_model": model,
            "fastrpc": {str(path): path.exists() for path in fastrpc_nodes},
        },
    )


def check_qemu(paths: Dict[str, Path]) -> Dict[str, Any]:
    entry = Path("/proc/sys/fs/binfmt_misc/qemu-x86_64")
    codex_entry = Path("/proc/sys/fs/binfmt_misc/codex-qemu-x86_64")
    interpreter = ""
    if entry.is_file():
        for line in entry.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("interpreter "):
                interpreter = line.split(maxsplit=1)[1]
                break
    qemu82 = Path("/usr/local/bin/qemu-x86_64-static-8.2.2")
    qemu82_version = run_cmd([str(qemu82), "--version"])["stdout"].splitlines()[0] if qemu82.exists() else ""
    return status(
        interpreter == str(qemu82),
        "canonical qemu-x86_64 should point to QEMU 8.2.2 before quantization work",
        {
            "canonical_interpreter": interpreter,
            "qemu82_exists": qemu82.exists(),
            "qemu82_version": qemu82_version,
            "codex_entry_exists": codex_entry.exists(),
            "check_script": str(paths["qemu_check"]),
            "register_script": str(paths["qemu_register"]),
        },
    )


def check_fallback(paths: Dict[str, Path]) -> Dict[str, Any]:
    expected = {
        "GPU": "hardware_backend_confirmed",
        "DSP": "backend_loaded_no_acceleration_evidence",
        "NPU": "suspected_cpu_fallback",
    }
    results: Dict[str, Any] = {}
    ok = True
    for runtime, verdict in expected.items():
        path = paths[f"fallback_{runtime.lower()}"]
        obj = load_json(path)
        actual = None
        if obj and obj.get("results"):
            actual = obj["results"][0].get("verdict")
        results[runtime] = {"path": str(path), "expected": verdict, "actual": actual}
        ok = ok and actual == verdict
    return status(ok, "fallback verdicts should match current backend conclusion", results)


def check_batch_summary(path: Path) -> Dict[str, Any]:
    obj = load_json(path)
    if not obj:
        return status(False, f"missing or invalid JSON: {path}")
    return status(
        obj.get("num_ok") == 100 and obj.get("num_failed") == 0,
        "SNPE GPU 100-sample baseline",
        {
            "path": str(path),
            "num_samples": obj.get("num_samples"),
            "num_ok": obj.get("num_ok"),
            "num_failed": obj.get("num_failed"),
            "mean_gpu_execute_ms": obj.get("mean_gpu_execute_ms"),
            "mean_speedup_cpu_over_gpu": obj.get("mean_speedup_cpu_over_gpu"),
            "mean_dbm_cpu_gpu_rmse": obj.get("mean_dbm_cpu_gpu_rmse"),
        },
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="检查当前设备 radio map SNPE GPU 部署就绪状态")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--strict", action="store_true", help="任一检查失败时返回非零")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = repo_root()
    paths = default_paths(root)
    checks = {
        "python_sdk": check_python_sdk(),
        "dlc": file_status(paths["dlc"], min_size=1024),
        "onnx": file_status(paths["onnx"], min_size=1024),
        "features_dir": dir_status(paths["features"]),
        "samples_csv": file_status(paths["samples_csv"], min_size=1),
        "stats_json": file_status(paths["stats_json"], min_size=1),
        "devices": check_devices(),
        "qemu_x86_64": check_qemu(paths),
        "fallback_judgement": check_fallback(paths),
        "snpe_gpu_test100": check_batch_summary(paths["snpe100_summary"]),
    }
    payload = {"ok": all(item["ok"] for item in checks.values()), "repo_root": str(root), "checks": checks}

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"overall={'OK' if payload['ok'] else 'WARN'}")
        for name, item in checks.items():
            marker = "OK" if item["ok"] else "WARN"
            print(f"[{marker}] {name}: {item['detail']}")
        if not checks["qemu_x86_64"]["ok"]:
            print("next: modules/fiboaistack_229_env/scripts/register_qemu82_binfmt.sh")

    return 1 if args.strict and not payload["ok"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
