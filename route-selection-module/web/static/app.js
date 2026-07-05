// 路径选择三维工作台前端：负责加载城市三维资产、调用规划接口，并在 Cesium 场景中展示建筑、天气和候选路线。
function $(id) {
  return document.getElementById(id);
}

const mapWrap = $("map-wrap");

const viewer = new Cesium.Viewer("cesiumContainer", {
  animation: false,
  timeline: false,
  baseLayerPicker: false,
  geocoder: false,
  homeButton: false,
  sceneModePicker: false,
  navigationHelpButton: false,
  selectionIndicator: false,
  infoBox: false,
  fullscreenButton: true,
  fullscreenElement: mapWrap || document.body,
  baseLayer: false,
  terrainProvider: new Cesium.EllipsoidTerrainProvider(),
  orderIndependentTranslucency: false,
});

viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString("#eef2ec");
viewer.scene.backgroundColor = Cesium.Color.fromCssColorString("#eef2ec");
viewer.scene.skyAtmosphere.show = false;
viewer.scene.fog.enabled = false;
viewer.scene.postProcessStages.fxaa.enabled = true;
viewer.scene.requestRenderMode = false;
viewer.cesiumWidget.creditContainer.style.display = "none";

const PLANNING_MODE = document.body.dataset.planningMode || "combined";
const MODE_CONFIG = {
  combined: {
    title: "建筑 + 天气综合路径规划",
    eyebrow: "Combined Routing",
    description: "同时考虑城市建筑分布与天气采样场，生成综合约束下的候选航线。",
    notes: [
      "优先加载本地 3D Tiles，加载失败时回退为建筑 GeoJSON 挤出模型。",
      "天气点颜色越偏橙红，代表湍流越强。",
      "默认提供五类候选路线：最快到达、低风险、能耗最少、均衡稳定推荐、最畅通路线。",
      "候选路线按综合评分从高到低排序，默认优先选中第 1 条。",
      "Cesium 默认支持缩放、倾斜、平移和绕楼旋转。",
    ],
    showBuildings: true,
    showWeather: true,
  },
  weather_only: {
    title: "仅天气路径规划",
    eyebrow: "Weather Routing",
    description: "路径规划只考虑天气因素，完全忽略建筑信息，允许路线直接穿越建筑投影区域。",
    notes: [
      "页面只展示天气采样和候选路线，不展示建筑模型。",
      "路径规划仅受风场、湍流、降水和气压异常影响。",
      "默认提供五类候选路线：最快到达、低风险、能耗最少、均衡稳定推荐、最畅通路线。",
      "候选路线按综合评分从高到低排序，默认优先选中第 1 条。",
      "Cesium 默认支持缩放、倾斜、平移和绕场景旋转。",
    ],
    showBuildings: false,
    showWeather: true,
  },
  building_only: {
    title: "仅建筑避障路径规划",
    eyebrow: "Building Routing",
    description: "路径规划只考虑建筑避障与净空约束，不考虑任何天气影响。",
    notes: [
      "页面只展示建筑模型和候选路线，不展示天气采样。",
      "路径规划仅受建筑碰撞、净空、飞越暴露和走廊复用影响。",
      "默认提供五类候选路线：最快到达、低风险、能耗最少、均衡稳定推荐、最畅通路线。",
      "候选路线按综合评分从高到低排序，默认优先选中第 1 条。",
      "Cesium 默认支持缩放、倾斜、平移和绕楼旋转。",
    ],
    showBuildings: true,
    showWeather: false,
  },
};
const pageConfig = MODE_CONFIG[PLANNING_MODE] || MODE_CONFIG.combined;

const state = {
  cities: [],
  cityName: "",
  citySummary: null,
  cityConfig: null,
  assetUrls: null,
  buildings: null,
  weather: null,
  weatherFieldIndex: null,
  routes: [],
  selectedRouteId: null,
  pickMode: null,
  buildingSource: null,
  tileset: null,
  groundTileset: null,
  outlineTileset: null,
  weatherPrimitives: null,
  routeEntities: [],
  routeParticleSystems: [],
  markerEntities: [],
  worldCenter: null,
  worldBounds: null,
  weatherAnimations: [],
  weatherAnimationBound: false,
  rainParticleImages: {},
  toggles: {
    buildings: pageConfig.showBuildings,
    weather: pageConfig.showWeather,
    routes: true,
  },
};

const ROUTE_COLORS = ["#00d0a1", "#f0893e", "#2b7bb8", "#d14d72", "#5b8f2a"];
const ROUTE_STRATEGY_TEXT = {
  fastest: "时效优先",
  safest: "安全优先",
  energy_saving: "能耗优先",
  balanced_stable: "综合稳健",
  most_accessible: "通行优先",
  balanced: "均衡推荐",
  low_altitude: "低空绕障",
  training: "训练穿行",
};
const ROUTE_SEGMENT_STEP_M = 160;
const RAIN_LIGHT_THRESHOLD_MM = 0.35;
const RAIN_HEAVY_THRESHOLD_MM = 1.2;
const RAIN_PARTICLE_SPACING_M = 130;
const MAX_RAIN_SPANS_PER_ROUTE = 6;
const MAX_RAIN_PARTICLE_EMITTERS_PER_SPAN = 3;
const STRONG_WIND_THRESHOLD_MPS = 8.5;
const HIGH_CLOUD_THRESHOLD_PCT = 62;
const PRESSURE_ANOMALY_THRESHOLD_HPA = 4.5;
const MAX_WEATHER_SPANS_PER_LAYER = 5;

function setStatus(text, type = "neutral") {
  const node = $("load-status");
  node.textContent = text;
  node.className = `status-tag ${type}`;
}

function formatNumber(value, digits = 2) {
  return Number(value).toFixed(digits);
}

function optionalNumber(id) {
  const raw = $(id).value;
  if (raw === "" || raw == null) {
    return null;
  }
  return Number(raw);
}

function routeById(routeId) {
  return state.routes.find((item) => item.route_id === routeId) || null;
}

function resolveSelectedRouteId(routes, preferredRouteId = state.selectedRouteId) {
  if (preferredRouteId && routes.some((route) => route.route_id === preferredRouteId)) {
    return preferredRouteId;
  }
  return routes[0]?.route_id || null;
}

function setRoutes(routes, preferredRouteId = state.selectedRouteId) {
  state.routes = Array.isArray(routes) ? routes : [];
  state.selectedRouteId = resolveSelectedRouteId(state.routes, preferredRouteId);
}

function selectRoute(routeId, { fly = false } = {}) {
  const nextRouteId = resolveSelectedRouteId(state.routes, routeId);
  if (!nextRouteId) {
    state.selectedRouteId = null;
    renderRouteList();
    renderRouteEntities();
    return;
  }
  const changed = nextRouteId !== state.selectedRouteId;
  state.selectedRouteId = nextRouteId;
  if (changed) {
    renderRouteList();
    renderRouteEntities();
  }
  if (fly) {
    flyRoute();
  }
}

function currentDefaultRoute() {
  return state.cityConfig?.default_route || [];
}

function currentCenter() {
  return state.citySummary?.center || state.cityConfig?.center || null;
}

function currentBbox() {
  return state.citySummary?.bbox || state.cityConfig?.bbox || null;
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok || data?.error) {
    throw new Error(data?.error || `请求失败：${response.status}`);
  }
  return data;
}

function detailMetric(label, value) {
  return `<div><span>${label}</span><strong>${value}</strong></div>`;
}

function hideElement(node, hidden) {
  if (!node) return;
  node.style.display = hidden ? "none" : "";
}

function applyPlanningModeUi() {
  document.title = pageConfig.title;
  $("brand-eyebrow").textContent = pageConfig.eyebrow;
  $("brand-title").textContent = pageConfig.title;
  $("brand-description").textContent = pageConfig.description;
  if ($("toggle-buildings")) $("toggle-buildings").checked = pageConfig.showBuildings;
  if ($("toggle-weather")) $("toggle-weather").checked = pageConfig.showWeather;
  const notesList = $("notes-list");
  notesList.innerHTML = pageConfig.notes.map((item) => `<li>${item}</li>`).join("");
  hideElement($("toggle-buildings")?.closest("label"), !pageConfig.showBuildings);
  hideElement($("toggle-weather")?.closest("label"), !pageConfig.showWeather);
  hideElement($("stat-buildings")?.parentElement, !pageConfig.showBuildings);
  hideElement($("stat-weather")?.parentElement, !pageConfig.showWeather);
}

function routeListExtraMetric(route) {
  if (pageConfig.showWeather) {
    return detailMetric("风速峰值", `${formatNumber(route.max_wind_speed_mps, 2)} m/s`);
  }
  if (pageConfig.showBuildings) {
    return detailMetric("飞越建筑", `${route.overflight_building_count}`);
  }
  return "";
}

function routeStrategyText(route) {
  return ROUTE_STRATEGY_TEXT[route?.strategy] || route?.strategy || "";
}

function setRouteDetail(route) {
  const node = $("route-detail");
  if (!route) {
    node.className = "detail-card empty";
    node.textContent = "选择一条候选路线后显示详细指标。";
    return;
  }
  const metrics = [
    detailMetric("距离", `${formatNumber(route.distance_m / 1000, 2)} km`),
    detailMetric("预计耗时", `${formatNumber(route.estimated_duration_s / 60, 1)} min`),
    detailMetric("TOPSIS", formatNumber(route.topsis_score, 2)),
    detailMetric("鲁棒性", formatNumber(route.robustness_score, 2)),
    detailMetric("可靠率", `${formatNumber((route.reliability_ratio || 0) * 100, 1)}%`),
  ];
  if (pageConfig.showWeather) {
    metrics.push(detailMetric("最大风速", `${formatNumber(route.max_wind_speed_mps, 2)} m/s`));
    metrics.push(detailMetric("最大逆风", `${formatNumber(route.max_headwind_mps, 2)} m/s`));
    metrics.push(detailMetric("最大侧风", `${formatNumber(route.max_crosswind_mps, 2)} m/s`));
    metrics.push(detailMetric("最大湍流", formatNumber(route.max_turbulence_index, 3)));
  }
  metrics.push(detailMetric("连通性", formatNumber(route.average_connectivity_index, 3)));
  metrics.push(detailMetric("可达性", formatNumber(route.average_reachability_index, 3)));
  metrics.push(detailMetric("P95耗时", `${formatNumber(route.duration_p95_s / 60, 1)} min`));
  metrics.push(detailMetric("走廊多样性", formatNumber(route.corridor_diversity_index, 3)));
  if (pageConfig.showBuildings) {
    metrics.push(detailMetric("城市密度", formatNumber(route.average_urban_density, 3)));
    metrics.push(detailMetric("飞越建筑", `${route.overflight_building_count}`));
    metrics.push(detailMetric("飞越暴露", formatNumber(route.overflight_exposure_index, 3)));
  }
  metrics.push(detailMetric("航点数量", `${route.waypoint_count}`));
  node.className = "detail-card";
  node.innerHTML = `
    <div class="route-card-head">
      <div>
        <strong>${route.label}</strong>
        <div class="small">${routeStrategyText(route)}｜第 ${route.recommended_rank} 推荐</div>
      </div>
      <span class="route-rank">综合评分 ${formatNumber(route.score, 2)}</span>
    </div>
    <div class="detail-grid">
      ${metrics.join("")}
    </div>
  `;
}

