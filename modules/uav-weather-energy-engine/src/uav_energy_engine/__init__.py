# 天气驱动无人机能耗引擎的公共导出入口。
"""天气驱动无人机能耗引擎的公共导出入口。"""

from .api import (
    audit_csv_semantics,
    build_research_feature_table,
    build_multi_source_training_tables,
    build_preflight_training_feature_view,
    build_route_time_feature_frame,
    build_segment_dataset,
    build_training_dataset,
    join_historical_weather,
    prepare_m100_dataset,
    prepare_wemuav_dataset,
    predict_fixed_route,
    run_speed_ablation,
    train_energy_model,
    train_target_suite,
)

__all__ = [
    "audit_csv_semantics",
    "build_research_feature_table",
    "build_multi_source_training_tables",
    "build_preflight_training_feature_view",
    "build_route_time_feature_frame",
    "build_segment_dataset",
    "build_training_dataset",
    "join_historical_weather",
    "prepare_m100_dataset",
    "prepare_wemuav_dataset",
    "predict_fixed_route",
    "run_speed_ablation",
    "train_energy_model",
    "train_target_suite",
]
