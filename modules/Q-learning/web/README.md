# Q-learning 独立前端

本目录是 `modules/Q-learning` 的独立前端，不属于 `modules/uav_virtual_validation` 的三维验证控制台。

## 当前功能

- 展示端-边-云三层卸载稳定性结论。
- 展示策略模块对外接口字段。
- 展示多场景 Q-learning 策略指标。
- 提供前端规则试算器，帮助理解 `queue`、`link`、`battery`、`edge_load`、`cloud_load`、`task_urgency`、`data_sensitivity`、`area_risk` 如何影响动作。

## 生成数据

```bash
cd modules/Q-learning
PYTHONPATH=src ../../._envs/uav-modules-py310/bin/python -m qlearning_policy export-dashboard-data
```

默认生成：

```text
web/static/data/policy-dashboard.json
```

## 本地访问

```bash
cd modules/Q-learning
python3 -m http.server 8091 --directory web
```

访问：

```text
http://127.0.0.1:8091/
```

## 边界

本前端只消费本模块导出的 JSON。它不直接调用、不修改、不接管 `uav_virtual_validation`、无线地图、天气能耗或其他模块。
