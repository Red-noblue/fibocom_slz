# 基础 Q-learning 框架说明

本文说明 `modules/Q-learning` 当前活跃基础框架的目标、目录、状态建模、动作建模、奖励设计和输出产物，方便后续在模块内部继续扩展，而不混淆历史归档案例。

## 1. 当前定位

当前活跃框架定位为：

```text
UAV 端边计算卸载的基础 Q-learning 策略评估器
```

从大项目角度看，它更准确的身份是：

```text
低空无人机端边云协同中的策略学习 / 计算卸载决策层雏形
```

这里的 `Q-learning` 是第一版算法选择，作用是用较低复杂度把“状态、动作、奖励、策略对比”这条决策链路跑通。最终模块不必限制为 Q-learning；当状态空间、动作空间或多无人机协同复杂度上升后，可以继续演进到 DQN、PPO、SAC、多智能体强化学习，或规则策略与学习策略混合的方案。

它只解决一个具体问题：

```text
给定当前任务队列、链路质量、电量状态和边缘负载，
决定当前时隙更适合本地计算、边缘卸载，还是二者组合。
```

在 `fibocom_slz` 大项目中的预期位置是接收其他模块的评估结果，再输出策略动作：

```text
无线电地图 / 网络覆盖 -> link、覆盖概率、吞吐估计
天气能耗引擎 -> battery、energy、天气风险、可达性
虚拟验证平台 -> 城市、航线、天气、仿真时序、验证指标
任务侧输入 -> queue、任务类型、deadline、数据敏感性

策略学习模块 -> local / edge / cloud / hybrid / defer / fallback
```

当前明确不负责：

- 飞控控制
- 真实网络通信
- 真实基站接口
- 多无人机协同
- 大规模深度强化学习

上述“不负责”是当前基础版本边界，不表示未来不能研究多无人机或深度强化学习；它表示当前代码不会直接承担飞控、真实通信或生产级调度职责。

## 2. 当前目录

活跃代码位于：

```text
src/qlearning_policy/
```

主要文件：

- `agent.py`
  - 表格型 Q-learning 智能体。
- `state.py`
  - 离散状态编码器 `StateCodec`。
- `offloading.py`
  - 计算卸载环境、状态、动作和奖励计算。
- `policies.py`
  - `LocalOnly`、`OffloadOnly`、`RuleBased` 三个可解释基线策略。
- `scenarios.py`
  - 覆盖场景配置，将网络覆盖抽象为链路和边缘负载概率。
- `simulation.py`
  - 训练、评估、策略对比和轨迹整理。
- `cli.py`
  - 当前最小命令行入口。

历史课程案例仍保留在：

```text
archives/案例5-qlearning-offloading/
```

## 3. 状态空间

当前基础状态已经从四维扩展为七维离散状态：

```text
state = (queue, link, battery, edge_load, task_urgency, data_sensitivity, area_risk)
```

含义：

- `queue`
  - 当前任务队列长度。
- `link`
  - 当前无线链路档位。
- `battery`
  - 当前电量档位。
- `edge_load`
  - 当前边缘节点负载档位。
- `task_urgency`
  - 当前任务紧急度档位。
- `data_sensitivity`
  - 当前任务数据敏感度档位。
- `area_risk`
  - 当前飞行区域风险档位。

默认情况下：

- `queue` 范围：`0 ~ 16`
- `link` 档位数：`3`
- `battery` 档位数：`5`
- `edge_load` 档位数：`3`
- `task_urgency` 档位数：`3`
- `data_sensitivity` 档位数：`3`
- `area_risk` 档位数：`3`

状态编码器 `StateCodec` 负责把上述多维离散状态压成一个整数索引，用于访问 Q 表。

## 4. 动作空间

当前动作为：

```text
action = (local_tasks, offload_tasks)
```

含义：

- `local_tasks`
  - 当前时隙本地处理的任务数。
- `offload_tasks`
  - 当前时隙卸载到边缘的任务数。

默认上限为：

- 本地处理最多 `2` 个任务
- 边缘卸载最多 `2` 个任务

因此当前动作空间是离散组合动作，不涉及连续卸载比例。

## 5. 奖励设计

当前 reward 由以下几部分组成：

```text
reward =
utility
- delay_weight * delay
- energy_weight * energy
- queue_penalty
- illegal_action_penalty
- low_link_offload_penalty
- urgency_delay_penalty
- deadline_miss_penalty
- data_sensitivity_penalty
- area_risk_penalty
```

其中：

