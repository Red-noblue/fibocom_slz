# 仿真世界设计

## 当前目标

第一版仿真世界不是高保真物理引擎，而是可控、可复现、可导出的城市低空环境资产层。

它用于承载：

- 城市建筑体块
- 高楼密集区
- 禁飞区和安全风险区
- 航线走廊
- 多高度天气采样点
- 后续 3D 展示和高保真仿真平台接入

## 当前实现

配置入口：

```text
configs/worlds/urban_grid_world.json
```

生成脚本：

```bash
python scripts/build_world.py
```

默认输出：

```text
outputs/urban_grid_world/world_summary.json
outputs/urban_grid_world/world.geojson
outputs/urban_grid_world/route.czml
```

## 数据含义

`world.geojson` 包含：

- `building`：建筑 footprint、高度、类型、风险增量
- `no_fly_zone`：禁飞区平面范围和高度范围
- `route`：计划航线
- `weather_sample`：三维天气采样点，包括风速、风向、温度、气压、湍流指数

`route.czml` 用于 Cesium 预览计划航线。

## 答辩边界

当前世界生成器是“程序化城市世界”，不是 Gazebo、AirSim 或 Isaac Sim 级别的高保真物理仿真。

它的价值是：

- 先形成可视化和验证可用的 3D 空间结构
- 让建筑、天气、风险区与航线统一到同一坐标系统
- 为后续接入高保真仿真器提供标准中间资产

不要宣称当前版本已经能精确复现真实城市风场或无人机动力学。