function renderRouteList() {
  const container = $("route-list");
  if (!state.routes.length) {
    container.className = "route-list empty";
    container.textContent = "尚未生成候选路线。";
    setRouteDetail(null);
    return;
  }
  state.selectedRouteId = resolveSelectedRouteId(state.routes, state.selectedRouteId);
  container.className = "route-list";
  container.innerHTML = "";
  state.routes.forEach((route) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = `route-card${route.route_id === state.selectedRouteId ? " active" : ""}`;
    item.innerHTML = `
      <div class="route-card-head">
        <div>
          <strong>${route.label}</strong>
          <div class="small">${routeStrategyText(route)}</div>
        </div>
        <span class="route-rank">#${route.recommended_rank}</span>
      </div>
      <div class="route-meta">
        <div><span>距离</span><strong>${formatNumber(route.distance_m / 1000, 2)} km</strong></div>
        <div><span>耗时</span><strong>${formatNumber(route.estimated_duration_s / 60, 1)} min</strong></div>
        <div><span>综合评分</span><strong>${formatNumber(route.score, 2)}</strong></div>
        <div><span>TOPSIS</span><strong>${formatNumber(route.topsis_score, 2)}</strong></div>
        <div><span>鲁棒性</span><strong>${formatNumber(route.robustness_score, 2)}</strong></div>
        ${routeListExtraMetric(route)}
      </div>
    `;
    item.addEventListener("click", () => {
      selectRoute(route.route_id, { fly: true });
    });
    container.appendChild(item);
  });
  setRouteDetail(routeById(state.selectedRouteId));
}

function updatePickHint() {
  const text = state.pickMode === "start" ? "点选模式：正在设置起点" : state.pickMode === "end" ? "点选模式：正在设置终点" : "点选模式：关闭";
  $("map-hint").textContent = text;
  $("interaction-tip").textContent = state.pickMode
    ? "在 3D 视图中左键点击地面或楼顶投影可写入坐标；再次点击按钮可取消。"
    : "Cesium 原生支持缩放、倾斜和平移；点选模式打开时，左键点击 3D 视图即可写入坐标。";
}

function updateSummary() {
  if (!state.citySummary) {
    $("summary-name").textContent = "未加载";
    $("stat-buildings").textContent = "--";
    $("stat-weather").textContent = "--";
    $("stat-lat-range").textContent = "--";
    $("stat-lon-range").textContent = "--";
    $("city-title").textContent = "等待城市加载";
    return;
  }
  const bbox = currentBbox();
  $("summary-name").textContent = state.citySummary.display_name || state.citySummary.name;
  $("city-title").textContent = `${state.citySummary.display_name || state.citySummary.name}｜三维候选航线`;
  $("stat-buildings").textContent = String(state.citySummary.building_count || state.buildings?.features?.length || 0);
  $("stat-weather").textContent = String(state.citySummary.weather_sample_count || state.weather?.features?.length || 0);
  $("stat-lat-range").textContent = bbox ? `${Number(bbox.south).toFixed(3)} - ${Number(bbox.north).toFixed(3)}` : "--";
  $("stat-lon-range").textContent = bbox ? `${Number(bbox.west).toFixed(3)} - ${Number(bbox.east).toFixed(3)}` : "--";
}

function updateCameraReadout() {
  const cartographic = viewer.camera.positionCartographic;
  if (!cartographic) {
    $("camera-readout").textContent = "等待相机初始化";
    return;
  }
  $("camera-readout").textContent = [
    `经度 ${Cesium.Math.toDegrees(cartographic.longitude).toFixed(4)}`,
    `纬度 ${Cesium.Math.toDegrees(cartographic.latitude).toFixed(4)}`,
    `高度 ${Math.max(0, cartographic.height).toFixed(0)}m`,
    `航向 ${Cesium.Math.toDegrees(viewer.camera.heading).toFixed(0)}°`,
    `俯仰 ${Cesium.Math.toDegrees(viewer.camera.pitch).toFixed(0)}°`,
  ].join("｜");
}

function setFormFromDefaultRoute() {
  const route = currentDefaultRoute();
  if (!route.length) return;
  const start = route[0];
  const end = route[route.length - 1];
  $("start-lat").value = start.lat;
  $("start-lon").value = start.lon;
  $("end-lat").value = end.lat;
  $("end-lon").value = end.lon;
  $("start-altitude").value = start.altitude_m || 120;
  $("end-altitude").value = end.altitude_m || 120;
  updateMarkers();
}

function buildingColor(height) {
  if (height >= 180) return Cesium.Color.fromCssColorString("#7a3f15").withAlpha(0.92);
  if (height >= 140) return Cesium.Color.fromCssColorString("#a85d25").withAlpha(0.88);
  if (height >= 100) return Cesium.Color.fromCssColorString("#c97a2e").withAlpha(0.84);
  if (height >= 70) return Cesium.Color.fromCssColorString("#d8a15b").withAlpha(0.78);
  if (height >= 40) return Cesium.Color.fromCssColorString("#7d9c8a").withAlpha(0.72);
  return Cesium.Color.fromCssColorString("#a8b6ae").withAlpha(0.68);
}

function weatherColor(turbulence) {
  if (turbulence >= 0.4) return Cesium.Color.fromCssColorString("#c04e25");
  if (turbulence >= 0.28) return Cesium.Color.fromCssColorString("#e39d44");
  return Cesium.Color.fromCssColorString("#4d9dc1");
}

function defaultWeatherSample() {
  return {
    wind_speed_mps: 0,
    turbulence_index: 0,
    precipitation_mm: 0,
    pressure_hpa: 1013.25,
    pressure_anomaly_hpa: 0,
    pressure_delta_hpa: 0,
    cloud_cover_pct: 0,
    temperature_c: 0,
  };
}

function percentile(values, ratio) {
  if (!values.length) return 0;
  const ordered = [...values].sort((a, b) => a - b);
  const position = Math.max(0, Math.min(1, ratio)) * (ordered.length - 1);
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  if (lower === upper) return ordered[lower];
  const weight = position - lower;
  return ordered[lower] * (1 - weight) + ordered[upper] * weight;
}

function createWeatherFieldIndex(weather) {
  if (!weather?.features?.length) return null;
  const grouped = new Map();
  (weather.features || []).forEach((feature) => {
    if (feature.geometry?.type !== "Point") return;
    const coords = feature.geometry.coordinates || [];
    if (coords.length < 2) return;
    const props = feature.properties || {};
    const altitude = Number(props.altitude_m ?? coords[2] ?? 0);
    const sample = {
      lon: Number(coords[0]),
      lat: Number(coords[1]),
      altitude_m: altitude,
      wind_speed_mps: Number(props.wind_speed_mps || 0),
      turbulence_index: Number(props.turbulence_index || 0),
      precipitation_mm: Number(props.precipitation_mm || 0),
      pressure_hpa: Number(props.pressure_hpa || 1013.25),
      cloud_cover_pct: Number(props.cloud_cover_pct ?? props.cloud_cover ?? props.cloud_cover_percent ?? 0),
      temperature_c: Number(props.temperature_c || 0),
    };
    const key = altitude.toFixed(2);
    if (!grouped.has(key)) {
      grouped.set(key, []);
    }
    grouped.get(key).push(sample);
  });
  const altitudeLevels = Array.from(grouped.keys()).map(Number).sort((a, b) => a - b);
  const byAltitude = new Map();
  const referencePressureByAltitude = new Map();
  altitudeLevels.forEach((level) => {
    const samples = grouped.get(level.toFixed(2)) || [];
    byAltitude.set(level, samples);
    referencePressureByAltitude.set(level, percentile(samples.map((sample) => sample.pressure_hpa), 0.5));
  });
  return { altitudeLevels, byAltitude, referencePressureByAltitude };
}

function interpolateWeather2d(samples, lon, lat) {
  if (!samples?.length) return defaultWeatherSample();
  const weighted = samples
    .map((sample) => {
      const distSq = (sample.lon - lon) ** 2 + (sample.lat - lat) ** 2;
      if (distSq < 1e-14) {
        return { weight: Number.POSITIVE_INFINITY, sample };
      }
      return { weight: 1 / distSq, sample };
    })
    .sort((a, b) => b.weight - a.weight)
    .slice(0, 4);
  if (weighted[0]?.weight === Number.POSITIVE_INFINITY) {
    return { ...weighted[0].sample };
  }
  const totalWeight = weighted.reduce((sum, item) => sum + item.weight, 0) || 1;
  return {
    wind_speed_mps: weighted.reduce((sum, item) => sum + item.weight * item.sample.wind_speed_mps, 0) / totalWeight,
    turbulence_index: weighted.reduce((sum, item) => sum + item.weight * item.sample.turbulence_index, 0) / totalWeight,
    precipitation_mm: weighted.reduce((sum, item) => sum + item.weight * item.sample.precipitation_mm, 0) / totalWeight,
    pressure_hpa: weighted.reduce((sum, item) => sum + item.weight * item.sample.pressure_hpa, 0) / totalWeight,
    cloud_cover_pct: weighted.reduce((sum, item) => sum + item.weight * item.sample.cloud_cover_pct, 0) / totalWeight,
    temperature_c: weighted.reduce((sum, item) => sum + item.weight * item.sample.temperature_c, 0) / totalWeight,
  };
}