- `utility`
  - 处理任务带来的收益，使用 `log(1 + processed_tasks)` 保持边际收益递减。
- `delay`
  - 等待时延、本地计算时延和边缘卸载时延的组合。
- `energy`
  - 本地计算能耗和边缘上传能耗的组合。
- `queue_penalty`
  - 当前队列积压惩罚。
- `illegal_action_penalty`
  - 当动作请求超过当前队列时的惩罚。
- `low_link_offload_penalty`
  - 保守卸载版本使用的低链路卸载惩罚；默认基础版本为 `0`，不影响原始实验口径。
- `urgency_delay_penalty`
  - 紧急任务对时延更敏感，紧急度越高，时延惩罚越大。
- `deadline_miss_penalty`
  - 紧急任务对应更短 deadline，任务时延超过 deadline 后额外扣分。
- `data_sensitivity_penalty`
  - 敏感数据被卸载时增加惩罚，模拟隐私、合规或安全要求。
- `area_risk_penalty`
  - 高风险区域卸载时增加惩罚，模拟低空监管和安全边界要求。

当前非法动作处理方式是：

```text
请求动作非法 -> 实际执行空动作 (0, 0) -> 给予惩罚
```

这能让 Q-learning 自己学会规避不合理动作。

## 6. 当前基线策略

为了避免 Q-learning 只和自己比，当前内置三种基线策略：

- `LocalOnly`
  - 全部优先本地计算。
- `OffloadOnly`
  - 全部优先边缘卸载。
- `RuleBased`
  - 根据链路质量、边缘负载和电量做简单规则判断。

当前 `run-demo` 会输出 `Q-learning` 与这三种基线策略的对比指标。

## 7. 当前命令行入口

运行基础演示：

```bash
cd modules/Q-learning
PYTHONPATH=src ../../._envs/uav-modules-py310/bin/python -m qlearning_policy run-demo --slots 1000 --seed 1
```

指定覆盖场景：

```bash
cd modules/Q-learning
PYTHONPATH=src ../../._envs/uav-modules-py310/bin/python -m qlearning_policy run-demo \
  --coverage-scenario weak_coverage \
  --slots 1000 \
  --seed 1
```

运行测试：

```bash
cd modules/Q-learning
PYTHONPATH=src ../../._envs/uav-modules-py310/bin/python -m pytest tests -q
```

批量运行全部覆盖场景：

```bash
cd modules/Q-learning
PYTHONPATH=src ../../._envs/uav-modules-py310/bin/python -m qlearning_policy run-scenarios \
  --slots 1000 \
  --seed 1
```

分析批量场景结果：

```bash
cd modules/Q-learning
PYTHONPATH=src ../../._envs/uav-modules-py310/bin/python -m qlearning_policy analyze-scenarios
```

分析单次实验结果：

```bash
cd modules/Q-learning
PYTHONPATH=src ../../._envs/uav-modules-py310/bin/python -m qlearning_policy analyze-run \
  --input-dir outputs/qlearning_policy/task_semantics_long/weak_coverage_20k \
  --scenario-name weak_coverage_20k
```

对比默认版与保守卸载版：

```bash
cd modules/Q-learning
PYTHONPATH=src ../../._envs/uav-modules-py310/bin/python -m qlearning_policy compare-conservative \
  --coverage-scenario weak_coverage \
  --slots 1000 \
  --seed 1
```

验证任务语义趋势稳定性：

```bash
cd modules/Q-learning
PYTHONPATH=src ../../._envs/uav-modules-py310/bin/python -m qlearning_policy validate-task-semantics \
  --slots 8000 \
  --seeds 1,2,3 \
  --coverage-scenario all
```

## 8. 当前输出产物

`run-demo` 当前会生成以下文件：

- `strategy_metrics.csv`
  - 各策略的聚合指标。
- `strategy_metrics.json`
  - 与 CSV 对应的 JSON 版本。
- `decision_trace.csv`
  - Q-learning 在每个时隙的状态、动作、奖励和下一状态。
- `learning_curve.csv`
  - Q-learning 每个时隙的即时 reward 和累计平均 reward。
- `policy_table.csv`
  - 训练结束后每个离散状态对应的贪心动作。

`run-scenarios` 会在根输出目录额外生成：

- `scenario_strategy_metrics.csv`
  - 跨覆盖场景的策略对比汇总表。
- `scenario_strategy_metrics.json`
  - 与 CSV 对应的 JSON 版本。

