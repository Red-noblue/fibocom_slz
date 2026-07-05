# 提供任务级候选方案评估与轻量优化入口，服务后续主动调度。
"""提供后续主动调度可复用的轻量优化入口。"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

from .evaluate import save_ablation_results, save_summary
from .predict import predict_fixed_route_energy
from .schema import BatterySpec, CandidateScore, EvaluationConfig, MissionSpec, VehicleSpec


def evaluate_candidate(
    model_path: Union[str, Path],
    weather_config: Union[str, Path],
    mission: MissionSpec,
    vehicle: VehicleSpec,
    battery: BatterySpec,
    candidate_id: str = "candidate",
    evaluation_config: Optional[EvaluationConfig] = None,
) -> CandidateScore:
    """评估单个候选任务方案并计算统一评分。"""

    cfg = evaluation_config or EvaluationConfig()
    bundle = predict_fixed_route_energy(
        model_path=model_path,
        weather_config=weather_config,
        mission=mission,
        vehicle=vehicle,
        battery=battery,
    )
    summary = bundle.summary
    total_energy = float(summary["predicted_total_energy_wh"])
    route_length_km = float(summary["route_length_km"])
    predicted_range_km = float(summary["predicted_range_km"])
    feasible = total_energy <= battery.capacity_wh and predicted_range_km >= route_length_km
    risk_alerts = summary.get("risk_alerts") or []
    hard_risk_count = len([alert for alert in risk_alerts if "风险" in str(alert) or "不足" in str(alert)])

    score = total_energy
    if not feasible:
        score += float(cfg.infeasible_penalty)
    score += float(hard_risk_count) * float(cfg.risk_penalty)

    return CandidateScore(
        candidate_id=candidate_id,
        score=float(score),
        total_energy_wh=total_energy,
        route_length_km=route_length_km,
        predicted_range_km=predicted_range_km,
        feasible=bool(feasible),
        risk_count=int(hard_risk_count),
        summary=summary,
    )


def grid_search_fixed_route_speed(
    model_path: Union[str, Path],
    weather_config: Union[str, Path],
    mission: MissionSpec,
    vehicle: VehicleSpec,
    battery: BatterySpec,
    speeds_mps: List[float],
) -> dict:
    """在固定路线下搜索不同速度对应的能耗结果。"""

    results = []
    best = None
    best_energy = None

    for speed in speeds_mps:
        candidate_vehicle = VehicleSpec(
            name=vehicle.name,
            payload_g=vehicle.payload_g,
            cruise_speed_mps=float(speed),
            altitude_m=vehicle.altitude_m,
            max_speed_mps=vehicle.max_speed_mps,
        )
        candidate_score = evaluate_candidate(
            model_path=model_path,
            weather_config=weather_config,
            mission=mission,
            vehicle=candidate_vehicle,
            battery=battery,
            candidate_id=f"speed_{float(speed):.3f}",
        )
        result_row = {
            "planned_ground_speed_mps": float(speed),
            "speed_mps": float(speed),
            "score": candidate_score.score,
            "feasible": candidate_score.feasible,
            "risk_count": candidate_score.risk_count,
            "predicted_total_energy_wh": candidate_score.total_energy_wh,
            "predicted_range_km": candidate_score.predicted_range_km,
            "predicted_flight_time_s": float(candidate_score.summary["predicted_flight_time_s"]),
            "route_length_km": candidate_score.route_length_km,
        }
        results.append(result_row)
        if best_energy is None or candidate_score.score < best_energy:
            best_energy = candidate_score.score
            best = result_row

    return {
        "best": best,
        "results": results,
    }


def write_speed_search_outputs(payload: dict, csv_path: Union[str, Path], json_path: Union[str, Path]) -> None:
    """保存速度搜索结果。"""

    save_ablation_results(payload["results"], csv_path)
    save_summary(payload, json_path)
