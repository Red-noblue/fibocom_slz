# 中文说明：本测试文件验证基础 Q-learning 策略框架的状态编码、环境转移和训练流程。
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from qlearning_policy import (
    OffloadingAction,
    OffloadingConfig,
    OffloadingEnv,
    OffloadingState,
    PolicyStatePayload,
    QLearningParams,
    StateCodec,
    build_interface_contract,
    decide_policy,
    list_coverage_scenario_names,
    make_conservative_offloading_config_for_coverage,
    make_offloading_config_for_coverage,
)
from qlearning_policy.dashboard import export_trained_policy_snapshot
from qlearning_policy.cli import main
from qlearning_policy.simulation import (
    build_policy_table_rows,
    compare_basic_strategies,
    evaluate_trained_q_learning,
    train_q_learning,
)
from qlearning_policy.webserver import (
    TrainedPolicyStore,
    build_act_response,
    build_rollout_response,
    build_step_response,
)


def test_state_codec_roundtrip() -> None:
    codec = StateCodec((("queue", 3), ("link", 2), ("battery", 4)))
    state = {"queue": 2, "link": 1, "battery": 3}
    encoded = codec.encode(state)
    assert codec.decode(encoded) == state


def test_environment_step_keeps_state_in_range() -> None:
    env = OffloadingEnv(seed=1)
    state = env.reset()
    result = env.step(state, OffloadingAction(local_tasks=0, offload_tasks=0))

    assert 0 <= result.next_state.queue <= env.config.queue_capacity
    assert 0 <= result.next_state.link < len(env.config.link_rates_bps)
    assert 0 <= result.next_state.battery < env.config.battery_level_count
    assert 0 <= result.next_state.edge_load < len(env.config.edge_load_levels)
    assert 0 <= result.next_state.cloud_load < len(env.config.cloud_load_levels)


def test_illegal_action_executes_idle_with_penalty() -> None:
    env = OffloadingEnv(seed=2)
    state = env.reset()
    result = env.step(state, OffloadingAction(local_tasks=2, offload_tasks=2))

    assert result.breakdown.executed_action == OffloadingAction(0, 0)
    assert result.breakdown.illegal_penalty == env.config.illegal_action_penalty


def test_training_returns_finite_metrics_and_q_table() -> None:
    config = OffloadingConfig(queue_capacity=8)
    params = QLearningParams(alpha=0.2, gamma=0.9, epsilon=0.2)
    result = train_q_learning(config=config, params=params, slots=128, seed=3)

    assert result.agent.q_table.shape == (OffloadingEnv(config).codec.size, len(OffloadingEnv(config).actions))
    assert result.rewards.shape == (128,)
    assert math.isfinite(result.metrics.average_reward)
    assert result.metrics.processed_tasks >= 0


def test_trained_q_learning_greedy_evaluation_returns_metrics() -> None:
    result = train_q_learning(config=OffloadingConfig(queue_capacity=8), slots=64, seed=3)
    metrics = evaluate_trained_q_learning(result, slots=32, seed=3)

    assert math.isfinite(metrics.average_reward)
    assert 0.0 <= metrics.offload_ratio <= 1.0


def test_coverage_scenario_overrides_link_probabilities() -> None:
    config = make_offloading_config_for_coverage("weak_coverage")

    assert config.link_probs == (0.70, 0.25, 0.05)
    assert sum(config.link_probs) == 1.0


def test_conservative_config_penalizes_low_link_offloading() -> None:
    base_config = make_offloading_config_for_coverage("weak_coverage")
    conservative_config = make_conservative_offloading_config_for_coverage(
        "weak_coverage",
        low_link_offload_penalty=8.0,
    )

    base_env = OffloadingEnv(config=base_config)
    conservative_env = OffloadingEnv(config=conservative_config)
    low_link_state = OffloadingState(
        queue=16,
        link=0,
        battery=4,
        edge_load=1,
        task_urgency=1,
        data_sensitivity=1,
        area_risk=1,
    )
    action = OffloadingAction(local_tasks=2, offload_tasks=2)

    base_reward = base_env.compute_reward(low_link_state, action)
    conservative_reward = conservative_env.compute_reward(low_link_state, action)

    assert conservative_reward.low_link_offload_penalty == 16.0
    assert math.isclose(conservative_reward.reward, base_reward.reward - 16.0)


