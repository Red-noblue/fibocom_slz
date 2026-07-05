/* 中文说明：本脚本驱动 Q-learning 计算卸载实验分析台，复用真实训练快照和后端运行接口。 */
const STATIC_DASHBOARD_PATH = "./static/data/policy-dashboard.json";
const STATIC_TRAINED_POLICY_PATH = "./static/data/trained-q-policy.json";
const POLICY_STATE_FIELDS = [
  "queue",
  "link",
  "battery",
  "edge_load",
  "cloud_load",
  "task_urgency",
  "data_sensitivity",
  "area_risk",
];

const FALLBACK_DASHBOARD = {
  interface_contract: { state_fields: [] },
  scenario_metrics: { qlearning_rows: [] },
  stability: { summary: { scheme3_ready: false, critical_checks: {} } },
  key_findings: [],
};

const DEFAULT_CONFIG = {
  queue_capacity: 16,
  max_local_tasks: 2,
  max_edge_tasks: 2,
  max_cloud_tasks: 2,
  link_rates_bps: [2e7, 1e8, 1.5e8],
  edge_load_levels: [0.15, 0.5, 0.85],
  cloud_load_levels: [0.2, 0.55, 0.85],
  battery_level_count: 5,
  avg_arrival_rate: 4.0,
  task_size_bits: 3e7,
  cycles_per_task: 1.3e9,
  local_cpu_hz: 1e9,
  beta: 8e-27,
  tx_power_watts: 10.0,
  theta: 30.0,
  delay_weight: 1.0,
  energy_weight: 0.12,
  queue_weight: 0.2,
  illegal_action_penalty: 8.0,
  low_link_offload_penalty: 0.0,
  low_link_penalty_threshold: 0,
  urgency_delay_weight: 0.6,
  task_deadlines: [8.0, 6.0, 4.5],
  deadline_miss_penalty: 12.0,
  data_sensitivity_offload_penalty: 3.0,
  area_risk_offload_penalty: 2.0,
  edge_delay_scale: 1.5,
  cloud_backhaul_delay_per_task: 0.8,
  cloud_compute_delay_per_task: 0.35,
  cloud_delay_scale: 0.8,
  cloud_usage_penalty_per_task: 0.6,
  low_link_cloud_penalty_per_task: 8.0,
  low_link_cloud_penalty_threshold: 0,
  edge_congestion_penalty_per_task: 6.0,
  edge_congestion_threshold: 2,
  cloud_congestion_relief_bonus_per_task: 10.0,
  cloud_data_sensitivity_multiplier: 2.5,
  cloud_area_risk_multiplier: 5.0,
  battery_energy_per_level_j: 35.0,
};

const SCENARIO_DEFAULTS = {
  balanced: { link: 1, edge_load: 1, cloud_load: 1 },
  good_coverage: { link: 2, edge_load: 0, cloud_load: 0 },
  weak_coverage: { link: 0, edge_load: 1, cloud_load: 1 },
  intermittent_coverage: { link: 1, edge_load: 1, cloud_load: 1 },
  congested_edge: { link: 2, edge_load: 2, cloud_load: 0 },
};

const CITY_PROFILES = {
  shenzhen: {
    name: "高密度城市任务",
    queue_delta: 2,
    link_delta: 0,
    edge_load_delta: 1,
    cloud_load_delta: 0,
    risk_delta: 0,
    coverage_hint: "高密度任务会增加任务队列和边缘负载。",
  },
  xuzhou: {
    name: "边云协同任务",
    queue_delta: 1,
    link_delta: 0,
    edge_load_delta: -1,
    cloud_load_delta: 0,
    risk_delta: 0,
    coverage_hint: "边云协同任务会降低边缘负载压力。",
  },
  baoshan: {
    name: "高风险监管任务",
    queue_delta: 0,
    link_delta: 1,
    edge_load_delta: 0,
    cloud_load_delta: 0,
    risk_delta: 1,
    coverage_hint: "高风险监管任务会提高区域风险等级。",
  },
};

const TASK_PROFILES = {
  inspection: { queue: 8, task_urgency: 1, data_sensitivity: 1, area_risk: 0 },
  obstacle_alert: { queue: 9, task_urgency: 2, data_sensitivity: 0, area_risk: 1 },
  video_analysis: { queue: 13, task_urgency: 1, data_sensitivity: 1, area_risk: 0 },
  log_upload: { queue: 6, task_urgency: 0, data_sensitivity: 0, area_risk: 0 },
  regulatory_capture: { queue: 10, task_urgency: 2, data_sensitivity: 2, area_risk: 2 },
};

const WEATHER_PROFILES = {
  calm: { battery: 4, risk_delta: 0, link_delta: 0 },
  windy: { battery: 2, risk_delta: 1, link_delta: 0 },
  rainy: { battery: 3, risk_delta: 1, link_delta: -1 },
};

const ROUTE_PROFILES = {
  urban_inspection: { name: "城区巡检路线", queue_delta: 1, risk_delta: 0, link_delta: 0, edge_load_delta: 0, cloud_load_delta: 0 },
  logistics_corridor: { name: "物流干线路线", queue_delta: 2, risk_delta: 0, link_delta: 0, edge_load_delta: 1, cloud_load_delta: 0 },
  airport_perimeter: { name: "机场周界路线", queue_delta: 1, risk_delta: 1, link_delta: 1, edge_load_delta: 0, cloud_load_delta: 0 },
};

const ROUTE_NODE_BIAS = [
  { queue_delta: 0, link_delta: 0, risk_delta: 0, edge_load_delta: 0, cloud_load_delta: 0 },
  { queue_delta: 1, link_delta: -1, risk_delta: 0, edge_load_delta: 0, cloud_load_delta: 0 },
  { queue_delta: 2, link_delta: 1, risk_delta: 0, edge_load_delta: 1, cloud_load_delta: 0 },
  { queue_delta: 2, link_delta: -1, risk_delta: 2, edge_load_delta: 0, cloud_load_delta: 1 },
  { queue_delta: -2, link_delta: 0, risk_delta: 0, edge_load_delta: 0, cloud_load_delta: -1 },
];

