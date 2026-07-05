# Sample Chain

基于旧 demo 的现有样例产物，当前两条子项目已经可以跑通：

`预测样例产物 -> GIS 地图渲染 -> 回放预览`

## 样例产物位置

预测子项目内：

`modules/uav/uav-weather-energy-predictor/samples/legacy_demo/`

其中包含：

- `features.csv`
- `metrics.json`
- `model.pkl`
- `route_summary.csv`
- `realtime_route_summary.json`
- `realtime_route_timeseries.csv`

## 生成 GIS 地图

```bash
python3 modules/uav/uav-gis-replay-studio/scripts/render_route_map.py \
  --summary modules/uav/uav-weather-energy-predictor/samples/legacy_demo/realtime_route_summary.json \
  --timeseries modules/uav/uav-weather-energy-predictor/samples/legacy_demo/realtime_route_timeseries.csv \
  --output modules/uav/uav-gis-replay-studio/outputs/sample_chain/realtime_route_map.html
```

## 生成回放预览 PNG

```bash
python3 modules/uav/uav-gis-replay-studio/scripts/replay_dashboard.py \
  --summary modules/uav/uav-weather-energy-predictor/samples/legacy_demo/realtime_route_summary.json \
  --timeseries modules/uav/uav-weather-energy-predictor/samples/legacy_demo/realtime_route_timeseries.csv \
  --steps 80 \
  --preview-png modules/uav/uav-gis-replay-studio/outputs/sample_chain/replay_dashboard_preview.png
```

## 当前输出位置

展示子项目内：

`modules/uav/uav-gis-replay-studio/outputs/sample_chain/`

## 编译成网站

```bash
python3 modules/uav/uav-gis-replay-studio/scripts/build_site.py \
  --summary modules/uav/uav-weather-energy-predictor/samples/legacy_demo/realtime_route_summary.json \
  --timeseries modules/uav/uav-weather-energy-predictor/samples/legacy_demo/realtime_route_timeseries.csv \
  --output-dir modules/uav/uav-gis-replay-studio/outputs/sample_site
```

生成后的网站入口：

`modules/uav/uav-gis-replay-studio/outputs/sample_site/index.html`

## 内网访问

```bash
python3 modules/uav/uav-gis-replay-studio/scripts/serve_site.py \
  --site-dir modules/uav/uav-gis-replay-studio/outputs/sample_site \
  --port 8765
```

默认会打印：

- 本机访问地址
- 内网访问地址