function referencePressureAtAltitude(altitude) {
  if (!state.weatherFieldIndex?.altitudeLevels?.length) return 1013.25;
  const levels = state.weatherFieldIndex.altitudeLevels;
  let lower = levels[0];
  let upper = levels[levels.length - 1];
  for (const level of levels) {
    if (level <= altitude) lower = level;
    if (level >= altitude) {
      upper = level;
      break;
    }
  }
  const lowerPressure = state.weatherFieldIndex.referencePressureByAltitude.get(lower) || 1013.25;
  const upperPressure = state.weatherFieldIndex.referencePressureByAltitude.get(upper) || lowerPressure;
  if (Math.abs(upper - lower) < 1e-6) return lowerPressure;
  const ratio = (altitude - lower) / (upper - lower);
  return lowerPressure * (1 - ratio) + upperPressure * ratio;
}

function estimatedCloudCover(weather) {
  if (weather.cloud_cover_pct > 0) return weather.cloud_cover_pct;
  const precipitationTerm = Math.min(100, Number(weather.precipitation_mm || 0) * 30);
  const turbulenceTerm = Math.min(100, Number(weather.turbulence_index || 0) * 120);
  const pressureTerm = Math.min(100, Number(weather.pressure_anomaly_hpa || 0) * 8);
  return Math.max(0, Math.min(100, precipitationTerm * 0.45 + turbulenceTerm * 0.30 + pressureTerm * 0.25));
}

function interpolateWeatherAtPoint(lon, lat, altitude) {
  if (!state.weatherFieldIndex?.altitudeLevels?.length) {
    return defaultWeatherSample();
  }
  const levels = state.weatherFieldIndex.altitudeLevels;
  let lower = levels[0];
  let upper = levels[levels.length - 1];
  for (const level of levels) {
    if (level <= altitude) lower = level;
    if (level >= altitude) {
      upper = level;
      break;
    }
  }
  const lowerState = interpolateWeather2d(state.weatherFieldIndex.byAltitude.get(lower), lon, lat);
  const upperState = interpolateWeather2d(state.weatherFieldIndex.byAltitude.get(upper), lon, lat);
  if (Math.abs(upper - lower) < 1e-6) {
    const pressureDelta = lowerState.pressure_hpa - referencePressureAtAltitude(altitude);
    const pressureAnomaly = Math.abs(pressureDelta);
    return { ...lowerState, pressure_delta_hpa: pressureDelta, pressure_anomaly_hpa: pressureAnomaly, cloud_cover_pct: estimatedCloudCover({ ...lowerState, pressure_anomaly_hpa: pressureAnomaly }) };
  }
  const ratio = (altitude - lower) / (upper - lower);
  const stateAtPoint = {
    wind_speed_mps: lowerState.wind_speed_mps * (1 - ratio) + upperState.wind_speed_mps * ratio,
    turbulence_index: lowerState.turbulence_index * (1 - ratio) + upperState.turbulence_index * ratio,
    precipitation_mm: lowerState.precipitation_mm * (1 - ratio) + upperState.precipitation_mm * ratio,
    pressure_hpa: lowerState.pressure_hpa * (1 - ratio) + upperState.pressure_hpa * ratio,
    cloud_cover_pct: lowerState.cloud_cover_pct * (1 - ratio) + upperState.cloud_cover_pct * ratio,
    temperature_c: lowerState.temperature_c * (1 - ratio) + upperState.temperature_c * ratio,
  };
  stateAtPoint.pressure_delta_hpa = stateAtPoint.pressure_hpa - referencePressureAtAltitude(altitude);
  stateAtPoint.pressure_anomaly_hpa = Math.abs(stateAtPoint.pressure_delta_hpa);
  stateAtPoint.cloud_cover_pct = estimatedCloudCover(stateAtPoint);
  return stateAtPoint;
}

function lerpValue(a, b, t) {
  return a + (b - a) * t;
}

function interpolateWaypoint(a, b, t) {
  return {
    lon: lerpValue(Number(a.lon), Number(b.lon), t),
    lat: lerpValue(Number(a.lat), Number(b.lat), t),
    altitude_m: lerpValue(Number(a.altitude_m || 0), Number(b.altitude_m || 0), t),
  };
}

function waypointCartesian(point) {
  return Cesium.Cartesian3.fromDegrees(Number(point.lon), Number(point.lat), Number(point.altitude_m || 0));
}

function classifyWeatherSegment(stats) {
  if (!stats || stats.precipitation_mm < RAIN_LIGHT_THRESHOLD_MM) {
    return "clear";
  }
  if (stats.precipitation_mm >= RAIN_HEAVY_THRESHOLD_MM || (stats.precipitation_mm >= 0.7 && stats.turbulence_index >= 0.36)) {
    return "rain_heavy";
  }
  return "rain_light";
}

function sampleWeatherForSegment(start, end) {
  const sampleCount = 3;
  let maxPrecipitation = 0;
  let maxTurbulence = 0;
  let maxWind = 0;
  let maxCloud = 0;
  let maxPressureAnomaly = 0;
  let pressureSum = 0;
  let pressureDeltaSum = 0;
  for (let idx = 0; idx < sampleCount; idx += 1) {
    const t = (idx + 0.5) / sampleCount;
    const point = interpolateWaypoint(start, end, t);
    const weather = interpolateWeatherAtPoint(point.lon, point.lat, point.altitude_m);
    maxPrecipitation = Math.max(maxPrecipitation, Number(weather.precipitation_mm || 0));
    maxTurbulence = Math.max(maxTurbulence, Number(weather.turbulence_index || 0));
    maxWind = Math.max(maxWind, Number(weather.wind_speed_mps || 0));
    maxCloud = Math.max(maxCloud, Number(weather.cloud_cover_pct || 0));
    maxPressureAnomaly = Math.max(maxPressureAnomaly, Number(weather.pressure_anomaly_hpa || 0));
    pressureSum += Number(weather.pressure_hpa || 1013.25);
    pressureDeltaSum += Number(weather.pressure_delta_hpa || 0);
  }
  return {
    precipitation_mm: maxPrecipitation,
    turbulence_index: maxTurbulence,
    wind_speed_mps: maxWind,
    cloud_cover_pct: maxCloud,
    pressure_anomaly_hpa: maxPressureAnomaly,
    pressure_hpa: pressureSum / sampleCount,
    pressure_delta_hpa: pressureDeltaSum / sampleCount,
  };
}

function buildRouteWeatherSegments(route) {
  const waypoints = route?.waypoints || [];
  if (waypoints.length < 2) return [];
  const segments = [];
  for (let index = 1; index < waypoints.length; index += 1) {
    const start = waypoints[index - 1];
    const end = waypoints[index];
    const distanceM = Cesium.Cartesian3.distance(waypointCartesian(start), waypointCartesian(end));
    const sliceCount = Math.max(1, Math.ceil(distanceM / ROUTE_SEGMENT_STEP_M));
    for (let sliceIndex = 0; sliceIndex < sliceCount; sliceIndex += 1) {
      const t0 = sliceIndex / sliceCount;
      const t1 = (sliceIndex + 1) / sliceCount;
      const pieceStart = interpolateWaypoint(start, end, t0);
      const pieceEnd = interpolateWaypoint(start, end, t1);
      const weather = sampleWeatherForSegment(pieceStart, pieceEnd);
      segments.push({
        start: pieceStart,
        end: pieceEnd,
        weather,
        category: classifyWeatherSegment(weather),
      });
    }
  }
  return segments;
}

function mergeWeatherSpans(segments) {
  const spans = [];
  segments.forEach((segment, segmentIndex) => {
    if (!segment.category.startsWith("rain")) return;
    const previous = spans[spans.length - 1];
    if (previous && previous.category === segment.category && previous.lastSegmentIndex === segmentIndex - 1) {
      previous.end = segment.end;
      previous.lastSegmentIndex = segmentIndex;
      previous.maxPrecipitation = Math.max(previous.maxPrecipitation, segment.weather.precipitation_mm);
      previous.maxTurbulence = Math.max(previous.maxTurbulence, segment.weather.turbulence_index);
      return;
    }
    spans.push({
      category: segment.category,
      start: segment.start,
      end: segment.end,
      maxPrecipitation: segment.weather.precipitation_mm,
      maxTurbulence: segment.weather.turbulence_index,
      maxWind: segment.weather.wind_speed_mps,
      maxCloud: segment.weather.cloud_cover_pct,
      maxPressureAnomaly: segment.weather.pressure_anomaly_hpa,
      pressureHpa: segment.weather.pressure_hpa,
      pressureDeltaHpa: segment.weather.pressure_delta_hpa,
      lastSegmentIndex: segmentIndex,
    });
  });
  return spans;
}

function mergeConditionSpans(segments, category, predicate) {
  const spans = [];
  segments.forEach((segment, segmentIndex) => {
    if (!predicate(segment.weather)) return;
    const previous = spans[spans.length - 1];
    if (previous && previous.lastSegmentIndex === segmentIndex - 1) {
      previous.end = segment.end;
      previous.lastSegmentIndex = segmentIndex;
      previous.maxPrecipitation = Math.max(previous.maxPrecipitation, segment.weather.precipitation_mm);
      previous.maxTurbulence = Math.max(previous.maxTurbulence, segment.weather.turbulence_index);
      previous.maxWind = Math.max(previous.maxWind, segment.weather.wind_speed_mps);
      previous.maxCloud = Math.max(previous.maxCloud, segment.weather.cloud_cover_pct);
      previous.maxPressureAnomaly = Math.max(previous.maxPressureAnomaly, segment.weather.pressure_anomaly_hpa);
      previous.pressureHpa = (previous.pressureHpa + segment.weather.pressure_hpa) / 2;
      previous.pressureDeltaHpa = (previous.pressureDeltaHpa + segment.weather.pressure_delta_hpa) / 2;
      return;
    }
    spans.push({
      category,
      start: segment.start,
      end: segment.end,
      maxPrecipitation: segment.weather.precipitation_mm,
      maxTurbulence: segment.weather.turbulence_index,
      maxWind: segment.weather.wind_speed_mps,
      maxCloud: segment.weather.cloud_cover_pct,
      maxPressureAnomaly: segment.weather.pressure_anomaly_hpa,
      pressureHpa: segment.weather.pressure_hpa,
      pressureDeltaHpa: segment.weather.pressure_delta_hpa,
      lastSegmentIndex: segmentIndex,
    });
  });
  return spans;
}

