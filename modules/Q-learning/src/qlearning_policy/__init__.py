# 中文说明：本包提供基础 Q-learning 智能体和无人机端边计算卸载实验环境。
from __future__ import annotations

from .agent import QLearningAgent, QLearningParams
from .analysis import analyze_scenario_sweep, analyze_single_run
from .dashboard import build_dashboard_payload, export_dashboard_payload
from .interface import (
    PolicyActionPayload,
    PolicyDecisionPayload,
    PolicyStatePayload,
    build_interface_contract,
    decide_policy,
)
from .offloading import OffloadingAction, OffloadingConfig, OffloadingEnv, OffloadingState
from .scenarios import (
    COVERAGE_SCENARIOS,
    CoverageScenario,
    get_coverage_scenario,
    list_coverage_scenario_names,
    make_conservative_offloading_config_for_coverage,
    make_offloading_config_for_coverage,
)
from .simulation import (
    DecisionTraceRow,
    build_decision_trace_rows,
    build_learning_curve_rows,
    build_policy_table_rows,
    compare_basic_strategies,
    evaluate_trained_q_learning,
    run_basic_strategy_suite,
    train_q_learning,
)
from .stability import run_task_semantics_stability
from .state import StateCodec
from .three_tier_analysis import analyze_three_tier_sweep, validate_three_tier_stability
from .webserver import (
    DEFAULT_WEB_HOST,
    DEFAULT_WEB_PORT,
    build_act_response,
    build_rollout_response,
    build_step_response,
    run_web_server,
)

__all__ = [
    "DecisionTraceRow",
    "OffloadingAction",
    "OffloadingConfig",
    "OffloadingEnv",
    "OffloadingState",
    "PolicyActionPayload",
    "PolicyDecisionPayload",
    "PolicyStatePayload",
    "QLearningAgent",
    "QLearningParams",
    "StateCodec",
    "COVERAGE_SCENARIOS",
    "CoverageScenario",
    "DEFAULT_WEB_HOST",
    "DEFAULT_WEB_PORT",
    "analyze_scenario_sweep",
    "analyze_single_run",
    "analyze_three_tier_sweep",
    "build_act_response",
    "build_dashboard_payload",
    "build_interface_contract",
    "build_decision_trace_rows",
    "build_learning_curve_rows",
    "build_policy_table_rows",
    "build_rollout_response",
    "build_step_response",
    "compare_basic_strategies",
    "decide_policy",
    "evaluate_trained_q_learning",
    "export_dashboard_payload",
    "get_coverage_scenario",
    "list_coverage_scenario_names",
    "make_conservative_offloading_config_for_coverage",
    "make_offloading_config_for_coverage",
    "run_basic_strategy_suite",
    "run_task_semantics_stability",
    "run_web_server",
    "train_q_learning",
    "validate_three_tier_stability",
]
