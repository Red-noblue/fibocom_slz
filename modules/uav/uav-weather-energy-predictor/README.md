# uav-weather-energy-predictor

从 `/home/fibo/uav_cma_realtime_gis_demo` 抽出的预测侧子项目。

当前目标不是做完整产品，而是把原 demo 里真正可复用的预测链路独立出来：

- 飞行日志 -> 训练样本
- 训练样本 -> 能耗模型
- 天气接口 -> 沿航线天气序列
- 任务配置 + 天气序列 -> 能耗预测结果

## 当前目录结构

```text
uav-weather-energy-predictor/
  configs/
    open_meteo_config.json
  docs/
    migration-notes.md
  scripts/
    build_features.py
    train_model.py
    predict_route.py
  src/
    uav_weather_energy_predictor/
      __init__.py
      common.py
      feature_builder.py
      route_prediction.py
      training.py
      weather_client.py
  pyproject.toml
  requirements.txt
```

## 从原 demo 迁移的内容

- `scripts/build_features.py`
- `scripts/train_model.py`
- `scripts/cma_generic_client.py`
- `scripts/realtime_route_demo.py` 中的预测内核、天气插值与结果输出逻辑

## 本轮轻量重构

- 去掉了对 `G:\...` 数据路径的硬编码依赖。
- 将“地图输出”从预测链路中剥离，不再耦合到同一个脚本。
- 将天气来源标识从硬编码 `CMA realtime` 改为根据配置自动识别。

## 暂不迁移

- GIS 地图渲染
- A* 路径/禁飞区演示
- 仪表盘回放