function buildRouteWeatherLayers(segments) {
  return {
    rain: mergeWeatherSpans(segments).slice(0, MAX_WEATHER_SPANS_PER_LAYER),
    wind: mergeConditionSpans(segments, "strong_wind", (weather) => weather.wind_speed_mps >= STRONG_WIND_THRESHOLD_MPS).slice(0, MAX_WEATHER_SPANS_PER_LAYER),
    pressure: mergeConditionSpans(segments, "pressure", (weather) => weather.pressure_anomaly_hpa >= PRESSURE_ANOMALY_THRESHOLD_HPA).slice(0, MAX_WEATHER_SPANS_PER_LAYER),
    cloud: mergeConditionSpans(segments, "cloud", (weather) => weather.cloud_cover_pct >= HIGH_CLOUD_THRESHOLD_PCT).slice(0, MAX_WEATHER_SPANS_PER_LAYER),
  };
}

function animatedBlueColor(baseAlpha, offset = 0) {
  return new Cesium.CallbackProperty(() => {
    const pulse = 0.72 + 0.28 * Math.sin(performance.now() * 0.008 + offset);
    return Cesium.Color.fromCssColorString("#2f8bff").withAlpha(baseAlpha * pulse);
  }, false);
}

function animatedBandColor(fromColorCss, toColorCss, alpha, offset = 0) {
  return new Cesium.CallbackProperty(() => {
    const t = 0.5 + 0.5 * Math.sin(performance.now() * 0.01 + offset);
    const from = Cesium.Color.fromCssColorString(fromColorCss);
    const to = Cesium.Color.fromCssColorString(toColorCss);
    const mixed = Cesium.Color.lerp(from, to, t, new Cesium.Color());
    return mixed.withAlpha(alpha);
  }, false);
}

function rainBackdropMaterial(category, selected, offset = 0) {
  const baseAlpha = category === "rain_heavy" ? (selected ? 0.88 : 0.76) : (selected ? 0.78 : 0.64);
  return new Cesium.PolylineGlowMaterialProperty({
    glowPower: category === "rain_heavy" ? 0.42 : 0.34,
    color: new Cesium.CallbackProperty(() => {
      const pulse = 0.70 + 0.30 * Math.sin(performance.now() * 0.008 + offset);
      return Cesium.Color.fromCssColorString(category === "rain_heavy" ? "#0a56ff" : "#126fff").withAlpha(baseAlpha * pulse);
    }, false),
  });
}

function rainCorridorMaterial(category, selected, offset = 0) {
  const alpha = category === "rain_heavy" ? (selected ? 0.72 : 0.64) : (selected ? 0.62 : 0.54);
  return new Cesium.ColorMaterialProperty(
    animatedBandColor(
      category === "rain_heavy" ? "#1a76ff" : "#2994ff",
      category === "rain_heavy" ? "#58b8ff" : "#7cd2ff",
      alpha,
      offset
    )
  );
}

function rainCoreMaterial(category, selected, offset = 0) {
  const alpha = category === "rain_heavy" ? (selected ? 0.95 : 0.88) : (selected ? 0.88 : 0.8);
  return new Cesium.ColorMaterialProperty(
    animatedBandColor(
      category === "rain_heavy" ? "#eef9ff" : "#d7f4ff",
      category === "rain_heavy" ? "#79cbff" : "#93ddff",
      alpha,
      offset
    )
  );
}

function rainEdgeMaterial(category, selected, offset = 0) {
  return new Cesium.PolylineGlowMaterialProperty({
    glowPower: category === "rain_heavy" ? 0.28 : 0.22,
    color: animatedBandColor(
      category === "rain_heavy" ? "#dff6ff" : "#c9efff",
      category === "rain_heavy" ? "#46b0ff" : "#69cfff",
      selected ? 0.98 : 0.9,
      offset
    ),
  });
}

function rainGlowMaterial(category, selected, offset = 0) {
  const baseAlpha = category === "rain_heavy" ? (selected ? 1.0 : 0.9) : (selected ? 0.92 : 0.8);
  return new Cesium.PolylineGlowMaterialProperty({
    glowPower: category === "rain_heavy" ? 0.46 : 0.34,
    color: animatedBlueColor(baseAlpha, offset),
  });
}

function drawRoundedRect(ctx, x, y, width, height, radius) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
}

function createRainAnimation(category) {
  const canvas = document.createElement("canvas");
  canvas.width = 84;
  canvas.height = 84;
  const ctx = canvas.getContext("2d");
  const dropCount = category === "rain_heavy" ? 7 : 4;
  const speed = category === "rain_heavy" ? 0.18 : 0.12;
  return {
    category,
    canvas,
    draw(now) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      drawRoundedRect(ctx, 8, 10, 68, 58, 16);
      ctx.fillStyle = "rgba(7, 18, 34, 0.72)";
      ctx.fill();
      ctx.strokeStyle = category === "rain_heavy" ? "rgba(98, 175, 255, 0.85)" : "rgba(126, 210, 255, 0.82)";
      ctx.lineWidth = 1.4;
      ctx.stroke();

      ctx.fillStyle = "rgba(236, 245, 255, 0.96)";
      ctx.beginPath();
      ctx.arc(32, 30, 10, Math.PI * 0.9, Math.PI * 2.1);
      ctx.arc(42, 24, 11, Math.PI, Math.PI * 2);
      ctx.arc(54, 30, 9, Math.PI * 1.05, Math.PI * 1.95);
      ctx.closePath();
      ctx.fill();

      ctx.lineCap = "round";
      ctx.lineWidth = category === "rain_heavy" ? 3 : 2.2;
      for (let idx = 0; idx < dropCount; idx += 1) {
        const laneX = 22 + idx * (category === "rain_heavy" ? 6 : 10);
        const phase = (now * speed + idx * 11) % 54;
        const y = 30 + phase;
        const dropLength = category === "rain_heavy" ? 10 : 8;
        ctx.strokeStyle = category === "rain_heavy" ? "rgba(86, 167, 255, 0.94)" : "rgba(117, 211, 255, 0.88)";
        ctx.beginPath();
        ctx.moveTo(laneX, y - dropLength);
        ctx.lineTo(laneX - 2, y);
        ctx.stroke();
      }

      if (category === "rain_heavy") {
        ctx.fillStyle = "rgba(152, 219, 255, 0.26)";
        ctx.beginPath();
        ctx.ellipse(42, 60, 20, 6, 0, 0, Math.PI * 2);
        ctx.fill();
      }
    },
  };
}

function ensureWeatherAnimationsTicking() {
  if (state.weatherAnimationBound) return;
  viewer.clock.onTick.addEventListener(() => {
    if (!state.weatherAnimations.length) return;
    const now = performance.now();
    state.weatherAnimations.forEach((animation) => animation.draw(now));
  });
  state.weatherAnimationBound = true;
}

function getRainAnimation(category) {
  let animation = state.weatherAnimations.find((item) => item.category === category);
  if (!animation) {
    animation = createRainAnimation(category);
    state.weatherAnimations.push(animation);
  }
  ensureWeatherAnimationsTicking();
  return animation;
}

function createWindArrowImage() {
  const canvas = document.createElement("canvas");
  canvas.width = 96;
  canvas.height = 36;
  const ctx = canvas.getContext("2d");
  const gradient = ctx.createLinearGradient(0, 0, canvas.width, 0);
  gradient.addColorStop(0, "rgba(185, 246, 255, 0.0)");
  gradient.addColorStop(0.25, "rgba(185, 246, 255, 0.86)");
  gradient.addColorStop(1, "rgba(255, 255, 255, 1.0)");
  ctx.strokeStyle = gradient;
  ctx.fillStyle = "rgba(255, 255, 255, 0.98)";
  ctx.lineWidth = 5;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(10, 18);
  ctx.lineTo(70, 18);
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(70, 7);
  ctx.lineTo(91, 18);
  ctx.lineTo(70, 29);
  ctx.closePath();
  ctx.fill();
  return canvas;
}

function getWindArrowImage() {
  if (!state.rainParticleImages.windArrow) {
    state.rainParticleImages.windArrow = createWindArrowImage();
  }
  return state.rainParticleImages.windArrow;
}

