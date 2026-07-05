# 仿真与 3D Web 控制台调研结论

## 调研对象

本轮重点参考以下成熟项目类型：

- CesiumJS：3D GIS、GeoJSON、CZML、3D Tiles、时间动态场景。
- QGroundControl：飞控地面站的任务规划、飞行监控、日志分析界面。
- PX4/Gazebo：SITL/HITL 飞控仿真链路。
- AirSim：无人机/自动驾驶高保真视觉、传感器、API 仿真。
- Webots：机器人仿真的场景树、3D 视图、控制器、世界文件组织。

## 对本项目有价值的设计模式

### 1. 三视图主结构

成熟飞控/仿真系统通常不会把所有功能塞进一个页面。

建议本项目拆成：

```text
Plan：任务与仿真配置
Sim：仿真世界与实时状态
Analyze：误差对比、日志、报告
```

当前 Web 控制台属于 `Sim`。

### 2. 图层系统

3D GIS 项目普遍使用图层组织复杂信息。

本项目应长期保留：

- 建筑图层
- 禁飞区图层
- 航线图层
- 天气采样图层
- 风场图层
- 风险热区图层
- 仿真轨迹图层
- 预测轨迹图层

这比把所有对象硬编码在页面里可靠。

### 3. 时间轴系统

无人机任务天然是时序过程。

后续页面应加入：

- 播放 / 暂停
- 速度倍数
- 时间拖动
- 关键事件标记
- 当前时刻无人机状态
- 当前时刻天气和功率

Cesium 的 CZML 适合承载动态轨迹和时间属性。

### 4. 对象检查器

Webots、Cesium、QGroundControl 都强调对象属性查看。

本项目需要保留并增强右侧 inspector：

- 建筑高度
- 风险分数
- 禁飞区高度范围
- 天气采样点
- 当前无人机状态
- 当前功率与剩余电量

### 5. 场景配置文件优先

成熟仿真系统通常通过配置描述世界和传感器，而不是把参数写死在代码里。

本项目应继续保持：

```text
configs/scenarios/
configs/worlds/
configs/weather/
configs/vehicles/
```

后续新增传感器时再加：

```text
configs/sensors/
```

### 6. 仿真后端解耦

PX4/Gazebo、AirSim、Webots 的共同点是：仿真执行、数据接口、展示界面应解耦。

本项目建议长期坚持：

```text
world generator -> artifacts -> web console
simple simulator -> artifacts -> validation
future PX4/Gazebo -> normalized artifacts -> web console
```

网页不直接绑定某一个仿真后端。

### 7. 可复现实验

仿真可信度来自可复现，不来自界面好看。

每个实验至少应保存：

- scenario 配置
- world 配置
- vehicle 配置
- weather 配置
- random seed
- 输出产物
- 验证指标

## 推荐下一阶段功能优先级

### P0：对外演示可用

- 外部访问地址固定为 `http://10.112.25.82:8090/web/`
- 图层开关稳定
- 对象属性可查看
- 世界资产可重复生成

### P1：任务配置页

- 起点终点输入
- 天气方案选择
- 车辆参数选择
- 城市密度和高楼区配置
- 一键重新生成世界

### P2：仿真播放页

- 读取 `sim_timeseries.csv`
- 动态无人机位置
- 时间轴播放
- 功率、电量、风险联动

### P3：验证分析页

- 预测曲线 vs 仿真曲线
- 总能耗误差
- 剩余电量误差
- 风速/温度/载荷消融
- 报告导出

### P4：高保真后端接入

- PX4/Gazebo 日志适配
- AirSim 传感器数据适配
- 真实日志 replay
- 3D Tiles 城市模型导入

## 当前项目定位

当前 Web 控制台应定位为：

```text
城市低空无人机虚拟验证平台的 3D 场景与仿真结果查看器
```

不要定位为：

```text
完整飞控地面站
完整物理仿真器
真实世界数字孪生最终版
```