const LABELS = {
  link: ["弱", "中", "强"],
  load: ["低", "中", "高"],
  level: ["低", "中", "高"],
  source: {
    trained_policy: "真实 Q-learning",
    rule_based_fallback: "规则回退",
    rule_based: "规则基线",
    local_only: "本地优先",
    edge_only: "边缘优先",
    cloud_only: "云端优先",
    defer: "延迟处理",
    uncovered_state: "训练未覆盖",
  },
};

let dashboardData = FALLBACK_DASHBOARD;
let simulatorConfig = DEFAULT_CONFIG;
let trainedPolicyStore = null;
let backendAvailable = false;
let currentRouteNode = 0;
let latestActPayload = null;

document.addEventListener("DOMContentLoaded", () => {
  void initPage();
});

async function initPage() {
  await loadStaticArtifacts();
  await probeBackend();
  bindEvents();
  deriveStateFromScenario();
  renderStaticSections();
  refreshAll();
}

async function loadStaticArtifacts() {
  const [dashboardResult, trainedPolicyResult] = await Promise.allSettled([
    fetchJson(STATIC_DASHBOARD_PATH),
    fetchJson(STATIC_TRAINED_POLICY_PATH),
  ]);

  dashboardData = dashboardResult.status === "fulfilled" ? dashboardResult.value : FALLBACK_DASHBOARD;
  simulatorConfig = { ...DEFAULT_CONFIG, ...(dashboardData.simulator_config || {}) };
  trainedPolicyStore = trainedPolicyResult.status === "fulfilled"
    ? buildTrainedPolicyStore(trainedPolicyResult.value)
    : null;
}

async function probeBackend() {
  try {
    const health = await fetchJson("/api/health");
    backendAvailable = health.status === "ok";
  } catch (error) {
    backendAvailable = false;
  }
}

function bindEvents() {
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => switchView(button.dataset.view));
  });
  document.querySelectorAll("#input-city,#input-route,#input-segment,#input-scenario,#input-weather,#input-task").forEach((node) => {
    node.addEventListener("change", () => {
      deriveStateFromScenario();
      refreshAll();
    });
  });
  document.querySelectorAll("#input-policy-mode,#input-runtime-seed,#input-rollout-steps,#input-queue,#input-battery,#input-link,#input-edge,#input-cloud,#input-urgency,#input-sensitive,#input-risk").forEach((node) => {
    node.addEventListener("input", refreshAll);
    node.addEventListener("change", refreshAll);
  });
  document.querySelector("#btn-derive-state").addEventListener("click", () => {
    deriveStateFromScenario();
    refreshAll();
    showToast("已根据任务场景生成状态");
  });
  document.querySelector("#btn-trained-sample").addEventListener("click", () => {
    applyTrainedSample();
    refreshAll();
  });
  document.querySelector("#btn-runtime-step").addEventListener("click", () => {
    void runBackendStep();
  });
  document.querySelector("#btn-runtime-rollout").addEventListener("click", () => {
    void runBackendRollout();
  });
  document.querySelector("#btn-copy-json").addEventListener("click", copyStateJson);
  document.querySelector("#btn-refresh-act").addEventListener("click", () => {
    refreshAll();
    showToast("已重新查表");
  });
}

function switchView(viewName) {
  document.querySelectorAll("[data-view]").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === viewName);
  });
  document.querySelectorAll(".view").forEach((view) => {
    view.classList.toggle("active", view.id === `view-${viewName}`);
  });
}

function deriveStateFromScenario() {
  currentRouteNode = readNumber("#input-segment");
  const city = CITY_PROFILES[readValue("#input-city")] || CITY_PROFILES.shenzhen;
  const scenario = readValue("#input-scenario");
  const route = ROUTE_PROFILES[readValue("#input-route")];
  const task = TASK_PROFILES[readValue("#input-task")];
  const weather = WEATHER_PROFILES[readValue("#input-weather")];
  const scenarioDefaults = SCENARIO_DEFAULTS[scenario] || SCENARIO_DEFAULTS.balanced;
  const nodeBias = ROUTE_NODE_BIAS[currentRouteNode] || ROUTE_NODE_BIAS[0];

  setValue("#input-queue", clamp(task.queue + route.queue_delta + city.queue_delta + nodeBias.queue_delta, 0, simulatorConfig.queue_capacity));
  setValue("#input-battery", clamp(weather.battery - Math.max(0, currentRouteNode - 2), 0, simulatorConfig.battery_level_count - 1));
  setValue("#input-link", clamp(scenarioDefaults.link + weather.link_delta + city.link_delta + route.link_delta + nodeBias.link_delta, 0, 2));
  setValue("#input-edge", clamp(scenarioDefaults.edge_load + route.edge_load_delta + city.edge_load_delta + nodeBias.edge_load_delta, 0, 2));
  setValue("#input-cloud", clamp(scenarioDefaults.cloud_load + route.cloud_load_delta + city.cloud_load_delta + nodeBias.cloud_load_delta, 0, 2));
  setValue("#input-urgency", clamp(task.task_urgency, 0, 2));
  setValue("#input-sensitive", clamp(task.data_sensitivity, 0, 2));
  setValue("#input-risk", clamp(task.area_risk + route.risk_delta + weather.risk_delta + city.risk_delta + nodeBias.risk_delta, 0, 2));
}

function refreshAll() {
  updateStatus();
  updateRangeLabels();
  renderRouteTelemetry();
  const state = readStateFromForm();
  renderStateJson(state);

  if (!trainedPolicyStore) {
    renderActUnavailable("真实训练快照未加载。");
    renderStrategyCompare(state);
    renderRuntimeRows([], "训练快照未加载。");
    return;
  }

  latestActPayload = buildTrustedActPayload(state);
  renderAct(latestActPayload);
  renderStrategyCompare(state);
}