function createCloudAnimation() {
  const canvas = document.createElement("canvas");
  canvas.width = 156;
  canvas.height = 108;
  const ctx = canvas.getContext("2d");
  function traceCloud(dx = 0, dy = 0) {
    ctx.beginPath();
    ctx.moveTo(24 + dx, 62 + dy);
    ctx.bezierCurveTo(15 + dx, 58 + dy, 13 + dx, 45 + dy, 25 + dx, 39 + dy);
    ctx.bezierCurveTo(26 + dx, 24 + dy, 39 + dx, 15 + dy, 56 + dx, 19 + dy);
    ctx.bezierCurveTo(64 + dx, 10 + dy, 82 + dx, 9 + dy, 94 + dx, 20 + dy);
    ctx.bezierCurveTo(111 + dx, 16 + dy, 127 + dx, 25 + dy, 131 + dx, 40 + dy);
    ctx.bezierCurveTo(143 + dx, 42 + dy, 149 + dx, 50 + dy, 146 + dx, 61 + dy);
    ctx.bezierCurveTo(147 + dx, 72 + dy, 140 + dx, 80 + dy, 126 + dx, 82 + dy);
    ctx.bezierCurveTo(117 + dx, 91 + dy, 103 + dx, 95 + dy, 89 + dx, 89 + dy);
    ctx.bezierCurveTo(79 + dx, 95 + dy, 62 + dx, 96 + dy, 49 + dx, 90 + dy);
    ctx.bezierCurveTo(36 + dx, 94 + dy, 24 + dx, 88 + dy, 19 + dx, 78 + dy);
    ctx.bezierCurveTo(10 + dx, 75 + dy, 10 + dx, 64 + dy, 24 + dx, 62 + dy);
    ctx.closePath();
  }

  function drawSpark(x, y, size, opacity) {
    ctx.save();
    ctx.strokeStyle = `rgba(213, 204, 170, ${opacity})`;
    ctx.lineWidth = 1.2;
    ctx.lineCap = "round";
    ctx.beginPath();
    ctx.moveTo(x - size, y);
    ctx.lineTo(x + size, y);
    ctx.moveTo(x, y - size);
    ctx.lineTo(x, y + size);
    ctx.stroke();
    ctx.restore();
  }
  return {
    category: "cloud",
    canvas,
    draw(now) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const drift = Math.sin(now * 0.0012) * 2.6;
      const bob = Math.sin(now * 0.0016 + 0.8) * 1.4;
      const alpha = 0.9 + 0.05 * Math.sin(now * 0.0022);

      ctx.save();
      ctx.translate(drift, bob);

      ctx.strokeStyle = `rgba(221, 216, 203, ${0.34 * alpha})`;
      ctx.lineWidth = 1.3;
      ctx.beginPath();
      ctx.arc(79, 57, 47, Math.PI * 0.26, Math.PI * 1.84);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(79, 57, 57, Math.PI * 0.45, Math.PI * 1.66);
      ctx.stroke();

      ctx.fillStyle = `rgba(176, 196, 213, ${0.14 * alpha})`;
      ctx.beginPath();
      ctx.ellipse(79, 86, 44, 10, 0, 0, Math.PI * 2);
      ctx.fill();

      traceCloud();
      ctx.save();
      ctx.clip();

      const base = ctx.createLinearGradient(0, 18, 0, 92);
      base.addColorStop(0, `rgba(252, 251, 246, ${0.98 * alpha})`);
      base.addColorStop(0.52, `rgba(240, 245, 247, ${0.94 * alpha})`);
      base.addColorStop(1, `rgba(191, 220, 238, ${0.94 * alpha})`);
      ctx.fillStyle = base;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const glow = ctx.createRadialGradient(78, 47, 8, 78, 49, 54);
      glow.addColorStop(0, `rgba(255, 250, 236, ${0.40 * alpha})`);
      glow.addColorStop(1, "rgba(255, 250, 236, 0)");
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      ctx.fillStyle = `rgba(198, 224, 239, ${0.36 * alpha})`;
      ctx.beginPath();
      ctx.ellipse(54, 68, 21, 14, -0.2, 0, Math.PI * 2);
      ctx.ellipse(101, 70, 25, 16, 0.18, 0, Math.PI * 2);
      ctx.ellipse(79, 79, 34, 12, 0, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = `rgba(228, 241, 248, ${0.42 * alpha})`;
      ctx.beginPath();
      ctx.ellipse(62, 34, 19, 10, -0.18, 0, Math.PI * 2);
      ctx.ellipse(94, 33, 23, 12, 0.14, 0, Math.PI * 2);
      ctx.ellipse(78, 49, 39, 17, 0, 0, Math.PI * 2);
      ctx.fill();

      ctx.restore();

      traceCloud();
      ctx.strokeStyle = `rgba(185, 193, 194, ${0.96 * alpha})`;
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      ctx.lineWidth = 2.6;
      ctx.stroke();

      ctx.strokeStyle = `rgba(244, 247, 246, ${0.82 * alpha})`;
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.moveTo(47, 41);
      ctx.bezierCurveTo(58, 32, 74, 28, 98, 34);
      ctx.stroke();

      ctx.strokeStyle = `rgba(173, 205, 227, ${0.48 * alpha})`;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(46, 72);
      ctx.bezierCurveTo(59, 68, 72, 76, 84, 72);
      ctx.bezierCurveTo(96, 69, 109, 77, 118, 72);
      ctx.stroke();

      drawSpark(30, 22, 3.4, 0.44 * alpha);
      drawSpark(128, 25, 2.8, 0.36 * alpha);
      drawSpark(41, 92, 2.2, 0.28 * alpha);
      ctx.restore();
    },
  };
}

function getCloudAnimation() {
  let animation = state.weatherAnimations.find((item) => item.category === "cloud");
  if (!animation) {
    animation = createCloudAnimation();
    state.weatherAnimations.push(animation);
  }
  ensureWeatherAnimationsTicking();
  return animation;
}

function createRainParticleImage(category) {
  const canvas = document.createElement("canvas");
  canvas.width = 16;
  canvas.height = category === "rain_heavy" ? 96 : 72;
  const ctx = canvas.getContext("2d");
  const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
  gradient.addColorStop(0, "rgba(255,255,255,0.0)");
  gradient.addColorStop(0.18, category === "rain_heavy" ? "rgba(228, 246, 255, 0.85)" : "rgba(217, 242, 255, 0.75)");
  gradient.addColorStop(1, category === "rain_heavy" ? "rgba(84, 179, 255, 1.0)" : "rgba(118, 210, 255, 0.96)");
  ctx.strokeStyle = gradient;
  ctx.lineWidth = category === "rain_heavy" ? 4 : 3;
  ctx.lineCap = "round";
  ctx.beginPath();
  ctx.moveTo(canvas.width / 2 + 1, 4);
  ctx.lineTo(canvas.width / 2 - 2, canvas.height - 6);
  ctx.stroke();
  return canvas;
}

function getRainParticleImage(category) {
  if (!state.rainParticleImages[category]) {
    state.rainParticleImages[category] = createRainParticleImage(category);
  }
  return state.rainParticleImages[category];
}

function addRouteParticleSystem(system, routeId) {
  viewer.scene.primitives.add(system);
  state.routeParticleSystems.push({ system, routeId });
}

function createRainParticleUpdate(directionWorld, category) {
  const scratchUp = new Cesium.Cartesian3();
  const scratchDown = new Cesium.Cartesian3();
  const scratchVelocity = new Cesium.Cartesian3();
  const tangent = Cesium.Cartesian3.normalize(directionWorld, new Cesium.Cartesian3());
  const driftSpeed = category === "rain_heavy" ? 2.4 : 1.5;
  const fallSpeed = category === "rain_heavy" ? 20 : 15;
  return (particle) => {
    const up = Cesium.Ellipsoid.WGS84.geodeticSurfaceNormal(particle.position, scratchUp);
    Cesium.Cartesian3.multiplyByScalar(up, -fallSpeed, scratchDown);
    Cesium.Cartesian3.multiplyByScalar(tangent, driftSpeed, scratchVelocity);
    particle.velocity = Cesium.Cartesian3.add(scratchDown, scratchVelocity, particle.velocity || new Cesium.Cartesian3());
  };
}

function addRainParticleCurtain(span, routeId, routeIndex, spanIndex) {
  const startCartesian = waypointCartesian(span.start);
  const endCartesian = waypointCartesian(span.end);
  const direction = Cesium.Cartesian3.subtract(endCartesian, startCartesian, new Cesium.Cartesian3());
  const spanLength = Cesium.Cartesian3.magnitude(direction);
  if (!Number.isFinite(spanLength) || spanLength <= 1) return;
  const emitterCount = Math.min(MAX_RAIN_PARTICLE_EMITTERS_PER_SPAN, Math.max(1, Math.ceil(spanLength / RAIN_PARTICLE_SPACING_M)));
  const chunkLength = spanLength / emitterCount;
  for (let emitterIndex = 0; emitterIndex < emitterCount; emitterIndex += 1) {
    const t = (emitterIndex + 0.5) / emitterCount;
    const point = interpolateWaypoint(span.start, span.end, t);
    const emitterPosition = Cesium.Cartesian3.fromDegrees(point.lon, point.lat, Number(point.altitude_m || 0) + 18);
    const boxWidth = span.category === "rain_heavy" ? 34 : 26;
    const boxLength = Math.max(28, Math.min(90, chunkLength * 0.78));
    const system = new Cesium.ParticleSystem({
      image: getRainParticleImage(span.category),
      startScale: span.category === "rain_heavy" ? 1.0 : 0.85,
      endScale: span.category === "rain_heavy" ? 0.78 : 0.68,
      minimumParticleLife: span.category === "rain_heavy" ? 0.85 : 0.95,
      maximumParticleLife: span.category === "rain_heavy" ? 1.2 : 1.35,
      minimumSpeed: 0.1,
      maximumSpeed: 0.3,
      emissionRate: span.category === "rain_heavy" ? 120 : 75,
      sizeInMeters: true,
      imageSize: new Cesium.Cartesian2(span.category === "rain_heavy" ? 0.6 : 0.48, span.category === "rain_heavy" ? 7.8 : 6.2),
      startColor: Cesium.Color.WHITE.withAlpha(span.category === "rain_heavy" ? 0.9 : 0.76),
      endColor: Cesium.Color.fromCssColorString(span.category === "rain_heavy" ? "#62bbff" : "#8fdcff").withAlpha(0.06),
      modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(emitterPosition),
      emitter: new Cesium.BoxEmitter(new Cesium.Cartesian3(boxLength, boxWidth, span.category === "rain_heavy" ? 7.5 : 6.0)),
      updateCallback: createRainParticleUpdate(direction, span.category),
    });
    system.show = state.toggles.routes && state.toggles.weather;
    system.__routeId = routeId;
    system.__routeRain = true;
    system.__routeRainSpan = `${routeIndex}-${spanIndex}-${emitterIndex}`;
    addRouteParticleSystem(system, routeId);
  }
}

async function clearScene() {
  state.routeEntities.forEach((entity) => viewer.entities.remove(entity));
  state.routeEntities = [];
  state.routeParticleSystems.forEach(({ system }) => {
    viewer.scene.primitives.remove(system);
  });
  state.routeParticleSystems = [];
  state.markerEntities.forEach((entity) => viewer.entities.remove(entity));
  state.markerEntities = [];
  state.weatherFieldIndex = null;
  if (state.buildingSource) {
    await viewer.dataSources.remove(state.buildingSource, true);
    state.buildingSource = null;
  }
  if (state.weatherPrimitives) {
    viewer.scene.primitives.remove(state.weatherPrimitives);
    state.weatherPrimitives = null;
  }
  if (state.tileset) {
    viewer.scene.primitives.remove(state.tileset);
    state.tileset = null;
  }
  if (state.groundTileset) {
    viewer.scene.primitives.remove(state.groundTileset);
    state.groundTileset = null;
  }
  if (state.outlineTileset) {
    viewer.scene.primitives.remove(state.outlineTileset);
    state.outlineTileset = null;
  }
}

