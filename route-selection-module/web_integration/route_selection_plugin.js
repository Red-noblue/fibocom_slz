// UAV 工作台候选航线插件：复用现有 Cesium 三维控制台，叠加起终点规划与多候选航线展示。
(function () {
  const viewer = window.viewer;
  if (!viewer || !document.getElementById("dataset-select")) {
    return;
  }

  const pluginConfig = window.ROUTE_SELECTION_PLUGIN_CONFIG || {};
  const PLANNING_MODE = pluginConfig.planning_mode || "combined";
  const MODE_CONFIG = {
    combined: {
      title: "综合候选航线选择",
      panelTitle: "综合候选航线",
      hint: "候选航线会叠加到现有默认航线上。点击某条路线后会单独显示该路线，再点一次同一路线卡片可恢复全部显示。",
      showBuildings: true,
      showWeather: true,
    },
    weather_only: {
      title: "仅天气候选航线选择",
      panelTitle: "仅天气候选航线",
      hint: "当前页只展示天气采样和候选路线，路径规划完全忽略建筑约束。",
      showBuildings: false,
      showWeather: true,
    },
    building_only: {
      title: "仅建筑候选航线选择",
      panelTitle: "仅建筑候选航线",
      hint: "当前页只展示建筑和候选路线，路径规划完全忽略天气因素。",
      showBuildings: true,
      showWeather: false,
    },
  };
  const pageConfig = MODE_CONFIG[PLANNING_MODE] || MODE_CONFIG.combined;

  const state = {
    datasets: {},
    currentDatasetKey: "",
    pickMode: null,
    routes: [],
    selectedRouteId: "",
    isolatedRouteId: "",
    entities: [],
    weather: null,
    weatherFieldIndex: null,
    weatherAnimations: [],
    weatherAnimationBound: false,
    cruiseTickBound: false,
    cruiseStartMs: 0,
    currentWeatherSample: null,
    datasetSupported: false,
    modeWorldReloaded: false,
  };

  const ROUTE_COLORS = ["#00b894", "#ff7a00", "#006eff", "#e84393", "#2d8f00"];
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
  const ROUTE_HALO = "#002b5c";
  const ROUTE_SEGMENT_STEP_M = 180;
  const RAIN_LIGHT_THRESHOLD_MM = 0.35;
  const RAIN_HEAVY_THRESHOLD_MM = 1.2;
  const STRONG_WIND_THRESHOLD_MPS = 8.5;
  const HIGH_CLOUD_THRESHOLD_PCT = 62;
  const PRESSURE_ANOMALY_THRESHOLD_HPA = 4.5;
  const MAX_WEATHER_SPANS_PER_LAYER = 4;
  const PROFILE_SIDE_OFFSET_M = 42;
  const MAX_WIND_FIELD_ARROWS = 30;
  const MAX_CLOUD_MARKERS = 14;
  const MAX_CONVECTION_COLUMNS = 3;
  const ELECTRIC_BLUE = "#0984E3";
  const RISK_YELLOW = "#ffe066";
  const RISK_ORANGE = "#ff922b";
  const RISK_RED = "#ff3b30";

  function $(id) {
    return document.getElementById(id);
  }

  function injectStyles() {
    if ($("route-selection-plugin-style")) return;
    const style = document.createElement("style");
    style.id = "route-selection-plugin-style";
    style.textContent = `
      #route-selection-plugin-panel .compact-grid {
        margin-top: 10px;
      }
      #route-selection-plugin-panel .route-selection-actions {
        display: grid;
        gap: 8px;
        margin-top: 10px;
      }
      #route-selection-plugin-panel .route-selection-list {
        display: grid;
        gap: 8px;
        margin-top: 10px;
      }
      #route-selection-plugin-panel .route-selection-card {
        text-align: left;
        background: #f8fbf9;
      }
      #route-selection-plugin-panel .route-selection-card.active {
        border-color: rgba(11, 122, 99, 0.4);
        box-shadow: 0 8px 20px rgba(11, 122, 99, 0.12);
      }
      #route-selection-plugin-panel .route-selection-meta {
        margin-top: 6px;
        color: var(--muted);
        line-height: 1.4;
      }
      #route-selection-plugin-panel .route-selection-hint {
        margin-top: 8px;
      }
      #route-selection-weather-panel .rs-weather-hero {
        border-radius: 18px;
        padding: 14px;
        color: #1f2d35;
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(242, 247, 250, 0.96));
        box-shadow: inset 0 0 0 1px rgba(9, 132, 227, 0.10), 0 14px 30px rgba(31, 45, 53, 0.10);
      }
      #route-selection-weather-panel .rs-weather-status {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 9px;
        border-radius: 999px;
        background: rgba(9, 132, 227, 0.10);
        color: #075a9f;
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0.04em;
      }
      #route-selection-weather-panel .rs-weather-main {
        margin-top: 8px;
        font-size: 22px;
        font-weight: 900;
      }
      #route-selection-weather-panel .rs-weather-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        margin-top: 12px;
      }
      #route-selection-weather-panel .rs-weather-grid div {
        border-radius: 12px;
        padding: 9px;
        background: rgba(9, 132, 227, 0.06);
      }
      #route-selection-weather-panel .rs-weather-grid span {
        display: block;
        color: rgba(54, 73, 86, 0.72);
        font-size: 11px;
      }
      #route-selection-weather-panel .rs-weather-grid strong {
        display: block;
        margin-top: 3px;
        font-size: 15px;
      }
      #route-selection-weather-panel .rs-weather-note {
        margin-top: 10px;
        color: rgba(54, 73, 86, 0.74);
        font-size: 12px;
        line-height: 1.45;
      }
      #route-selection-weather-panel .rs-risk-legend {
        display: grid;
        gap: 6px;
        margin-top: 10px;
        font-size: 11px;
        color: rgba(54, 73, 86, 0.78);
      }
      #route-selection-weather-panel .rs-risk-legend-row {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      #route-selection-weather-panel .rs-risk-chip {
        width: 34px;
        height: 9px;
        border-radius: 999px;
        box-shadow: 0 0 12px rgba(255,255,255,0.12);
      }
      body[data-planning-mode="weather_only"] .map-panel,
      body[data-planning-mode="combined"] .map-panel {
        background: linear-gradient(135deg, rgba(255,255,255,0.98), rgba(244,248,246,0.96));
      }
      body[data-planning-mode="weather_only"] #cesiumContainer,
      body[data-planning-mode="combined"] #cesiumContainer {
        background: #ffffff;
      }
    `;
    document.head.appendChild(style);
  }

  function injectWeatherInspector() {
    if (!pageConfig.showWeather || $("route-selection-weather-panel")) return;
    const inspector = document.querySelector(".inspector");
    if (!inspector) return;
    const panel = document.createElement("section");
    panel.className = "panel";
    panel.id = "route-selection-weather-panel";
    panel.innerHTML = `
      <h2>航线气象态势</h2>
      <div class="rs-weather-hero">
        <div class="rs-weather-status" id="rs-weather-state">等待选中航线</div>
        <div class="rs-weather-main" id="rs-weather-title">未开始巡航</div>
        <div class="rs-weather-grid">
          <div><span>气压</span><strong id="rs-weather-pressure">-- hPa</strong></div>
          <div><span>风速 / 风向</span><strong id="rs-weather-wind">--</strong></div>
          <div><span>温度</span><strong id="rs-weather-temp">-- ℃</strong></div>
          <div><span>湿度 / 云量</span><strong id="rs-weather-humidity">--</strong></div>
          <div><span>空气密度</span><strong id="rs-weather-density">-- kg/m3</strong></div>
          <div><span>逆风 / 侧风</span><strong id="rs-weather-route-wind">--</strong></div>
        </div>
        <p class="rs-weather-note" id="rs-weather-note">${PLANNING_MODE === "combined" ? "选中综合候选航线后，建筑模型、避障航线管体和天气态势会叠加显示，便于同时判断绕障空间和气象风险。" : "选中候选航线后，俯瞰图会展示区域降水热力图、全航线风场、雨幕、云量和强对流动态。"}</p>
        <div class="rs-risk-legend">
          ${PLANNING_MODE === "combined" ? '<div class="rs-risk-legend-row"><span class="rs-risk-chip" style="background:rgba(9,132,227,0.42)"></span><span>综合叠加：航线管体表示建筑避障路径，气象图标叠加在同一路径周边</span></div>' : ""}
          <div class="rs-risk-legend-row"><span class="rs-risk-chip" style="background:linear-gradient(90deg,rgba(188,218,235,0.45),rgba(111,166,205,0.58),rgba(46,101,158,0.68))"></span><span>区域降水热力图：浅蓝→深蓝表示 precipitation_mm 从小到大</span></div>
          <div class="rs-risk-legend-row"><span class="rs-risk-chip" style="background:rgba(116,185,255,0.28)"></span><span>低风险：气象影响弱，热力层接近透明蓝</span></div>
          <div class="rs-risk-legend-row"><span class="rs-risk-chip" style="background:#ffe066"></span><span>中低风险：轻度云量/风/降水压力</span></div>
          <div class="rs-risk-legend-row"><span class="rs-risk-chip" style="background:#ff922b"></span><span>中高风险：强风、降雨或湍流开始显著</span></div>
          <div class="rs-risk-legend-row"><span class="rs-risk-chip" style="background:#ff3b30"></span><span>高风险：强降雨/强对流/高湍流集中区域</span></div>
        </div>
      </div>
    `;
    const routeDetail = $("route-detail")?.closest(".panel");
    if (routeDetail?.nextSibling) {
      inspector.insertBefore(panel, routeDetail.nextSibling);
    } else {
      inspector.appendChild(panel);
    }
  }

  function injectPanel() {
    if ($("route-selection-plugin-panel")) return;
    const sidebar = document.querySelector(".sidebar");
    const anchor = document.querySelector(".route-draw-panel");
    if (!sidebar) return;
    const panel = document.createElement("details");
    panel.className = "panel";
    panel.id = "route-selection-plugin-panel";
    panel.open = true;
    panel.innerHTML = `
      <summary>${pageConfig.panelTitle}</summary>
      <p id="route-selection-status" class="small">等待数据集信息。</p>
      <div class="compact-grid">
        <label for="rs-start-lat">起点纬度</label>
        <label for="rs-start-lon">起点经度</label>
        <input id="rs-start-lat" type="number" step="0.000001">
        <input id="rs-start-lon" type="number" step="0.000001">
        <label for="rs-end-lat">终点纬度</label>
        <label for="rs-end-lon">终点经度</label>
        <input id="rs-end-lat" type="number" step="0.000001">
        <input id="rs-end-lon" type="number" step="0.000001">
        <label for="rs-start-alt">起点高度 m</label>
        <label for="rs-end-alt">终点高度 m</label>
        <input id="rs-start-alt" type="number" min="0" max="800" step="5" value="120">
        <input id="rs-end-alt" type="number" min="0" max="800" step="5" value="120">
        <label for="rs-min-altitude">最低高度 m</label>
        <label for="rs-candidate-count">候选数量</label>
        <input id="rs-min-altitude" type="number" min="0" max="400" step="5" value="0">
        <input id="rs-candidate-count" type="number" min="1" max="5" step="1" value="5">
        <label for="rs-cell-size">栅格尺寸 m</label>
        <input id="rs-cell-size" type="number" min="60" max="600" step="10" value="220">
        <label for="rs-safety-clearance">安全净空 m</label>
        <label for="rs-max-altitude">最大高度上限 m（留空或≤0 自动）</label>
        <input id="rs-safety-clearance" type="number" min="5" max="120" step="5" value="25">
        <input id="rs-max-altitude" type="number" step="10" placeholder="自动">
      </div>
      <div class="route-selection-actions">
        <button id="rs-use-default" type="button">使用当前默认起终点</button>
        <button id="rs-pick-start" type="button">场景点选起点</button>
        <button id="rs-pick-end" type="button">场景点选终点</button>
        <button id="rs-plan" type="button" class="primary">生成候选航线</button>
        <button id="rs-clear" type="button">清除候选航线</button>
        <button id="rs-fly-selected" type="button">飞到选中路线</button>
      </div>
      <p id="route-selection-hint" class="small route-selection-hint">${pageConfig.hint}</p>
      <div id="route-selection-list" class="route-selection-list"></div>
    `;
    if (anchor && anchor.parentNode === sidebar) {
      sidebar.insertBefore(panel, anchor);
    } else {
      sidebar.appendChild(panel);
    }
    injectWeatherInspector();
  }

  function currentDatasetKey() {
    return $("dataset-select")?.value || "";
  }

  function setStatus(text) {
    const node = $("route-selection-status");
    if (node) node.textContent = text;
  }

  function setHint(text) {
    const node = $("route-selection-hint");
    if (node) node.textContent = text;
  }

  function applyProfessionalWeatherStyle() {
    if (viewer.scene) {
      viewer.scene.backgroundColor = Cesium.Color.WHITE;
      viewer.scene.highDynamicRange = false;
    }
    const bloom = viewer.scene?.postProcessStages?.bloom;
    if (bloom) {
      bloom.enabled = false;
      bloom.uniforms.glowOnly = false;
      bloom.uniforms.contrast = 72;
      bloom.uniforms.brightness = -0.08;
      bloom.uniforms.delta = 1.0;
      bloom.uniforms.sigma = 1.2;
      bloom.uniforms.stepSize = 1.0;
    }
  }

  async function fetchJson(url, options) {
    const response = await fetch(url, options);
    const data = await response.json();
    if (!response.ok || data?.error) {
      throw new Error(data?.error || `请求失败：${response.status}`);
    }
    return data;
  }

  function hideElement(node, hidden) {
    if (!node) return;
    node.style.display = hidden ? "none" : "";
  }

  function setCheckboxState(id, checked) {
    const node = $(id);
    if (!node) return;
    node.checked = checked;
    node.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function applyWorkbenchModeUi() {
    document.title = pageConfig.title;
    hideElement($("stat-buildings")?.parentElement, !pageConfig.showBuildings);
    hideElement($("layer-buildings")?.closest("label"), !pageConfig.showBuildings);
    hideElement($("layer-weather")?.closest("label"), !pageConfig.showWeather);
    hideElement(document.querySelector('label[for="render-mode"]'), !pageConfig.showBuildings);
    hideElement($("render-mode"), !pageConfig.showBuildings);
    hideElement(document.querySelector('label[for="building-backend"]'), !pageConfig.showBuildings);
    hideElement($("building-backend"), !pageConfig.showBuildings);
    hideElement($("ion-hint"), !pageConfig.showBuildings);
    hideElement(document.querySelector('label[for="altitude-filter"]'), !pageConfig.showWeather);
    hideElement($("altitude-filter"), !pageConfig.showWeather);
    hideElement(Array.from(document.querySelectorAll("details.panel > summary")).find((node) => node.textContent.trim() === "城市要素纠错")?.parentElement, !pageConfig.showBuildings);
    setCheckboxState("layer-buildings", pageConfig.showBuildings);
    setCheckboxState("layer-weather", pageConfig.showWeather);
    const featureDetail = $("feature-detail");
    if (featureDetail && !featureDetail.textContent.startsWith("候选航线")) {
      featureDetail.textContent = pageConfig.showBuildings
        ? "空间信息：点击建筑、道路、天气点或航线查看属性。"
        : "空间信息：点击天气点或航线查看属性。";
    }
    const buildingBackend = $("building-backend");
    if (!pageConfig.showBuildings && buildingBackend && buildingBackend.value !== "none") {
      buildingBackend.value = "none";
      return true;
    }
    return false;
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

  function routeStrategyText(route) {
    return ROUTE_STRATEGY_TEXT[route?.strategy] || route?.strategy || "";
  }

  function routeAltitudeRangeText(route) {
    const altitudes = (route?.waypoints || [])
      .map((point) => Number(point.altitude_m))
      .filter((value) => Number.isFinite(value));
    if (!altitudes.length) return "高度 -";
    const minAltitude = Math.min(...altitudes);
    const maxAltitude = Math.max(...altitudes);
    if (Math.abs(maxAltitude - minAltitude) < 1e-6) {
      return `高度 ${formatNumber(minAltitude, 0)} m`;
    }
    return `高度 ${formatNumber(minAltitude, 0)}-${formatNumber(maxAltitude, 0)} m`;
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
        wind_dir_deg: Number(props.wind_dir_deg ?? props.wind_direction_deg ?? props.wind_direction_10m ?? 0),
        temperature_c: Number(props.temperature_c ?? props.temperature_2m ?? NaN),
        relative_humidity_pct: Number(props.rh_pct ?? props.rh2_pct ?? props.relative_humidity_pct ?? props.relative_humidity_2m ?? props.humidity_pct ?? NaN),
        air_density_kgm3: Number(props.air_density_kgm3 ?? NaN),
        headwind_mps: Number(props.headwind_mps ?? NaN),
        crosswind_mps: Number(props.crosswind_mps ?? NaN),
        turbulence_index: Number(props.turbulence_index || 0),
        precipitation_mm: Number(props.precipitation_mm || 0),
        pressure_hpa: Number(props.pressure_hpa || 1013.25),
        cloud_cover_pct: Number(props.cloud_cover_pct ?? props.cloud_cover ?? props.cloud_cover_percent ?? 0),
      };
      const key = altitude.toFixed(2);
      if (!grouped.has(key)) grouped.set(key, []);
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

  function defaultWeatherSample() {
    return {
      wind_speed_mps: 0,
      wind_dir_deg: 0,
      temperature_c: 22,
      relative_humidity_pct: 60,
      air_density_kgm3: NaN,
      headwind_mps: NaN,
      crosswind_mps: NaN,
      turbulence_index: 0,
      precipitation_mm: 0,
      pressure_hpa: 1013.25,
      pressure_delta_hpa: 0,
      pressure_anomaly_hpa: 0,
      cloud_cover_pct: 0,
    };
  }

  function interpolateWeather2d(samples, lon, lat) {
    if (!samples?.length) return defaultWeatherSample();
    const weighted = samples
      .map((sample) => {
        const distSq = (sample.lon - lon) ** 2 + (sample.lat - lat) ** 2;
        return { weight: distSq < 1e-14 ? Number.POSITIVE_INFINITY : 1 / distSq, sample };
      })
      .sort((a, b) => b.weight - a.weight)
      .slice(0, 4);
    if (weighted[0]?.weight === Number.POSITIVE_INFINITY) return { ...weighted[0].sample };
    const totalWeight = weighted.reduce((sum, item) => sum + item.weight, 0) || 1;
    const optionalWeightedAverage = (key) => {
      const usable = weighted.filter((item) => Number.isFinite(item.sample[key]));
      const usableWeight = usable.reduce((sum, item) => sum + item.weight, 0);
      if (!usable.length || !usableWeight) return NaN;
      return usable.reduce((sum, item) => sum + item.weight * item.sample[key], 0) / usableWeight;
    };
    return {
      wind_speed_mps: weighted.reduce((sum, item) => sum + item.weight * item.sample.wind_speed_mps, 0) / totalWeight,
      wind_dir_deg: weighted.reduce((sum, item) => sum + item.weight * item.sample.wind_dir_deg, 0) / totalWeight,
      temperature_c: weighted.reduce((sum, item) => sum + item.weight * (Number.isFinite(item.sample.temperature_c) ? item.sample.temperature_c : 22), 0) / totalWeight,
      relative_humidity_pct: weighted.reduce((sum, item) => sum + item.weight * (Number.isFinite(item.sample.relative_humidity_pct) ? item.sample.relative_humidity_pct : 60), 0) / totalWeight,
      air_density_kgm3: optionalWeightedAverage("air_density_kgm3"),
      headwind_mps: optionalWeightedAverage("headwind_mps"),
      crosswind_mps: optionalWeightedAverage("crosswind_mps"),
      turbulence_index: weighted.reduce((sum, item) => sum + item.weight * item.sample.turbulence_index, 0) / totalWeight,
      precipitation_mm: weighted.reduce((sum, item) => sum + item.weight * item.sample.precipitation_mm, 0) / totalWeight,
      pressure_hpa: weighted.reduce((sum, item) => sum + item.weight * item.sample.pressure_hpa, 0) / totalWeight,
      cloud_cover_pct: weighted.reduce((sum, item) => sum + item.weight * item.sample.cloud_cover_pct, 0) / totalWeight,
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
    if (!state.weatherFieldIndex?.altitudeLevels?.length) return defaultWeatherSample();
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
    const ratio = Math.abs(upper - lower) < 1e-6 ? 0 : (altitude - lower) / (upper - lower);
    const blendOptional = (key) => {
      const lowerValue = lowerState[key];
      const upperValue = upperState[key];
      if (Number.isFinite(lowerValue) && Number.isFinite(upperValue)) return lowerValue * (1 - ratio) + upperValue * ratio;
      if (Number.isFinite(lowerValue)) return lowerValue;
      if (Number.isFinite(upperValue)) return upperValue;
      return NaN;
    };
    const stateAtPoint = {
      wind_speed_mps: lowerState.wind_speed_mps * (1 - ratio) + upperState.wind_speed_mps * ratio,
      wind_dir_deg: lowerState.wind_dir_deg * (1 - ratio) + upperState.wind_dir_deg * ratio,
      temperature_c: lowerState.temperature_c * (1 - ratio) + upperState.temperature_c * ratio,
      relative_humidity_pct: lowerState.relative_humidity_pct * (1 - ratio) + upperState.relative_humidity_pct * ratio,
      air_density_kgm3: blendOptional("air_density_kgm3"),
      headwind_mps: blendOptional("headwind_mps"),
      crosswind_mps: blendOptional("crosswind_mps"),
      turbulence_index: lowerState.turbulence_index * (1 - ratio) + upperState.turbulence_index * ratio,
      precipitation_mm: lowerState.precipitation_mm * (1 - ratio) + upperState.precipitation_mm * ratio,
      pressure_hpa: lowerState.pressure_hpa * (1 - ratio) + upperState.pressure_hpa * ratio,
      cloud_cover_pct: lowerState.cloud_cover_pct * (1 - ratio) + upperState.cloud_cover_pct * ratio,
    };
    stateAtPoint.pressure_delta_hpa = stateAtPoint.pressure_hpa - referencePressureAtAltitude(altitude);
    stateAtPoint.pressure_anomaly_hpa = Math.abs(stateAtPoint.pressure_delta_hpa);
    stateAtPoint.cloud_cover_pct = estimatedCloudCover(stateAtPoint);
    return stateAtPoint;
  }

  function interpolateWaypoint(a, b, t) {
    return {
      lon: Number(a.lon) + (Number(b.lon) - Number(a.lon)) * t,
      lat: Number(a.lat) + (Number(b.lat) - Number(a.lat)) * t,
      altitude_m: Number(a.altitude_m || 0) + (Number(b.altitude_m || 0) - Number(a.altitude_m || 0)) * t,
    };
  }

  function waypointCartesian(point) {
    return Cesium.Cartesian3.fromDegrees(Number(point.lon), Number(point.lat), Number(point.altitude_m || 0));
  }

  function offsetWaypointSide(point, start, end, meters = PROFILE_SIDE_OFFSET_M) {
    const midLat = Cesium.Math.toRadians((Number(start.lat) + Number(end.lat)) / 2);
    const latMeters = 111320;
    const lonMeters = Math.max(1, latMeters * Math.cos(midLat));
    const dx = (Number(end.lon) - Number(start.lon)) * lonMeters;
    const dy = (Number(end.lat) - Number(start.lat)) * latMeters;
    const length = Math.max(1, Math.hypot(dx, dy));
    const nx = -dy / length;
    const ny = dx / length;
    return {
      ...point,
      lon: Number(point.lon) + (nx * meters) / lonMeters,
      lat: Number(point.lat) + (ny * meters) / latMeters,
    };
  }

  function offsetWaypointByMeters(point, eastM, northM, altitudeOffsetM = 0) {
    const latMeters = 111320;
    const lonMeters = Math.max(1, latMeters * Math.cos(Cesium.Math.toRadians(Number(point.lat))));
    return {
      ...point,
      lon: Number(point.lon) + eastM / lonMeters,
      lat: Number(point.lat) + northM / latMeters,
      altitude_m: Number(point.altitude_m || 0) + altitudeOffsetM,
    };
  }

  function windFlowUnit(weather) {
    const fromDeg = Number(weather?.wind_dir_deg ?? weather?.wind_direction_deg ?? 0);
    const rad = Cesium.Math.toRadians(fromDeg);
    return {
      east: -Math.sin(rad),
      north: -Math.cos(rad),
    };
  }

  function classifyWeatherSegment(stats) {
    if (!stats || stats.precipitation_mm < RAIN_LIGHT_THRESHOLD_MM) return "clear";
    if (stats.precipitation_mm >= RAIN_HEAVY_THRESHOLD_MM || (stats.precipitation_mm >= 0.7 && stats.turbulence_index >= 0.36)) return "rain_heavy";
    return "rain_light";
  }

  function sampleWeatherForSegment(start, end) {
    const sampleCount = 3;
    let maxPrecipitation = 0;
    let maxTurbulence = 0;
    let maxWind = 0;
    let windDirSum = 0;
    let maxCloud = 0;
    let maxPressureAnomaly = 0;
    let temperatureSum = 0;
    let humiditySum = 0;
    let densitySum = 0;
    let pressureSum = 0;
    let pressureDeltaSum = 0;
    for (let idx = 0; idx < sampleCount; idx += 1) {
      const point = interpolateWaypoint(start, end, (idx + 0.5) / sampleCount);
      const weather = interpolateWeatherAtPoint(point.lon, point.lat, point.altitude_m);
      maxPrecipitation = Math.max(maxPrecipitation, weather.precipitation_mm);
      maxTurbulence = Math.max(maxTurbulence, weather.turbulence_index);
      maxWind = Math.max(maxWind, weather.wind_speed_mps);
      windDirSum += weather.wind_dir_deg || 0;
      maxCloud = Math.max(maxCloud, weather.cloud_cover_pct);
      maxPressureAnomaly = Math.max(maxPressureAnomaly, weather.pressure_anomaly_hpa);
      temperatureSum += Number.isFinite(weather.temperature_c) ? weather.temperature_c : weatherTemperature(weather, point.altitude_m);
      humiditySum += Number.isFinite(weather.relative_humidity_pct) ? weather.relative_humidity_pct : weatherHumidity(weather);
      densitySum += airDensity(weather, point.altitude_m);
      pressureSum += weather.pressure_hpa;
      pressureDeltaSum += weather.pressure_delta_hpa;
    }
    return {
      precipitation_mm: maxPrecipitation,
      turbulence_index: maxTurbulence,
      wind_speed_mps: maxWind,
      wind_dir_deg: windDirSum / sampleCount,
      cloud_cover_pct: maxCloud,
      pressure_anomaly_hpa: maxPressureAnomaly,
      temperature_c: temperatureSum / sampleCount,
      relative_humidity_pct: humiditySum / sampleCount,
      air_density_kgm3: densitySum / sampleCount,
      pressure_hpa: pressureSum / sampleCount,
      pressure_delta_hpa: pressureDeltaSum / sampleCount,
    };
  }

  function buildRouteWeatherSegments(route) {
    const waypoints = route?.waypoints || [];
    const segments = [];
    for (let index = 1; index < waypoints.length; index += 1) {
      const start = waypoints[index - 1];
      const end = waypoints[index];
      const distanceM = Cesium.Cartesian3.distance(waypointCartesian(start), waypointCartesian(end));
      const sliceCount = Math.max(1, Math.ceil(distanceM / ROUTE_SEGMENT_STEP_M));
      for (let sliceIndex = 0; sliceIndex < sliceCount; sliceIndex += 1) {
        const pieceStart = interpolateWaypoint(start, end, sliceIndex / sliceCount);
        const pieceEnd = interpolateWaypoint(start, end, (sliceIndex + 1) / sliceCount);
        const weather = sampleWeatherForSegment(pieceStart, pieceEnd);
        segments.push({ start: pieceStart, end: pieceEnd, weather, category: classifyWeatherSegment(weather) });
      }
    }
    return segments;
  }

  function mergeConditionSpans(segments, category, predicate) {
    const spans = [];
    segments.forEach((segment, segmentIndex) => {
      if (!predicate(segment.weather, segment)) return;
      const previous = spans[spans.length - 1];
      if (previous && previous.category === category && previous.lastSegmentIndex === segmentIndex - 1) {
        previous.end = segment.end;
        previous.lastSegmentIndex = segmentIndex;
        previous.maxPrecipitation = Math.max(previous.maxPrecipitation, segment.weather.precipitation_mm);
        previous.maxTurbulence = Math.max(previous.maxTurbulence, segment.weather.turbulence_index);
        previous.maxWind = Math.max(previous.maxWind, segment.weather.wind_speed_mps);
        previous.maxCloud = Math.max(previous.maxCloud, segment.weather.cloud_cover_pct);
        previous.maxPressureAnomaly = Math.max(previous.maxPressureAnomaly, segment.weather.pressure_anomaly_hpa);
        previous.pressureHpa = (previous.pressureHpa + segment.weather.pressure_hpa) / 2;
        previous.pressureDeltaHpa = (previous.pressureDeltaHpa + segment.weather.pressure_delta_hpa) / 2;
        previous.windDirDeg = (previous.windDirDeg + segment.weather.wind_dir_deg) / 2;
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
        windDirDeg: segment.weather.wind_dir_deg,
        lastSegmentIndex: segmentIndex,
      });
    });
    return spans;
  }

  function buildRouteWeatherLayers(segments) {
    return {
      rain: mergeConditionSpans(segments, "rain", (_weather, segment) => segment.category.startsWith("rain")).slice(0, MAX_WEATHER_SPANS_PER_LAYER),
      wind: mergeConditionSpans(segments, "strong_wind", (weather) => weather.wind_speed_mps >= STRONG_WIND_THRESHOLD_MPS).slice(0, MAX_WEATHER_SPANS_PER_LAYER),
      pressure: mergeConditionSpans(segments, "pressure", (weather) => weather.pressure_anomaly_hpa >= PRESSURE_ANOMALY_THRESHOLD_HPA).slice(0, MAX_WEATHER_SPANS_PER_LAYER),
      cloud: mergeConditionSpans(segments, "cloud", (weather) => weather.cloud_cover_pct >= HIGH_CLOUD_THRESHOLD_PCT).slice(0, MAX_WEATHER_SPANS_PER_LAYER),
    };
  }

  function currentMeta() {
    return state.datasets[state.currentDatasetKey] || null;
  }

  function setInputsFromDefaultRoute(meta) {
    const route = meta?.default_route || [];
    if (!route.length) return;
    const start = route[0];
    const end = route[route.length - 1];
    $("rs-start-lat").value = start.lat;
    $("rs-start-lon").value = start.lon;
    $("rs-end-lat").value = end.lat;
    $("rs-end-lon").value = end.lon;
    $("rs-start-alt").value = start.altitude_m || 120;
    $("rs-end-alt").value = end.altitude_m || 120;
  }

  function updateControlAvailability() {
    const disabled = !state.datasetSupported;
    ["rs-start-lat", "rs-start-lon", "rs-end-lat", "rs-end-lon", "rs-start-alt", "rs-end-alt", "rs-min-altitude", "rs-candidate-count", "rs-cell-size", "rs-safety-clearance", "rs-max-altitude", "rs-use-default", "rs-pick-start", "rs-pick-end", "rs-plan", "rs-clear", "rs-fly-selected"].forEach((id) => {
      const node = $(id);
      if (node) node.disabled = disabled;
    });
  }

  function removeEntities() {
    state.entities.forEach((entity) => viewer.entities.remove(entity));
    state.entities = [];
  }

  function clearRoutes() {
    removeEntities();
    state.routes = [];
    state.selectedRouteId = "";
    state.isolatedRouteId = "";
    renderRouteList();
    updateRouteVisibility();
  }

  async function loadWeatherForCurrentDataset() {
    state.weather = null;
    state.weatherFieldIndex = null;
    if (!pageConfig.showWeather || !state.currentDatasetKey || !state.datasetSupported) {
      return;
    }
    const weather = await fetchJson(`/api/route-selection/weather?dataset_key=${encodeURIComponent(state.currentDatasetKey)}`);
    state.weather = weather;
    state.weatherFieldIndex = createWeatherFieldIndex(weather);
  }

  function routeMaterial(colorCss, selected) {
    if (Cesium.PolylineOutlineMaterialProperty) {
      return new Cesium.PolylineOutlineMaterialProperty({
        color: Cesium.Color.fromCssColorString(colorCss).withAlpha(1.0),
        outlineColor: Cesium.Color.fromCssColorString(selected ? "#001f4d" : "#ffffff").withAlpha(selected ? 0.96 : 0.9),
        outlineWidth: selected ? 4 : 2,
      });
    }
    return new Cesium.ColorMaterialProperty(Cesium.Color.fromCssColorString(colorCss).withAlpha(1.0));
  }

  function routeHaloMaterial(selected) {
    return new Cesium.ColorMaterialProperty(
      Cesium.Color.fromCssColorString(ROUTE_HALO).withAlpha(selected ? 0.18 : 0.08)
    );
  }

  function routeTubeShape(radiusM, sides = 12) {
    return Array.from({ length: sides }, (_item, index) => {
      const angle = (Math.PI * 2 * index) / sides;
      return new Cesium.Cartesian2(Math.cos(angle) * radiusM, Math.sin(angle) * radiusM);
    });
  }

  function renderSpatialRouteBody(route, selected, colorCss, positions) {
    if (!pageConfig.showBuildings || positions.length < 2) return;
    const combinedMode = pageConfig.showWeather;
    const bodyColor = combinedMode ? "#00b894" : colorCss;
    const outlineColor = combinedMode ? (selected ? "#063f34" : "#24584e") : (selected ? "#052653" : "#26343f");
    const bodyAlpha = combinedMode ? (selected ? 0.34 : 0.18) : (selected ? 0.92 : 0.74);
    const outlineAlpha = combinedMode ? (selected ? 0.58 : 0.32) : (selected ? 0.92 : 0.62);
    const radiusM = combinedMode ? (selected ? 6.2 : 3.2) : (selected ? 3.6 : 2.4);
    const tube = viewer.entities.add({
      polylineVolume: {
        positions,
        shape: routeTubeShape(radiusM),
        cornerType: Cesium.CornerType.ROUNDED,
        material: new Cesium.ColorMaterialProperty(Cesium.Color.fromCssColorString(bodyColor).withAlpha(bodyAlpha)),
        outline: true,
        outlineColor: Cesium.Color.fromCssColorString(outlineColor).withAlpha(outlineAlpha),
      },
      properties: {
        plugin_route_id: route.route_id,
        plugin_label: route.label,
        plugin_strategy: route.strategy,
        plugin_score: route.score,
        plugin_distance_m: route.distance_m,
        plugin_duration_s: route.estimated_duration_s,
        plugin_spatial_route_body: true,
      },
    });
    tube.__routeSelectionId = route.route_id;
    tube.__routeSelectionSelectable = true;
    state.entities.push(tube);
  }

  function updateRouteVisibility() {
    const show = $("layer-route")?.checked !== false;
    state.entities.forEach((entity) => {
      const visibleByRoute = !state.isolatedRouteId || entity.__routeSelectionId === state.isolatedRouteId;
      entity.show = show && visibleByRoute;
    });
  }

  function resolveSelectedRouteId(routes, preferredRouteId = state.selectedRouteId) {
    if (preferredRouteId && routes.some((route) => route.route_id === preferredRouteId)) {
      return preferredRouteId;
    }
    return routes[0]?.route_id || "";
  }

  function applyRouteSelection(routeId, isolate, { force = false } = {}) {
    const nextRouteId = resolveSelectedRouteId(state.routes, routeId);
    const nextIsolatedRouteId = isolate && nextRouteId ? nextRouteId : "";
    if (!force && nextRouteId === state.selectedRouteId && nextIsolatedRouteId === state.isolatedRouteId) {
      writeFeatureDetail(routeById(nextRouteId));
      return;
    }
    state.selectedRouteId = nextRouteId;
    state.isolatedRouteId = nextIsolatedRouteId;
    renderRouteList();
    renderEntities();
    writeFeatureDetail(routeById(state.selectedRouteId));
  }

  function eventToCanvasPosition(event) {
    const rect = viewer.canvas.getBoundingClientRect();
    return new Cesium.Cartesian2(event.clientX - rect.left, event.clientY - rect.top);
  }

  function pickRouteEntity(position) {
    const picked = viewer.scene.pick(position);
    const entity = picked?.id;
    if (!entity || !entity.__routeSelectionId || !entity.__routeSelectionSelectable) {
      return null;
    }
    return entity;
  }

  function routeFocusFromWaypoints(waypoints) {
    if (!waypoints?.length) return null;
    const coords = waypoints.map((point) => [point.lon, point.lat, point.altitude_m]);
    const lons = coords.map((coord) => coord[0]);
    const lats = coords.map((coord) => coord[1]);
    const positions = coords.map((coord) => Cesium.Cartesian3.fromDegrees(coord[0], coord[1], coord[2] || 100.0));
    let lengthM = 0.0;
    for (let idx = 1; idx < positions.length; idx += 1) {
      lengthM += Cesium.Cartesian3.distance(positions[idx - 1], positions[idx]);
    }
    const start = coords[0];
    const end = coords[coords.length - 1];
    const lat1 = Cesium.Math.toRadians(start[1]);
    const lat2 = Cesium.Math.toRadians(end[1]);
    const dLon = Cesium.Math.toRadians(end[0] - start[0]);
    const y = Math.sin(dLon) * Math.cos(lat2);
    const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLon);
    const headingDeg = (Cesium.Math.toDegrees(Math.atan2(y, x)) + 360.0) % 360.0;
    return {
      center: {
        lon: (Math.min(...lons) + Math.max(...lons)) / 2.0,
        lat: (Math.min(...lats) + Math.max(...lats)) / 2.0,
      },
      headingDeg,
      lengthM,
    };
  }

  function formatWindDirection(deg) {
    const dirs = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"];
    const index = Math.round((((Number(deg) || 0) % 360) / 45)) % dirs.length;
    return `${dirs[index]} ${formatNumber(deg, 0)}°`;
  }

  function headingBetweenPoints(start, end) {
    const lat1 = Cesium.Math.toRadians(Number(start.lat));
    const lat2 = Cesium.Math.toRadians(Number(end.lat));
    const dLon = Cesium.Math.toRadians(Number(end.lon) - Number(start.lon));
    const y = Math.sin(dLon) * Math.cos(lat2);
    const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLon);
    return (Cesium.Math.toDegrees(Math.atan2(y, x)) + 360.0) % 360.0;
  }

  function airDensity(weather, altitudeM = 0) {
    if (Number.isFinite(weather?.air_density_kgm3)) return weather.air_density_kgm3;
    const tempK = Math.max(180, weatherTemperature(weather, altitudeM) + 273.15);
    const pressurePa = Math.max(1000, Number(weather?.pressure_hpa || 1013.25) * 100);
    return pressurePa / (287.05 * tempK);
  }

  function routeWindComponents(weather, headingDeg = 0) {
    if (Number.isFinite(weather?.headwind_mps) && Number.isFinite(weather?.crosswind_mps)) {
      return { headwind_mps: weather.headwind_mps, crosswind_mps: weather.crosswind_mps };
    }
    const speed = Number(weather?.wind_speed_mps || 0);
    const rel = Cesium.Math.toRadians(((Number(weather?.wind_dir_deg || weather?.wind_direction_deg || 0) - Number(headingDeg || 0)) + 360) % 360);
    return {
      headwind_mps: speed * Math.cos(rel),
      crosswind_mps: Math.abs(speed * Math.sin(rel)),
    };
  }

  function weatherStateLabel(weather) {
    if (!weather) return "等待气象数据";
    if (weather.turbulence_index >= 0.46) return "强对流 / 垂直气流";
    if (weather.precipitation_mm >= RAIN_HEAVY_THRESHOLD_MM) return "强降雨";
    if (weather.precipitation_mm >= RAIN_LIGHT_THRESHOLD_MM) return "降雨";
    if (weather.wind_speed_mps >= STRONG_WIND_THRESHOLD_MPS) return "强风";
    if (weather.cloud_cover_pct >= HIGH_CLOUD_THRESHOLD_PCT) return "高云量";
    return "晴好";
  }

  function weatherTemperature(weather, altitudeM) {
    if (Number.isFinite(weather?.temperature_c)) return weather.temperature_c;
    return 22 - Number(altitudeM || 0) * 0.0065 - Math.min(5, Number(weather?.cloud_cover_pct || 0) / 28);
  }

  function weatherHumidity(weather) {
    if (Number.isFinite(weather?.relative_humidity_pct)) return weather.relative_humidity_pct;
    return Math.max(38, Math.min(98, 48 + Number(weather?.cloud_cover_pct || 0) * 0.36 + Number(weather?.precipitation_mm || 0) * 16));
  }

  function updateWeatherInspector(point, weather, progressPct = 0) {
    if (!pageConfig.showWeather) return;
    const stateNode = $("rs-weather-state");
    const titleNode = $("rs-weather-title");
    const pressureNode = $("rs-weather-pressure");
    const windNode = $("rs-weather-wind");
    const tempNode = $("rs-weather-temp");
    const humidityNode = $("rs-weather-humidity");
    const densityNode = $("rs-weather-density");
    const routeWindNode = $("rs-weather-route-wind");
    const noteNode = $("rs-weather-note");
    if (!weather || !stateNode) return;
    const components = routeWindComponents(weather, point?.heading_deg || 0);
    stateNode.textContent = `巡航进度 ${formatNumber(progressPct, 0)}%`;
    titleNode.textContent = weatherStateLabel(weather);
    pressureNode.textContent = `${formatNumber(weather.pressure_hpa, 1)} hPa`;
    windNode.textContent = `${formatNumber(weather.wind_speed_mps, 1)} m/s | ${formatWindDirection(weather.wind_dir_deg || weather.wind_direction_deg || 0)}`;
    tempNode.textContent = `${formatNumber(weatherTemperature(weather, point?.altitude_m), 1)} ℃`;
    humidityNode.textContent = `${formatNumber(weatherHumidity(weather), 0)}% | 云 ${formatNumber(weather.cloud_cover_pct, 0)}%`;
    if (densityNode) densityNode.textContent = `${formatNumber(airDensity(weather, point?.altitude_m), 3)} kg/m3`;
    if (routeWindNode) routeWindNode.textContent = `${formatNumber(components.headwind_mps, 1)} / ${formatNumber(components.crosswind_mps, 1)} m/s`;
    noteNode.textContent = `高度 ${formatNumber(point?.altitude_m || 0, 0)} m，航向 ${formatNumber(point?.heading_deg || 0, 0)}°，降雨 ${formatNumber(weather.precipitation_mm, 2)} mm，湍流 ${formatNumber(weather.turbulence_index, 2)}。`;
  }

  function pointAlongRoute(route, progress) {
    const waypoints = route?.waypoints || [];
    if (waypoints.length < 2) return waypoints[0] || null;
    const distances = [];
    let total = 0;
    for (let idx = 1; idx < waypoints.length; idx += 1) {
      const distance = Cesium.Cartesian3.distance(waypointCartesian(waypoints[idx - 1]), waypointCartesian(waypoints[idx]));
      distances.push(distance);
      total += distance;
    }
    let remaining = Math.max(0, Math.min(1, progress)) * total;
    for (let idx = 0; idx < distances.length; idx += 1) {
      if (remaining <= distances[idx]) {
        return {
          ...interpolateWaypoint(waypoints[idx], waypoints[idx + 1], distances[idx] <= 0 ? 0 : remaining / distances[idx]),
          heading_deg: headingBetweenPoints(waypoints[idx], waypoints[idx + 1]),
        };
      }
      remaining -= distances[idx];
    }
    return {
      ...waypoints[waypoints.length - 1],
      heading_deg: headingBetweenPoints(waypoints[waypoints.length - 2], waypoints[waypoints.length - 1]),
    };
  }

  function ensureCruiseTick() {
    if (state.cruiseTickBound) return;
    viewer.clock.onTick.addEventListener(() => {
      const route = routeById(state.selectedRouteId);
      if (!route || !state.weatherFieldIndex) return;
      if (!state.cruiseStartMs) state.cruiseStartMs = performance.now();
      const progress = ((performance.now() - state.cruiseStartMs) % 26000) / 26000;
      const point = pointAlongRoute(route, progress);
      if (!point) return;
      const weather = interpolateWeatherAtPoint(point.lon, point.lat, point.altitude_m);
      state.currentWeatherSample = weather;
      updateWeatherInspector(point, weather, progress * 100);
    });
    state.cruiseTickBound = true;
  }

  function flyToRoute(route) {
    if (!route) return;
    const focus = routeFocusFromWaypoints(route.waypoints);
    if (!focus) return;
    const target = Cesium.Cartesian3.fromDegrees(focus.center.lon, focus.center.lat, 0.0);
    const offset = new Cesium.HeadingPitchRange(
      Cesium.Math.toRadians(0.0),
      Cesium.Math.toRadians(-82.0),
      Math.max(980.0, Math.min(5200.0, focus.lengthM * 0.95))
    );
    viewer.camera.flyToBoundingSphere(new Cesium.BoundingSphere(target, Math.max(120.0, focus.lengthM * 0.08)), {
      offset,
      duration: 1.1,
    });
    ensureCruiseTick();
  }

  function writeFeatureDetail(route) {
    const node = $("feature-detail");
    if (!node || !route) return;
    const payload = {
      route_id: route.route_id,
      label: route.label,
      strategy: route.strategy,
      score: route.score,
      topsis_score: route.topsis_score,
      base_cost: route.base_cost,
      robustness_score: route.robustness_score,
      reliability_ratio: route.reliability_ratio,
      duration_p95_s: route.duration_p95_s,
      expected_delay_ratio: route.expected_delay_ratio,
      distance_m: route.distance_m,
      estimated_duration_s: route.estimated_duration_s,
      average_connectivity_index: route.average_connectivity_index,
      minimum_connectivity_index: route.minimum_connectivity_index,
      average_reachability_index: route.average_reachability_index,
      corridor_diversity_index: route.corridor_diversity_index,
      waypoint_count: route.waypoint_count,
    };
    if (pageConfig.showWeather) {
      payload.max_wind_speed_mps = route.max_wind_speed_mps;
      payload.max_headwind_mps = route.max_headwind_mps;
      payload.max_crosswind_mps = route.max_crosswind_mps;
      payload.max_turbulence_index = route.max_turbulence_index;
      payload.max_precipitation_mm = route.max_precipitation_mm;
      payload.max_weather_risk_score = route.max_weather_risk_score;
      payload.high_risk_exposure_ratio = route.high_risk_exposure_ratio;
    }
    if (pageConfig.showBuildings) {
      payload.average_urban_density = route.average_urban_density;
      payload.overflight_building_count = route.overflight_building_count;
      payload.overflight_exposure_index = route.overflight_exposure_index;
    }
    node.textContent = `候选航线\n${JSON.stringify(payload, null, 2)}`;
  }

  function animatedColor(fromColorCss, toColorCss, alpha, offset = 0) {
    return new Cesium.CallbackProperty(() => {
      const t = 0.5 + 0.5 * Math.sin(performance.now() * 0.008 + offset);
      const from = Cesium.Color.fromCssColorString(fromColorCss);
      const to = Cesium.Color.fromCssColorString(toColorCss);
      return Cesium.Color.lerp(from, to, t, new Cesium.Color()).withAlpha(alpha);
    }, false);
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
    canvas.width = 92;
    canvas.height = 92;
    const ctx = canvas.getContext("2d");
    const heavy = category === "rain_heavy";
    return {
      category,
      canvas,
      draw(now) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        drawRoundedRect(ctx, 8, 8, 76, 66, 18);
        ctx.fillStyle = heavy ? "rgba(4, 20, 58, 0.78)" : "rgba(8, 31, 68, 0.68)";
        ctx.fill();
        ctx.strokeStyle = heavy ? "rgba(92, 180, 255, 0.92)" : "rgba(130, 215, 255, 0.82)";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        ctx.fillStyle = "rgba(238, 248, 255, 0.96)";
        ctx.beginPath();
        ctx.arc(34, 31, 10, Math.PI * 0.9, Math.PI * 2.1);
        ctx.arc(46, 25, 12, Math.PI, Math.PI * 2);
        ctx.arc(59, 32, 10, Math.PI * 1.05, Math.PI * 1.95);
        ctx.quadraticCurveTo(66, 45, 28, 44);
        ctx.quadraticCurveTo(22, 39, 34, 31);
        ctx.closePath();
        ctx.fill();

        ctx.lineCap = "round";
        ctx.lineWidth = heavy ? 3.2 : 2.4;
        const dropCount = heavy ? 8 : 5;
        const speed = heavy ? 0.2 : 0.14;
        for (let idx = 0; idx < dropCount; idx += 1) {
          const laneX = 21 + idx * (heavy ? 6 : 10);
          const phase = (now * speed + idx * 13) % 58;
          const y = 33 + phase;
          ctx.strokeStyle = heavy ? "rgba(83, 170, 255, 0.96)" : "rgba(120, 215, 255, 0.9)";
          ctx.beginPath();
          ctx.moveTo(laneX, y - (heavy ? 12 : 9));
          ctx.lineTo(laneX - 2, y);
          ctx.stroke();
        }
      },
    };
  }

  function weatherColorForSegment(segment) {
    const weather = segment.weather || {};
    if (segment.category?.startsWith("rain")) return ["#0a56ff", "#7fd7ff", 0.58];
    if (weather.wind_speed_mps >= STRONG_WIND_THRESHOLD_MPS) return ["#00d5ff", "#ffffff", 0.48];
    if (weather.cloud_cover_pct >= HIGH_CLOUD_THRESHOLD_PCT) return ["#dcecff", "#8fb6d8", 0.42];
    if (weather.pressure_anomaly_hpa >= PRESSURE_ANOMALY_THRESHOLD_HPA) return ["#ff7a4f", "#ffd0aa", 0.42];
    return ["#35e7c5", "#eafffb", 0.34];
  }

  function weatherRiskScore(weather) {
    if (!weather) return 0;
    const rain = Math.min(1, Number(weather.precipitation_mm || 0) / 2.2);
    const convective = Math.min(1, Number(weather.turbulence_index || 0) / 0.72);
    const wind = Math.min(1, Number(weather.wind_speed_mps || 0) / 14);
    const cloud = Math.min(1, Number(weather.cloud_cover_pct || 0) / 100);
    const pressure = Math.min(1, Number(weather.pressure_anomaly_hpa || 0) / 8);
    return Math.max(0, Math.min(1, rain * 0.34 + convective * 0.28 + wind * 0.18 + cloud * 0.12 + pressure * 0.08));
  }

  function riskColor(score, alpha = 0.42) {
    if (score < 0.16) return Cesium.Color.fromCssColorString("#74b9ff").withAlpha(alpha);
    if (score >= 0.72) return Cesium.Color.fromCssColorString(RISK_RED).withAlpha(alpha);
    if (score >= 0.46) return Cesium.Color.fromCssColorString(RISK_ORANGE).withAlpha(alpha);
    return Cesium.Color.fromCssColorString(RISK_YELLOW).withAlpha(alpha);
  }

  function riskCssColor(score) {
    if (score < 0.16) return "#74b9ff";
    if (score >= 0.72) return RISK_RED;
    if (score >= 0.46) return RISK_ORANGE;
    return RISK_YELLOW;
  }

  function precipitationHeatColor(precipitationMm) {
    const value = Number(precipitationMm || 0);
    if (value < 0.05) return Cesium.Color.TRANSPARENT;
    if (value < 0.35) return Cesium.Color.fromCssColorString("#bcd9eb").withAlpha(0.18);
    if (value < 0.8) return Cesium.Color.fromCssColorString("#9cc7e2").withAlpha(0.24);
    if (value < 1.2) return Cesium.Color.fromCssColorString("#78afd4").withAlpha(0.31);
    if (value < 1.8) return Cesium.Color.fromCssColorString("#5b96c5").withAlpha(0.38);
    if (value < 2.5) return Cesium.Color.fromCssColorString("#3f7bb2").withAlpha(0.45);
    return Cesium.Color.fromCssColorString("#2e659e").withAlpha(0.52);
  }

  function inferGridHalfSteps(samples) {
    const lons = [...new Set(samples.map((sample) => Number(sample.lon)).filter(Number.isFinite))].sort((a, b) => a - b);
    const lats = [...new Set(samples.map((sample) => Number(sample.lat)).filter(Number.isFinite))].sort((a, b) => a - b);
    const medianStep = (values, fallback) => {
      const steps = [];
      for (let idx = 1; idx < values.length; idx += 1) {
        const step = Math.abs(values[idx] - values[idx - 1]);
        if (step > 1e-8) steps.push(step);
      }
      if (!steps.length) return fallback;
      steps.sort((a, b) => a - b);
      return steps[Math.floor(steps.length / 2)];
    };
    return {
      lonHalfStep: medianStep(lons, 0.004) * 0.55,
      latHalfStep: medianStep(lats, 0.004) * 0.55,
    };
  }

  function renderPrecipitationAreaHeatmap(routeId) {
    if (!state.weatherFieldIndex?.altitudeLevels?.length) return;
    const lowestLevel = state.weatherFieldIndex.altitudeLevels[0];
    const samples = (state.weatherFieldIndex.byAltitude.get(lowestLevel) || [])
      .filter((sample) => Number(sample.precipitation_mm || 0) >= 0.05);
    if (!samples.length) return;
    const { lonHalfStep, latHalfStep } = inferGridHalfSteps(samples);
    samples.forEach((sample) => {
      const precipitation = Number(sample.precipitation_mm || 0);
      const color = precipitationHeatColor(precipitation);
      if (color.alpha <= 0) return;
      const entity = viewer.entities.add({
        rectangle: {
          coordinates: Cesium.Rectangle.fromDegrees(
            sample.lon - lonHalfStep,
            sample.lat - latHalfStep,
            sample.lon + lonHalfStep,
            sample.lat + latHalfStep
          ),
          height: 4,
          material: new Cesium.ColorMaterialProperty(color),
          outline: false,
        },
        properties: {
          plugin_route_id: routeId,
          plugin_weather_category: "precipitation_area_heatmap",
          plugin_precipitation_mm: precipitation,
        },
      });
      addWeatherEntity(entity, routeId);
    });
  }

  function riskMeaning(score) {
    if (score < 0.46) return "moderate";
    if (score < 0.72) return "elevated";
    return "high";
  }

  function buildRiskSpans(segments) {
    const spans = [];
    segments.forEach((segment, segmentIndex) => {
      const score = weatherRiskScore(segment.weather);
      if (score < 0.18) return;
      const previous = spans[spans.length - 1];
      if (previous && previous.lastSegmentIndex === segmentIndex - 1) {
        previous.points.push(segment.end);
        previous.maxScore = Math.max(previous.maxScore, score);
        previous.scoreSum += score;
        previous.count += 1;
        previous.lastSegmentIndex = segmentIndex;
        return;
      }
      spans.push({
        points: [segment.start, segment.end],
        maxScore: score,
        scoreSum: score,
        count: 1,
        lastSegmentIndex: segmentIndex,
      });
    });
    return spans;
  }

  function riskCorridorPolygon(points, widthM, altitudeOffset = 10) {
    if (!points || points.length < 2) return [];
    const left = [];
    const right = [];
    points.forEach((point, index) => {
      const before = index === 0 ? point : points[index - 1];
      const after = index === points.length - 1 ? point : points[index + 1];
      const tangentStart = index === 0 ? point : before;
      const tangentEnd = index === points.length - 1 ? point : after;
      left.push(offsetWaypointSide(point, tangentStart, tangentEnd, widthM / 2));
      right.push(offsetWaypointSide(point, tangentStart, tangentEnd, -widthM / 2));
    });
    return left.concat(right.reverse()).map((point) => {
      return Cesium.Cartesian3.fromDegrees(point.lon, point.lat, Number(point.altitude_m || 0) + altitudeOffset);
    });
  }

  function renderRiskHeatIslands(route, segments) {
    const routeId = route.route_id;
    const spans = buildRiskSpans(segments);
    spans.forEach((span, spanIndex) => {
      const score = Math.max(span.maxScore, span.scoreSum / Math.max(1, span.count));
      [
        { width: 460, alpha: 0.16, height: 8, outline: false },
        { width: 320, alpha: 0.28, height: 16, outline: false },
        { width: 190, alpha: 0.46, height: 25, outline: true },
      ].forEach((band, bandIndex) => {
        const polygon = riskCorridorPolygon(span.points, band.width * (0.62 + score * 0.48), band.height);
        if (polygon.length < 4) return;
        const entity = viewer.entities.add({
          polygon: {
            hierarchy: new Cesium.PolygonHierarchy(polygon),
            perPositionHeight: true,
            material: new Cesium.ColorMaterialProperty(new Cesium.CallbackProperty(() => {
              const pulse = 0.88 + 0.12 * Math.sin(performance.now() * 0.003 + spanIndex + bandIndex);
              return riskColor(score, band.alpha * pulse);
            }, false)),
            outline: band.outline,
            outlineColor: riskColor(score, 0.76),
          },
          properties: {
            plugin_route_id: routeId,
            plugin_weather_risk_score: score,
            plugin_weather_risk_meaning: riskMeaning(score),
          },
        });
        addWeatherEntity(entity, routeId);
      });
    });
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

  function animationByCategory(category, factory) {
    let animation = state.weatherAnimations.find((item) => item.category === category);
    if (!animation) {
      animation = factory();
      state.weatherAnimations.push(animation);
    }
    if (!state.weatherAnimationBound) {
      viewer.clock.onTick.addEventListener(() => {
        const now = performance.now();
        state.weatherAnimations.forEach((item) => item.draw?.(now));
      });
      state.weatherAnimationBound = true;
    }
    return animation;
  }

  function spanPoint(span, t, altitudeOffset = 0) {
    const point = interpolateWaypoint(span.start, span.end, t);
    return { ...point, altitude_m: Number(point.altitude_m || 0) + altitudeOffset };
  }

  function spanBearingRad(span) {
    const focus = routeFocusFromWaypoints([
      { lon: span.start.lon, lat: span.start.lat, altitude_m: span.start.altitude_m },
      { lon: span.end.lon, lat: span.end.lat, altitude_m: span.end.altitude_m },
    ]);
    return Cesium.Math.toRadians(90 - (focus?.headingDeg || 0));
  }

  function addWeatherEntity(entity, routeId) {
    entity.__routeSelectionId = routeId;
    entity.__routeSelectionSelectable = false;
    state.entities.push(entity);
  }

  function addBillboardWeatherEntity(routeId, position, image, options = {}) {
    const entity = viewer.entities.add({
      position,
      billboard: {
        image,
        scale: options.scale ?? 0.65,
        rotation: options.rotation ?? 0,
        verticalOrigin: Cesium.VerticalOrigin.CENTER,
        horizontalOrigin: Cesium.HorizontalOrigin.CENTER,
        pixelOffset: options.pixelOffset || Cesium.Cartesian2.ZERO,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
      label: options.text
        ? {
            text: options.text,
            font: '800 12px "Avenir Next", "PingFang SC", sans-serif',
            fillColor: Cesium.Color.WHITE,
            outlineColor: Cesium.Color.fromCssColorString("#07140f"),
            outlineWidth: 3,
            style: Cesium.LabelStyle.FILL_AND_OUTLINE,
            showBackground: true,
            backgroundColor: Cesium.Color.fromCssColorString("#07140f").withAlpha(0.68),
            pixelOffset: new Cesium.Cartesian2(0, -34),
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
          }
        : undefined,
    });
    addWeatherEntity(entity, routeId);
    return entity;
  }

  function renderSelectedRouteTube(route, routeIndex) {
    const routeId = route.route_id;
    const positions = route.waypoints.map((point) => Cesium.Cartesian3.fromDegrees(point.lon, point.lat, point.altitude_m));
    const tubeShape = Array.from({ length: 16 }, (_item, index) => {
      const angle = (Math.PI * 2 * index) / 16;
      return new Cesium.Cartesian2(Math.cos(angle) * 9.5, Math.sin(angle) * 9.5);
    });
    const tube = viewer.entities.add({
      polylineVolume: {
        positions,
        shape: tubeShape,
        cornerType: Cesium.CornerType.ROUNDED,
        material: new Cesium.ColorMaterialProperty(Cesium.Color.fromCssColorString(ELECTRIC_BLUE).withAlpha(0.96)),
        outline: true,
        outlineColor: Cesium.Color.fromCssColorString("#001f4d").withAlpha(0.96),
      },
      properties: {
        plugin_route_id: routeId,
        plugin_route_tube: true,
      },
    });
    addWeatherEntity(tube, routeId);
    const centerLine = viewer.entities.add({
      polyline: {
        positions,
        width: 5,
        material: new Cesium.ColorMaterialProperty(Cesium.Color.WHITE.withAlpha(0.95)),
      },
    });
    addWeatherEntity(centerLine, routeId);
  }

  function renderWaypointGuides(route) {
    const routeId = route.route_id;
    const sampleEvery = Math.max(1, Math.ceil((route.waypoints?.length || 1) / 16));
    route.waypoints.forEach((point, pointIndex) => {
      if (pointIndex % sampleEvery !== 0 && pointIndex !== route.waypoints.length - 1) return;
      const ground = Cesium.Cartesian3.fromDegrees(point.lon, point.lat, 0);
      const air = Cesium.Cartesian3.fromDegrees(point.lon, point.lat, point.altitude_m);
      const guide = viewer.entities.add({
        polyline: {
          positions: [ground, air],
          width: 1.5,
          material: new Cesium.PolylineDashMaterialProperty({
            color: Cesium.Color.fromCssColorString("#dfe6e9").withAlpha(0.62),
            dashLength: 12,
          }),
        },
        point: {
          pixelSize: 8,
          color: Cesium.Color.fromCssColorString(ELECTRIC_BLUE).withAlpha(0.95),
          outlineColor: Cesium.Color.WHITE.withAlpha(0.9),
          outlineWidth: 2,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
        position: air,
      });
      addWeatherEntity(guide, routeId);
    });
  }

  function renderRiskInfoCards(route, segments) {
    const routeId = route.route_id;
    const keySegments = [...segments]
      .map((segment, segmentIndex) => ({ segment, segmentIndex, score: weatherRiskScore(segment.weather) }))
      .filter((item) => item.score >= 0.18)
      .sort((a, b) => b.score - a.score)
      .reduce((picked, item) => {
        const minGap = Math.max(3, Math.ceil(segments.length / 8));
        if (picked.length < 3 && picked.every((chosen) => Math.abs(chosen.segmentIndex - item.segmentIndex) >= minGap)) {
          picked.push(item);
        }
        return picked;
      }, []);
    keySegments.sort((a, b) => a.segmentIndex - b.segmentIndex).forEach(({ segment, score }, index) => {
      const midpoint = interpolateWaypoint(segment.start, segment.end, 0.5);
      const side = offsetWaypointSide(midpoint, segment.start, segment.end, index % 2 ? -280 : 280);
      const anchor = Cesium.Cartesian3.fromDegrees(midpoint.lon, midpoint.lat, Number(midpoint.altitude_m || 0) + 18);
      const labelPoint = Cesium.Cartesian3.fromDegrees(side.lon, side.lat, Number(side.altitude_m || 0) + 154 + index * 26);
      const leader = viewer.entities.add({
        polyline: {
          positions: [anchor, labelPoint],
          width: 1.6,
          material: new Cesium.PolylineDashMaterialProperty({
            color: riskColor(score, 0.82),
            dashLength: 8,
          }),
        },
      });
      addWeatherEntity(leader, routeId);
      const card = viewer.entities.add({
        position: labelPoint,
        label: {
          text: `RISK ${formatNumber(score * 100, 0)}\nRAIN ${formatNumber(segment.weather.precipitation_mm, 1)}mm  WIND ${formatNumber(segment.weather.wind_speed_mps, 1)}m/s\nCLOUD ${formatNumber(segment.weather.cloud_cover_pct, 0)}%  TURB ${formatNumber(segment.weather.turbulence_index, 2)}`,
          font: '800 12px "Roboto Mono", "SFMono-Regular", Consolas, monospace',
          fillColor: Cesium.Color.fromCssColorString("#1f2d35"),
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 2,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          showBackground: true,
          backgroundColor: Cesium.Color.fromCssColorString("#ffffff").withAlpha(0.78),
          pixelOffset: Cesium.Cartesian2.ZERO,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
        point: {
          pixelSize: 7,
          color: riskColor(score, 0.96),
          outlineColor: Cesium.Color.WHITE.withAlpha(0.86),
          outlineWidth: 1,
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
      });
      addWeatherEntity(card, routeId);
    });
  }

  function windStreamColor(windSpeedMps, alpha = 0.74) {
    if (windSpeedMps >= STRONG_WIND_THRESHOLD_MPS) {
      return Cesium.Color.fromCssColorString("#ffffff").withAlpha(alpha);
    }
    if (windSpeedMps >= STRONG_WIND_THRESHOLD_MPS * 0.65) {
      return Cesium.Color.fromCssColorString("#b7f5ff").withAlpha(alpha);
    }
    return Cesium.Color.fromCssColorString("#8eefff").withAlpha(alpha * 0.88);
  }

  function addWindStreamline(routeId, anchor, wind, seed, options = {}) {
    const speed = Math.max(0.4, Number(wind?.wind_speed_mps || 0));
    const flow = windFlowUnit(wind);
    const lengthM = options.lengthM ?? (58 + Math.min(80, speed * 6));
    const travelM = options.travelM ?? (150 + Math.min(210, speed * 15));
    const altitudeM = options.altitudeM ?? 92;
    const streamEndpoints = () => {
      const phase = (seed + performance.now() * 0.00009 * (0.55 + speed / 8)) % 1;
      const centerOffsetM = (phase - 0.5) * travelM;
      return {
        tail: offsetWaypointByMeters(anchor, flow.east * (centerOffsetM - lengthM * 0.5), flow.north * (centerOffsetM - lengthM * 0.5), altitudeM),
        head: offsetWaypointByMeters(anchor, flow.east * (centerOffsetM + lengthM * 0.5), flow.north * (centerOffsetM + lengthM * 0.5), altitudeM + 3),
      };
    };
    const stream = viewer.entities.add({
      polyline: {
        positions: new Cesium.CallbackProperty(() => {
          const { tail, head } = streamEndpoints();
          return [
            Cesium.Cartesian3.fromDegrees(tail.lon, tail.lat, tail.altitude_m),
            Cesium.Cartesian3.fromDegrees(head.lon, head.lat, head.altitude_m),
          ];
        }, false),
        width: options.width ?? (speed >= STRONG_WIND_THRESHOLD_MPS ? 2.4 : 1.8),
        material: new Cesium.PolylineGlowMaterialProperty({
          glowPower: 0.18,
          taperPower: 0.88,
          color: windStreamColor(speed, options.alpha ?? 0.78),
        }),
      },
      properties: {
        plugin_route_id: routeId,
        plugin_weather_category: "wind_stream",
        plugin_wind_speed_mps: speed,
      },
    });
    addWeatherEntity(stream, routeId);
    if (options.showArrow) {
      const arrow = viewer.entities.add({
        polyline: {
          positions: new Cesium.CallbackProperty(() => {
            const { head } = streamEndpoints();
            const back = offsetWaypointByMeters(head, -flow.east * 22, -flow.north * 22, -1);
            const left = offsetWaypointByMeters(back, -flow.north * 8, flow.east * 8, 0);
            const right = offsetWaypointByMeters(back, flow.north * 8, -flow.east * 8, 0);
            return [
              Cesium.Cartesian3.fromDegrees(left.lon, left.lat, left.altitude_m),
              Cesium.Cartesian3.fromDegrees(head.lon, head.lat, head.altitude_m),
              Cesium.Cartesian3.fromDegrees(right.lon, right.lat, right.altitude_m),
            ];
          }, false),
          width: options.arrowWidth ?? 2.0,
          material: new Cesium.ColorMaterialProperty(windStreamColor(speed, options.arrowAlpha ?? 0.88)),
        },
        properties: {
          plugin_route_id: routeId,
          plugin_weather_category: "wind_stream_arrow",
          plugin_wind_speed_mps: speed,
        },
      });
      addWeatherEntity(arrow, routeId);
    }
  }

  function renderWindField(route, segments) {
    const routeId = route.route_id;
    const step = Math.max(1, Math.ceil(segments.length / MAX_WIND_FIELD_ARROWS));
    segments.filter((_segment, index) => index % step === 0).forEach((segment, index) => {
      const wind = segment.weather;
      [-130, -70, -15, 45, 105].forEach((offsetM, laneIndex) => {
        const base = offsetWaypointSide(interpolateWaypoint(segment.start, segment.end, 0.5), segment.start, segment.end, offsetM);
        addWindStreamline(routeId, base, wind, (index * 0.137 + laneIndex * 0.193) % 1, {
          altitudeM: 82 + laneIndex * 5,
          alpha: 0.72,
          showArrow: laneIndex === 2,
        });
      });
    });
  }

  function renderCloudField(route, segments) {
    const routeId = route.route_id;
    const animation = animationByCategory("cloud", createCloudAnimation);
    const step = Math.max(1, Math.ceil(segments.length / MAX_CLOUD_MARKERS));
    const clouds = segments.filter((_segment, index) => index % step === 0).slice(0, MAX_CLOUD_MARKERS);
    clouds.forEach((segment, index) => {
      const lane = index % 3 === 0 ? -135 : index % 3 === 1 ? 0 : 135;
      const side = offsetWaypointSide(interpolateWaypoint(segment.start, segment.end, 0.5), segment.start, segment.end, lane);
      const position = new Cesium.CallbackProperty(() => {
        const drift = Math.sin(performance.now() * 0.001 + index) * 18;
        const moved = offsetWaypointSide(side, segment.start, segment.end, drift);
        return Cesium.Cartesian3.fromDegrees(moved.lon, moved.lat, Number(moved.altitude_m || 0) + 120 + (index % 3) * 12);
      }, false);
      addBillboardWeatherEntity(routeId, position, animation.canvas, {
        scale: 0.46 + Math.min(0.28, Math.max(12, segment.weather.cloud_cover_pct) / 220),
        text: index % 5 === 0 ? `云量 ${formatNumber(segment.weather.cloud_cover_pct, 0)}%` : "",
      });
    });
  }

  function renderConvectionColumns(route, segments) {
    const routeId = route.route_id;
    const severe = [...segments]
      .sort((a, b) => b.weather.turbulence_index - a.weather.turbulence_index)
      .filter((segment) => segment.weather.turbulence_index >= 0.36)
      .slice(0, MAX_CONVECTION_COLUMNS);
    severe.forEach((segment, index) => {
      const midpoint = interpolateWaypoint(segment.start, segment.end, 0.5);
      const updraft = viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(midpoint.lon, midpoint.lat, Number(midpoint.altitude_m || 0) + 70),
        cylinder: {
          length: new Cesium.CallbackProperty(() => 130 + Math.sin(performance.now() * 0.006 + index) * 34, false),
          topRadius: new Cesium.CallbackProperty(() => 18 + Math.sin(performance.now() * 0.005 + index) * 5, false),
          bottomRadius: 42,
          material: new Cesium.ColorMaterialProperty(new Cesium.CallbackProperty(() => {
            const alpha = 0.34 + 0.24 * (0.5 + 0.5 * Math.sin(performance.now() * 0.007 + index));
            return Cesium.Color.fromCssColorString("#ff5b2f").withAlpha(alpha);
          }, false)),
          outline: true,
          outlineColor: Cesium.Color.fromCssColorString("#ffd2bd").withAlpha(0.78),
        },
        label: {
          text: "强对流 ↑↓",
          font: '900 13px "Avenir Next", "PingFang SC", sans-serif',
          fillColor: Cesium.Color.WHITE,
          outlineColor: Cesium.Color.fromCssColorString("#431207"),
          outlineWidth: 3,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          showBackground: true,
          backgroundColor: Cesium.Color.fromCssColorString("#9d2a12").withAlpha(0.76),
          pixelOffset: new Cesium.Cartesian2(0, -42),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
      });
      addWeatherEntity(updraft, routeId);
      for (let flow = 0; flow < 5; flow += 1) {
        const flowEntity = viewer.entities.add({
          position: new Cesium.CallbackProperty(() => {
            const t = (performance.now() * 0.00034 + flow / 5) % 1;
            const angle = t * Math.PI * 2 + flow;
            const radius = 34 + flow * 5;
            const latMeters = 111320;
            const lonMeters = latMeters * Math.cos(Cesium.Math.toRadians(midpoint.lat));
            return Cesium.Cartesian3.fromDegrees(
              midpoint.lon + Math.cos(angle) * radius / lonMeters,
              midpoint.lat + Math.sin(angle) * radius / latMeters,
              Number(midpoint.altitude_m || 0) + 28 + t * 150
            );
          }, false),
          point: {
            pixelSize: 8,
            color: Cesium.Color.fromCssColorString("#ff7a39").withAlpha(0.92),
            outlineColor: Cesium.Color.WHITE.withAlpha(0.65),
            outlineWidth: 1,
            disableDepthTestDistance: Number.POSITIVE_INFINITY,
          },
        });
        addWeatherEntity(flowEntity, routeId);
      }
    });
  }

  function renderRainSpan(span, route, routeIndex, spanIndex) {
    const routeId = route.route_id;
    const heavy = span.category === "rain_heavy";
    const dropCount = heavy ? 180 : 110;
    const laneCount = heavy ? 18 : 12;
    const laneSpacingM = heavy ? 4 : 6;
    const segmentOffsetM = PROFILE_SIDE_OFFSET_M + (spanIndex % 2 ? -12 : 12);
    for (let idx = 0; idx < dropCount; idx += 1) {
      const phase = ((idx * 0.37 + routeIndex * 0.13) % 1);
      const t = ((idx % Math.ceil(dropCount / laneCount)) + 0.5) / Math.ceil(dropCount / laneCount);
      const lane = (idx % laneCount) - (laneCount - 1) / 2;
      const anchor = offsetWaypointSide(
        spanPoint(span, Math.min(0.96, Math.max(0.04, t)), 0),
        span.start,
        span.end,
        segmentOffsetM + lane * laneSpacingM
      );
      const rainDrop = viewer.entities.add({
        polyline: {
          positions: new Cesium.CallbackProperty(() => {
            const cycle = (phase + performance.now() * (heavy ? 0.00105 : 0.00082)) % 1;
            const topAltitude = Number(anchor.altitude_m || 0) + 118 - cycle * 78;
            const bottomAltitude = topAltitude - (heavy ? 28 : 20);
            return [
              Cesium.Cartesian3.fromDegrees(anchor.lon, anchor.lat, topAltitude),
              Cesium.Cartesian3.fromDegrees(anchor.lon, anchor.lat, bottomAltitude),
            ];
          }, false),
          width: heavy ? 2.0 : 1.5,
          material: new Cesium.ColorMaterialProperty(
            Cesium.Color.fromCssColorString(heavy ? "#006eff" : "#00b8ff").withAlpha(heavy ? 0.92 : 0.78)
          ),
        },
        properties: {
          plugin_route_id: routeId,
          plugin_weather_category: span.category,
          plugin_precipitation_mm: span.maxPrecipitation,
        },
      });
      addWeatherEntity(rainDrop, routeId);
    }
  }

  function renderWindSpan(span, route, routeIndex, spanIndex) {
    const routeId = route.route_id;
    const positions = [waypointCartesian(spanPoint(span, 0, 22)), waypointCartesian(spanPoint(span, 1, 22))];
    const line = viewer.entities.add({
      polyline: {
        positions,
        width: 8,
        material: new Cesium.PolylineGlowMaterialProperty({
          glowPower: 0.42,
          color: animatedColor("#9df8ff", "#f7feff", 0.76, routeIndex + spanIndex),
        }),
      },
      properties: {
        plugin_route_id: routeId,
        plugin_weather_category: "strong_wind",
        plugin_wind_speed_mps: span.maxWind,
      },
    });
    addWeatherEntity(line, routeId);
    for (let idx = 0; idx < 8; idx += 1) {
      const t = (idx + 0.5) / 8;
      const side = offsetWaypointSide(spanPoint(span, t, 0), span.start, span.end, idx % 2 ? -55 : 55);
      addWindStreamline(routeId, side, { wind_speed_mps: span.maxWind, wind_dir_deg: span.windDirDeg || 0 }, (idx * 0.157 + spanIndex * 0.11) % 1, {
        altitudeM: 64 + (idx % 3) * 8,
        alpha: 0.88,
        width: 2.4,
        showArrow: idx % 2 === 0,
        arrowWidth: 2.3,
      });
    }
  }

  function renderPressureSpan(span, route, _routeIndex, spanIndex) {
    const routeId = route.route_id;
    const midpoint = spanPoint(span, 0.5, 44);
    const isHigh = span.pressureDeltaHpa >= 0;
    const color = isHigh ? "#ff6d4a" : "#4f8dff";
    const entity = viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(midpoint.lon, midpoint.lat, midpoint.altitude_m),
      cylinder: {
        length: 78,
        topRadius: 17,
        bottomRadius: 34,
        material: new Cesium.ColorMaterialProperty(new Cesium.CallbackProperty(() => {
          const alpha = 0.24 + 0.18 * (0.5 + 0.5 * Math.sin(performance.now() * 0.006 + spanIndex));
          return Cesium.Color.fromCssColorString(color).withAlpha(alpha);
        }, false)),
        outline: true,
        outlineColor: Cesium.Color.fromCssColorString(color).withAlpha(0.82),
      },
      label: {
        text: `${isHigh ? "高压" : "低压"} ${span.pressureDeltaHpa >= 0 ? "+" : ""}${formatNumber(span.pressureDeltaHpa, 1)}hPa`,
        font: '700 12px "Avenir Next", "PingFang SC", sans-serif',
        fillColor: Cesium.Color.WHITE,
        outlineColor: Cesium.Color.fromCssColorString("#09111f"),
        outlineWidth: 3,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        showBackground: true,
        backgroundColor: Cesium.Color.fromCssColorString(isHigh ? "#3a130c" : "#071b3d").withAlpha(0.74),
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        pixelOffset: new Cesium.Cartesian2(spanIndex % 2 === 0 ? -30 : 30, -38),
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
      },
    });
    addWeatherEntity(entity, routeId);
  }

  function renderCloudSpan(span, route) {
    const routeId = route.route_id;
    const animation = animationByCategory("cloud", createCloudAnimation);
    for (let idx = 0; idx < 2; idx += 1) {
      const point = spanPoint(span, (idx + 1) / 3, 58 + idx * 5);
      const cloud = viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(point.lon, point.lat, point.altitude_m),
        billboard: {
          image: animation.canvas,
          scale: 0.70 + Math.min(0.22, span.maxCloud / 280),
          pixelOffset: new Cesium.Cartesian2((idx - 0.5) * 28, -22),
          eyeOffset: new Cesium.Cartesian3(0, 0, -20),
          disableDepthTestDistance: Number.POSITIVE_INFINITY,
        },
        label: idx === 0
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
              pixelOffset: new Cesium.Cartesian2(0, 28),
              disableDepthTestDistance: Number.POSITIVE_INFINITY,
            }
          : undefined,
      });
      addWeatherEntity(cloud, routeId);
    }
  }

  function renderRouteWeatherLayers(route, routeIndex) {
    if (!pageConfig.showWeather || !state.weatherFieldIndex || route.route_id !== state.selectedRouteId) return;
    const segments = buildRouteWeatherSegments(route);
    renderPrecipitationAreaHeatmap(route.route_id);
    renderRiskHeatIslands(route, segments);
    renderSelectedRouteTube(route, routeIndex);
    renderWaypointGuides(route);
    renderRiskInfoCards(route, segments);
    renderWindField(route, segments);
    renderCloudField(route, segments);
    renderConvectionColumns(route, segments);
    const layers = buildRouteWeatherLayers(segments);
    layers.rain.forEach((span, spanIndex) => renderRainSpan(span, route, routeIndex, spanIndex));
    layers.wind.forEach((span, spanIndex) => renderWindSpan(span, route, routeIndex, spanIndex));
    layers.pressure.forEach((span, spanIndex) => renderPressureSpan(span, route, routeIndex, spanIndex));
    if (!layers.rain.length && segments.length) {
      const strongest = [...segments].sort((a, b) => b.weather.precipitation_mm - a.weather.precipitation_mm)[0];
      if (strongest?.weather?.precipitation_mm > 0.05) {
        renderRainSpan({
          category: strongest.category === "clear" ? "rain_light" : strongest.category,
          start: strongest.start,
          end: strongest.end,
          maxPrecipitation: strongest.weather.precipitation_mm,
        }, route, routeIndex, 0);
      }
    }
  }

  function renderEntities() {
    removeEntities();
    state.selectedRouteId = resolveSelectedRouteId(state.routes, state.selectedRouteId);
    if (state.isolatedRouteId && !routeById(state.isolatedRouteId)) {
      state.isolatedRouteId = "";
    }
    state.routes.forEach((route, routeIndex) => {
      const selected = route.route_id === state.selectedRouteId;
      const color = selected ? ELECTRIC_BLUE : ROUTE_COLORS[routeIndex % ROUTE_COLORS.length];
      const positions = route.waypoints.map((point) => Cesium.Cartesian3.fromDegrees(point.lon, point.lat, point.altitude_m));
      const spatialRouteMode = pageConfig.showBuildings && !pageConfig.showWeather;
      renderSpatialRouteBody(route, selected, color, positions);
      const halo = viewer.entities.add({
        polyline: {
          positions,
          width: spatialRouteMode ? (selected ? 5 : 3) : (selected ? 14 : 9),
          material: routeHaloMaterial(selected),
          arcType: Cesium.ArcType.NONE,
        },
      });
      halo.__routeSelectionId = route.route_id;
      halo.__routeSelectionSelectable = false;
      state.entities.push(halo);
      const polyline = viewer.entities.add({
        polyline: {
          positions,
          width: spatialRouteMode ? (selected ? 3 : 2) : (selected ? 7 : 4),
          material: routeMaterial(color, selected),
          arcType: Cesium.ArcType.NONE,
        },
        properties: {
          plugin_route_id: route.route_id,
          plugin_label: route.label,
          plugin_strategy: route.strategy,
          plugin_score: route.score,
          plugin_distance_m: route.distance_m,
          plugin_duration_s: route.estimated_duration_s,
        },
      });
      polyline.__routeSelectionId = route.route_id;
      polyline.__routeSelectionSelectable = true;
      state.entities.push(polyline);
      renderRouteWeatherLayers(route, routeIndex);
      route.waypoints.forEach((point, pointIndex) => {
        const entity = viewer.entities.add({
          position: Cesium.Cartesian3.fromDegrees(point.lon, point.lat, point.altitude_m),
          point: {
            pixelSize: selected ? 13 : 10,
            color: Cesium.Color.fromCssColorString(color),
            outlineColor: Cesium.Color.WHITE.withAlpha(0.96),
            outlineWidth: 3,
            disableDepthTestDistance: 0.0,
          },
          label: selected
            ? {
                text: `${pointIndex + 1}`,
                font: '700 13px "Avenir Next", "PingFang SC", sans-serif',
                fillColor: Cesium.Color.fromCssColorString("#0f201b"),
                outlineColor: Cesium.Color.WHITE,
                outlineWidth: 3,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                pixelOffset: new Cesium.Cartesian2(0, -14),
                disableDepthTestDistance: 0.0,
              }
            : undefined,
          properties: {
            plugin_route_id: route.route_id,
            plugin_waypoint_index: pointIndex + 1,
            plugin_altitude_m: point.altitude_m,
          },
        });
        entity.__routeSelectionId = route.route_id;
        entity.__routeSelectionSelectable = true;
        state.entities.push(entity);
      });
    });
    updateRouteVisibility();
  }

  function renderRouteList() {
    const container = $("route-selection-list");
    if (!container) return;
    if (!state.routes.length) {
      container.innerHTML = '<p class="small">尚未生成候选航线。</p>';
      return;
    }
    state.selectedRouteId = resolveSelectedRouteId(state.routes, state.selectedRouteId);
    if (state.isolatedRouteId && !routeById(state.isolatedRouteId)) {
      state.isolatedRouteId = "";
    }
    container.innerHTML = "";
    state.routes.forEach((route) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `route-selection-card${route.route_id === state.selectedRouteId ? " active" : ""}`;
      const buildingAvoidanceText = Number(route.overflight_building_count || 0) > 0
        ? `飞越建筑 ${formatNumber(route.overflight_building_count || 0, 0)}`
        : "绕开建筑投影";
      button.innerHTML = `
        <strong>${route.label}</strong>
        <div class="route-selection-meta">
          第 ${route.recommended_rank} 推荐｜${routeStrategyText(route)}<br>
          ${(route.distance_m / 1000.0).toFixed(2)} km｜${(route.estimated_duration_s / 60.0).toFixed(1)} min｜${routeAltitudeRangeText(route)}｜综合评分 ${formatNumber(route.score, 2)}｜鲁棒性 ${formatNumber(route.robustness_score, 2)}<br>
          ${pageConfig.showWeather ? `最大降雨 ${formatNumber(route.max_precipitation_mm || 0, 2)} mm｜最高风险 ${formatNumber((route.max_weather_risk_score || 0) * 100, 0)}｜红区暴露 ${formatNumber((route.high_risk_exposure_ratio || 0) * 100, 0)}%` : ""}
          ${PLANNING_MODE === "combined" ? `<br>建筑避障 ${buildingAvoidanceText}｜建筑暴露 ${formatNumber(route.overflight_exposure_index || 0, 2)}｜城区密度 ${formatNumber((route.average_urban_density || 0) * 100, 0)}%` : ""}
        </div>
      `;
      button.addEventListener("click", () => {
        const isolate = state.isolatedRouteId !== route.route_id;
        applyRouteSelection(route.route_id, isolate);
        flyToRoute(route);
      });
      container.appendChild(button);
    });
  }

  function currentPlanPayload() {
    return {
      dataset_key: state.currentDatasetKey,
      planning_mode: PLANNING_MODE,
      start_lat: Number($("rs-start-lat").value),
      start_lon: Number($("rs-start-lon").value),
      end_lat: Number($("rs-end-lat").value),
      end_lon: Number($("rs-end-lon").value),
      start_altitude_m: Number($("rs-start-alt").value),
      end_altitude_m: Number($("rs-end-alt").value),
      min_altitude_m: Number($("rs-min-altitude").value),
      candidate_count: Number($("rs-candidate-count").value),
      cell_m: Number($("rs-cell-size").value),
      safety_clearance_m: Number($("rs-safety-clearance").value),
      max_altitude_m: optionalNumber("rs-max-altitude"),
    };
  }

  async function planRoutes() {
    if (!state.datasetSupported) {
      setStatus("当前数据集不支持候选航线规划。");
      return;
    }
    const button = $("rs-plan");
    button.disabled = true;
    setStatus("正在生成候选航线，请稍候。");
    try {
      const payload = currentPlanPayload();
      const result = await fetchJson("/api/route-selection/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      state.routes = result.routes || [];
      state.selectedRouteId = state.routes[0]?.route_id || "";
      state.isolatedRouteId = "";
      if (pageConfig.showWeather && !state.weatherFieldIndex) {
        await loadWeatherForCurrentDataset();
      }
      renderRouteList();
      renderEntities();
      if (state.routes.length) {
        const first = routeById(state.selectedRouteId);
        flyToRoute(first);
        writeFeatureDetail(first);
      }
      const outputPath = result.output_paths?.json || "";
      setStatus(`已生成 ${state.routes.length} 条候选航线。${outputPath ? `结果：${outputPath}` : ""}`);
    } catch (error) {
      console.error(error);
      setStatus(`生成失败：${error.message || error}`);
    } finally {
      button.disabled = false;
    }
  }

  async function syncDatasetContext() {
    state.currentDatasetKey = currentDatasetKey();
    const meta = currentMeta();
    clearRoutes();
    if (!meta || !meta.supported) {
      state.datasetSupported = false;
      updateControlAvailability();
      setStatus(meta ? "当前数据集没有对应真实城市资产，无法做候选航线规划。" : "未找到数据集信息。");
      setHint("请切换到真实城市数据集后再生成候选航线。");
      return;
    }
    state.datasetSupported = true;
    updateControlAvailability();
    setInputsFromDefaultRoute(meta);
    try {
      await loadWeatherForCurrentDataset();
      setStatus(`当前数据集：${meta.display_name || meta.city_name}。可直接生成候选航线。`);
      setHint(`${pageConfig.hint} 点“场景点选起点/终点”后，在 3D 视图中左键取点。`);
    } catch (error) {
      console.error(error);
      setStatus(`天气场加载失败：${error.message || error}`);
    }
  }

  function togglePickMode(mode) {
    if (!state.datasetSupported) return;
    state.pickMode = state.pickMode === mode ? null : mode;
    const text = state.pickMode === "start" ? "正在点选起点。" : state.pickMode === "end" ? "正在点选终点。" : "点选模式已关闭。";
    setStatus(text);
  }

  function screenToLonLat(position) {
    let cartesian = viewer.scene.pickPosition(position);
    if (!Cesium.defined(cartesian)) {
      cartesian = viewer.camera.pickEllipsoid(position, Cesium.Ellipsoid.WGS84);
    }
    if (!Cesium.defined(cartesian)) return null;
    const cartographic = Cesium.Cartographic.fromCartesian(cartesian);
    return {
      lon: Cesium.Math.toDegrees(cartographic.longitude),
      lat: Cesium.Math.toDegrees(cartographic.latitude),
    };
  }

  function handleSceneClick(event) {
    const position = eventToCanvasPosition(event);
    if (state.pickMode) {
      const coord = screenToLonLat(position);
      if (!coord) {
        setStatus("未拾取到有效坐标，请点击地面或建筑区域。");
        return;
      }
      if (state.pickMode === "start") {
        $("rs-start-lat").value = coord.lat.toFixed(6);
        $("rs-start-lon").value = coord.lon.toFixed(6);
      } else {
        $("rs-end-lat").value = coord.lat.toFixed(6);
        $("rs-end-lon").value = coord.lon.toFixed(6);
      }
      state.pickMode = null;
      setStatus("已写入场景点坐标。");
      event.preventDefault();
      event.stopPropagation();
      return;
    }

    const routeEntity = pickRouteEntity(position);
    if (!routeEntity) {
      return;
    }
    applyRouteSelection(routeEntity.__routeSelectionId, true);
    viewer.selectedEntity = undefined;
    event.preventDefault();
    event.stopPropagation();
  }

  function bindEvents() {
    $("dataset-select")?.addEventListener("change", () => {
      setTimeout(() => {
        applyWorkbenchModeUi();
        syncDatasetContext().catch((error) => console.error(error));
      }, 20);
    });
    $("btn-load")?.addEventListener("click", () => {
      setStatus("正在加载默认世界。");
      setTimeout(() => {
        applyWorkbenchModeUi();
        syncDatasetContext().catch((error) => console.error(error));
      }, 900);
    });
    $("layer-route")?.addEventListener("change", updateRouteVisibility);
    $("rs-use-default")?.addEventListener("click", () => {
      const meta = currentMeta();
      if (meta) {
        setInputsFromDefaultRoute(meta);
        setStatus("已写入当前数据集默认起终点。");
      }
    });
    $("rs-pick-start")?.addEventListener("click", () => togglePickMode("start"));
    $("rs-pick-end")?.addEventListener("click", () => togglePickMode("end"));
    $("rs-plan")?.addEventListener("click", () => {
      planRoutes().catch((error) => {
        console.error(error);
        setStatus(`生成失败：${error.message || error}`);
        $("rs-plan").disabled = false;
      });
    });
    $("rs-clear")?.addEventListener("click", () => {
      clearRoutes();
      setStatus("已清除候选航线叠加层。");
    });
    $("rs-fly-selected")?.addEventListener("click", () => {
      flyToRoute(routeById(state.selectedRouteId));
    });
    viewer.canvas.addEventListener("click", handleSceneClick, true);
  }

  async function boot() {
    const backendChanged = applyWorkbenchModeUi();
    applyProfessionalWeatherStyle();
    injectStyles();
    injectPanel();
    bindEvents();
    if (backendChanged && !state.modeWorldReloaded && typeof window.loadWorld === "function") {
      state.modeWorldReloaded = true;
      setTimeout(() => {
        const reload = window.loadWorld();
        if (reload && typeof reload.catch === "function") {
          reload.catch((error) => console.error(error));
        }
      }, 0);
    }
    try {
      const payload = await fetchJson("/api/route-selection/datasets");
      state.datasets = Object.fromEntries((payload.datasets || []).map((item) => [item.dataset_key, item]));
      await syncDatasetContext();
      setTimeout(() => {
        const loadButton = $("btn-load");
        if (loadButton && $("world-name")?.textContent?.trim() === "未加载") {
          loadButton.click();
        }
      }, 100);
    } catch (error) {
      console.error(error);
      setStatus(`候选航线插件初始化失败：${error.message || error}`);
    }
  }

  boot();
})();
