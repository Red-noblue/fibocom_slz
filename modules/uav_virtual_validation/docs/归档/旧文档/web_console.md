# Web 控制台

## 目标

Web 控制台用于对外展示仿真世界，提供交互式查看能力：

- 城市建筑体块
- 高楼密集区
- 禁飞区
- 计划航线
- 多高度天气采样点
- 对象属性检查
- 图层开关
- 天气高度层筛选
- 程序化城市 / 真实城市资产切换

## 运行步骤

先生成世界资产：

```bash
python projects/uav_virtual_validation/scripts/build_world.py
```

启动 Web 服务：

```bash
python projects/uav_virtual_validation/scripts/serve_web.py
```

默认访问：

```text
http://127.0.0.1:8090/web/
```

服务器对外访问地址：

```text
http://10.112.25.82:8090/web/
```

如果需要更换端口：

```bash
python projects/uav_virtual_validation/scripts/serve_web.py --port 8091
```

脚本默认绑定 `0.0.0.0`，会输出本机、局域网和指定服务器 IP 访问地址。

如果外部设备无法访问，优先检查：

- 服务器防火墙是否放行端口。
- 当前网络是否允许访问 `10.112.25.82`。
- 是否已经通过 `build_world.py` 生成 `outputs/urban_grid_world/`。

## 技术选择

第一版使用 CesiumJS，原因：

- 原生支持 GeoJSON
- 原生支持 CZML
- 适合 3D GIS、航线和城市空间展示
- 后续可以升级到 3D Tiles、地形、真实城市模型和时间动态场景

当前不直接使用 PX4/Gazebo/AirSim/Isaac Sim 做网页底座。

原因是这些平台更适合仿真执行或高保真物理/视觉仿真，不适合作为第一阶段对外 Web 控制台的展示底座。

## 当前边界

当前页面展示的是程序化城市世界资产，不是完整高保真物理仿真。

它用于：

- 对外展示系统空间能力
- 检查场景资产是否合理
- 支撑后续预测、仿真、验证结果叠加
- 为 Cesium 3D Tiles 或高保真仿真平台接入做准备