function routeBearingDeg(coords) {
  if (coords.length < 2) return 30.0;
  const start = coords[0];
  const end = coords[coords.length - 1];
  const lat1 = Cesium.Math.toRadians(start[1]);
  const lat2 = Cesium.Math.toRadians(end[1]);
  const dLon = Cesium.Math.toRadians(end[0] - start[0]);
  const y = Math.sin(dLon) * Math.cos(lat2);
  const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLon);
  return (Cesium.Math.toDegrees(Math.atan2(y, x)) + 360.0) % 360.0;
}

function routeFocusFromCoordinates(coords) {
  if (!coords?.length) return null;
  const lons = coords.map((coord) => coord[0]);
  const lats = coords.map((coord) => coord[1]);
  const positions = coords.map((coord) => Cesium.Cartesian3.fromDegrees(coord[0], coord[1], coord[2] ?? 100.0));
  let lengthM = 0;
  for (let idx = 1; idx < positions.length; idx += 1) {
    lengthM += Cesium.Cartesian3.distance(positions[idx - 1], positions[idx]);
  }
  return {
    center: {
      lon: (Math.min(...lons) + Math.max(...lons)) / 2,
      lat: (Math.min(...lats) + Math.max(...lats)) / 2,
    },
    headingDeg: routeBearingDeg(coords),
    lengthM,
  };
}

function setOrbitView(center, headingDeg, pitchDeg, rangeM, duration = 1.2) {
  if (!center) return;
  const target = Cesium.Cartesian3.fromDegrees(center.lon, center.lat, 0);
  const offset = new Cesium.HeadingPitchRange(
    Cesium.Math.toRadians(headingDeg),
    Cesium.Math.toRadians(pitchDeg),
    rangeM
  );
  viewer.camera.flyToBoundingSphere(
    new Cesium.BoundingSphere(target, Math.max(120, rangeM * 0.15)),
    { offset, duration }
  );
}

function bboxDiagonalApproxM(bbox) {
  if (!bbox) return 1600;
  const latScale = 111000;
  const lonScale = latScale * Math.max(0.2, Math.cos(Cesium.Math.toRadians((bbox.south + bbox.north) / 2)));
  const dx = Math.abs(bbox.east - bbox.west) * lonScale;
  const dy = Math.abs(bbox.north - bbox.south) * latScale;
  return Math.hypot(dx, dy);
}

function flyOblique() {
  const center = currentCenter();
  const range = Math.max(900, Math.min(5600, bboxDiagonalApproxM(currentBbox()) * 1.15));
  setOrbitView(center, 32, -36, range, 1.3);
}

function flyTopdown() {
  const center = currentCenter();
  const range = Math.max(1200, Math.min(7200, bboxDiagonalApproxM(currentBbox()) * 1.4));
  setOrbitView(center, 0, -85, range, 1.2);
}

function resetView() {
  flyOblique();
}

function flyRoute() {
  const route = routeById(state.selectedRouteId) || state.routes[0];
  if (!route) return;
  const coords = route.waypoints.map((point) => [point.lon, point.lat, point.altitude_m]);
  const focus = routeFocusFromCoordinates(coords);
  if (!focus) return;
  const range = Math.max(650, Math.min(3600, focus.lengthM * 0.72));
  setOrbitView(focus.center, (focus.headingDeg + 24) % 360, -42, range, 1.2);
}

async function tryLoadTilesets(assetUrls) {
  if (!assetUrls?.tileset) {
    return false;
  }
  try {
    if (assetUrls.ground_tileset) {
      state.groundTileset = await Cesium.Cesium3DTileset.fromUrl(assetUrls.ground_tileset);
      if (Cesium.ShadowMode) {
        state.groundTileset.shadows = Cesium.ShadowMode.DISABLED;
      }
      viewer.scene.primitives.add(state.groundTileset);
    }
    state.tileset = await Cesium.Cesium3DTileset.fromUrl(assetUrls.tileset);
    if (Cesium.ShadowMode) {
      state.tileset.shadows = Cesium.ShadowMode.DISABLED;
    }
    viewer.scene.primitives.add(state.tileset);
    if (assetUrls.outline_tileset) {
      state.outlineTileset = await Cesium.Cesium3DTileset.fromUrl(assetUrls.outline_tileset);
      if (Cesium.ShadowMode) {
        state.outlineTileset.shadows = Cesium.ShadowMode.DISABLED;
      }
      viewer.scene.primitives.add(state.outlineTileset);
    }
    return true;
  } catch (error) {
    console.warn("load tileset failed, fallback to geojson extrusions", error);
    if (state.tileset) {
      viewer.scene.primitives.remove(state.tileset);
      state.tileset = null;
    }
    if (state.groundTileset) {
      viewer.scene.primitives.remove(state.groundTileset);
      state.groundTileset = null;
    }
    if (state.outlineTileset) {
      viewer.scene.primitives.remove(state.outlineTileset);
      state.outlineTileset = null;
    }
    return false;
  }
}

async function loadBuildingGeoJson(buildings) {
  const source = await Cesium.GeoJsonDataSource.load(buildings, { clampToGround: false });
  const time = Cesium.JulianDate.now();
  source.entities.values.forEach((entity) => {
    if (!entity.polygon) return;
    const height = Number(entity.properties?.height_m?.getValue?.(time) || 0);
    entity.polygon.height = 0;
    entity.polygon.extrudedHeight = Math.max(4, height);
    entity.polygon.material = buildingColor(height);
    entity.polygon.outline = true;
    entity.polygon.outlineColor = Cesium.Color.fromCssColorString("#f6fbf7").withAlpha(0.18);
    entity.routeSelectable = false;
  });
  state.buildingSource = source;
  viewer.dataSources.add(source);
}

function loadWeatherPrimitives(weather) {
  const collection = new Cesium.PointPrimitiveCollection();
  (weather.features || []).filter((feature) => feature.geometry?.type === "Point").slice(0, 400).forEach((feature) => {
    const coords = feature.geometry.coordinates;
    const props = feature.properties || {};
    const altitude = Number(coords[2] || props.altitude_m || 0);
    collection.add({
      position: Cesium.Cartesian3.fromDegrees(coords[0], coords[1], altitude),
      pixelSize: altitude >= 150 ? 7 : 5,
      color: weatherColor(Number(props.turbulence_index || 0)).withAlpha(0.84),
      outlineColor: Cesium.Color.WHITE.withAlpha(0.45),
      outlineWidth: 1,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    });
  });
  state.weatherPrimitives = viewer.scene.primitives.add(collection);
}

function updateMarkers() {
  state.markerEntities.forEach((entity) => viewer.entities.remove(entity));
  state.markerEntities = [];
  const markers = [
    {
      label: "起点",
      short: "起",
      lat: Number($("start-lat").value),
      lon: Number($("start-lon").value),
      altitude: Number($("start-altitude").value || 120),
      color: Cesium.Color.fromCssColorString("#0f7b62"),
    },
    {
      label: "终点",
      short: "终",
      lat: Number($("end-lat").value),
      lon: Number($("end-lon").value),
      altitude: Number($("end-altitude").value || 120),
      color: Cesium.Color.fromCssColorString("#b13a35"),
    },
  ];
  markers.forEach((marker) => {
    if (!Number.isFinite(marker.lat) || !Number.isFinite(marker.lon)) return;
    const entity = viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(marker.lon, marker.lat, marker.altitude),
      point: {
        pixelSize: 12,
        color: marker.color,
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 2,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: {
        text: marker.short,
        font: '700 12px "Avenir Next", "PingFang SC", sans-serif',
        fillColor: Cesium.Color.WHITE,
        outlineColor: Cesium.Color.fromCssColorString("#10251f"),
        outlineWidth: 3,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(0, -16),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      properties: {
        kind: marker.label,
        lat: marker.lat,
        lon: marker.lon,
        altitude_m: marker.altitude,
      },
    });
    state.markerEntities.push(entity);
  });
}

function routeMaterial(color, selected) {
  const alpha = pageConfig.showWeather ? (selected ? 0.64 : 0.46) : (selected ? 0.98 : 0.68);
  return new Cesium.PolylineGlowMaterialProperty({
    glowPower: pageConfig.showWeather ? (selected ? 0.14 : 0.06) : (selected ? 0.2 : 0.08),
    color: Cesium.Color.fromCssColorString(color).withAlpha(alpha),
  });
}

function addRouteEntity(entity, routeId, selectable = false) {
  entity.routeId = routeId;
  entity.isRoute = selectable;
  state.routeEntities.push(entity);
}

