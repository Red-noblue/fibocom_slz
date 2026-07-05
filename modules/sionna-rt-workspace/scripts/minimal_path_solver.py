# 本脚本用于最小化复现 Sionna RT：加载内置三维场景，设置无人机虚拟发射点与探测接收点，并输出路径求解结果。
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import drjit as dr
import numpy as np
from sionna.rt import PathSolver, PlanarArray, Receiver, Transmitter, load_scene
from sionna.rt.scene import floor_wall


def _tensor_to_list(value: Any) -> list[Any]:
    return np.asarray(value).tolist()


def _scalar_to_float(value: Any) -> float:
    return float(np.asarray(value).reshape(-1)[0])


def _count_valid_paths(paths: Any) -> int:
    if hasattr(paths, "valid"):
        return int(np.asarray(paths.valid).sum())
    return int(np.asarray(paths.tau).size)


def _extract_path_gains_db(paths: Any) -> list[float]:
    # paths.a 是极化后的复振幅元组；不同后端返回结构略有差异，因此只抽取可稳定转换的幅度。
    amplitudes: list[np.ndarray] = []
    raw_amplitudes = paths.a if isinstance(paths.a, tuple) else (paths.a,)
    for item in raw_amplitudes:
        try:
            amplitudes.append(np.asarray(dr.abs(item), dtype=float))
        except Exception:
            continue

    if not amplitudes:
        return []

    merged = np.maximum.reduce([np.ravel(item) for item in amplitudes])
    positive = merged[merged > 0]
    return (20.0 * np.log10(positive)).round(3).tolist()


def run(output_path: Path) -> dict[str, Any]:
    scene = load_scene(floor_wall)
    scene.frequency = 3.5e9
    scene.tx_array = PlanarArray(
        num_rows=1,
        num_cols=1,
        vertical_spacing=0.5,
        horizontal_spacing=0.5,
        pattern="iso",
        polarization="V",
    )
    scene.rx_array = PlanarArray(
        num_rows=1,
        num_cols=1,
        vertical_spacing=0.5,
        horizontal_spacing=0.5,
        pattern="iso",
        polarization="V",
    )

    tx_position = [0.0, -4.0, 3.0]
    rx_position = [0.0, 4.0, 1.5]
    scene.add(Transmitter(name="tx_uav_sample", position=tx_position, power_dbm=30))
    scene.add(Receiver(name="rx_probe", position=rx_position))

    paths = PathSolver()(
        scene,
        max_depth=1,
        samples_per_src=1000,
        los=True,
        specular_reflection=True,
        diffuse_reflection=False,
        diffraction=False,
        seed=1,
    )

    result = {
        "scene": "sionna.rt.scene.floor_wall",
        "frequency_hz": _scalar_to_float(scene.frequency),
        "tx": {"name": "tx_uav_sample", "position_m": tx_position, "power_dbm": 30},
        "rx": {"name": "rx_probe", "position_m": rx_position},
        "solver": {
            "max_depth": 1,
            "samples_per_src": 1000,
            "los": True,
            "specular_reflection": True,
            "diffraction": False,
            "seed": 1,
        },
        "num_tx": int(paths.num_tx),
        "num_rx": int(paths.num_rx),
        "valid_path_count": _count_valid_paths(paths),
        "delay_s": _tensor_to_list(paths.tau),
        "path_gain_db": _extract_path_gains_db(paths),
        "theta_t_rad": _tensor_to_list(paths.theta_t),
        "phi_t_rad": _tensor_to_list(paths.phi_t),
        "theta_r_rad": _tensor_to_list(paths.theta_r),
        "phi_r_rad": _tensor_to_list(paths.phi_r),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="最小化复现 Sionna RT 路径求解。")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "outputs" / "minimal_path_solver.json",
        help="JSON 结果输出路径。",
    )
    args = parser.parse_args()

    result = run(args.output)
    print(json.dumps({
        "output": str(args.output),
        "valid_path_count": result["valid_path_count"],
        "path_gain_db": result["path_gain_db"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
