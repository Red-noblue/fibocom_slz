# 天气驱动无人机能耗引擎

`uav-weather-energy-engine` 是本项目的核心算法模块。

它只负责一件事：

```text
根据任务参数、动力参数和天气条件，评估无人机任务能耗与风险。
```

## 模块定位

本模块明确不负责：

1. 飞控控制
2. 姿态控制
3. 电机闭环
4. 控制指令下发

本模块明确负责：

1. 飞行日志转训练样本
2. 天气数据接入与对齐
3. 特征工程
4. 能耗模型训练与保存
5. 固定路线、固定航速条件下的预测
6. 为后续速度/高度/路线优化提供评估内核

## 目录结构

```text
uav-weather-energy-engine/
├── configs/
├── data/
├── docs/
├── experiments/
├── notebooks/
├── outputs/
├── references/
├── scripts/
├── src/
└── tests/
```

## 当前阶段目标

先做硬核心算法：

1. 固定路线
2. 固定航速
3. 固定其他参数
4. 在给定天气下输出分段能耗、累计能耗、可达性和风险结果

后续所有主动调度能力都建立在这个内核之上。

## 参考资料工作区

本模块内置 `references/` 目录，用来集中放：

1. 开源仓库归档
2. 开放论文/学位论文
3. 数据集入口与元信息

抓取脚本：

```bash
python scripts/fetch_references.py
```

## 内置样例

当前已放入一份历史 demo 样例，位置：

```text
data/samples/legacy_demo/
```

可用于：

1. 对齐旧 demo 输出结构
2. 快速验证后续展示或评估链路
3. 作为论文复现前的本地参考样例

## 快速命令

构建训练样本：

```bash
python scripts/build_dataset.py --input path/to/flights.csv --output outputs/features.csv --route R1
```

训练模型：

```bash
python scripts/train_model.py --features outputs/features.csv --model-out outputs/model.pkl --metrics-out outputs/metrics.json
```

执行固定路线预测：

```bash
python scripts/run_predict.py \
  --model outputs/model.pkl \
  --features outputs/features.csv \
  --weather-config configs/weather.yaml \
  --departure "2026-05-11 08:00:00"
```

执行固定路线速度搜索：

```bash
python scripts/run_ablation.py \
  --model outputs/model.pkl \
  --features outputs/features.csv \
  --weather-config configs/weather.yaml \
  --departure "2026-05-11 08:00:00" \
  --speed-min 6.0 \
  --speed-max 12.0 \
  --speed-step 1.0
```
