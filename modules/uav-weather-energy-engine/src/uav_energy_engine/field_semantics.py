# 维护公开无人机数据集字段语义，并对实际 CSV 做可执行审计。
"""字段语义审计规则，用于阻止不同数据源字段被粗暴混用。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional, Sequence, Union

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DatasetSemantic:
    """定义一个数据源在训练链路中的角色。"""

    dataset: str
    title: str
    role: str
    vehicle: str
    direct_training_use: str
    caution: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class FieldSemantic:
    """定义一个字段的物理含义、单位和使用风险。"""

    dataset: str
    column: str
    canonical: str
    meaning_zh: str
    unit: str
    source_kind: str
    measurement_kind: str
    reference_frame: str
    model_use: str
    risk_level: str
    evidence: tuple[str, ...]


DATASET_SEMANTICS: Dict[str, DatasetSemantic] = {
    "m100": DatasetSemantic(
        dataset="m100",
        title="DJI Matrice 100 小包裹配送飞行位置与能耗数据集",
        role="路线/里程/载荷/能耗校准主数据源",
        vehicle="DJI Matrice 100",
        direct_training_use="适合训练配送路线分段能耗、里程能耗、载荷和设定高度/速度影响。",
        caution="机载风速计原始风字段不是飞行前可直接获得的环境天气，优先用于校准天气风场到机载等效相对风的转换。",
        evidence=(
            "01_M100.../README.txt:238-258",
            "01_M100.../README.txt:330-349",
            "01_M100.../appendix.tex:82-106",
        ),
    ),
    "wemuav": DatasetSemantic(
        dataset="wemuav",
        title="WEMUAV 多旋翼风估计验证数据集",
        role="风/天气/飞行阶段/平均功率辅助数据源",
        vehicle="DJI Phantom 4 Pro",
        direct_training_use="适合补强外部气象站天气、悬停/垂直/定速工况与平均功率目标。",
        caution="不是包裹配送数据；payload 当前只能视作固定无载荷条件，不能代表配送载荷变化。",
        evidence=(
            "03_多旋翼风估计_2022/data/00_README.txt:23-30",
            "03_多旋翼风估计_2022/data/00_README.txt:51-70",
        ),
    ),
    "quadrotor_energy_04": DatasetSemantic(
        dataset="quadrotor_energy_04",
        title="Quadrotor Model for Energy Consumption Analysis",
        role="物理模型与飞控日志候选数据源",
        vehicle="四旋翼实验平台",
        direct_training_use="当前更适合做物理基线和日志解析候选，尚未进入训练表。",
        caution="补充包中确认有飞行日志/航点/参数，但字段还未完成解析审计。",
        evidence=("04_四旋翼能耗分析模型_2022/index.md:20-33",),
    ),
    "weather_constraints_05": DatasetSemantic(
        dataset="weather_constraints_05",
        title="Weather constraints on global drone flyability",
        role="天气变量筛选与可飞边界参考",
        vehicle="非特定单机训练数据",
        direct_training_use="不适合直接做能耗监督训练，可用于天气约束和变量优先级。",
        caution="完整原始数据和额外代码需向作者申请。",
        evidence=("05_全球无人机天气飞行约束_2021/index.md:17-38",),
    ),
}


FIELD_SEMANTICS: list[FieldSemantic] = [
    FieldSemantic(
        dataset="m100",
        column="wind_speed",
        canonical="onboard_airflow_speed_mps",
        meaning_zh="机载超声风速计测得的来流/空速相关幅值，原始数据未完成自机运动修正。",
        unit="m/s",
        source_kind="机载风速计",
        measurement_kind="逐时刻实测",
        reference_frame="相对安装在无人机上的风速计；风向相对北向记录",
        model_use="可用于校准/审计天气风场到机载等效相对风的转换；飞行前部署模型应优先使用 hist_* 环境天气映射。",
        risk_level="high",
        evidence=(
            "01_M100.../README.txt:140-145",
            "01_M100.../README.txt:330-334",
            "01_M100.../appendix.tex:82-106",
        ),
    ),
    FieldSemantic(
        dataset="m100",
        column="wind_angle",
        canonical="onboard_airflow_angle_deg",
        meaning_zh="机载风速计记录的来流角度，角度参考北向，但仍受机体运动和安装扰动影响。",
        unit="deg",
        source_kind="机载风速计",
        measurement_kind="逐时刻实测",
        reference_frame="相对风速计测得的气流方向，角度相对北向",
        model_use="可用于校准/审计天气风场到机载等效相对风的转换；飞行前部署模型不能直接假设可获得。",
        risk_level="high",
        evidence=("01_M100.../README.txt:330-334", "01_M100.../appendix.tex:82-106"),
    ),
    FieldSemantic(
        dataset="m100",
        column="speed",
        canonical="planned_ground_speed_mps",
        meaning_zh="巡航阶段设定的水平地速，不是每个时刻由 GPS 反算的瞬时速度。",
        unit="m/s",
        source_kind="任务参数表/处理后飞行表",
        measurement_kind="任务设定值",
        reference_frame="地面坐标系水平速度",
        model_use="适合作为飞行前任务输入；当前工程约定默认按计划地速处理。",
        risk_level="medium",
        evidence=("01_M100.../README.txt:242-243", "01_M100.../README.txt:418-419"),
    ),
    FieldSemantic(
        dataset="m100",
        column="payload",
        canonical="attached_payload_g",
        meaning_zh="挂载包裹质量，不是整机起飞重量。",
        unit="g",
        source_kind="任务参数表",
        measurement_kind="任务设定值",
        reference_frame="载荷物体质量",
        model_use="训练载荷影响时应与机体基础重量分开处理。",
        risk_level="high",
        evidence=("01_M100.../README.txt:245-246", "01_M100.../README.txt:421-422"),
    ),
    FieldSemantic(
        dataset="m100",
        column="altitude",
        canonical="programmed_altitude_m",
        meaning_zh="预设巡航高度，飞行器垂直起飞至该设定高度。",
        unit="m",
        source_kind="任务参数表",
        measurement_kind="任务设定值",
        reference_frame="任务设定高度",
        model_use="适合作为飞行前任务输入，但不能替代逐时刻 position_z。",
        risk_level="medium",
        evidence=("01_M100.../README.txt:248-249", "01_M100.../README.txt:424-425"),
    ),
    FieldSemantic(
        dataset="m100",
        column="position_z",
        canonical="aircraft_altitude_msl_m",
        meaning_zh="飞行器逐时刻高度，文档描述为相对海平面高度。",
        unit="m",
        source_kind="飞行定位日志",
        measurement_kind="逐时刻实测/估计",
        reference_frame="海平面高度",
        model_use="可用于推断爬升/下降阶段；与 altitude 不是同一语义。",
        risk_level="high",
        evidence=("01_M100.../README.txt:348-349", "01_M100.../README.txt:403-404"),
    ),
    FieldSemantic(
        dataset="m100",
        column="hist_wind_speed_mps",
        canonical="historical_environment_wind_speed_mps",
        meaning_zh="按飞行时间和位置回填的历史环境天气风速。",
        unit="m/s",
        source_kind="外部历史天气",
        measurement_kind="空间/时间插值或邻近匹配",
        reference_frame="物理世界环境风",
        model_use="适合作为飞行前部署模型的天气代理输入。",
        risk_level="medium",
        evidence=("模块历史天气回填产物 data/processed/flights_with_historical_weather_100m.csv",),
    ),
    FieldSemantic(
        dataset="wemuav",
        column="hist_wind_speed_mps",
        canonical="nearby_met_mast_wind_speed_mps",
        meaning_zh="飞行附近气象站/气象仪器给出的环境风速。",
        unit="m/s",
        source_kind="外部气象站",
        measurement_kind="任务时间窗汇总",
        reference_frame="物理世界环境风",
        model_use="适合作为天气/风影响训练字段，但覆盖率需审计。",
        risk_level="medium",
        evidence=("03_多旋翼风估计_2022/data/00_README.txt:26-28", "03_多旋翼风估计_2022/data/00_README.txt:66-70"),
    ),
    FieldSemantic(
        dataset="wemuav",
        column="wind_speed",
        canonical="flight_log_or_weather_wind_speed_mps",
        meaning_zh="统一表中的当前风速字段；可能来自飞行日志，缺失时可能由外部天气补齐。",
        unit="m/s",
        source_kind="飞行日志或外部天气",
        measurement_kind="逐时刻/任务窗混合",
        reference_frame="取决于 wind_speed_source",
        model_use="必须结合 wind_speed_source 使用，不能裸用。",
        risk_level="high",
        evidence=("03_多旋翼风估计_2022/data/00_README.txt:26-30",),
    ),
    FieldSemantic(
        dataset="wemuav",
        column="payload",
        canonical="placeholder_payload_g",
        meaning_zh="当前适配器填充为 0，表示无包裹载荷假设，不代表整机重量。",
        unit="g",
        source_kind="适配器占位",
        measurement_kind="固定条件",
        reference_frame="载荷物体质量",
        model_use="不能用于学习载荷变化，只能作为无载荷工况。",
        risk_level="high",
        evidence=("03_多旋翼风估计_2022/data/00_README.txt:23-30",),
    ),
    FieldSemantic(
        dataset="wemuav",
        column="source_data_type",
        canonical="datcon_export_version",
        meaning_zh="DJI 原始飞行日志经 DatCon 导出的格式版本，例如 datconv3/datconv4。",
        unit="category",
        source_kind="数据集 overview",
        measurement_kind="数据血缘",
        reference_frame="非物理量",
        model_use="用于审计字段别名和单位转换，通常不直接进模型。",
        risk_level="medium",
        evidence=("03_多旋翼风估计_2022/data/00_README.txt:28-30", "03_多旋翼风估计_2022/data/00_README.txt:69-70"),
    ),
]


DATASET_ALIASES = {
    "m100_raw": "m100",
    "m100_historical": "m100",
    "m100_segments": "m100",
    "wemuav_flights": "wemuav",
    "wemuav_segments": "wemuav",
}


def canonical_dataset_name(dataset: str) -> str:
    """将输入标签归一为语义规则中的数据集名。"""

    normalized = str(dataset).strip().lower()
    return DATASET_ALIASES.get(normalized, normalized)


def dataset_semantic_catalog() -> dict[str, dict]:
    """返回当前已整理的数据源语义目录。"""

    return {name: asdict(spec) for name, spec in DATASET_SEMANTICS.items()}


def field_semantic_catalog(dataset: Optional[str] = None) -> list[dict]:
    """返回字段语义目录，可按数据集过滤。"""

    target_dataset = canonical_dataset_name(dataset) if dataset else None
    rows = []
    for item in FIELD_SEMANTICS:
        if target_dataset and item.dataset != target_dataset:
            continue
        rows.append(asdict(item))
    return rows


def _coverage(frame: pd.DataFrame, column: str) -> float:
    """计算列非空覆盖率。"""

    if column not in frame.columns or frame.empty:
        return 0.0
    values = frame[column].replace([np.inf, -np.inf], np.nan)
    return float(values.notna().mean())


def _known_semantics(dataset: str) -> Mapping[str, FieldSemantic]:
    """读取一个数据集的字段语义映射。"""

    return {item.column: item for item in FIELD_SEMANTICS if item.dataset == dataset}


def _warn(warnings: list[dict], level: str, column: str, message: str, action: str) -> None:
    """追加一条审计告警。"""

    warnings.append(
        {
            "level": level,
            "column": column,
            "message": message,
            "recommended_action": action,
        }
    )


def audit_field_semantics(frame: pd.DataFrame, dataset: str, label: Optional[str] = None) -> dict:
    """对一个 DataFrame 执行字段语义审计。"""

    canonical_dataset = canonical_dataset_name(dataset)
    semantics = _known_semantics(canonical_dataset)
    known_present = sorted(column for column in semantics if column in frame.columns)
    important_columns = [
        "flight",
        "time",
        "route",
        "speed",
        "payload",
        "altitude",
        "position_z",
        "battery_voltage",
        "battery_current",
        "wind_speed",
        "wind_angle",
        "hist_wind_speed_mps",
        "hist_wind_dir_deg",
        "hist_temperature_c",
        "hist_pressure_hpa",
        "hist_relative_humidity_pct",
        "segment_energy_wh",
        "segment_wh_per_s",
        "mean_power_w",
        "segment_wh_per_km",
        "source_dataset",
        "source_data_type",
        "wind_speed_source",
        "altitude_source",
    ]
    coverage = {
        column: round(_coverage(frame, column), 6)
        for column in important_columns
        if column in frame.columns
    }
    semantic_rows = []
    warnings: list[dict] = []

    for column in known_present:
        item = semantics[column]
        row = asdict(item)
        row["coverage"] = coverage.get(column, round(_coverage(frame, column), 6))
        semantic_rows.append(row)
        if item.risk_level == "high":
            _warn(
                warnings,
                "high",
                column,
                item.meaning_zh,
                item.model_use,
            )

    if canonical_dataset == "m100":
        if "wind_speed" in frame.columns and "hist_wind_speed_mps" not in frame.columns:
            _warn(
                warnings,
                "high",
                "wind_speed",
                "当前只有机载风速计风字段，缺少飞行前部署口径的外部天气风字段。",
                "训练部署模型前先回填 hist_* 历史天气，或明确该模型是机载上限模型。",
            )
        if {"altitude", "position_z"}.issubset(frame.columns):
            _warn(
                warnings,
                "medium",
                "altitude/position_z",
                "altitude 是任务设定高度，position_z 是逐时刻高度，二者不能互相替代。",
                "分段阶段特征用 position_z，飞行前任务配置用 altitude。",
            )
    if canonical_dataset == "wemuav":
        if "wind_speed" in frame.columns and "wind_speed_source" not in frame.columns:
            _warn(
                warnings,
                "high",
                "wind_speed",
                "WEMUAV 统一风字段可能来自飞行日志或外部天气，但当前表没有来源列。",
                "重新运行 WEMUAV 适配器，保留 wind_speed_source/wind_angle_source。",
            )
        if "payload" in frame.columns:
            payload = pd.to_numeric(frame["payload"], errors="coerce")
            if payload.notna().any() and float(payload.fillna(0.0).abs().max()) == 0.0:
                _warn(
                    warnings,
                    "medium",
                    "payload",
                    "WEMUAV 当前 payload 全为 0，只能表达无包裹载荷工况。",
                    "不要把它用于学习载荷变化；合并训练时增加 source/role 标识。",
                )
        weather_columns = ["hist_wind_speed_mps", "hist_temperature_c", "hist_pressure_hpa", "hist_relative_humidity_pct"]
        available_weather = [column for column in weather_columns if column in frame.columns]
        if available_weather:
            min_weather_coverage = min(_coverage(frame, column) for column in available_weather)
            if min_weather_coverage < 0.95:
                _warn(
                    warnings,
                    "medium",
                    "hist_*",
                    f"WEMUAV 外部天气字段覆盖率最低约 {min_weather_coverage:.1%}，不是全量覆盖。",
                    "天气敏感训练可先使用 weather-complete 子集，并保留缺失率统计。",
                )

    unknown_numeric_columns = []
    for column in frame.columns:
        if column in semantics:
            continue
        if pd.api.types.is_numeric_dtype(frame[column]):
            unknown_numeric_columns.append(column)

    return {
        "label": label or dataset,
        "dataset": canonical_dataset,
        "rows": int(len(frame.index)),
        "columns": int(len(frame.columns)),
        "known_semantic_columns": known_present,
        "known_semantic_count": int(len(known_present)),
        "important_coverage": coverage,
        "field_semantics": semantic_rows,
        "warnings": warnings,
        "unknown_numeric_columns_sample": unknown_numeric_columns[:50],
    }


def audit_csv_semantics(
    input_csv: Union[str, Path],
    dataset: str,
    label: Optional[str] = None,
) -> dict:
    """读取 CSV 并执行字段语义审计。"""

    path = Path(input_csv)
    if not path.exists():
        raise FileNotFoundError(f"字段审计输入不存在: {path}")
    frame = pd.read_csv(path, low_memory=False)
    payload = audit_field_semantics(frame, dataset=dataset, label=label)
    payload["path"] = str(path)
    return payload


def summarize_audits(audits: Iterable[dict]) -> dict:
    """汇总多个数据表的审计结果。"""

    audit_list = list(audits)
    return {
        "dataset_catalog": dataset_semantic_catalog(),
        "audits": audit_list,
        "high_risk_count": int(
            sum(1 for audit in audit_list for warning in audit.get("warnings", []) if warning.get("level") == "high")
        ),
        "warning_count": int(sum(len(audit.get("warnings", [])) for audit in audit_list)),
    }
