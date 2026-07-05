"""验证核心输入输出对象能正常构造。"""

from __future__ import annotations

from datetime import datetime

from uav_energy_engine.schema import BatterySpec, CandidateScore, EvaluationConfig, GeoPoint, MissionSpec, VehicleSpec


def test_schema_construction():
    """基础 schema 应可正常实例化。"""

    mission = MissionSpec(
        route_name="demo",
        start=GeoPoint(lat=39.0, lon=116.0),
        end=GeoPoint(lat=40.0, lon=116.1),
        departure_time=datetime(2026, 5, 11, 8, 0, 0),
    )
    vehicle = VehicleSpec(name="demo_uav", payload_g=250.0, cruise_speed_mps=8.0, altitude_m=60.0)
    battery = BatterySpec(capacity_wh=130.0)

    assert mission.route_name == "demo"
    assert vehicle.payload_g == 250.0
    assert battery.capacity_wh == 130.0


def test_candidate_score_schema_construction():
    """候选方案评分对象应可正常实例化。"""

    config = EvaluationConfig(infeasible_penalty=100.0)
    score = CandidateScore(
        candidate_id="speed_8",
        score=120.0,
        total_energy_wh=20.0,
        route_length_km=2.0,
        predicted_range_km=10.0,
        feasible=True,
        risk_count=0,
        summary={"route_name": "demo"},
    )

    assert config.infeasible_penalty == 100.0
    assert score.candidate_id == "speed_8"
    assert score.feasible is True