function updateStatus() {
  const dataStatus = document.querySelector("#data-status");
  const backendStatus = document.querySelector("#backend-status");
  const coverageStatus = document.querySelector("#coverage-status");
  const state = readStateFromForm();
  const coverage = buildCoveragePayload(state.scenario);

  dataStatus.textContent = trainedPolicyStore ? "训练快照已加载" : "训练快照缺失";
  dataStatus.classList.toggle("ok", Boolean(trainedPolicyStore));
  backendStatus.textContent = backendAvailable ? "后端运行接口可用" : "纯静态查表模式";
  backendStatus.classList.toggle("ok", backendAvailable);
  coverageStatus.textContent = `覆盖率 ${formatPercent(coverage.visited_ratio || 0)}`;
  coverageStatus.classList.toggle("ok", Boolean(coverage.visited_ratio));

  document.querySelector("#btn-runtime-step").disabled = !backendAvailable;
  document.querySelector("#btn-runtime-rollout").disabled = !backendAvailable;
}

function renderRouteTelemetry() {
  const city = CITY_PROFILES[readValue("#input-city")] || CITY_PROFILES.shenzhen;
  const state = readStateFromForm();
  const route = ROUTE_PROFILES[readValue("#input-route")];
  document.querySelector("#route-name").textContent = `${city.name}｜${route?.name || "当前航线"}`;
  document.querySelector("#route-context").textContent = `${city.coverage_hint} 下方数值是当前策略真正读取的离散状态，不是 GIS 页面或仿真截图。`;
  document.querySelector("#metric-queue").textContent = `${state.queue}/16`;
  document.querySelector("#metric-link").textContent = LABELS.link[state.link] || "--";
  document.querySelector("#metric-battery").textContent = `${state.battery}/4`;
  document.querySelector("#metric-risk").textContent = LABELS.level[state.area_risk] || "--";
  document.querySelector("#metric-edge").textContent = LABELS.load[state.edge_load] || "--";
  document.querySelector("#metric-cloud").textContent = LABELS.load[state.cloud_load] || "--";
  document.querySelector("#metric-urgency").textContent = LABELS.level[state.task_urgency] || "--";
  document.querySelector("#metric-sensitive").textContent = LABELS.level[state.data_sensitivity] || "--";
  document.querySelector("#input-impact").innerHTML = buildInputImpact(city, route, state);
}

function buildInputImpact(city, route, state) {
  const task = TASK_PROFILES[readValue("#input-task")];
  const weather = WEATHER_PROFILES[readValue("#input-weather")];
  const scenarioDefaults = SCENARIO_DEFAULTS[readValue("#input-scenario")] || SCENARIO_DEFAULTS.balanced;
  const nodeBias = ROUTE_NODE_BIAS[currentRouteNode] || ROUTE_NODE_BIAS[0];
  const rows = [
    ["环境模板", `队列 ${signedDelta(city.queue_delta)}｜边缘负载 ${signedDelta(city.edge_load_delta)}｜区域风险 ${signedDelta(city.risk_delta)}`],
    ["路线模板", `队列 ${signedDelta(route.queue_delta)}｜链路 ${signedDelta(route.link_delta)}｜区域风险 ${signedDelta(route.risk_delta)}`],
    ["网络覆盖", `链路等级 ${scenarioDefaults.link}｜边缘负载 ${scenarioDefaults.edge_load}｜云端负载 ${scenarioDefaults.cloud_load}`],
    ["能耗条件", `电量等级 ${weather.battery}｜链路 ${signedDelta(weather.link_delta)}｜区域风险 ${signedDelta(weather.risk_delta)}`],
    ["任务模板", `队列 ${task.queue}｜紧急度 ${task.task_urgency}｜敏感度 ${task.data_sensitivity}`],
    ["路线阶段", `阶段 ${currentRouteNode}｜队列 ${signedDelta(nodeBias.queue_delta)}｜区域风险 ${signedDelta(nodeBias.risk_delta)}`],
    ["运行参数", `随机种子 ${readValue("#input-runtime-seed")}｜运行步数 ${readValue("#input-rollout-steps")}｜只影响后端连续运行`],
  ];
  return rows.map(([name, value]) => `
    <div class="impact-row">
      <strong>${name}</strong>
      <span>${value}</span>
    </div>
  `).join("");
}

function renderAct(payload) {
  const decision = payload.resolved_decision;
  const coverage = payload.coverage || {};
  const sourceLabel = LABELS.source[decision.source] || decision.source;
  document.querySelector("#policy-source").textContent = sourceLabel;

  if (!decision.action) {
    document.querySelector("#decision-action").textContent = "无有效动作";
    document.querySelector("#decision-reason").textContent = (decision.notes || []).join("｜") || "当前状态未被训练覆盖。";
    document.querySelector("#decision-q").textContent = decision.q_value == null ? "--" : formatNumber(decision.q_value, 3);
    document.querySelector("#decision-reward").textContent = "--";
    document.querySelector("#decision-delay").textContent = "--";
    document.querySelector("#decision-energy").textContent = "--";
    document.querySelector("#decision-coverage").textContent = formatPercent(coverage.visited_ratio || 0);
    document.querySelector("#explain-action").textContent = "无有效动作";
    renderBreakdown(null);
    return;
  }

  document.querySelector("#decision-action").textContent = formatAction(decision.action);
  document.querySelector("#decision-reason").textContent = buildDecisionReason(decision);
  document.querySelector("#decision-q").textContent = decision.q_value == null ? "--" : formatNumber(decision.q_value, 3);
  document.querySelector("#decision-reward").textContent = formatNumber(decision.estimated_reward, 2);
  document.querySelector("#decision-delay").textContent = `${formatNumber(decision.estimated_delay, 2)}s`;
  document.querySelector("#decision-energy").textContent = `${formatNumber(decision.estimated_energy, 2)}J`;
  document.querySelector("#decision-coverage").textContent = formatPercent(coverage.visited_ratio || 0);
  document.querySelector("#explain-action").textContent = `${sourceLabel}｜${formatAction(decision.action)}`;
  renderBreakdown(decision.reward_breakdown);
}

