# 可视化质量升级方案

## 当前已接入

- OpenStreetMap 影像底图
- 程序化城市世界
- 真实城市 GeoJSON
- 本地 3D Tiles 建筑
- Cesium OSM Buildings（需 token）
- 椭球地形 / 真实地形切换（需 token）

## 推荐使用顺序

### 默认模式

- 城市：Manhattan Midtown
- 建筑后端：本地 3D Tiles
- 地形：椭球地形
- 影像：OpenStreetMap

### 高质量模式

- 城市：Chicago / London / Tokyo
- 建筑后端：本地 3D Tiles
- 地形：真实地形
- 需要 Cesium Ion Token

### 快速演示模式

- 建筑后端：Cesium OSM Buildings
- 地形：真实地形
- 需要 Cesium Ion Token

## 颜色策略

建筑颜色不应只承担“好看”的任务，还应承载分析信息。

推荐三种模式：

- `中性实景`：更接近真实城市外观
- `高度分析`：按高度分层显示
- `风险强调`：按风险等级染色

## 后续重点

- 把大城市默认切到本地 3D Tiles。
- 为不同城市增加更精确的建筑和地面语义分层。
- 继续优化相机、阴影、标签和底图。
- 逐步引入分块加载，避免一次性载入所有要素。
