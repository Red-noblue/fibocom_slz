# 提供对外统一调用入口，供脚本、前端服务和后续调度层复用。
"""提供对外统一调用入口。"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

from .dataset import (
    build_research_feature_table as _build_research_feature_table,
    build_segment_dataset as _build_segment_dataset,
    build_training_dataset as _build_training_dataset,
    prepare_m100_dataset as _prepare_m100_dataset,
)
from .field_semantics import audit_csv_semantics as _audit_csv_semantics
from .multi_source_training import build_multi_source_training_tables as _build_multi_source_training_tables
from .wemuav_dataset import prepare_wemuav_dataset as _prepare_wemuav_dataset
from .model import train_energy_model as _train_energy_model
from .model import train_target_suite as _train_target_suite
from .optimize import grid_search_fixed_route_speed as _grid_search_fixed_route_speed
from .predict import predict_fixed_route_energy as _predict_fixed_route_energy
from .route_features import (
    build_preflight_training_feature_view as _build_preflight_training_feature_view,
    build_route_time_feature_frame as _build_route_time_feature_frame,
)
from .schema import BatterySpec, MissionSpec, VehicleSpec
from .weather import join_historical_weather as _join_historical_weather


def build_training_dataset_api(
    input_csv: Union[str, Path],
    output_csv: Union[str, Path],
    route: Optional[str] = None,
):
    """对外暴露训练样本构建。"""

    return _build_training_dataset(input_csv=input_csv, output_csv=output_csv, route=route)


def build_research_feature_table_api(
    input_csv: Union[str, Path],
    output_csv: Union[str, Path],
    route: Optional[str] = None,
):
    """对外暴露论文复现特征表构建。"""

    return _build_research_feature_table(input_csv=input_csv, output_csv=output_csv, route=route)


def build_segment_dataset_api(
    input_csv: Union[str, Path],
    output_csv: Union[str, Path],
    route: Optional[str] = None,
    segment_seconds: float = 60.0,
    min_distance_m: float = 50.0,
    min_duration_s: float = 10.0,
):
    """对外暴露分段级训练样本构建。"""

    return _build_segment_dataset(
        input_csv=input_csv,
        output_csv=output_csv,
        route=route,
        segment_seconds=segment_seconds,
        min_distance_m=min_distance_m,
        min_duration_s=min_duration_s,
    )


def prepare_m100_dataset_api(
    dataset_root: Union[str, Path],
    output_csv: Union[str, Path],
    flights_zip: Optional[Union[str, Path]] = None,
    parameters_csv: Optional[Union[str, Path]] = None,
    flight_id_offset: int = 0,
):
    """对外暴露 M100 数据集整理入口。"""

    return _prepare_m100_dataset(
        dataset_root=dataset_root,
        output_csv=output_csv,
        flights_zip=flights_zip,
        parameters_csv=parameters_csv,
        flight_id_offset=flight_id_offset,
    )


def prepare_wemuav_dataset_api(
    dataset_root: Union[str, Path],
    output_csv: Union[str, Path],
    overview_csv: Optional[Union[str, Path]] = None,
    flight_id_offset: int = 1_000_000,
    max_cases: Optional[int] = None,
):
    """对外暴露 WEMUAV 数据集整理入口。"""

    return _prepare_wemuav_dataset(
        dataset_root=dataset_root,
        output_csv=output_csv,
        overview_csv=overview_csv,
        flight_id_offset=flight_id_offset,
        max_cases=max_cases,
    )


def join_historical_weather_api(
    input_csv: Union[str, Path],
    output_csv: Union[str, Path],
    weather_config: Union[str, Path],
    route: Optional[str] = None,
    timezone: str = "America/New_York",
    cache_precision: int = 2,
):
    """对外暴露历史天气回填入口。"""

    return _join_historical_weather(
        input_csv=input_csv,
        output_csv=output_csv,
        weather_config=weather_config,
        route=route,
        timezone=timezone,
        cache_precision=cache_precision,
    )


def build_route_time_feature_frame_api(
    mission: MissionSpec,
    vehicle: VehicleSpec,
    weather_frame,
    weather_source: str = "forecast_weather",
    feature_source: str = "weather_adapter",
):
    """对外暴露飞行前天气到路线时序特征的适配入口。"""

    return _build_route_time_feature_frame(
        mission=mission,
        vehicle=vehicle,
        weather_frame=weather_frame,
        weather_source=weather_source,
        feature_source=feature_source,
    )


def build_preflight_training_feature_view_api(
    segment_frame,
    weather_source: str = "historical_weather",
    feature_source: str = "preflight_training_view",
):
    """对外暴露部署口径训练视图构建。"""

    return _build_preflight_training_feature_view(
        segment_frame=segment_frame,
        weather_source=weather_source,
        feature_source=feature_source,
    )


def train_energy_model_api(
    features_csv: Union[str, Path],
    model_out: Union[str, Path],
    metrics_out: Union[str, Path],
    random_state: int = 42,
    method: str = "linear_residual_gb",
    target: str = "energy_wh_per_km",
):
    """对外暴露模型训练。"""

    return _train_energy_model(
        features_csv=features_csv,
        model_out=model_out,
        metrics_out=metrics_out,
        random_state=random_state,
        method=method,
        target=target,
    )


def audit_csv_semantics_api(
    input_csv: Union[str, Path],
    dataset: str,
    label: Optional[str] = None,
):
    """对外暴露字段语义审计入口。"""

    return _audit_csv_semantics(input_csv=input_csv, dataset=dataset, label=label)


def build_multi_source_training_tables_api(
    output_dir: Union[str, Path],
    m100_input_csv: Optional[Union[str, Path]] = None,
    wemuav_input_csv: Optional[Union[str, Path]] = None,
    segment_seconds: float = 60.0,
    min_duration_s: float = 10.0,
    m100_min_distance_m: float = 50.0,
    wemuav_min_distance_m: float = 0.1,
    m100_route: Optional[str] = None,
    wemuav_route: Optional[str] = None,
):
    """对外暴露多来源训练表构建入口。"""

    return _build_multi_source_training_tables(
        output_dir=output_dir,
        m100_input_csv=m100_input_csv,
        wemuav_input_csv=wemuav_input_csv,
        segment_seconds=segment_seconds,
        min_duration_s=min_duration_s,
        m100_min_distance_m=m100_min_distance_m,
        wemuav_min_distance_m=wemuav_min_distance_m,
        m100_route=m100_route,
        wemuav_route=wemuav_route,
    )


def train_target_suite_api(
    features_csv: Union[str, Path],
    model_dir: Union[str, Path],
    metrics_out: Union[str, Path],
    methods: List[str],
    targets: List[str],
    random_state: int = 42,
):
    """对外暴露多目标多方法训练入口。"""

    return _train_target_suite(
        features_csv=features_csv,
        model_dir=model_dir,
        metrics_out=metrics_out,
        methods=methods,
        targets=targets,
        random_state=random_state,
    )


def predict_fixed_route_api(
    model_path: Union[str, Path],
    weather_config: Union[str, Path],
    mission: MissionSpec,
    vehicle: VehicleSpec,
    battery: BatterySpec,
):
    """对外暴露固定路线预测。"""

    return _predict_fixed_route_energy(
        model_path=model_path,
        weather_config=weather_config,
        mission=mission,
        vehicle=vehicle,
        battery=battery,
    )


def run_speed_ablation_api(
    model_path: Union[str, Path],
    weather_config: Union[str, Path],
    mission: MissionSpec,
    vehicle: VehicleSpec,
    battery: BatterySpec,
    speeds_mps: List[float],
):
    """对外暴露固定路线速度搜索。"""

    return _grid_search_fixed_route_speed(
        model_path=model_path,
        weather_config=weather_config,
        mission=mission,
        vehicle=vehicle,
        battery=battery,
        speeds_mps=speeds_mps,
    )


build_training_dataset = build_training_dataset_api
build_research_feature_table = build_research_feature_table_api
build_segment_dataset = build_segment_dataset_api
build_multi_source_training_tables = build_multi_source_training_tables_api
audit_csv_semantics = audit_csv_semantics_api
build_route_time_feature_frame = build_route_time_feature_frame_api
build_preflight_training_feature_view = build_preflight_training_feature_view_api
prepare_m100_dataset = prepare_m100_dataset_api
prepare_wemuav_dataset = prepare_wemuav_dataset_api
join_historical_weather = join_historical_weather_api
train_energy_model = train_energy_model_api
train_target_suite = train_target_suite_api
predict_fixed_route = predict_fixed_route_api
run_speed_ablation = run_speed_ablation_api