function renderActUnavailable(message) {
  document.querySelector("#policy-source").textContent = "策略不可用";
  document.querySelector("#decision-action").textContent = "不可用";
  document.querySelector("#decision-reason").textContent = message;
  document.querySelector("#decision-q").textContent = "--";
  document.querySelector("#decision-reward").textContent = "--";
  document.querySelector("#decision-delay").textContent = "--";
  document.querySelector("#decision-energy").textContent = "--";
  document.querySelector("#decision-coverage").textContent = "--";
  renderBreakdown(null);
}

function renderStrategyCompare(state) {
  const root = document.querySelector("#strategy-compare");
  const qDecision = trainedPolicyStore
    ? buildTrustedActPayload({ ...state, policy_mode: readValue("#input-policy-mode") }).resolved_decision
    : null;
  const rows = [
    buildStrategyRow("当前策略", qDecision, state),
    buildStrategyRow("规则基线", buildResolvedDecision({
      scenarioName: state.scenario,
      source: "rule_based",
      covered: false,
      visitCount: 0,
      qValue: null,
      action: selectRuleBasedAction(state, simulatorConfig),
      notes: [],
      state,
    }), state),
    buildStrategyRow("本地优先", buildManualDecision("local_only", state), state),
    buildStrategyRow("边缘优先", buildManualDecision("edge_only", state), state),
    buildStrategyRow("云端优先", buildManualDecision("cloud_only", state), state),
    buildStrategyRow("延迟处理", buildManualDecision("defer", state), state),
  ];
  const validRows = rows.filter((row) => Number.isFinite(row.reward));
  const bestReward = validRows.length ? Math.max(...validRows.map((row) => row.reward)) : null;

  root.innerHTML = rows.map((row) => `
    <article class="strategy-card ${bestReward !== null && row.reward === bestReward ? "best" : ""}">
      <strong>${row.name}</strong>
      <span>${row.source}</span>
      <div>${row.action}</div>
      <div class="score">${Number.isFinite(row.reward) ? formatNumber(row.reward, 2) : "--"}</div>
      <span>时延 ${Number.isFinite(row.delay) ? `${formatNumber(row.delay, 2)}s` : "--"}｜能耗 ${Number.isFinite(row.energy) ? `${formatNumber(row.energy, 2)}J` : "--"}</span>
      <span>${row.note}</span>
    </article>
  `).join("");
}

function buildStrategyRow(name, decision, state) {
  if (!decision?.action) {
    return {
      name,
      source: decision ? LABELS.source[decision.source] || decision.source : "不可用",
      action: "无有效动作",
      reward: Number.NEGATIVE_INFINITY,
      delay: Number.NaN,
      energy: Number.NaN,
      note: "当前状态没有可执行策略。",
    };
  }
  return {
    name,
    source: LABELS.source[decision.source] || decision.source,
    action: formatAction(decision.action),
    reward: Number(decision.estimated_reward),
    delay: Number(decision.estimated_delay),
    energy: Number(decision.estimated_energy),
    note: summarizeAction(state, decision.action),
  };
}

function buildManualDecision(source, state) {
  let action;
  if (source === "local_only") {
    action = { local_tasks: Math.min(simulatorConfig.max_local_tasks, state.queue), edge_tasks: 0, cloud_tasks: 0 };
  } else if (source === "edge_only") {
    action = { local_tasks: 0, edge_tasks: Math.min(simulatorConfig.max_edge_tasks, state.queue), cloud_tasks: 0 };
  } else if (source === "cloud_only") {
    action = { local_tasks: 0, edge_tasks: 0, cloud_tasks: Math.min(simulatorConfig.max_cloud_tasks, state.queue) };
  } else {
    action = { local_tasks: 0, edge_tasks: 0, cloud_tasks: 0 };
  }
  return buildResolvedDecision({
    scenarioName: state.scenario,
    source,
    covered: false,
    visitCount: 0,
    qValue: null,
    action,
    notes: [],
    state,
  });
}

function renderBreakdown(breakdown) {
  const root = document.querySelector("#reward-breakdown");
  if (!breakdown) {
    root.innerHTML = `<p>当前没有可解释分解。</p>`;
    return;
  }
  const rows = [
    ["utility", "任务收益", true],
    ["cloud_congestion_relief_bonus", "云端缓解拥塞", true],
    ["queue_penalty", "队列惩罚", false],
    ["illegal_penalty", "非法动作", false],
    ["low_link_offload_penalty", "弱链路远端", false],
    ["urgency_delay_penalty", "紧急时延", false],
    ["deadline_miss_penalty", "超时惩罚", false],
    ["data_sensitivity_penalty", "数据敏感", false],
    ["area_risk_penalty", "区域风险", false],
    ["cloud_usage_penalty", "云端使用", false],
    ["low_link_cloud_penalty", "弱链路云端", false],
    ["edge_congestion_penalty", "边缘拥塞", false],
  ].filter(([key]) => Math.abs(Number(breakdown[key] || 0)) > 1e-9);
  root.innerHTML = rows.map(([key, label, positive]) => `
    <div class="breakdown-row ${positive ? "plus" : "minus"}">
      <span>${label}</span>
      <strong>${positive ? "+" : "-"}${formatNumber(Number(breakdown[key] || 0), 2)}</strong>
    </div>
  `).join("");
}

