# Q-learning 策略模块工作区

本目录现在作为 `fibocom_slz` 中与 Q-learning 相关作业、实验和无人机策略学习的通用工作区使用。更准确地说，它面向的是“低空无人机端边云协同决策层”：根据任务队列、链路质量、电量状态、边缘负载等状态，决定任务应本地计算、卸载到边缘，还是采用混合策略。

当前主线先构建一个基础表格型 Q-learning 框架，用于验证无人机端边计算卸载策略。Q-learning 是第一版可解释、低门槛的基线算法，不代表本目录未来只允许使用 Q-learning；后续可以在同一问题口径下升级到 DQN、PPO、SAC、多智能体强化学习或规则策略与强化学习的混合方案。

## 当前结构

- `pyproject.toml`
  - 当前活跃基础框架的 Python 包配置。
- `archives/`
  - 存放已经完成、需要保留但不再作为当前主线继续演化的历史案例。
- `src/`
  - 当前活跃基础框架代码。
- `tests/`
  - 当前活跃基础框架测试。
- `web/`
  - 本模块独立前端，用于展示策略实验结果、对外接口字段和轻量试算。
- `docs/`
  - 预留给后续新作业文档。
- `outputs/`
  - 预留给后续新作业产物。
- `tools/`
  - 保留通用工具，不随单个案例归档移动。

## 已归档案例

- `archives/案例5-qlearning-offloading`
  - 对应“基于 Q-learning 的计算卸载策略”案例 5 的完整活归档。
  - 已包含代码、测试、文档、提交材料、运行结果和最小依赖文件。

## 当前活跃框架

当前根目录新增 `qlearning_policy` 包，最小功能包括：

- 表格型 `QLearningAgent`
- 离散 `StateCodec`
- UAV 端边计算卸载环境 `OffloadingEnv`
- 低空任务语义状态：任务紧急度、数据敏感度、区域风险
- 本地计算、边缘卸载、规则策略和 Q-learning 策略对比
- 覆盖场景配置：`balanced`、`good_coverage`、`weak_coverage`、`intermittent_coverage`、`congested_edge`
- 最小 CLI：`python -m qlearning_policy run-demo`
- 训练产物：`strategy_metrics.csv`、`decision_trace.csv`、`learning_curve.csv`、`policy_table.csv`
- 对外接口：`describe-interface`、`decide`、`export-dashboard-data`
- 独立前端：`web/index.html`

## 在大项目中的功能位置

本模块当前不直接介入其他模块代码，但未来的接口位置可以按下面理解：

```text
无线电地图 / 网络覆盖模块 -> 提供链路质量、覆盖概率、吞吐能力
天气能耗模块 -> 提供电量、能耗、天气风险、任务可达性
虚拟验证模块 -> 提供城市、航线、天气、仿真时序和验证环境
任务输入 -> 提供任务队列、任务类型、紧急度、数据敏感性

上述状态输入
  -> 策略学习 / 计算卸载决策模块
  -> 输出本地计算、边缘卸载、混合计算、延迟处理或降级策略
```

因此，本目录短期服务课程作业和基础 Q-learning 实验；中期更适合作为 `policy-learning` 或 `offloading-decision` 类型模块的雏形。

## 使用建议

如果要运行当前基础框架：

```bash
cd modules/Q-learning
PYTHONPATH=src ../../._envs/uav-modules-py310/bin/python -m qlearning_policy run-demo --slots 1000 --seed 1
PYTHONPATH=src ../../._envs/uav-modules-py310/bin/python -m pytest tests -q
```

指定网络覆盖场景：

```bash
PYTHONPATH=src ../../._envs/uav-modules-py310/bin/python -m qlearning_policy run-demo \
  --coverage-scenario weak_coverage \
  --slots 1000 \
  --seed 1
```

批量运行全部覆盖场景：

```bash
PYTHONPATH=src ../../._envs/uav-modules-py310/bin/python -m qlearning_policy run-scenarios \
  --slots 1000 \
  --seed 1
```

分析批量场景结果：

```bash
PYTHONPATH=src ../../._envs/uav-modules-py310/bin/python -m qlearning_policy analyze-scenarios
```

分析单次实验结果：

```bash
PYTHONPATH=src ../../._envs/uav-modules-py310/bin/python -m qlearning_policy analyze-run \
  --input-dir outputs/qlearning_policy/task_semantics_long/weak_coverage_20k \
  --scenario-name weak_coverage_20k
```

查看对外接口契约：

```bash
PYTHONPATH=src ../../._envs/uav-modules-py310/bin/python -m qlearning_policy describe-interface
```

执行一次接口决策：

```bash
PYTHONPATH=src ../../._envs/uav-modules-py310/bin/python -m qlearning_policy decide \
  --coverage-scenario congested_edge \
  --queue 10 \
  --link 2 \
  --battery 4 \
  --edge-load 2 \
  --cloud-load 0 \
  --task-urgency 1 \
  --data-sensitivity 0 \
  --area-risk 0
```

生成并查看独立前端：

```bash
PYTHONPATH=src ../../._envs/uav-modules-py310/bin/python -m qlearning_policy export-dashboard-data
python3 -m http.server 8091 --directory web
```

访问 `http://127.0.0.1:8091/`。

对比默认版与保守卸载版：

```bash
PYTHONPATH=src ../../._envs/uav-modules-py310/bin/python -m qlearning_policy compare-conservative \
  --coverage-scenario weak_coverage \
  --slots 1000 \
  --seed 1
```

验证任务语义趋势稳定性：

```bash
PYTHONPATH=src ../../._envs/uav-modules-py310/bin/python -m qlearning_policy validate-task-semantics \
  --slots 8000 \
  --seeds 1,2,3 \
  --coverage-scenario all
```

该命令会额外输出 `task_urgency_penalty_summary.csv`，其中 `task_urgency` 不再强行按“少卸载”判定，而是重点检查 deadline 惩罚对齐是否稳定。

后续继续扩展时：

1. 不要直接改 `archives/案例5-qlearning-offloading`
2. 优先在当前根目录的 `src/`、`tests/`、`outputs/` 中开启新工作
3. 需要参考案例 5 时，再从归档区查看或复制