function renderRainSpan(span, route, routeIndex, spanIndex, selected) {
  const segmentPositions = [
    Cesium.Cartesian3.fromDegrees(span.start.lon, span.start.lat, span.start.altitude_m || 100),
    Cesium.Cartesian3.fromDegrees(span.end.lon, span.end.lat, span.end.altitude_m || 100),
  ];
  const routeId = route.route_id;
  const backdropEntity = viewer.entities.add({
    polyline: {
      positions: segmentPositions,
      width: 28,
      material: rainBackdropMaterial(span.category, selected, routeIndex * 1.1 + spanIndex * 0.35),
      clampToGround: false,
    },
    properties: {
      route_id: routeId,
      weather_category: span.category,
    },
  });
  addRouteEntity(backdropEntity, routeId);
  const corridorEntity = viewer.entities.add({
    polyline: {
      positions: segmentPositions,
      width: 18,
      material: rainCorridorMaterial(span.category, selected, routeIndex * 0.85 + spanIndex * 0.22),
      clampToGround: false,
    },
    properties: {
      route_id: routeId,
      weather_category: span.category,
      precipitation_mm: span.maxPrecipitation,
      turbulence_index: span.maxTurbulence,
    },
  });
  addRouteEntity(corridorEntity, routeId);
  const coreEntity = viewer.entities.add({
    polyline: {
      positions: segmentPositions,
      width: 9,
      material: rainCoreMaterial(span.category, selected, routeIndex * 0.7 + spanIndex * 0.3),
      clampToGround: false,
    },
    properties: {
      route_id: routeId,
      weather_category: span.category,
    },
  });
  addRouteEntity(coreEntity, routeId);
  const glowEntity = viewer.entities.add({
    polyline: {
      positions: segmentPositions,
      width: 13,
      material: rainGlowMaterial(span.category, selected, routeIndex * 0.9 + spanIndex * 0.4),
      clampToGround: false,
    },
    properties: {
      route_id: routeId,
      weather_category: span.category,
    },
  });
  addRouteEntity(glowEntity, routeId);
  addRainParticleCurtain(span, routeId, routeIndex, spanIndex);
  const iconPoint = interpolateWaypoint(span.start, span.end, 0.5);
  const animation = getRainAnimation(span.category);
  const billboardEntity = viewer.entities.add({
    position: Cesium.Cartesian3.fromDegrees(iconPoint.lon, iconPoint.lat, Number(iconPoint.altitude_m || 0) + 18),
    billboard: {
      image: animation.canvas,
      scale: span.category === "rain_heavy" ? 1.05 : 0.92,
      verticalOrigin: Cesium.VerticalOrigin.CENTER,
      horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
      pixelOffset: new Cesium.Cartesian2(spanIndex % 2 === 0 ? 40 : -40, -30 - (spanIndex % 2) * 8),
      eyeOffset: new Cesium.Cartesian3(0, 0, -16),
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
    label: {
      text: span.category === "rain_heavy" ? "强降雨区" : "降雨区",
      font: '700 12px "Avenir Next", "PingFang SC", sans-serif',
      fillColor: Cesium.Color.fromCssColorString("#d9f2ff"),
      outlineColor: Cesium.Color.fromCssColorString("#0a1524"),
      outlineWidth: 3,
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      showBackground: true,
      backgroundColor: Cesium.Color.fromCssColorString("#07192d").withAlpha(0.72),
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      pixelOffset: new Cesium.Cartesian2(spanIndex % 2 === 0 ? 40 : -40, 34),
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
    properties: {
      route_id: routeId,
      weather_category: span.category,
      precipitation_mm: span.maxPrecipitation,
      turbulence_index: span.maxTurbulence,
    },
  });
  addRouteEntity(billboardEntity, routeId);
}

function spanPoint(span, t, altitudeOffset = 0) {
  const point = interpolateWaypoint(span.start, span.end, t);
  return {
    ...point,
    altitude_m: Number(point.altitude_m || 0) + altitudeOffset,
  };
}

function spanBearingRad(span) {
  const headingDeg = routeBearingDeg([
    [span.start.lon, span.start.lat, span.start.altitude_m],
    [span.end.lon, span.end.lat, span.end.altitude_m],
  ]);
  return Cesium.Math.toRadians(90 - headingDeg);
}

function renderWindSpan(span, route, routeIndex, spanIndex) {
  const routeId = route.route_id;
  const positions = [
    waypointCartesian(spanPoint(span, 0, 22)),
    waypointCartesian(spanPoint(span, 1, 22)),
  ];
  const windLine = viewer.entities.add({
    polyline: {
      positions,
      width: 9,
      material: new Cesium.PolylineGlowMaterialProperty({
        glowPower: 0.42,
        color: animatedBandColor("#9df8ff", "#f7feff", 0.78, routeIndex + spanIndex * 0.4),
      }),
      clampToGround: false,
    },
    properties: {
      route_id: routeId,
      weather_category: "strong_wind",
      wind_speed_mps: span.maxWind,
    },
  });
  addRouteEntity(windLine, routeId);
  const arrowImage = getWindArrowImage();
  const rotation = spanBearingRad(span);
  for (let idx = 0; idx < 4; idx += 1) {
    const phase = idx / 4;
    const arrow = viewer.entities.add({
      position: new Cesium.CallbackProperty(() => {
        const t = (phase + (performance.now() * 0.00022 * Math.max(1, span.maxWind / STRONG_WIND_THRESHOLD_MPS))) % 1;
        const point = spanPoint(span, t, 30 + idx * 2);
        return Cesium.Cartesian3.fromDegrees(point.lon, point.lat, point.altitude_m);
      }, false),
      billboard: {
        image: arrowImage,
        scale: 0.72,
        rotation,
        alignedAxis: Cesium.Cartesian3.ZERO,
        verticalOrigin: Cesium.VerticalOrigin.CENTER,
        horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
        pixelOffset: new Cesium.Cartesian2(0, -18 - idx * 2),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: idx === 0
        ? {
            text: `强风 ${formatNumber(span.maxWind, 1)}m/s`,
            font: '700 12px "Avenir Next", "PingFang SC", sans-serif',
            fillColor: Cesium.Color.WHITE,
            outlineColor: Cesium.Color.fromCssColorString("#06313c"),
            outlineWidth: 3,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            showBackground: true,
            backgroundColor: Cesium.Color.fromCssColorString("#06313c").withAlpha(0.72),
            verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
            pixelOffset: new Cesium.Cartesian2(0, -42),
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
          }
        : undefined,
      properties: {
        route_id: routeId,
        weather_category: "strong_wind",
        wind_speed_mps: span.maxWind,
      },
    });
    addRouteEntity(arrow, routeId);
  }
}

function renderPressureSpan(span, route, routeIndex, spanIndex) {
  const routeId = route.route_id;
  const midpoint = spanPoint(span, 0.5, 42);
  const isHigh = span.pressureDeltaHpa >= 0;
  const baseColor = isHigh ? "#ff6d4a" : "#4f8dff";
  const label = `${isHigh ? "高压" : "低压"} ${span.pressureDeltaHpa >= 0 ? "+" : ""}${formatNumber(span.pressureDeltaHpa, 1)}hPa`;
  const pressureColumn = viewer.entities.add({
    position: Cesium.Cartesian3.fromDegrees(midpoint.lon, midpoint.lat, midpoint.altitude_m),
    cylinder: {
      length: 84,
      topRadius: 18,
      bottomRadius: 38,
      material: new Cesium.ColorMaterialProperty(new Cesium.CallbackProperty(() => {
        const alpha = 0.28 + 0.18 * (0.5 + 0.5 * Math.sin(performance.now() * 0.006 + spanIndex));
        return Cesium.Color.fromCssColorString(baseColor).withAlpha(alpha);
      }, false)),
      outline: true,
      outlineColor: Cesium.Color.fromCssColorString(baseColor).withAlpha(0.82),
    },
    label: {
      text: `${label}\n${formatNumber(span.pressureHpa, 1)}hPa`,
      font: '700 12px "Avenir Next", "PingFang SC", sans-serif',
      fillColor: Cesium.Color.WHITE,
      outlineColor: Cesium.Color.fromCssColorString("#20110f"),
      outlineWidth: 3,
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      showBackground: true,
      backgroundColor: Cesium.Color.fromCssColorString(isHigh ? "#3a130c" : "#071b3d").withAlpha(0.74),
      verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
      pixelOffset: new Cesium.Cartesian2(spanIndex % 2 === 0 ? -34 : 34, -42),
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    },
    properties: {
      route_id: routeId,
      weather_category: "pressure",
      pressure_hpa: span.pressureHpa,
      pressure_delta_hpa: span.pressureDeltaHpa,
    },
  });
  addRouteEntity(pressureColumn, routeId);
}

function renderCloudSpan(span, route, routeIndex, spanIndex) {
  const routeId = route.route_id;
  const animation = getCloudAnimation();
  const cloudCount = 3;
  for (let idx = 0; idx < cloudCount; idx += 1) {
    const point = spanPoint(span, (idx + 1) / (cloudCount + 1), 56 + idx * 4);
    const cloud = viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(point.lon, point.lat, point.altitude_m),
      billboard: {
        image: animation.canvas,
        scale: 0.72 + Math.min(0.26, span.maxCloud / 260),
        verticalOrigin: Cesium.VerticalOrigin.CENTER,
        horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
        pixelOffset: new Cesium.Cartesian2((idx - 1) * 22, -22 - idx * 3),
        eyeOffset: new Cesium.Cartesian3(0, 0, -20),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: idx === 1
        ? {
            text: `云量 ${formatNumber(span.maxCloud, 0)}%`,
            font: '700 12px "Avenir Next", "PingFang SC", sans-serif',
            fillColor: Cesium.Color.fromCssColorString("#f4fbff"),
            outlineColor: Cesium.Color.fromCssColorString("#182636"),
            outlineWidth: 3,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            showBackground: true,
            backgroundColor: Cesium.Color.fromCssColorString("#182636").withAlpha(0.68),
            verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
            pixelOffset: new Cesium.Cartesian2(0, 26),
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
          }
        : undefined,
      properties: {
        route_id: routeId,
        weather_category: "cloud",
        cloud_cover_pct: span.maxCloud,
      },
    });
    addRouteEntity(cloud, routeId);
  }
}

function renderRouteEntities() {
  state.routeEntities.forEach((entity) => viewer.entities.remove(entity));
  state.routeEntities = [];
  state.routeParticleSystems.forEach(({ system }) => {
    viewer.scene.primitives.remove(system);
  });
  state.routeParticleSystems = [];
  if (!state.routes.length) {
    setRouteDetail(null);
    return;
  }
  state.selectedRouteId = resolveSelectedRouteId(state.routes, state.selectedRouteId);
  state.routes.forEach((route, routeIndex) => {
    const selected = route.route_id === state.selectedRouteId;
    const color = ROUTE_COLORS[routeIndex % ROUTE_COLORS.length];
    const coords = route.waypoints.map((point) => [point.lon, point.lat, point.altitude_m]);
    const positions = coords.map((coord) => Cesium.Cartesian3.fromDegrees(coord[0], coord[1], coord[2] || 100));
    const routeEntity = viewer.entities.add({
      polyline: {
        positions,
        width: selected ? 8 : 4,
        material: routeMaterial(color, selected),
        clampToGround: false,
      },
      properties: {
        route_id: route.route_id,
        label: route.label,
        strategy: route.strategy,
        score: route.score,
      },
    });
  addRouteEntity(routeEntity, route.route_id, true);

    if (pageConfig.showWeather && state.weatherFieldIndex && selected) {
      const weatherSegments = buildRouteWeatherSegments(route);
      const weatherLayers = buildRouteWeatherLayers(weatherSegments);
      weatherLayers.rain
        .slice(0, MAX_RAIN_SPANS_PER_ROUTE)
        .forEach((span, spanIndex) => renderRainSpan(span, route, routeIndex, spanIndex, selected));
      weatherLayers.wind
        .forEach((span, spanIndex) => renderWindSpan(span, route, routeIndex, spanIndex));
      weatherLayers.pressure
        .forEach((span, spanIndex) => renderPressureSpan(span, route, routeIndex, spanIndex));
      weatherLayers.cloud
        .forEach((span, spanIndex) => renderCloudSpan(span, route, routeIndex, spanIndex));
    }

    route.waypoints.forEach((point, pointIndex) => {
      const waypointEntity = viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(point.lon, point.lat, point.altitude_m),
        point: {
          pixelSize: selected ? 10 : 7,
          color: Cesium.Color.fromCssColorString(color),
          outlineColor: Cesium.Color.WHITE.withAlpha(0.8),
          outlineWidth: 2,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
        label: selected
          ? {
              text: `${pointIndex + 1}`,
              font: '700 11px "Avenir Next", "PingFang SC", sans-serif',
              fillColor: Cesium.Color.fromCssColorString("#10251f"),
              outlineColor: Cesium.Color.WHITE,
              outlineWidth: 3,
              style: Cesium.LabelStyle.FILL_AND_OUTLINE,
              verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
              pixelOffset: new Cesium.Cartesian2(0, -14),
              disableDepthTestDistance: Number.POSITIVE_INFINITY,
            }
          : undefined,
        properties: {
          route_id: route.route_id,
          waypoint_index: pointIndex + 1,
          altitude_m: point.altitude_m,
        },
      });
      addRouteEntity(waypointEntity, route.route_id, true);
    });
  });
  updateLayerVisibility();
  setRouteDetail(routeById(state.selectedRouteId));
}

function updateLayerVisibility() {
  if (state.buildingSource) {
    state.buildingSource.show = state.toggles.buildings;
  }
  if (state.tileset) state.tileset.show = state.toggles.buildings;
  if (state.groundTileset) state.groundTileset.show = state.toggles.buildings;
  if (state.outlineTileset) state.outlineTileset.show = state.toggles.buildings;
  if (state.weatherPrimitives) state.weatherPrimitives.show = state.toggles.weather;
  state.routeEntities.forEach((entity) => {
    entity.show = state.toggles.routes;
  });
  state.routeParticleSystems.forEach(({ system }) => {
    system.show = state.toggles.routes && state.toggles.weather;
  });
}

function screenToLonLat(position) {
  let cartesian = viewer.scene.pickPosition(position);
  if (!Cesium.defined(cartesian)) {
    cartesian = viewer.camera.pickEllipsoid(position, Cesium.Ellipsoid.WGS84);
  }
  if (!Cesium.defined(cartesian)) {
    return null;
  }
  const cartographic = Cesium.Cartographic.fromCartesian(cartesian);
  return {
    lon: Cesium.Math.toDegrees(cartographic.longitude),
    lat: Cesium.Math.toDegrees(cartographic.latitude),
  };
}

function activatePickMode(mode) {
  state.pickMode = state.pickMode === mode ? null : mode;
  updatePickHint();
}

async function loadCity(cityName, { keepRoutes = false } = {}) {
  setStatus("加载三维城市资产中", "neutral");
  const cityPayload = await fetchJson(`/api/city?city=${encodeURIComponent(cityName)}&planning_mode=${encodeURIComponent(PLANNING_MODE)}`);
  const [buildings, weather] = await Promise.all([
    pageConfig.showBuildings ? fetchJson(`/api/buildings?city=${encodeURIComponent(cityName)}`) : Promise.resolve(null),
    pageConfig.showWeather ? fetchJson(`/api/weather?city=${encodeURIComponent(cityName)}`) : Promise.resolve(null),
  ]);
  await clearScene();
  state.cityName = cityName;
  state.citySummary = cityPayload.summary;
  state.cityConfig = cityPayload.config;
  state.assetUrls = cityPayload.asset_urls || {};
  state.buildings = buildings;
  state.weather = weather;
  state.weatherFieldIndex = createWeatherFieldIndex(weather);
  const latestRoutes = cityPayload.latest_plan?.routes || [];
  const nextRoutes = keepRoutes && state.routes.length ? state.routes : latestRoutes;
  setRoutes(nextRoutes, keepRoutes ? state.selectedRouteId : null);
  state.worldCenter = currentCenter();
  state.worldBounds = currentBbox();

  let loadedTiles = false;
  if (pageConfig.showBuildings && buildings) {
    loadedTiles = await tryLoadTilesets(state.assetUrls);
    if (!loadedTiles) {
      await loadBuildingGeoJson(buildings);
    }
  }
  if (pageConfig.showWeather && weather) {
    loadWeatherPrimitives(weather);
  }
  updateSummary();
  if (!keepRoutes || !$("start-lat").value || !$("end-lat").value) {
    setFormFromDefaultRoute();
  } else {
    updateMarkers();
  }
  renderRouteList();
  renderRouteEntities();
  updateLayerVisibility();
  flyOblique();
  if (pageConfig.showBuildings) {
    setStatus(loadedTiles ? "三维城市 Tiles 已加载" : "已回退为 GeoJSON 三维挤出", "success");
  } else {
    setStatus("天气模式城市底图已加载", "success");
  }
}

async function loadCities() {
  const payload = await fetchJson("/api/cities");
  state.cities = payload.cities || [];
  const select = $("city-select");
  select.innerHTML = "";
  state.cities.forEach((city) => {
    const option = document.createElement("option");
    option.value = city.name;
    option.textContent = city.display_name;
    select.appendChild(option);
  });
  const defaultCity = state.cities.find((item) => item.name === payload.default_city)?.name || state.cities[0]?.name;
  if (!defaultCity) {
    setStatus("未发现可用城市资产", "error");
    return;
  }
  select.value = defaultCity;
  await loadCity(defaultCity);
}

async function planRoutes() {
  const payload = {
    city: $("city-select").value,
    planning_mode: PLANNING_MODE,
    start_lat: Number($("start-lat").value),
    start_lon: Number($("start-lon").value),
    end_lat: Number($("end-lat").value),
    end_lon: Number($("end-lon").value),
    start_altitude_m: Number($("start-altitude").value),
    end_altitude_m: Number($("end-altitude").value),
    min_altitude_m: Number($("min-altitude").value),
    candidate_count: Number($("candidate-count").value),
    cell_m: Number($("cell-size").value),
    safety_clearance_m: Number($("safety-clearance").value),
    max_altitude_m: optionalNumber("max-altitude"),
  };
  setStatus("正在规划候选航线", "warning");
  $("btn-plan").disabled = true;
  try {
    const result = await fetchJson("/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setRoutes(result.routes || [], null);
    renderRouteList();
    renderRouteEntities();
    flyRoute();
    setStatus(`已生成 ${state.routes.length} 条候选航线`, "success");
  } catch (error) {
    console.error(error);
    setStatus(error.message || String(error), "error");
  } finally {
    $("btn-plan").disabled = false;
  }
}

function bindEvents() {
  $("city-select").addEventListener("change", async (event) => {
    try {
      await loadCity(event.target.value);
    } catch (error) {
      console.error(error);
      setStatus(error.message || String(error), "error");
    }
  });
  $("btn-use-default").addEventListener("click", () => {
    setFormFromDefaultRoute();
  });
  $("btn-pick-start").addEventListener("click", () => activatePickMode("start"));
  $("btn-pick-end").addEventListener("click", () => activatePickMode("end"));
  $("btn-plan").addEventListener("click", () => {
    planRoutes().catch((error) => {
      console.error(error);
      setStatus(error.message || String(error), "error");
      $("btn-plan").disabled = false;
    });
  });
  $("btn-fly-route").addEventListener("click", flyRoute);
  $("btn-oblique").addEventListener("click", flyOblique);
  $("btn-topdown").addEventListener("click", flyTopdown);
  $("btn-reset-view").addEventListener("click", resetView);
  $("toggle-buildings")?.addEventListener("change", (event) => {
    state.toggles.buildings = event.target.checked;
    updateLayerVisibility();
  });
  $("toggle-weather")?.addEventListener("change", (event) => {
    state.toggles.weather = event.target.checked;
    updateLayerVisibility();
  });
  $("toggle-routes")?.addEventListener("change", (event) => {
    state.toggles.routes = event.target.checked;
    updateLayerVisibility();
  });
  ["start-lat", "start-lon", "end-lat", "end-lon", "start-altitude", "end-altitude"].forEach((id) => {
    $(id).addEventListener("input", updateMarkers);
  });

  viewer.screenSpaceEventHandler.setInputAction((movement) => {
    if (state.pickMode) {
      const coord = screenToLonLat(movement.position);
      if (!coord) return;
      if (state.pickMode === "start") {
        $("start-lat").value = coord.lat.toFixed(6);
        $("start-lon").value = coord.lon.toFixed(6);
      } else {
        $("end-lat").value = coord.lat.toFixed(6);
        $("end-lon").value = coord.lon.toFixed(6);
      }
      state.pickMode = null;
      updatePickHint();
      updateMarkers();
      return;
    }
    const picked = viewer.scene.pick(movement.position);
    if (picked?.id?.isRoute && picked.id.routeId) {
      selectRoute(picked.id.routeId);
    }
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

  viewer.camera.moveEnd.addEventListener(updateCameraReadout);
}

async function boot() {
  applyPlanningModeUi();
  bindEvents();
  updatePickHint();
  updateCameraReadout();
  try {
    await loadCities();
  } catch (error) {
    console.error(error);
    setStatus(error.message || String(error), "error");
  }
}

boot();