async function runBackendStep() {
  if (!backendAvailable) {
    showToast("执行一步需要 Python 后端");
    return;
  }
  try {
    const response = await postApi("/api/step", buildRuntimePayload(readStateFromForm()));
    const step = response.step_result;
    if (step?.next_state) {
      renderRuntimeRows([{ step: 0, state: response.state, resolved_decision: response.resolved_decision, step_result: step }]);
      applyBackendState(step.next_state);
      currentRouteNode = Math.min(4, currentRouteNode + 1);
      setValue("#input-segment", currentRouteNode);
      refreshAll();
    document.querySelector("#rollout-summary").textContent = `一步奖励 ${formatNumber(step.reward, 2)}｜新到达任务 ${step.arrival}`;
    }
    showToast("已执行一步");
  } catch (error) {
    renderRuntimeRows([], `执行一步失败：${error.message}`);
    showToast("执行一步失败");
  }
}

async function runBackendRollout() {
  if (!backendAvailable) {
    showToast("连续运行需要 Python 后端");
    return;
  }
  try {
    const state = readStateFromForm();
    const response = await postApi("/api/rollout", {
      ...buildRuntimePayload(state),
      steps: state.rollout_steps,
    });
    renderRuntimeRows(response.trace || []);
    const summary = response.summary || {};
    document.querySelector("#rollout-summary").textContent =
      `${summary.steps_executed || 0}/${summary.steps_requested || 0} 步｜均值 ${formatNumber(summary.average_reward || 0, 2)}`;
    showToast("连续运行完成");
  } catch (error) {
    renderRuntimeRows([], `连续运行失败：${error.message}`);
    showToast("连续运行失败");
  }
}

