# uav-gis-replay-studio

从 `/home/fibo/uav_cma_realtime_gis_demo` 抽出的展示侧子项目。

它不负责训练或预测，只消费预测子项目输出的：

- `realtime_route_summary.json`
- `realtime_route_timeseries.csv`

## 当前目录结构

```text
uav-gis-replay-studio/
  docs/
    migration-notes.md
  scripts/
    render_route_map.py
    replay_dashboard.py
  src/
    uav_gis_replay_studio/
      __init__.py
      map_renderer.py
      replay_dashboard.py
  pyproject.toml
  requirements.txt
```

## 当前范围

- GIS 路线地图渲染
- 预测结果回放仪表盘
- 静态网站编译与 HTTP 内网访问

## 本轮轻量重构

- 将地图渲染从预测主脚本剥离成独立模块。
- 保留原有回放仪表盘作为展示资产。
- 暂不迁移原 demo 中的 A* 路径/禁飞区演示逻辑，它仍属于展示增强片段。