def test_task_semantics_penalize_delay_and_sensitive_offloading() -> None:
    env = OffloadingEnv()
    action = OffloadingAction(local_tasks=0, offload_tasks=1)
    low_semantic_state = OffloadingState(
        queue=8,
        link=1,
        battery=4,
        edge_load=1,
        task_urgency=0,
        data_sensitivity=0,
        area_risk=0,
    )
    high_semantic_state = OffloadingState(
        queue=8,
        link=1,
        battery=4,
        edge_load=1,
        task_urgency=2,
        data_sensitivity=2,
        area_risk=2,
    )

    low = env.compute_reward(low_semantic_state, action)
    high = env.compute_reward(high_semantic_state, action)

    assert high.urgency_delay_penalty > low.urgency_delay_penalty
    assert high.deadline_miss_penalty >= low.deadline_miss_penalty
    assert high.data_sensitivity_penalty > low.data_sensitivity_penalty
    assert high.area_risk_penalty > low.area_risk_penalty
    assert high.reward < low.reward


def test_deadline_miss_penalty_increases_for_urgent_tasks() -> None:
    env = OffloadingEnv()
    action = OffloadingAction(local_tasks=0, offload_tasks=2)
    relaxed_state = OffloadingState(
        queue=16,
        link=0,
        battery=4,
        edge_load=2,
        task_urgency=0,
        data_sensitivity=0,
        area_risk=0,
    )
    urgent_state = OffloadingState(
        queue=16,
        link=0,
        battery=4,
        edge_load=2,
        task_urgency=2,
        data_sensitivity=0,
        area_risk=0,
    )

    relaxed = env.compute_reward(relaxed_state, action)
    urgent = env.compute_reward(urgent_state, action)

    assert relaxed.delay == urgent.delay
    assert urgent.deadline_miss_penalty > relaxed.deadline_miss_penalty
    assert urgent.reward < relaxed.reward


def test_three_tier_reward_penalizes_low_link_cloud_and_congested_edge() -> None:
    env = OffloadingEnv()
    low_link_state = OffloadingState(
        queue=16,
        link=0,
        battery=4,
        edge_load=1,
        cloud_load=0,
        task_urgency=1,
        data_sensitivity=0,
        area_risk=0,
    )
    high_link_state = OffloadingState(
        queue=16,
        link=2,
        battery=4,
        edge_load=1,
        cloud_load=0,
        task_urgency=1,
        data_sensitivity=0,
        area_risk=0,
    )
    low_link_cloud = env.compute_reward(low_link_state, OffloadingAction(local_tasks=0, offload_tasks=0, cloud_tasks=1))
    high_link_cloud = env.compute_reward(high_link_state, OffloadingAction(local_tasks=0, offload_tasks=0, cloud_tasks=1))

    congested_edge_state = OffloadingState(
        queue=16,
        link=2,
        battery=4,
        edge_load=2,
        cloud_load=0,
        task_urgency=1,
        data_sensitivity=0,
        area_risk=0,
    )
    normal_edge_state = OffloadingState(
        queue=16,
        link=2,
        battery=4,
        edge_load=1,
        cloud_load=0,
        task_urgency=1,
        data_sensitivity=0,
        area_risk=0,
    )
    congested_edge = env.compute_reward(congested_edge_state, OffloadingAction(local_tasks=0, offload_tasks=1))
    normal_edge = env.compute_reward(normal_edge_state, OffloadingAction(local_tasks=0, offload_tasks=1))
    congested_cloud = env.compute_reward(congested_edge_state, OffloadingAction(local_tasks=0, offload_tasks=0, cloud_tasks=1))
    normal_cloud = env.compute_reward(normal_edge_state, OffloadingAction(local_tasks=0, offload_tasks=0, cloud_tasks=1))

    assert low_link_cloud.low_link_cloud_penalty > high_link_cloud.low_link_cloud_penalty
    assert low_link_cloud.reward < high_link_cloud.reward
    assert congested_edge.edge_congestion_penalty > normal_edge.edge_congestion_penalty
    assert congested_edge.reward < normal_edge.reward
    assert congested_cloud.cloud_congestion_relief_bonus > normal_cloud.cloud_congestion_relief_bonus