function renderRuntimeRows(rows, emptyMessage = "尚未执行一步或连续运行。") {
  const tbody = document.querySelector("#runtime-table");
  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="7">${emptyMessage}</td></tr>`;
    return;
  }
  tbody.innerHTML = rows.map((row) => {
    const decision = row.resolved_decision || {};
    const step = row.step_result || {};
    return `
      <tr>
        <td>${row.step ?? 0}</td>
        <td>${LABELS.source[decision.source] || decision.source || "--"}</td>
        <td>${renderStateChips(row.state || step.current_state || {})}</td>
        <td>${decision.action ? renderActionChips(decision.action) : "无"}</td>
        <td>${step.reward == null ? "--" : formatNumber(step.reward, 2)}</td>
        <td>${step.arrival == null ? "--" : step.arrival}</td>
        <td>${step.next_state ? renderStateChips(step.next_state) : "--"}</td>
      </tr>
    `;
  }).join("");
}

function renderStaticSections() {
  renderAssets();
  renderContractFields(dashboardData.interface_contract?.state_fields || []);
  renderScenarioBars(dashboardData.scenario_metrics?.qlearning_rows || []);
  const summary = dashboardData.stability?.summary || {};
  document.querySelector("#scheme-status").textContent = summary.scheme3_ready ? "方案 3 可用" : "等待验证";
}

function renderAssets() {
  const training = trainedPolicyStore?.training || {};
  document.querySelector("#asset-training").textContent = training.slots
    ? `${training.algorithm || "tabular_q_learning"}｜${training.slots} slots｜seed ${training.seed}`
    : "未加载";
  const root = document.querySelector("#asset-scenarios");
  const scenarios = Object.entries(trainedPolicyStore?.scenarios || {});
  root.innerHTML = scenarios.length
    ? scenarios.map(([name, scenario]) => `
      <div class="asset-row">
        <div><strong>${name}</strong><br><small>访问 ${scenario.visited_state_count} / ${scenario.entry_count}</small></div>
        <strong>${formatPercent(scenario.visited_ratio)}</strong>
      </div>
    `).join("")
    : `<p>暂无训练快照。</p>`;
}

function renderContractFields(fields) {
  const root = document.querySelector("#contract-fields");
  root.innerHTML = fields.length
    ? fields.map((field) => `
      <div class="field-row">
        <strong>${field.name}</strong>
        <span>${Array.isArray(field.range) ? field.range.join("..") : "--"}</span>
        <small>${field.source_hint || ""}</small>
      </div>
    `).join("")
    : `<p>暂无接口字段。</p>`;
}

function renderScenarioBars(rows) {
  const root = document.querySelector("#scenario-bars");
  if (!rows.length) {
    root.innerHTML = `<p>暂无场景指标。</p>`;
    return;
  }
  const maxReward = Math.max(...rows.map((item) => Number(item.average_reward || 0)), 1);
  root.innerHTML = rows.map((row) => {
    const reward = Number(row.average_reward || 0);
    return `
      <div class="bar-row">
        <div><strong>${row.coverage_scenario}</strong><span>${formatNumber(reward, 2)}</span></div>
        <i><b style="width:${Math.max(4, (reward / maxReward) * 100)}%"></b></i>
        <small>云端比例 ${formatPercent(row.cloud_offload_ratio || 0)}</small>
      </div>
    `;
  }).join("");
}

function buildTrustedActPayload(state) {
  const entry = lookupTrainedPolicyEntry(state.scenario, state);
  return {
    schema_version: "qlearning_policy.api.act.v1",
    scenario_name: state.scenario,
    policy_mode: state.policy_mode,
    state: buildStatePayload(state),
    resolved_decision: resolveLocalDecision(state, entry),
    coverage: buildCoveragePayload(state.scenario),
  };
}

function resolveLocalDecision(state, entry) {
  const visitCount = entry?.visit_count || 0;
  const qValue = entry?.q_value ?? null;
  if (entry && visitCount > 0 && ["trained_only", "trained_or_rule"].includes(state.policy_mode)) {
    return buildResolvedDecision({
      scenarioName: state.scenario,
      source: "trained_policy",
      covered: true,
      visitCount,
      qValue,
      action: entry.action,
      notes: [],
      state,
    });
  }
  if (state.policy_mode === "trained_only") {
    return buildResolvedDecision({
      scenarioName: state.scenario,
      source: "uncovered_state",
      covered: false,
      visitCount,
      qValue,
      action: null,
      notes: ["当前状态未被训练覆盖。"],
      state,
    });
  }
  return buildResolvedDecision({
    scenarioName: state.scenario,
    source: state.policy_mode === "rule_based" ? "rule_based" : "rule_based_fallback",
    covered: false,
    visitCount,
    qValue,
    action: selectRuleBasedAction(state, simulatorConfig),
    notes: state.policy_mode === "trained_or_rule" ? ["当前状态未命中训练表，使用规则回退。"] : [],
    state,
  });
}

function buildResolvedDecision({ scenarioName, source, covered, visitCount, qValue, action, notes, state }) {
  if (!action) {
    return {
      scenario_name: scenarioName,
      source,
      covered,
      visit_count: visitCount,
      q_value: qValue,
      action: null,
      action_class: null,
      estimated_reward: null,
      estimated_delay: null,
      estimated_energy: null,
      reward_breakdown: null,
      notes,
    };
  }
  const breakdown = computeRewardBreakdown(state, action, simulatorConfig);
  return {
    scenario_name: scenarioName,
    source,
    covered,
    visit_count: visitCount,
    q_value: qValue,
    action: buildActionPayload(action),
    action_class: classifyAction(action),
    estimated_reward: breakdown.reward,
    estimated_delay: breakdown.delay,
    estimated_energy: breakdown.energy,
    reward_breakdown: breakdown,
    notes,
  };
}

function computeRewardBreakdown(state, action, config) {
  const illegal = isIllegalAction(state, action, config);
  const executed = illegal ? { local_tasks: 0, edge_tasks: 0, cloud_tasks: 0 } : action;
  const processed = executed.local_tasks + executed.edge_tasks + executed.cloud_tasks;
  const remoteTasks = executed.edge_tasks + executed.cloud_tasks;
  const rate = config.link_rates_bps[state.link];
  const edgeLoad = config.edge_load_levels[state.edge_load];
  const cloudLoad = config.cloud_load_levels[state.cloud_load];

  const waitDelay = state.queue / Math.max(config.avg_arrival_rate, 1e-9);
  const localDelay = (config.cycles_per_task * executed.local_tasks) / config.local_cpu_hz;
  const txDelay = (config.task_size_bits * executed.edge_tasks) / rate;
  const cloudTxDelay = (config.task_size_bits * executed.cloud_tasks) / rate;
  const edgeDelay = txDelay * (1.0 + config.edge_delay_scale * edgeLoad);
  const cloudDelay =
    cloudTxDelay
    + config.cloud_backhaul_delay_per_task * executed.cloud_tasks
    + config.cloud_compute_delay_per_task * executed.cloud_tasks * (1.0 + config.cloud_delay_scale * cloudLoad);
  const delay = processed === 0 ? waitDelay : waitDelay + (localDelay + edgeDelay + cloudDelay) / processed;
  const localEnergy = config.beta * (config.local_cpu_hz ** 2) * config.cycles_per_task * executed.local_tasks;
  const txEnergy = (config.tx_power_watts * config.task_size_bits * remoteTasks) / rate;
  const energy = localEnergy + txEnergy;
  const utility = config.theta * Math.log1p(processed);
  const queuePenalty = config.queue_weight * state.queue;
  const illegalPenalty = illegal ? config.illegal_action_penalty : 0.0;
  const lowLinkOffloadPenalty = state.link <= config.low_link_penalty_threshold
    ? config.low_link_offload_penalty * remoteTasks
    : 0.0;
  const urgencyDelayPenalty = config.urgency_delay_weight * state.task_urgency * delay;
  const deadlineMissPenalty = config.deadline_miss_penalty * Math.max(0.0, delay - config.task_deadlines[state.task_urgency]);
  const sensitivityWeightedRemoteTasks = executed.edge_tasks + config.cloud_data_sensitivity_multiplier * executed.cloud_tasks;
  const riskWeightedRemoteTasks = executed.edge_tasks + config.cloud_area_risk_multiplier * executed.cloud_tasks;
  const dataSensitivityPenalty = config.data_sensitivity_offload_penalty * state.data_sensitivity * sensitivityWeightedRemoteTasks;
  const areaRiskPenalty = config.area_risk_offload_penalty * state.area_risk * riskWeightedRemoteTasks;
  const cloudUsagePenalty = config.cloud_usage_penalty_per_task * executed.cloud_tasks;
  const lowLinkCloudPenalty = state.link <= config.low_link_cloud_penalty_threshold
    ? config.low_link_cloud_penalty_per_task * executed.cloud_tasks
    : 0.0;
  const edgeCongestionPenalty = state.edge_load >= config.edge_congestion_threshold
    ? config.edge_congestion_penalty_per_task * executed.edge_tasks
    : 0.0;
  const cloudCongestionReliefBonus =
    state.edge_load >= config.edge_congestion_threshold && state.link > config.low_link_cloud_penalty_threshold
      ? config.cloud_congestion_relief_bonus_per_task * executed.cloud_tasks
      : 0.0;
  const batteryPenalty = state.battery <= 0 && processed > 0 ? 4.0 : 0.0;
  const reward =
    utility
    + cloudCongestionReliefBonus
    - config.delay_weight * delay
    - config.energy_weight * energy
    - queuePenalty
    - illegalPenalty
    - lowLinkOffloadPenalty
    - urgencyDelayPenalty
    - deadlineMissPenalty
    - dataSensitivityPenalty
    - areaRiskPenalty
    - cloudUsagePenalty
    - lowLinkCloudPenalty
    - edgeCongestionPenalty
    - batteryPenalty;

  return {
    reward,
    utility,
    delay,
    energy,
    queue_penalty: queuePenalty,
    illegal_penalty: illegalPenalty,
    low_link_offload_penalty: lowLinkOffloadPenalty,
    urgency_delay_penalty: urgencyDelayPenalty,
    deadline_miss_penalty: deadlineMissPenalty,
    data_sensitivity_penalty: dataSensitivityPenalty,
    area_risk_penalty: areaRiskPenalty,
    cloud_usage_penalty: cloudUsagePenalty,
    low_link_cloud_penalty: lowLinkCloudPenalty,
    edge_congestion_penalty: edgeCongestionPenalty,
    cloud_congestion_relief_bonus: cloudCongestionReliefBonus,
  };
}

function selectRuleBasedAction(state, config) {
  if (state.queue <= 0) {
    return { local_tasks: 0, edge_tasks: 0, cloud_tasks: 0 };
  }
  const highLink = state.link >= config.link_rates_bps.length - 1;
  const lowEdgeLoad = state.edge_load === 0;
  const highEdgeLoad = state.edge_load >= config.edge_load_levels.length - 1;
  const lowCloudLoad = state.cloud_load === 0;
  const enoughBattery = state.battery >= 2;
  const remoteSensitive = state.data_sensitivity >= 2 || state.area_risk >= 2;
  if (remoteSensitive && enoughBattery) {
    return { local_tasks: Math.min(config.max_local_tasks, state.queue), edge_tasks: 0, cloud_tasks: 0 };
  }
  if (highLink && highEdgeLoad && lowCloudLoad && !remoteSensitive) {
    return { local_tasks: 0, edge_tasks: 0, cloud_tasks: Math.min(config.max_cloud_tasks, state.queue) };
  }
  if (highLink && lowEdgeLoad && state.queue >= 3 && enoughBattery) {
    return { local_tasks: 1, edge_tasks: 1, cloud_tasks: Math.min(config.max_cloud_tasks, Math.max(0, state.queue - 2)) };
  }
  if (highLink && state.edge_load <= 1) {
    return { local_tasks: 0, edge_tasks: Math.min(config.max_edge_tasks, state.queue), cloud_tasks: 0 };
  }
  if (enoughBattery) {
    return { local_tasks: Math.min(config.max_local_tasks, state.queue), edge_tasks: 0, cloud_tasks: 0 };
  }
  return { local_tasks: 0, edge_tasks: 0, cloud_tasks: 0 };
}

function isIllegalAction(state, action, config) {
  const processed = action.local_tasks + action.edge_tasks + action.cloud_tasks;
  return (
    action.local_tasks < 0
    || action.edge_tasks < 0
    || action.cloud_tasks < 0
    || action.local_tasks > config.max_local_tasks
    || action.edge_tasks > config.max_edge_tasks
    || action.cloud_tasks > config.max_cloud_tasks
    || processed > state.queue
  );
}

function buildActionPayload(action) {
  return {
    local_tasks: action.local_tasks,
    edge_tasks: action.edge_tasks,
    cloud_tasks: action.cloud_tasks,
    processed_tasks: action.local_tasks + action.edge_tasks + action.cloud_tasks,
    remote_tasks: action.edge_tasks + action.cloud_tasks,
  };
}

function classifyAction(action) {
  const processedTasks = action.local_tasks + action.edge_tasks + action.cloud_tasks;
  if (processedTasks === 0) {
    return "defer";
  }
  const activeParts = [action.local_tasks, action.edge_tasks, action.cloud_tasks].filter((value) => value > 0).length;
  if (activeParts > 1) {
    return "hybrid";
  }
  if (action.local_tasks > 0) {
    return "local_only";
  }
  if (action.edge_tasks > 0) {
    return "edge_only";
  }
  return "cloud_only";
}

function buildDecisionReason(decision) {
  if (decision.notes?.length) {
    return decision.notes.join("｜");
  }
  if (decision.source === "trained_policy") {
    return "真实训练快照命中，当前动作来自 Q 表查表。";
  }
  if (decision.source === "rule_based") {
    return "当前使用规则策略基线。";
  }
  return "当前状态未命中训练表，使用规则回退。";
}

function summarizeAction(state, action) {
  if (action.processed_tasks === 0) {
    return "暂不处理，队列压力会保留。";
  }
  if (state.area_risk >= 2 && action.cloud_tasks === 0) {
    return "高风险区域下抑制云端卸载。";
  }
  if (state.edge_load >= 2 && action.cloud_tasks > 0) {
    return "边缘拥塞时尝试转云。";
  }
  if (state.link <= 0 && action.cloud_tasks === 0) {
    return "弱链路下减少云端使用。";
  }
  return "按当前 reward 口径估计。";
}

function buildCoveragePayload(scenarioName) {
  const scenario = trainedPolicyStore?.scenarios?.[scenarioName];
  if (!scenario) {
    return {};
  }
  return {
    entry_count: scenario.entry_count,
    visited_state_count: scenario.visited_state_count,
    visited_ratio: scenario.visited_ratio,
    sample_states: scenario.sample_states,
    training: trainedPolicyStore.training,
  };
}

function lookupTrainedPolicyEntry(scenarioName, state) {
  const scenario = trainedPolicyStore?.scenarios?.[scenarioName];
  if (!scenario) {
    return null;
  }
  return scenario.entries.get(buildStateKey(state)) || null;
}

function buildTrainedPolicyStore(payload) {
  const scenarios = {};
  Object.entries(payload.scenarios || {}).forEach(([scenarioName, scenarioPayload]) => {
    const entries = new Map();
    (scenarioPayload.entries || []).forEach((row) => {
      entries.set(row.slice(0, 8).map((value) => Number(value)).join("|"), {
        action: {
          local_tasks: Number(row[8]),
          edge_tasks: Number(row[9]),
          cloud_tasks: Number(row[10]),
        },
        q_value: Number(row[11]),
        visit_count: Number(row[12]),
      });
    });
    scenarios[scenarioName] = {
      entries,
      entry_count: Number(scenarioPayload.entry_count || entries.size),
      visited_state_count: Number(scenarioPayload.visited_state_count || 0),
      visited_ratio: Number(scenarioPayload.visited_ratio || 0),
      sample_states: (scenarioPayload.sample_states || []).map((row) => row.map((value) => Number(value))),
    };
  });
  return {
    training: payload.training || {},
    scenarios,
  };
}

function applyTrainedSample() {
  const scenarioName = readValue("#input-scenario");
  const scenario = trainedPolicyStore?.scenarios?.[scenarioName];
  if (!scenario?.sample_states?.length) {
    showToast("当前场景没有训练样例");
    return;
  }
  const sample = scenario.sample_states[Math.floor(Math.random() * scenario.sample_states.length)];
  setValue("#input-queue", sample[0]);
  setValue("#input-link", sample[1]);
  setValue("#input-battery", sample[2]);
  setValue("#input-edge", sample[3]);
  setValue("#input-cloud", sample[4]);
  setValue("#input-urgency", sample[5]);
  setValue("#input-sensitive", sample[6]);
  setValue("#input-risk", sample[7]);
  showToast(`已载入访问 ${sample[8]} 次的训练状态`);
}

function applyBackendState(nextState) {
  setValue("#input-queue", nextState.queue);
  setValue("#input-link", nextState.link);
  setValue("#input-battery", nextState.battery);
  setValue("#input-edge", nextState.edge_load);
  setValue("#input-cloud", nextState.cloud_load);
  setValue("#input-urgency", nextState.task_urgency);
  setValue("#input-sensitive", nextState.data_sensitivity);
  setValue("#input-risk", nextState.area_risk);
}

function readStateFromForm() {
  return {
    scenario: readValue("#input-scenario"),
    queue: readNumber("#input-queue"),
    link: readNumber("#input-link"),
    battery: readNumber("#input-battery"),
    edge_load: readNumber("#input-edge"),
    cloud_load: readNumber("#input-cloud"),
    task_urgency: readNumber("#input-urgency"),
    data_sensitivity: readNumber("#input-sensitive"),
    area_risk: readNumber("#input-risk"),
    policy_mode: readValue("#input-policy-mode"),
    runtime_seed: readOptionalNumber("#input-runtime-seed"),
    rollout_steps: readNumber("#input-rollout-steps"),
  };
}

function buildRuntimePayload(state) {
  return {
    scenario_name: state.scenario,
    policy_mode: state.policy_mode,
    seed: state.runtime_seed,
    state: buildStatePayload(state),
  };
}

function buildStatePayload(state) {
  return {
    queue: state.queue,
    link: state.link,
    battery: state.battery,
    edge_load: state.edge_load,
    cloud_load: state.cloud_load,
    task_urgency: state.task_urgency,
    data_sensitivity: state.data_sensitivity,
    area_risk: state.area_risk,
  };
}

function renderStateJson(state) {
  document.querySelector("#state-json").textContent = JSON.stringify({
    city: readValue("#input-city"),
    route: readValue("#input-route"),
    task: readValue("#input-task"),
    weather: readValue("#input-weather"),
    scenario_name: state.scenario,
    policy_mode: state.policy_mode,
    seed: state.runtime_seed,
    state: buildStatePayload(state),
  }, null, 2);
}

async function copyStateJson() {
  try {
    await navigator.clipboard.writeText(document.querySelector("#state-json").textContent);
    showToast("接口 JSON 已复制");
  } catch (error) {
    showToast("复制失败");
  }
}

async function fetchJson(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

async function postApi(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `HTTP ${response.status}`);
  }
  return data;
}

function buildStateKey(state) {
  return POLICY_STATE_FIELDS.map((fieldName) => Number(state[fieldName])).join("|");
}

function formatAction(action) {
  return `本地 ${action.local_tasks}｜边缘 ${action.edge_tasks}｜云端 ${action.cloud_tasks}`;
}

function renderStateChips(state) {
  return `
    <div class="chip-list">
      <span>队列 ${state.queue ?? "--"}</span>
      <span>链路 ${state.link == null ? "--" : LABELS.link[state.link]}</span>
      <span>电量 ${state.battery ?? "--"}</span>
      <span>边缘 ${state.edge_load == null ? "--" : LABELS.load[state.edge_load]}</span>
      <span>云端 ${state.cloud_load == null ? "--" : LABELS.load[state.cloud_load]}</span>
      <span>紧急 ${state.task_urgency == null ? "--" : LABELS.level[state.task_urgency]}</span>
      <span>敏感 ${state.data_sensitivity == null ? "--" : LABELS.level[state.data_sensitivity]}</span>
      <span>风险 ${state.area_risk == null ? "--" : LABELS.level[state.area_risk]}</span>
    </div>
  `;
}

function renderActionChips(action) {
  return `
    <div class="chip-list action-chips">
      <span>本地 ${action.local_tasks}</span>
      <span>边缘 ${action.edge_tasks}</span>
      <span>云端 ${action.cloud_tasks}</span>
    </div>
  `;
}

function updateRangeLabels() {
  document.querySelector("#label-queue").textContent = readValue("#input-queue");
  document.querySelector("#label-battery").textContent = readValue("#input-battery");
}

function readValue(selector) {
  return document.querySelector(selector).value;
}

function setValue(selector, value) {
  document.querySelector(selector).value = String(value);
}

function readNumber(selector) {
  return Number(readValue(selector));
}

function readOptionalNumber(selector) {
  const raw = readValue(selector);
  return raw === "" ? null : Number(raw);
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function formatNumber(value, digits) {
  return Number(value || 0).toFixed(digits);
}

function formatPercent(value) {
  return `${(Number(value || 0) * 100).toFixed(1)}%`;
}

function signedDelta(value) {
  const numeric = Number(value || 0);
  return numeric >= 0 ? `+${numeric}` : String(numeric);
}

function showToast(message) {
  const toast = document.querySelector("#toast");
  toast.textContent = message;
  toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 1700);
}
