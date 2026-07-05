# 中文说明：本文件提供基础命令行入口，用于快速运行 Q-learning 策略对比实验。
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .analysis import analyze_scenario_sweep, analyze_single_run
from .dashboard import (
    DEFAULT_DASHBOARD_OUTPUT,
    DEFAULT_SCENARIO_DIR,
    DEFAULT_STABILITY_DIR,
    DEFAULT_TRAINED_POLICY_OUTPUT,
    export_dashboard_payload,
    export_trained_policy_snapshot,
)
from .interface import PolicyStatePayload, build_interface_contract, decide_policy
from .scenarios import (
    list_coverage_scenario_names,
    make_conservative_offloading_config_for_coverage,
    make_offloading_config_for_coverage,
)
from .simulation import (
    StrategySuiteResult,
    build_decision_trace_rows,
    build_learning_curve_rows,
    build_policy_table_rows,
    evaluate_trained_q_learning,
    run_basic_strategy_suite,
)
from .stability import run_task_semantics_stability
from .three_tier_analysis import analyze_three_tier_sweep, validate_three_tier_stability
from .webserver import (
    DEFAULT_POLICY_SEED,
    DEFAULT_POLICY_SLOTS,
    DEFAULT_WEB_HOST,
    DEFAULT_WEB_PORT,
    run_web_server,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="运行基础 Q-learning 计算卸载策略实验。")
    subparsers = parser.add_subparsers(dest="command")

    run_demo = subparsers.add_parser("run-demo", help="运行基础策略对比实验")
    run_demo.add_argument("--slots", type=int, default=3000, help="仿真时隙数")
    run_demo.add_argument("--seed", type=int, default=0, help="随机种子")
    run_demo.add_argument(
        "--coverage-scenario",
        choices=list_coverage_scenario_names(),
        default="balanced",
        help="覆盖/边缘负载场景",
    )
    run_demo.add_argument("--output-dir", type=Path, default=Path("outputs/qlearning_policy/demo"), help="输出目录")

    run_scenarios = subparsers.add_parser("run-scenarios", help="批量运行所有覆盖场景")
    run_scenarios.add_argument("--slots", type=int, default=3000, help="每个场景的仿真时隙数")
    run_scenarios.add_argument("--seed", type=int, default=0, help="随机种子")
    run_scenarios.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/qlearning_policy/scenario_sweep"),
        help="批量场景输出目录",
    )

    analyze_scenarios = subparsers.add_parser("analyze-scenarios", help="分析批量场景结果")
    analyze_scenarios.add_argument(
        "--input-dir",
        type=Path,
        default=Path("outputs/qlearning_policy/scenario_sweep"),
        help="run-scenarios 的输出目录",
    )
    analyze_scenarios.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="分析产物输出目录，默认写入 input-dir/analysis",
    )

    analyze_three_tier = subparsers.add_parser("analyze-three-tier", help="分析端-边-云三层卸载专项结果")
    analyze_three_tier.add_argument(
        "--input-dir",
        type=Path,
        default=Path("outputs/qlearning_policy/scenario_sweep"),
        help="run-scenarios 的输出目录",
    )
    analyze_three_tier.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="三层分析产物输出目录，默认写入 input-dir/three_tier_analysis",
    )

    validate_three_tier = subparsers.add_parser("validate-three-tier", help="多 seed 验证端-边-云三层卸载趋势")
    validate_three_tier.add_argument("--slots", type=int, default=8000, help="每个场景/seed 的训练时隙数")
    validate_three_tier.add_argument("--seeds", default="1,2,3", help="逗号分隔的随机种子")
    validate_three_tier.add_argument(
        "--coverage-scenario",
        default="all",
        help="覆盖场景名称；传入 all 时批量验证所有场景",
    )
    validate_three_tier.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/qlearning_policy/three_tier_stability"),
        help="三层稳定性验证输出目录",
    )

    analyze_run = subparsers.add_parser("analyze-run", help="分析单个 run-demo 输出目录")
    analyze_run.add_argument("--input-dir", type=Path, required=True, help="run-demo 的输出目录")
    analyze_run.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="分析产物输出目录，默认写入 input-dir/analysis",
    )
    analyze_run.add_argument("--scenario-name", default="run", help="分析表中的场景名称")

    compare_conservative = subparsers.add_parser("compare-conservative", help="对比默认版与保守卸载版")
    compare_conservative.add_argument("--slots", type=int, default=3000, help="每个版本的仿真时隙数")
    compare_conservative.add_argument("--seed", type=int, default=0, help="随机种子")
    compare_conservative.add_argument(
        "--coverage-scenario",
        default="weak_coverage",
        help="覆盖场景名称；传入 all 时批量对比所有场景",
    )
    compare_conservative.add_argument(
        "--low-link-offload-penalty",
        type=float,
        default=16.0,
        help="低链路状态下每个卸载任务的额外惩罚",
    )
    compare_conservative.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/qlearning_policy/conservative_compare"),
        help="保守卸载对比输出目录",
    )

    validate_task_semantics = subparsers.add_parser("validate-task-semantics", help="多场景多 seed 验证任务语义趋势")
    validate_task_semantics.add_argument("--slots", type=int, default=8000, help="每个场景/seed 的训练时隙数")
    validate_task_semantics.add_argument("--seeds", default="1,2,3", help="逗号分隔的随机种子")
    validate_task_semantics.add_argument(
        "--coverage-scenario",
        default="all",
        help="覆盖场景名称；传入 all 时批量验证所有场景",
    )
    validate_task_semantics.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/qlearning_policy/task_semantics_stability"),
        help="任务语义稳定性验证输出目录",
    )

    describe_interface = subparsers.add_parser("describe-interface", help="输出本模块对外接口契约")
    describe_interface.set_defaults(command="describe-interface")

    decide = subparsers.add_parser("decide", help="按对外接口输入状态，输出一次策略决策")
    decide.add_argument("--coverage-scenario", default="balanced", help="覆盖场景名称")
    decide.add_argument("--policy-table", type=Path, default=None, help="可选：训练后的 policy_table.csv")
    decide.add_argument("--state-json", type=Path, default=None, help="可选：包含状态字段的 JSON 文件")
    decide.add_argument("--queue", type=int, default=8, help="任务队列长度")
    decide.add_argument("--link", type=int, default=1, help="链路质量等级")
    decide.add_argument("--battery", type=int, default=4, help="电量等级")
    decide.add_argument("--edge-load", type=int, default=1, help="边缘负载等级")
    decide.add_argument("--cloud-load", type=int, default=1, help="云端负载等级")
    decide.add_argument("--task-urgency", type=int, default=1, help="任务紧急度")
    decide.add_argument("--data-sensitivity", type=int, default=1, help="数据敏感等级")
    decide.add_argument("--area-risk", type=int, default=1, help="区域风险等级")

    export_dashboard = subparsers.add_parser("export-dashboard-data", help="导出前端仪表盘 JSON 数据")
    export_dashboard.add_argument("--stability-dir", type=Path, default=DEFAULT_STABILITY_DIR, help="方案3稳定性产物目录")
    export_dashboard.add_argument("--scenario-dir", type=Path, default=DEFAULT_SCENARIO_DIR, help="多场景实验产物目录")
    export_dashboard.add_argument("--output-path", type=Path, default=DEFAULT_DASHBOARD_OUTPUT, help="前端 JSON 输出路径")

    export_trained_policy = subparsers.add_parser("export-trained-policy", help="训练并导出前端可查表的 Q-learning 策略快照")
    export_trained_policy.add_argument("--slots", type=int, default=8000, help="每个场景训练时隙数")
    export_trained_policy.add_argument("--seed", type=int, default=31, help="随机种子")
    export_trained_policy.add_argument(
        "--coverage-scenario",
        default="all",
        help="覆盖场景名称；传入 all 时导出全部场景",
    )
    export_trained_policy.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_TRAINED_POLICY_OUTPUT,
        help="训练策略快照 JSON 输出路径",
    )

    serve_web = subparsers.add_parser("serve-web", help="启动带 act/step/rollout API 的前端服务")
    serve_web.add_argument("--host", default=DEFAULT_WEB_HOST, help="监听地址")
    serve_web.add_argument("--port", type=int, default=DEFAULT_WEB_PORT, help="监听端口")
    serve_web.add_argument(
        "--static-dir",
        type=Path,
        default=Path("web"),
        help="静态前端目录",
    )
    serve_web.add_argument(
        "--dashboard-path",
        type=Path,
        default=DEFAULT_DASHBOARD_OUTPUT,
        help="前端仪表盘 JSON 路径",
    )
    serve_web.add_argument(
        "--trained-policy-path",
        type=Path,
        default=DEFAULT_TRAINED_POLICY_OUTPUT,
        help="训练策略快照 JSON 路径",
    )
    serve_web.add_argument("--policy-slots", type=int, default=DEFAULT_POLICY_SLOTS, help="缺失策略快照时的训练时隙数")
    serve_web.add_argument("--policy-seed", type=int, default=DEFAULT_POLICY_SEED, help="缺失策略快照时的训练随机种子")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        args = parser.parse_args(["run-demo"])

    if args.command == "run-demo":
        output_dir: Path = args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        config = make_offloading_config_for_coverage(args.coverage_scenario)
        suite = run_basic_strategy_suite(config=config, slots=args.slots, seed=args.seed)
        rows, artifacts = _write_suite_outputs(output_dir=output_dir, suite=suite)

        print(
            json.dumps(
                {
                    "output_dir": str(output_dir),
                    "coverage_scenario": args.coverage_scenario,
                    "rows": rows,
                    "artifacts": artifacts,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "run-scenarios":
        output_dir: Path = args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        summary_rows: list[dict[str, float | int | str]] = []
        scenario_artifacts: dict[str, dict[str, str]] = {}

        for scenario_name in list_coverage_scenario_names():
            scenario_dir = output_dir / scenario_name
            scenario_dir.mkdir(parents=True, exist_ok=True)
            config = make_offloading_config_for_coverage(scenario_name)
            suite = run_basic_strategy_suite(config=config, slots=args.slots, seed=args.seed)
            rows, artifacts = _write_suite_outputs(output_dir=scenario_dir, suite=suite)
            scenario_artifacts[scenario_name] = artifacts
            summary_rows.extend({"coverage_scenario": scenario_name, **row} for row in rows)

        summary_csv_path = output_dir / "scenario_strategy_metrics.csv"
        _write_csv(summary_csv_path, summary_rows)
        summary_json_path = output_dir / "scenario_strategy_metrics.json"
        summary_json_path.write_text(json.dumps(summary_rows, ensure_ascii=False, indent=2), encoding="utf-8")

        print(
            json.dumps(
                {
                    "output_dir": str(output_dir),
                    "coverage_scenarios": list(list_coverage_scenario_names()),
                    "summary_rows": summary_rows,
                    "artifacts": {
                        "scenario_strategy_metrics_csv": str(summary_csv_path),
                        "scenario_strategy_metrics_json": str(summary_json_path),
                        "scenario_dirs": scenario_artifacts,
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "analyze-scenarios":
        artifacts = analyze_scenario_sweep(input_dir=args.input_dir, output_dir=args.output_dir)
        print(json.dumps({"input_dir": str(args.input_dir), "artifacts": artifacts}, ensure_ascii=False, indent=2))
        return

    if args.command == "analyze-three-tier":
        artifacts = analyze_three_tier_sweep(input_dir=args.input_dir, output_dir=args.output_dir)
        print(json.dumps({"input_dir": str(args.input_dir), "artifacts": artifacts}, ensure_ascii=False, indent=2))
        return

    if args.command == "validate-three-tier":
        scenario_names = (
            list_coverage_scenario_names()
            if args.coverage_scenario == "all"
            else (args.coverage_scenario,)
        )
        seeds = _parse_int_tuple(args.seeds)
        artifacts = validate_three_tier_stability(
            scenario_names=tuple(scenario_names),
            seeds=seeds,
            slots=args.slots,
            output_dir=args.output_dir,
        )
        print(
            json.dumps(
                {
                    "output_dir": str(args.output_dir),
                    "coverage_scenarios": list(scenario_names),
                    "seeds": list(seeds),
                    "slots": args.slots,
                    "artifacts": artifacts,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "describe-interface":
        print(json.dumps(build_interface_contract(), ensure_ascii=False, indent=2))
        return

    if args.command == "decide":
        state_payload = _load_policy_state_payload(args)
        decision = decide_policy(
            state_payload,
            scenario_name=args.coverage_scenario,
            policy_table_path=args.policy_table,
        )
        print(json.dumps(decision.as_dict(), ensure_ascii=False, indent=2))
        return

    if args.command == "export-dashboard-data":
        artifacts = export_dashboard_payload(
            stability_dir=args.stability_dir,
            scenario_dir=args.scenario_dir,
            output_path=args.output_path,
        )
        print(json.dumps({"artifacts": artifacts}, ensure_ascii=False, indent=2))
        return

    if args.command == "export-trained-policy":
        scenario_names = (
            list_coverage_scenario_names()
            if args.coverage_scenario == "all"
            else (args.coverage_scenario,)
        )
        artifacts = export_trained_policy_snapshot(
            scenario_names=tuple(scenario_names),
            slots=args.slots,
            seed=args.seed,
            output_path=args.output_path,
        )
        print(json.dumps({"artifacts": artifacts}, ensure_ascii=False, indent=2))
        return

    if args.command == "serve-web":
        run_web_server(
            host=args.host,
            port=args.port,
            static_dir=args.static_dir,
            dashboard_path=args.dashboard_path,
            trained_policy_path=args.trained_policy_path,
            policy_slots=args.policy_slots,
            policy_seed=args.policy_seed,
        )
        return

    if args.command == "analyze-run":
        artifacts = analyze_single_run(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            scenario_name=args.scenario_name,
        )
        print(json.dumps({"input_dir": str(args.input_dir), "artifacts": artifacts}, ensure_ascii=False, indent=2))
        return

    if args.command == "compare-conservative":
        output_dir: Path = args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        scenario_names = (
            list_coverage_scenario_names()
            if args.coverage_scenario == "all"
            else (args.coverage_scenario,)
        )
        summary_rows: list[dict[str, float | int | str]] = []
        delta_rows: list[dict[str, float | int | str]] = []
        variant_artifacts: dict[str, dict[str, dict[str, str]]] = {}

        for scenario_name in scenario_names:
            base_config = make_offloading_config_for_coverage(scenario_name)
            conservative_config = make_conservative_offloading_config_for_coverage(
                scenario_name,
                low_link_offload_penalty=args.low_link_offload_penalty,
            )
            scenario_artifacts: dict[str, dict[str, str]] = {}
            variant_rows: dict[str, list[dict[str, float | int | str]]] = {}

            for variant_name, config in (("base", base_config), ("conservative", conservative_config)):
                variant_dir = output_dir / scenario_name / variant_name
                variant_dir.mkdir(parents=True, exist_ok=True)
                suite = run_basic_strategy_suite(config=config, slots=args.slots, seed=args.seed)
                rows, artifacts = _write_suite_outputs(output_dir=variant_dir, suite=suite)
                greedy_metrics = evaluate_trained_q_learning(suite.q_learning, slots=args.slots, seed=args.seed)
                rows = [*rows, {"strategy": "q_learning_greedy", **greedy_metrics.as_dict()}]
                scenario_artifacts[variant_name] = artifacts
                variant_rows[variant_name] = rows
                summary_rows.extend(
                    {
                        "coverage_scenario": scenario_name,
                        "variant": variant_name,
                        "low_link_offload_penalty": config.low_link_offload_penalty,
                        "low_link_penalty_threshold": config.low_link_penalty_threshold,
                        **row,
                    }
                    for row in rows
                )

            delta_rows.append(_build_qlearning_delta_row(scenario_name, variant_rows))
            variant_artifacts[scenario_name] = scenario_artifacts

        summary_csv_path = output_dir / "conservative_comparison.csv"
        _write_csv(summary_csv_path, summary_rows)
        summary_json_path = output_dir / "conservative_comparison.json"
        summary_json_path.write_text(json.dumps(summary_rows, ensure_ascii=False, indent=2), encoding="utf-8")

        delta_csv_path = output_dir / "qlearning_conservative_delta.csv"
        _write_csv(delta_csv_path, delta_rows)
        delta_json_path = output_dir / "qlearning_conservative_delta.json"
        delta_json_path.write_text(json.dumps(delta_rows, ensure_ascii=False, indent=2), encoding="utf-8")

        print(
            json.dumps(
                {
                    "output_dir": str(output_dir),
                    "coverage_scenarios": list(scenario_names),
                    "low_link_offload_penalty": args.low_link_offload_penalty,
                    "summary_rows": summary_rows,
                    "delta_rows": delta_rows,
                    "artifacts": {
                        "conservative_comparison_csv": str(summary_csv_path),
                        "conservative_comparison_json": str(summary_json_path),
                        "qlearning_conservative_delta_csv": str(delta_csv_path),
                        "qlearning_conservative_delta_json": str(delta_json_path),
                        "scenario_variant_dirs": variant_artifacts,
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.command == "validate-task-semantics":
        scenario_names = (
            list_coverage_scenario_names()
            if args.coverage_scenario == "all"
            else (args.coverage_scenario,)
        )
        seeds = _parse_int_tuple(args.seeds)
        artifacts = run_task_semantics_stability(
            scenario_names=tuple(scenario_names),
            seeds=seeds,
            slots=args.slots,
            output_dir=args.output_dir,
        )
        print(
            json.dumps(
                {
                    "output_dir": str(args.output_dir),
                    "coverage_scenarios": list(scenario_names),
                    "seeds": list(seeds),
                    "slots": args.slots,
                    "artifacts": artifacts,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    raise SystemExit(f"未知命令：{args.command}")


def _load_policy_state_payload(args: argparse.Namespace) -> PolicyStatePayload:
    if args.state_json is not None:
        payload = json.loads(args.state_json.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise SystemExit("state-json 顶层必须是 JSON 对象")
        return PolicyStatePayload.from_mapping(payload)
    return PolicyStatePayload(
        queue=args.queue,
        link=args.link,
        battery=args.battery,
        edge_load=args.edge_load,
        cloud_load=args.cloud_load,
        task_urgency=args.task_urgency,
        data_sensitivity=args.data_sensitivity,
        area_risk=args.area_risk,
    )


def _write_suite_outputs(
    *,
    output_dir: Path,
    suite: StrategySuiteResult,
) -> tuple[list[dict[str, float | int | str]], dict[str, str]]:
    rows: list[dict[str, float | int | str]] = [
        {"strategy": name, **result.as_dict()} for name, result in suite.metrics_by_strategy.items()
    ]

    csv_path = output_dir / "strategy_metrics.csv"
    _write_csv(csv_path, rows)

    json_path = output_dir / "strategy_metrics.json"
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    decision_trace_rows = build_decision_trace_rows(suite.q_learning)
    decision_trace_path = output_dir / "decision_trace.csv"
    _write_csv(decision_trace_path, decision_trace_rows)

    learning_curve_rows = build_learning_curve_rows(suite.q_learning)
    learning_curve_path = output_dir / "learning_curve.csv"
    _write_csv(learning_curve_path, learning_curve_rows)

    policy_table_rows = build_policy_table_rows(suite.q_learning)
    policy_table_path = output_dir / "policy_table.csv"
    _write_csv(policy_table_path, policy_table_rows)

    return rows, {
        "strategy_metrics_csv": str(csv_path),
        "strategy_metrics_json": str(json_path),
        "decision_trace_csv": str(decision_trace_path),
        "learning_curve_csv": str(learning_curve_path),
        "policy_table_csv": str(policy_table_path),
    }


def _write_csv(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    if not rows:
        raise ValueError("rows must not be empty")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _build_qlearning_delta_row(
    scenario_name: str,
    variant_rows: dict[str, list[dict[str, float | int | str]]],
) -> dict[str, float | int | str]:
    base = _find_strategy_metrics(variant_rows["base"], "q_learning")
    conservative = _find_strategy_metrics(variant_rows["conservative"], "q_learning")
    base_greedy = _find_strategy_metrics(variant_rows["base"], "q_learning_greedy")
    conservative_greedy = _find_strategy_metrics(variant_rows["conservative"], "q_learning_greedy")
    return {
        "coverage_scenario": scenario_name,
        "base_average_reward": float(base["average_reward"]),
        "conservative_average_reward": float(conservative["average_reward"]),
        "reward_delta": float(conservative["average_reward"]) - float(base["average_reward"]),
        "base_offload_ratio": float(base["offload_ratio"]),
        "conservative_offload_ratio": float(conservative["offload_ratio"]),
        "offload_ratio_delta": float(conservative["offload_ratio"]) - float(base["offload_ratio"]),
        "base_average_delay": float(base["average_delay"]),
        "conservative_average_delay": float(conservative["average_delay"]),
        "delay_delta": float(conservative["average_delay"]) - float(base["average_delay"]),
        "base_average_energy": float(base["average_energy"]),
        "conservative_average_energy": float(conservative["average_energy"]),
        "energy_delta": float(conservative["average_energy"]) - float(base["average_energy"]),
        "base_processed_tasks": int(base["processed_tasks"]),
        "conservative_processed_tasks": int(conservative["processed_tasks"]),
        "processed_tasks_delta": int(conservative["processed_tasks"]) - int(base["processed_tasks"]),
        "base_greedy_average_reward": float(base_greedy["average_reward"]),
        "conservative_greedy_average_reward": float(conservative_greedy["average_reward"]),
        "greedy_reward_delta": float(conservative_greedy["average_reward"]) - float(base_greedy["average_reward"]),
        "base_greedy_offload_ratio": float(base_greedy["offload_ratio"]),
        "conservative_greedy_offload_ratio": float(conservative_greedy["offload_ratio"]),
        "greedy_offload_ratio_delta": float(conservative_greedy["offload_ratio"]) - float(base_greedy["offload_ratio"]),
        "base_greedy_processed_tasks": int(base_greedy["processed_tasks"]),
        "conservative_greedy_processed_tasks": int(conservative_greedy["processed_tasks"]),
        "greedy_processed_tasks_delta": int(conservative_greedy["processed_tasks"]) - int(base_greedy["processed_tasks"]),
    }


def _find_strategy_metrics(rows: list[dict[str, float | int | str]], strategy: str) -> dict[str, float | int | str]:
    for row in rows:
        if row["strategy"] == strategy:
            return row
    raise ValueError(f"missing strategy metrics: {strategy}")


def _parse_int_tuple(value: str) -> tuple[int, ...]:
    try:
        parsed = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    except ValueError as exc:
        raise SystemExit(f"随机种子格式错误：{value}") from exc
    if not parsed:
        raise SystemExit("至少需要一个随机种子")
    return parsed


if __name__ == "__main__":
    main()