def test_public_interface_contract_and_rule_decision() -> None:
    contract = build_interface_contract()

    assert contract["schema_version"] == "qlearning_policy.interface.v1"
    assert contract["module_role"] == "低空无人机端-边-云计算卸载策略决策层"
    assert {field["name"] for field in contract["state_fields"]} >= {
        "queue",
        "link",
        "battery",
        "edge_load",
        "cloud_load",
        "task_urgency",
        "data_sensitivity",
        "area_risk",
    }

    decision = decide_policy(
        PolicyStatePayload(
            queue=10,
            link=2,
            battery=4,
            edge_load=2,
            cloud_load=0,
            task_urgency=1,
            data_sensitivity=0,
            area_risk=0,
        ),
        scenario_name="congested_edge",
    )

    assert decision.decision_source == "rule_based"
    assert decision.action.cloud_tasks > 0
    assert decision.action_class == "cloud_only"


def test_public_interface_can_decide_from_policy_table(tmp_path: Path) -> None:
    policy_table = tmp_path / "policy_table.csv"
    rows = [
        {
            "queue": 4,
            "link": 2,
            "battery": 4,
            "edge_load": 2,
            "cloud_load": 0,
            "task_urgency": 1,
            "data_sensitivity": 0,
            "area_risk": 0,
            "local_tasks": 0,
            "offload_tasks": 0,
            "cloud_tasks": 2,
            "q_value": 7.5,
        }
    ]
    with policy_table.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    decision = decide_policy(
        PolicyStatePayload(
            queue=4,
            link=2,
            battery=4,
            edge_load=2,
            cloud_load=0,
            task_urgency=1,
            data_sensitivity=0,
            area_risk=0,
        ),
        policy_table_path=policy_table,
    )

    assert decision.decision_source == "policy_table"
    assert decision.action.cloud_tasks == 2
    assert decision.q_value == 7.5


def test_strategy_comparison_contains_expected_baselines() -> None:
    metrics = compare_basic_strategies(OffloadingConfig(queue_capacity=8), slots=96, seed=4)

    assert set(metrics) == {"q_learning", "local_only", "offload_only", "cloud_only", "rule_based"}
    for result in metrics.values():
        assert math.isfinite(result.average_reward)
        assert 0.0 <= result.offload_ratio <= 1.0
        assert 0.0 <= result.edge_offload_ratio <= 1.0
        assert 0.0 <= result.cloud_offload_ratio <= 1.0