同时，每个覆盖场景都会生成自己的 `strategy_metrics.csv`、`decision_trace.csv`、`learning_curve.csv` 和 `policy_table.csv`。

`analyze-scenarios` 会在分析输出目录生成：

- `scenario_best_strategy.csv`
  - 每个覆盖场景下平均 reward 最高的策略，以及 Q-learning 与最优策略的差距。
- `qlearning_scenario_summary.csv`
  - Q-learning 在每个场景下的 reward、时延、能耗、队列、任务数和卸载比例。
- `qlearning_trace_action_summary.csv`
  - 基于实际轨迹，按链路、边缘负载、电量分组统计本地、卸载、混合、空闲动作比例。
- `qlearning_trace_action_class_summary.csv`
  - 基于实际轨迹，继续按动作类型拆分平均 reward、处理任务数和卸载比例。
- `qlearning_policy_action_summary.csv`
  - 基于训练后的策略表，按状态分组统计策略倾向。
- `reward_diagnostics.csv`
  - 固定代表性状态，逐动作计算 reward 分解，用于解释为什么某些低链路状态仍可能选择卸载。
- `analysis_notes.json`
  - 面向解释的简短结论。

`analyze-run` 会针对单个 `run-demo` 输出目录生成同类分析表，适合长训练、单场景专项实验和方案 2 的任务语义分组分析。

`compare-conservative` 会生成：

- `conservative_comparison.csv`
  - 默认版与保守卸载版的策略指标对比。
- `qlearning_conservative_delta.csv`
  - Q-learning 训练轨迹和训练后贪心策略的 reward、卸载比例、时延、能耗、任务数差异。
- `<coverage_scenario>/base/`
  - 默认 reward 版本的完整产物。
- `<coverage_scenario>/conservative/`
  - 保守卸载 reward 版本的完整产物。

`validate-task-semantics` 会生成：

- `task_semantics_metrics.csv`
  - 多场景、多 seed 下各策略的基础指标。
- `task_semantics_trace_trends.csv`
  - 训练轨迹中高语义等级相对低等级的卸载比例变化。
- `task_semantics_greedy_trace_trends.csv`
  - 训练后无 epsilon 探索的贪心轨迹趋势，用于排除训练探索噪声。
- `task_semantics_policy_trends.csv`
  - 训练后策略表中高语义等级相对低等级的平均卸载任务数变化。
- `task_semantics_stability_summary.csv`
  - 稳定性汇总，`stable_ratio` 越接近 `1` 表示趋势越稳定。
- `task_urgency_penalty_summary.csv`
  - `task_urgency` 的 deadline 惩罚对齐摘要；紧急任务不强行按“少卸载”判定，而重点看超时惩罚和 reward 是否稳定体现更高风险。
- `task_semantics_stability_notes.json`
  - 对稳定性结果的文字化结论。

`decision_trace.csv` 适合做：

- 动作行为分析
- 非法动作检查
- 状态转移抽样复查

`learning_curve.csv` 适合做：

- 收敛曲线绘制
- 不同超参数训练过程对比

`policy_table.csv` 适合做：

- 分析不同 `link` 档位下的策略差异
- 分析不同 `edge_load` 档位下是否减少卸载
- 解释训练完成后的策略行为

## 9. 当前测试覆盖

当前测试主要覆盖：

- `StateCodec` 编码和解码
- 环境状态转移是否合法
- 非法动作是否被置为空动作并惩罚
- Q-learning 训练流程是否返回有限指标
- 基线策略对比是否齐全
- `run-demo` 输出文件是否完整
- `run-scenarios` 是否生成跨场景汇总和每个场景的独立产物
- `analyze-scenarios` 是否生成策略解释表
- `analyze-run` 是否能按任务语义字段分组分析单次实验
- `compare-conservative` 是否生成默认版与保守卸载版对比表
- `validate-task-semantics` 是否能完成多场景多 seed 稳定性验证

## 10. 后续建议

当前最稳的扩展顺序是：

1. 巩固当前表格型 Q-learning 基线，继续使用 `policy_table.csv` 解释每个状态下的贪心动作。
2. 增加更多参数敏感性实验，例如链路分布、任务到达分布、电量初值、reward 权重。
3. 增加更多状态变量，例如任务紧急度、区域风险、数据敏感度。
4. 增加动作层级，例如本地、边缘、云端、混合计算、延迟处理或安全降级。
5. 再考虑升级到 `DQN/PPO/SAC` 或多智能体强化学习，先把基础表格型框架打磨清楚，再上更重的模型。
