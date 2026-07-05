# 真实城市背景任务验证平台

## 当前能力

平台已经从随机程序化城市推进到真实城市背景：

- 默认城市：Manhattan Midtown。
- 城市预设：Manhattan Midtown、芝加哥 The Loop、伦敦 Canary Wharf、东京 Shinjuku、新加坡 Marina Bay、上海陆家嘴。
- 建筑数据：通过 OpenStreetMap / Overpass 获取真实建筑 footprint。
- 地面要素：通过 OpenStreetMap / Overpass 获取道路、水域、绿地，并生成城市范围地面面片。
- 建筑高度：优先使用 OSM `height` / `building:levels`，缺失时使用城市默认高度。
- 天气数据：通过 Open-Meteo 历史天气 API 获取小时级天气。
- 三维天气场：由 Open-Meteo 历史天气扩展为沿航线、横向分布、多高度层的天气采样场。
- 航线：城市预设提供多航点任务路线，不再是单一直线。
- Web 展示：控制台可切换“程序化城市”和“真实城市 Manhattan”。

## 默认真实城市

当前默认真实城市为：

```text
纽约 Manhattan Midtown
```

原因：

- 高楼密集，适合城市低空无人机验证叙事。
- OSM 建筑覆盖较好。
- 历史天气数据容易获取。
- 国际化示例更适合展示系统泛化能力。

## 运行命令

抓取真实城市资产：

```bash
python projects/uav_virtual_validation/scripts/fetch_real_city_assets.py \
  --city projects/uav_virtual_validation/configs/cities/manhattan_midtown.json \
  --output-dir projects/uav_virtual_validation/outputs/real_city/manhattan_midtown
```

启动 Web：

```bash
python projects/uav_virtual_validation/scripts/serve_web.py
```

访问：

```text
http://10.112.25.82:8090/web/
```

在页面左侧“数据集”选择：

```text
真实城市：Manhattan Midtown
```

## 输出资产

```text
outputs/real_city/manhattan_midtown/
  city_config_snapshot.json
  city_summary.json
  route.geojson
  real_buildings.geojson
  ground_layers.geojson
  real_weather_field.geojson
  historical_weather_open_meteo.json
  overpass_query.txt
```

当前 Manhattan Midtown 资产规模：

```text
建筑：2500
地面/道路/水域/绿地要素：3051
三维天气场采样点：300
历史天气小时样本：24
多航点路线长度：约 2.12 km
```

当前 Chicago The Loop 资产规模：

```text
建筑：2800
地面/道路/水域/绿地要素：7619
三维天气场采样点：300
历史天气小时样本：24
多航点路线长度：约 2.35 km
```

当前已生成城市资产总览：

```text
chicago_loop             8.9MB  建筑 2800  地面要素 7619  天气点 300  航线 2.35km
london_canary_wharf      7.5MB  建筑 2800  地面要素 5253  天气点 300  航线 2.58km
manhattan_midtown        5.3MB  建筑 2500  地面要素 3051  天气点 300  航线 2.12km
shanghai_lujiazui        3.2MB  建筑 1318  地面要素 1325  天气点 300  航线 2.60km
singapore_marina_bay     4.4MB  建筑 1914  地面要素 2980  天气点 300  航线 2.60km
tokyo_shinjuku           7.1MB  建筑 3200  地面要素 4576  天气点 300  航线 2.49km
```

性能判断：

- 上海、新加坡、Manhattan 适合作为较轻演示城市。
- 东京、伦敦、芝加哥要素更多，浏览器端 GeoJSON 挤出会更吃性能。
- 后续如果继续扩大范围，应尽快迁移到 3D Tiles 或做分块懒加载。

## 数据源边界

### OpenStreetMap

OSM 建筑 footprint 通常可用，但高度字段完整性取决于城市和社区维护情况。

因此：

- 有 `height` 时使用真实高度。
- 有 `building:levels` 时按层高估算。
- 都没有时使用默认高度。

不能把所有建筑高度都宣称为真实测量值。

### Open-Meteo

Open-Meteo 适合快速获得历史天气和预报天气。

它提供的是气象数据产品，不是建筑尺度 CFD 风场。

因此当前天气适合做：

- 城市级天气背景
- 任务级能耗预测输入
- 历史天气回放

还不能直接宣称为：

- 楼宇间真实湍流
- 每栋楼旁边的精细风场
- 高保真微气象仿真

## 下一步

建议继续推进：

- 继续增强真实建筑周围的城市峡谷扰动。
- 叠加动态无人机轨迹和电量曲线。
- 增加任务配置页，支持选择城市、日期、起终点和航点。
- 后续用 3D Tiles 替代大规模 GeoJSON，提升浏览器性能。
- 引入地形/影像底图和真实 3D Tiles 城市模型，提高视觉精度。