def test_run_demo_writes_expected_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "demo_outputs"

    main(["run-demo", "--slots", "32", "--seed", "5", "--output-dir", str(output_dir)])

    expected_files = {
        "strategy_metrics.csv",
        "strategy_metrics.json",
        "decision_trace.csv",
        "learning_curve.csv",
        "policy_table.csv",
    }
    assert {path.name for path in output_dir.iterdir() if path.is_file()} == expected_files

    with (output_dir / "strategy_metrics.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 5
    assert {row["strategy"] for row in rows} == {"q_learning", "local_only", "offload_only", "cloud_only", "rule_based"}

    with (output_dir / "decision_trace.csv").open("r", encoding="utf-8", newline="") as handle:
        trace_rows = list(csv.DictReader(handle))
    assert len(trace_rows) == 32
    assert "requested_local_tasks" in trace_rows[0]
    assert "next_edge_load" in trace_rows[0]
    assert "requested_cloud_tasks" in trace_rows[0]
    assert "next_cloud_load" in trace_rows[0]

    with (output_dir / "learning_curve.csv").open("r", encoding="utf-8", newline="") as handle:
        curve_rows = list(csv.DictReader(handle))
    assert len(curve_rows) == 32
    assert set(curve_rows[0]) == {"slot", "reward", "average_reward"}

    with (output_dir / "policy_table.csv").open("r", encoding="utf-8", newline="") as handle:
        policy_rows = list(csv.DictReader(handle))
    assert len(policy_rows) == OffloadingEnv().codec.size
    assert "greedy_action_index" in policy_rows[0]
    assert "link_rate_bps" in policy_rows[0]

    payload = json.loads((output_dir / "strategy_metrics.json").read_text(encoding="utf-8"))
    assert len(payload) == 5


def test_run_scenarios_writes_summary_and_per_scenario_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "scenario_outputs"

    main(["run-scenarios", "--slots", "24", "--seed", "7", "--output-dir", str(output_dir)])

    scenario_names = list_coverage_scenario_names()
    assert (output_dir / "scenario_strategy_metrics.csv").is_file()
    assert (output_dir / "scenario_strategy_metrics.json").is_file()

    with (output_dir / "scenario_strategy_metrics.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == len(scenario_names) * 5
    assert {row["coverage_scenario"] for row in rows} == set(scenario_names)
    assert {row["strategy"] for row in rows} == {"q_learning", "local_only", "offload_only", "cloud_only", "rule_based"}

    payload = json.loads((output_dir / "scenario_strategy_metrics.json").read_text(encoding="utf-8"))
    assert len(payload) == len(scenario_names) * 5

    for scenario_name in scenario_names:
        scenario_dir = output_dir / scenario_name
        assert scenario_dir.is_dir()
        assert (scenario_dir / "strategy_metrics.csv").is_file()
        assert (scenario_dir / "decision_trace.csv").is_file()
        assert (scenario_dir / "learning_curve.csv").is_file()
        assert (scenario_dir / "policy_table.csv").is_file()


def test_analyze_scenarios_writes_explanation_artifacts(tmp_path: Path) -> None:
    scenario_dir = tmp_path / "scenario_outputs"
    analysis_dir = tmp_path / "analysis_outputs"
    three_tier_dir = tmp_path / "three_tier_outputs"

    main(["run-scenarios", "--slots", "24", "--seed", "8", "--output-dir", str(scenario_dir)])
    main(["analyze-scenarios", "--input-dir", str(scenario_dir), "--output-dir", str(analysis_dir)])
    main(["analyze-three-tier", "--input-dir", str(scenario_dir), "--output-dir", str(three_tier_dir)])

    expected_files = {
        "scenario_best_strategy.csv",
        "scenario_best_strategy.json",
        "qlearning_scenario_summary.csv",
        "qlearning_scenario_summary.json",
        "qlearning_trace_action_summary.csv",
        "qlearning_trace_action_summary.json",
        "qlearning_trace_action_class_summary.csv",
        "qlearning_trace_action_class_summary.json",
        "qlearning_policy_action_summary.csv",
        "qlearning_policy_action_summary.json",
        "reward_diagnostics.csv",
        "reward_diagnostics.json",
        "analysis_notes.json",
    }
    assert {path.name for path in analysis_dir.iterdir() if path.is_file()} == expected_files

    with (analysis_dir / "scenario_best_strategy.csv").open("r", encoding="utf-8", newline="") as handle:
        best_rows = list(csv.DictReader(handle))
    assert len(best_rows) == len(list_coverage_scenario_names())
    assert "q_learning_reward_gap_to_best" in best_rows[0]

    with (analysis_dir / "qlearning_trace_action_summary.csv").open("r", encoding="utf-8", newline="") as handle:
        trace_rows = list(csv.DictReader(handle))
    assert {"overall", "link", "edge_load", "battery"} <= {row["group_by"] for row in trace_rows}
    assert "hybrid_slot_ratio" in trace_rows[0]

    with (analysis_dir / "qlearning_trace_action_class_summary.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        action_class_rows = list(csv.DictReader(handle))
    assert "action_class" in action_class_rows[0]

    with (analysis_dir / "reward_diagnostics.csv").open("r", encoding="utf-8", newline="") as handle:
        reward_rows = list(csv.DictReader(handle))
    assert "rank_by_reward" in reward_rows[0]
    assert "utility" in reward_rows[0]

    notes = json.loads((analysis_dir / "analysis_notes.json").read_text(encoding="utf-8"))
    assert "weak_coverage_note" in notes
    assert "metric_scope_warning" in notes

    expected_three_tier_files = {
        "three_tier_scenario_cloud_summary.csv",
        "three_tier_scenario_cloud_summary.json",
        "three_tier_trace_semantic_cloud_trends.csv",
        "three_tier_trace_semantic_cloud_trends.json",
        "three_tier_policy_semantic_cloud_trends.csv",
        "three_tier_policy_semantic_cloud_trends.json",
        "three_tier_hypothesis_checks.csv",
        "three_tier_hypothesis_checks.json",
        "three_tier_notes.json",
    }
    assert {path.name for path in three_tier_dir.iterdir() if path.is_file()} == expected_three_tier_files

    with (three_tier_dir / "three_tier_hypothesis_checks.csv").open("r", encoding="utf-8", newline="") as handle:
        hypothesis_rows = list(csv.DictReader(handle))
    assert {"weak_coverage_少云", "congested_edge_转云"} <= {row["hypothesis"] for row in hypothesis_rows}
    assert {"data_sensitivity", "area_risk"} <= {
        row["semantic_field"] for row in hypothesis_rows if row["semantic_field"]
    }


def test_analyze_run_writes_task_semantic_groups(tmp_path: Path) -> None:
    run_dir = tmp_path / "run_outputs"
    analysis_dir = tmp_path / "run_analysis"

    main(["run-demo", "--slots", "24", "--seed", "10", "--output-dir", str(run_dir)])
    main(["analyze-run", "--input-dir", str(run_dir), "--output-dir", str(analysis_dir), "--scenario-name", "smoke"])

    with (analysis_dir / "qlearning_trace_action_summary.csv").open("r", encoding="utf-8", newline="") as handle:
        trace_rows = list(csv.DictReader(handle))
    assert {"task_urgency", "data_sensitivity", "area_risk"} <= {row["group_by"] for row in trace_rows}

    with (analysis_dir / "qlearning_policy_action_summary.csv").open("r", encoding="utf-8", newline="") as handle:
        policy_rows = list(csv.DictReader(handle))
    assert {"task_urgency", "data_sensitivity", "area_risk"} <= {row["group_by"] for row in policy_rows}

    notes = json.loads((analysis_dir / "analysis_notes.json").read_text(encoding="utf-8"))
    assert "data_sensitivity_trace_note" in notes


def test_compare_conservative_writes_delta_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "conservative_outputs"

    main(
        [
            "compare-conservative",
            "--coverage-scenario",
            "weak_coverage",
            "--slots",
            "24",
            "--seed",
            "9",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert (output_dir / "conservative_comparison.csv").is_file()
    assert (output_dir / "qlearning_conservative_delta.csv").is_file()
    assert (output_dir / "weak_coverage" / "base" / "strategy_metrics.csv").is_file()
    assert (output_dir / "weak_coverage" / "conservative" / "strategy_metrics.csv").is_file()

    with (output_dir / "conservative_comparison.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 12
    assert {row["variant"] for row in rows} == {"base", "conservative"}
    assert "q_learning_greedy" in {row["strategy"] for row in rows}

    with (output_dir / "qlearning_conservative_delta.csv").open("r", encoding="utf-8", newline="") as handle:
        delta_rows = list(csv.DictReader(handle))
    assert len(delta_rows) == 1
    assert delta_rows[0]["coverage_scenario"] == "weak_coverage"
    assert "offload_ratio_delta" in delta_rows[0]
    assert "greedy_offload_ratio_delta" in delta_rows[0]


def test_validate_task_semantics_writes_stability_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "stability_outputs"

    main(
        [
            "validate-task-semantics",
            "--coverage-scenario",
            "weak_coverage",
            "--slots",
            "12",
            "--seeds",
            "1",
            "--output-dir",
            str(output_dir),
        ]
    )

    expected_files = {
        "task_semantics_metrics.csv",
        "task_semantics_metrics.json",
        "task_semantics_trace_trends.csv",
        "task_semantics_trace_trends.json",
        "task_semantics_greedy_trace_trends.csv",
        "task_semantics_greedy_trace_trends.json",
        "task_semantics_policy_trends.csv",
        "task_semantics_policy_trends.json",
        "task_semantics_stability_summary.csv",
        "task_semantics_stability_summary.json",
        "task_urgency_penalty_summary.csv",
        "task_urgency_penalty_summary.json",
        "task_semantics_stability_notes.json",
    }
    assert {path.name for path in output_dir.iterdir() if path.is_file()} == expected_files

    with (output_dir / "task_semantics_stability_summary.csv").open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert {"trace", "greedy_trace", "policy"} <= {row["source"] for row in rows}
    assert {"task_urgency", "data_sensitivity", "area_risk"} <= {row["semantic_field"] for row in rows}

    with (output_dir / "task_semantics_trace_trends.csv").open("r", encoding="utf-8", newline="") as handle:
        trace_rows = list(csv.DictReader(handle))
    assert "deadline_miss_rate_delta" in trace_rows[0]
    assert "average_deadline_miss_penalty_delta" in trace_rows[0]

    with (output_dir / "task_urgency_penalty_summary.csv").open("r", encoding="utf-8", newline="") as handle:
        urgency_rows = list(csv.DictReader(handle))
    assert {"trace", "greedy_trace"} <= {row["source"] for row in urgency_rows}
    assert "penalty_alignment_ratio" in urgency_rows[0]


def test_validate_three_tier_writes_stability_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "three_tier_stability"

    main(
        [
            "validate-three-tier",
            "--slots",
            "8",
            "--seeds",
            "1",
            "--coverage-scenario",
            "all",
            "--output-dir",
            str(output_dir),
        ]
    )

    expected_files = {
        "three_tier_seed_scenario_metrics.csv",
        "three_tier_seed_scenario_metrics.json",
        "three_tier_trace_semantic_cloud_trends.csv",
        "three_tier_trace_semantic_cloud_trends.json",
        "three_tier_greedy_trace_semantic_cloud_trends.csv",
        "three_tier_greedy_trace_semantic_cloud_trends.json",
        "three_tier_policy_semantic_cloud_trends.csv",
        "three_tier_policy_semantic_cloud_trends.json",
        "three_tier_stability_summary.csv",
        "three_tier_stability_summary.json",
        "three_tier_stability_notes.json",
    }
    assert {path.name for path in output_dir.iterdir() if path.is_file()} == expected_files

    with (output_dir / "three_tier_seed_scenario_metrics.csv").open("r", encoding="utf-8", newline="") as handle:
        metric_rows = list(csv.DictReader(handle))
    assert {"trace", "greedy_eval"} <= {row["metric_source"] for row in metric_rows}

    with (output_dir / "three_tier_stability_summary.csv").open("r", encoding="utf-8", newline="") as handle:
        summary_rows = list(csv.DictReader(handle))
    assert {"weak_coverage_少云", "congested_edge_转云"} <= {row["hypothesis"] for row in summary_rows}
    assert {"data_sensitivity", "area_risk"} <= {row["semantic_field"] for row in summary_rows if row["semantic_field"]}


def test_export_dashboard_data_writes_frontend_payload(tmp_path: Path) -> None:
    stability_dir = tmp_path / "stability"
    scenario_dir = tmp_path / "scenario"
    output_path = tmp_path / "web" / "policy-dashboard.json"
    stability_dir.mkdir()
    scenario_dir.mkdir()

    stability_rows = [
        {
            "hypothesis": "weak_coverage_少云",
            "source": "trace",
            "semantic_field": "",
            "run_count": 3,
            "stable_count": 3,
            "stable_ratio": 1.0,
            "passed": 1,
            "mean_delta": -0.02,
            "min_delta": -0.03,
            "max_delta": -0.01,
            "mean_primary_metric": 0.2,
            "mean_threshold": 0.3,
            "mean_aux_metric": 0.0,
        },
        {
            "hypothesis": "congested_edge_转云",
            "source": "trace",
            "semantic_field": "",
            "run_count": 3,
            "stable_count": 3,
            "stable_ratio": 1.0,
            "passed": 1,
            "mean_delta": 0.02,
            "min_delta": 0.01,
            "max_delta": 0.03,
            "mean_primary_metric": 0.32,
            "mean_threshold": 0.30,
            "mean_aux_metric": 0.0,
        },
        {
            "hypothesis": "area_risk_抑制云端卸载",
            "source": "policy",
            "semantic_field": "area_risk",
            "run_count": 15,
            "stable_count": 15,
            "stable_ratio": 1.0,
            "passed": 1,
            "mean_delta": -0.05,
            "min_delta": -0.06,
            "max_delta": -0.04,
            "mean_primary_metric": -0.05,
            "mean_threshold": 0.0,
            "mean_aux_metric": 0.0,
        },
    ]
    with (stability_dir / "three_tier_stability_summary.csv").open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(stability_rows[0].keys()))
        writer.writeheader()
        writer.writerows(stability_rows)

    metric_rows = [
        {
            "coverage_scenario": "balanced",
            "strategy": "q_learning",
            "average_reward": 10.0,
            "average_delay": 4.0,
            "average_energy": 20.0,
            "average_queue": 10.0,
            "processed_tasks": 100,
            "offload_ratio": 0.6,
            "edge_offload_ratio": 0.3,
            "cloud_offload_ratio": 0.3,
        }
    ]
    with (scenario_dir / "scenario_strategy_metrics.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(metric_rows[0].keys()))
        writer.writeheader()
        writer.writerows(metric_rows)

    main(
        [
            "export-dashboard-data",
            "--stability-dir",
            str(stability_dir),
            "--scenario-dir",
            str(scenario_dir),
            "--output-path",
            str(output_path),
        ]
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "qlearning_policy.dashboard.v1"
    assert payload["stability"]["summary"]["scheme3_ready"] is True
    assert payload["scenario_metrics"]["qlearning_rows"][0]["coverage_scenario"] == "balanced"


def test_export_trained_policy_writes_real_policy_snapshot(tmp_path: Path) -> None:
    output_path = tmp_path / "trained-q-policy.json"

    main(
        [
            "export-trained-policy",
            "--coverage-scenario",
            "weak_coverage",
            "--slots",
            "8",
            "--seed",
            "1",
            "--output-path",
            str(output_path),
        ]
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    scenario = payload["scenarios"]["weak_coverage"]

    assert payload["schema_version"] == "qlearning_policy.trained_policy.v1"
    assert payload["state_field_order"] == [
        "queue",
        "link",
        "battery",
        "edge_load",
        "cloud_load",
        "task_urgency",
        "data_sensitivity",
        "area_risk",
    ]
    assert scenario["entry_count"] == OffloadingEnv(make_offloading_config_for_coverage("weak_coverage")).codec.size
    assert scenario["visited_state_count"] > 0
    assert scenario["visited_ratio"] > 0.0
    assert len(scenario["sample_states"][0]) == 9
    assert len(scenario["entries"][0]) == 13


def test_webserver_act_step_and_rollout_use_trained_snapshot(tmp_path: Path) -> None:
    output_path = tmp_path / "trained-q-policy.json"
    export_trained_policy_snapshot(
        scenario_names=("weak_coverage",),
        slots=24,
        seed=2,
        output_path=output_path,
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    sample = payload["scenarios"]["weak_coverage"]["sample_states"][0]
    state = PolicyStatePayload(
        queue=sample[0],
        link=sample[1],
        battery=sample[2],
        edge_load=sample[3],
        cloud_load=sample[4],
        task_urgency=sample[5],
        data_sensitivity=sample[6],
        area_risk=sample[7],
    )
    store = TrainedPolicyStore.load(output_path)

    act_response = build_act_response(
        scenario_name="weak_coverage",
        state_payload=state,
        policy_store=store,
        policy_mode="trained_only",
    )
    assert act_response["resolved_decision"]["source"] == "trained_policy"
    assert act_response["resolved_decision"]["action"] is not None
    assert act_response["resolved_decision"]["visit_count"] > 0

    step_response = build_step_response(
        scenario_name="weak_coverage",
        state_payload=state,
        policy_store=store,
        policy_mode="trained_only",
        seed=7,
    )
    assert step_response["step_result"] is not None
    assert 0 <= step_response["step_result"]["next_state"]["queue"] <= 16

    rollout_response = build_rollout_response(
        scenario_name="weak_coverage",
        initial_state_payload=state,
        policy_store=store,
        policy_mode="trained_or_rule",
        steps=3,
        seed=11,
    )
    assert rollout_response["summary"]["steps_requested"] == 3
    assert 0 < rollout_response["summary"]["steps_executed"] <= 3
    assert len(rollout_response["trace"]) >= rollout_response["summary"]["steps_executed"]


def test_webserver_reports_uncovered_state_in_trained_only_mode(tmp_path: Path) -> None:
    output_path = tmp_path / "trained-q-policy.json"
    export_trained_policy_snapshot(
        scenario_names=("balanced",),
        slots=8,
        seed=1,
        output_path=output_path,
    )
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    uncovered_row = next(
        row for row in payload["scenarios"]["balanced"]["entries"] if row[12] == 0
    )
    state = PolicyStatePayload(
        queue=uncovered_row[0],
        link=uncovered_row[1],
        battery=uncovered_row[2],
        edge_load=uncovered_row[3],
        cloud_load=uncovered_row[4],
        task_urgency=uncovered_row[5],
        data_sensitivity=uncovered_row[6],
        area_risk=uncovered_row[7],
    )
    store = TrainedPolicyStore.load(output_path)

    response = build_act_response(
        scenario_name="balanced",
        state_payload=state,
        policy_store=store,
        policy_mode="trained_only",
    )

    assert response["resolved_decision"]["source"] == "uncovered_state"
    assert response["resolved_decision"]["action"] is None


def test_policy_table_covers_all_states() -> None:
    config = OffloadingConfig(queue_capacity=4)
    result = train_q_learning(config=config, slots=32, seed=6)
    rows = build_policy_table_rows(result)

    assert len(rows) == OffloadingEnv(config=config).codec.size
    assert set(rows[0]) == {
        "state_index",
        "queue",
        "link",
        "link_rate_bps",
        "battery",
        "edge_load",
        "edge_load_value",
        "cloud_load",
        "cloud_load_value",
        "task_urgency",
        "data_sensitivity",
        "area_risk",
        "greedy_action_index",
        "local_tasks",
        "offload_tasks",
        "cloud_tasks",
        "q_value",
    }
