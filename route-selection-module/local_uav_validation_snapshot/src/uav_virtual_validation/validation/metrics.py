"""预测结果与虚拟仿真结果的误差指标。"""

from __future__ import annotations

from typing import Any


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def compare_energy_curves(pred_rows: list[dict[str, Any]], sim_rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = min(len(pred_rows), len(sim_rows))
    if count == 0:
        raise ValueError("预测时序和仿真时序不能为空。")

    comparison: list[dict[str, Any]] = []
    abs_errors = []
    pct_errors = []
    for idx in range(count):
        pred = pred_rows[idx]
        sim = sim_rows[idx]
        pred_energy = _to_float(pred.get("cumulative_energy_wh"))
        sim_energy = _to_float(sim.get("cumulative_energy_wh"))
        error = pred_energy - sim_energy
        pct_error = error / sim_energy * 100.0 if abs(sim_energy) > 1e-9 else 0.0
        abs_errors.append(abs(error))
        pct_errors.append(abs(pct_error))
        comparison.append(
            {
                "index": idx,
                "time": sim.get("time") or pred.get("time"),
                "pred_cumulative_energy_wh": pred_energy,
                "sim_cumulative_energy_wh": sim_energy,
                "energy_error_wh": error,
                "energy_error_pct": pct_error,
            }
        )

    final_pred = _to_float(pred_rows[count - 1].get("cumulative_energy_wh"))
    final_sim = _to_float(sim_rows[count - 1].get("cumulative_energy_wh"))
    metrics = {
        "matched_points": count,
        "energy_mae_wh": sum(abs_errors) / count,
        "energy_mape_pct": sum(pct_errors) / count,
        "final_energy_error_wh": final_pred - final_sim,
        "final_energy_error_pct": (final_pred - final_sim) / final_sim * 100.0 if abs(final_sim) > 1e-9 else 0.0,
    }
    return {"metrics": metrics, "comparison": comparison}
