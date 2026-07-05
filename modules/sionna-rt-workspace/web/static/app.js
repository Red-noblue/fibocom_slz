// Sionna RT 3D Radio Map 前端：加载点云与建筑 PLY，用 Canvas 绘制可旋转的三维无线电强度视图。
const DATA_ROOT = "../outputs/uav_city_3d_radio_map/manhattan_midtown";
const state = {
  summary: null,
  radio: null,
  mesh: null,
  heightFilter: "all",
  metric: "combined_signal_building",
  showLabels: false,
  yaw: -0.72,
  pitch: 0.72,
  zoom: 1,
  dragging: false,
  lastMouse: null,
  selectedPoint: null,
  projectedPoints: [],
};

const els = {
  status: document.querySelector("#status"),
  canvas: document.querySelector("#map-canvas"),
  heightFilter: document.querySelector("#height-filter"),
  metricSelect: document.querySelector("#metric-select"),
  showLabels: document.querySelector("#show-labels"),
  reloadBtn: document.querySelector("#reload-btn"),
  layerReadout: document.querySelector("#layer-readout"),
  city: document.querySelector("#stat-city"),
  rx: document.querySelector("#stat-rx"),
  buildings: document.querySelector("#stat-buildings"),
  paths: document.querySelector("#stat-paths"),
  min: document.querySelector("#stat-min"),
  max: document.querySelector("#stat-max"),
  txInfo: document.querySelector("#tx-info"),
  rxInfo: document.querySelector("#rx-info"),
};

const ctx = els.canvas.getContext("2d");

function fmt(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return Number(value).toFixed(digits);
}

function metricValue(point) {
  if (state.metric === "combined_signal_building") {
    return point.best_path_gain_db;
  }
  if (state.metric === "is_los_blocked_by_building") {
    return point.is_los_blocked_by_building ? 1 : 0;
  }
  const value = point[state.metric];
  if (value === null || value === undefined) return null;
  return Number(value);
}

function colorFor(value, min, max) {
  if (state.metric === "is_los_blocked_by_building") {
    return value === 1 ? "#ff4b3e" : "#1fc07a";
  }
  if (value === null || !Number.isFinite(value)) return "#9aa8a1";
  const t = max === min ? 0.5 : Math.max(0, Math.min(1, (value - min) / (max - min)));
  const signalStrength = state.metric === "combined_signal_building" || state.metric === "best_path_gain_db" || state.metric === "estimated_rx_power_dbm";
  const lossStrength = state.metric === "path_loss_db";
  if (signalStrength) {
    return `hsl(${215 - t * 190}, 82%, 55%)`;
  }
  if (lossStrength) {
    return `hsl(${25 + (1 - t) * 190}, 82%, 55%)`;
  }
  const hue = state.metric === "excess_loss_db" ? 145 - t * 120 : 215 - t * 190;
  return `hsl(${hue}, 82%, 55%)`;
}

function excessLossStyle(point, maxExcessLoss) {
  const loss = Number(point.excess_loss_db);
  if (!Number.isFinite(loss) || maxExcessLoss <= 0) {
    return { stroke: "rgba(255,255,255,0.82)", lineWidth: 1.5 };
  }
  const t = Math.max(0, Math.min(1, loss / maxExcessLoss));
  return {
    stroke: point.is_los_blocked_by_building ? "rgba(255,75,62,0.98)" : `hsla(${45 - t * 20}, 95%, 56%, ${0.62 + t * 0.33})`,
    lineWidth: 1.5 + t * 5.5,
  };
}

function selectedPoints() {
  const points = state.radio?.points || [];
  if (state.heightFilter === "all") return points;
  const z = Number(state.heightFilter);
  return points.filter((point) => Math.abs(point.rx_xyz_m[2] - z) < 1e-6);
}

function updateHeightOptions() {
  const heights = [...new Set((state.radio?.points || []).map((point) => point.rx_xyz_m[2]))].sort((a, b) => a - b);
  els.heightFilter.innerHTML = '<option value="all">全部高度</option>';
  heights.forEach((height) => {
    const option = document.createElement("option");
    option.value = String(height);
    option.textContent = `${fmt(height, 1)} m`;
    els.heightFilter.appendChild(option);
  });
}

function renderSummary() {
  const s = state.summary;
  const r = state.radio;
  els.city.textContent = s?.city || "--";
  els.rx.textContent = s?.rx_points ?? "--";
  els.buildings.textContent = s?.buildings_imported ?? "--";
  els.paths.textContent = s?.valid_path_count_total ?? "--";
  els.min.textContent = `${fmt(s?.global_path_gain_db_min, 2)} dB`;
  els.max.textContent = `${fmt(s?.global_path_gain_db_max, 2)} dB`;
  els.txInfo.textContent = JSON.stringify(r?.tx || {}, null, 2);
}

function parsePly(text) {
  const lines = text.trim().split(/\r?\n/);
  let vertexCount = 0;
  let faceCount = 0;
  let headerEnd = -1;
  lines.some((line, index) => {
    if (line.startsWith("element vertex")) vertexCount = Number(line.split(/\s+/)[2]);
    if (line.startsWith("element face")) faceCount = Number(line.split(/\s+/)[2]);
    if (line === "end_header") {
      headerEnd = index;
      return true;
    }
    return false;
  });
  if (headerEnd < 0 || !vertexCount) return { vertices: [], faces: [] };

  const vertices = lines.slice(headerEnd + 1, headerEnd + 1 + vertexCount).map((line) => {
    const [x, y, z] = line.trim().split(/\s+/).map(Number);
    return [x, y, z];
  });
  const faces = lines.slice(headerEnd + 1 + vertexCount, headerEnd + 1 + vertexCount + faceCount).map((line) => {
    const values = line.trim().split(/\s+/).map(Number);
    return values.slice(1, 1 + values[0]);
  });
  return { vertices, faces };
}

function collectSceneBounds(points, mesh) {
  const coords = [];
  points.forEach((point) => coords.push(point.rx_xyz_m));
  if (state.radio?.tx?.position_m) coords.push(state.radio.tx.position_m);
  (mesh?.vertices || []).forEach((vertex) => coords.push(vertex));
  if (!coords.length) return { center: [0, 0, 0], radius: 1 };

  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
  coords.forEach((coord) => {
    for (let i = 0; i < 3; i += 1) {
      min[i] = Math.min(min[i], coord[i]);
      max[i] = Math.max(max[i], coord[i]);
    }
  });
  const center = min.map((value, index) => (value + max[index]) / 2);
  const radius = Math.max(
    1,
    ...coords.map((coord) => Math.hypot(coord[0] - center[0], coord[1] - center[1], coord[2] - center[2])),
  );
  return { center, radius };
}

function rotatePoint(coord, bounds) {
  const x = coord[0] - bounds.center[0];
  const y = coord[1] - bounds.center[1];
  const z = coord[2] - bounds.center[2];
  const cy = Math.cos(state.yaw);
  const sy = Math.sin(state.yaw);
  const cp = Math.cos(state.pitch);
  const sp = Math.sin(state.pitch);
  const x1 = x * cy - y * sy;
  const y1 = x * sy + y * cy;
  const z1 = z;
  return [x1, y1 * cp - z1 * sp, y1 * sp + z1 * cp];
}

function project(coord, bounds, width, height) {
  const [x, y, z] = rotatePoint(coord, bounds);
  const cameraDistance = bounds.radius * 4.5;
  const depth = cameraDistance - z;
  const perspective = cameraDistance / Math.max(bounds.radius * 0.35, depth);
  const scale = Math.min(width, height) * 0.43 * state.zoom / bounds.radius;
  return {
    x: width / 2 + x * scale * perspective,
    y: height / 2 - y * scale * perspective,
    depth: z,
    perspective,
  };
}

function resizeCanvas() {
  const rect = els.canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  els.canvas.width = Math.max(1, Math.round(rect.width * dpr));
  els.canvas.height = Math.max(1, Math.round(rect.height * dpr));
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function drawLine(a, b, bounds, width, height, style = "rgba(255,255,255,0.12)", lineWidth = 1) {
  const pa = project(a, bounds, width, height);
  const pb = project(b, bounds, width, height);
  ctx.strokeStyle = style;
  ctx.lineWidth = lineWidth;
  ctx.beginPath();
  ctx.moveTo(pa.x, pa.y);
  ctx.lineTo(pb.x, pb.y);
  ctx.stroke();
}

function drawSightLine(rxPoint, bounds, width, height) {
  const tx = state.radio?.tx?.position_m;
  if (!tx || !rxPoint) return;
  const style = rxPoint.is_los_blocked_by_building ? "rgba(255,75,62,0.88)" : "rgba(31,192,122,0.82)";
  ctx.save();
  ctx.setLineDash(rxPoint.is_los_blocked_by_building ? [8, 7] : []);
  drawLine(tx, rxPoint.rx_xyz_m, bounds, width, height, style, 3);
  ctx.restore();
}

function drawGround(bounds, width, height) {
  const step = Math.max(25, Math.round(bounds.radius / 4 / 10) * 10);
  const extent = Math.ceil(bounds.radius / step) * step;
  const z = 0;
  for (let value = -extent; value <= extent; value += step) {
    drawLine([value, -extent, z], [value, extent, z], bounds, width, height);
    drawLine([-extent, value, z], [extent, value, z], bounds, width, height);
  }
  drawLine([0, 0, z], [extent, 0, z], bounds, width, height, "rgba(216,111,44,0.72)", 2);
  drawLine([0, 0, z], [0, extent, z], bounds, width, height, "rgba(11,122,99,0.72)", 2);
}

function drawBuildings(bounds, width, height) {
  const mesh = state.mesh;
  if (!mesh?.faces?.length) return;
  ctx.strokeStyle = "rgba(206, 229, 221, 0.22)";
  ctx.lineWidth = 0.8;
  mesh.faces.forEach((face) => {
    const points = face.map((index) => project(mesh.vertices[index], bounds, width, height));
    ctx.beginPath();
    points.forEach((point, index) => {
      if (index === 0) ctx.moveTo(point.x, point.y);
      else ctx.lineTo(point.x, point.y);
    });
    ctx.closePath();
    ctx.stroke();
  });
}

function drawMarker(coord, bounds, width, height, options) {
  const point = project(coord, bounds, width, height);
  const radius = options.radius * Math.max(0.65, Math.min(1.6, point.perspective));
  ctx.save();
  ctx.shadowColor = options.shadow || "rgba(0,0,0,0.35)";
  ctx.shadowBlur = 14;
  ctx.fillStyle = options.fill;
  ctx.strokeStyle = options.stroke || "rgba(255,255,255,0.9)";
  ctx.lineWidth = options.lineWidth || 1.5;
  ctx.beginPath();
  ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.restore();
  return { ...point, radius };
}

function renderMap() {
  resizeCanvas();
  const width = els.canvas.clientWidth;
  const height = els.canvas.clientHeight;
  const points = selectedPoints();
  const values = points.map(metricValue).filter((value) => value !== null && Number.isFinite(value));
  const min = values.length ? Math.min(...values) : 0;
  const max = values.length ? Math.max(...values) : 1;
  const maxExcessLoss = Math.max(0, ...points.map((point) => Number(point.excess_loss_db)).filter(Number.isFinite));
  const activeLayer = state.heightFilter === "all" ? "全部高度" : `${fmt(state.heightFilter, 1)} m`;
  els.layerReadout.textContent = `${activeLayer} · ${points.length} 个点 · 3D`;

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#101916";
  ctx.fillRect(0, 0, width, height);

  const bounds = collectSceneBounds(points, state.mesh);
  drawGround(bounds, width, height);
  drawBuildings(bounds, width, height);
  drawSightLine(state.selectedPoint, bounds, width, height);

  const sortedPoints = points
    .map((point) => ({ point, screen: project(point.rx_xyz_m, bounds, width, height) }))
    .sort((a, b) => a.screen.depth - b.screen.depth);
  state.projectedPoints = [];

  sortedPoints.forEach(({ point }) => {
    const value = metricValue(point);
    const overlay = state.metric === "combined_signal_building"
      ? excessLossStyle(point, maxExcessLoss)
      : {
          stroke: point.is_los_blocked_by_building ? "rgba(255,75,62,0.95)" : "rgba(255,255,255,0.86)",
          lineWidth: point.is_los_blocked_by_building ? 2.8 : 1.5,
        };
    const marker = drawMarker(point.rx_xyz_m, bounds, width, height, {
      radius: 5 + Math.min(8, point.valid_path_count || 0),
      fill: colorFor(value, min, max),
      stroke: overlay.stroke,
      lineWidth: overlay.lineWidth,
    });
    state.projectedPoints.push({ point, ...marker });
    if (state.showLabels) {
      ctx.fillStyle = "rgba(255,255,255,0.82)";
      ctx.font = "700 12px sans-serif";
      ctx.fillText(point.rx_id, marker.x + marker.radius + 5, marker.y - marker.radius);
    }
  });

  if (state.radio?.tx?.position_m) {
    const tx = drawMarker(state.radio.tx.position_m, bounds, width, height, {
      radius: 12,
      fill: "#ffffff",
      stroke: "#d86f2c",
      lineWidth: 4,
      shadow: "rgba(216,111,44,0.55)",
    });
    ctx.fillStyle = "rgba(255,255,255,0.9)";
    ctx.font = "900 13px sans-serif";
    ctx.fillText("Tx", tx.x + 15, tx.y - 12);
  }

  ctx.fillStyle = "rgba(255,255,255,0.72)";
  ctx.font = "700 12px sans-serif";
  ctx.fillText("橙色：+X / 东向", 18, height - 34);
  ctx.fillText("绿色：+Y / 北向", 18, height - 16);
  if (state.metric === "combined_signal_building") {
    ctx.fillText("叠加：填充色=信号强弱，外圈=建筑额外损耗，红边=LOS 遮挡", 150, height - 16);
  }
  if (state.metric === "excess_loss_db") {
    ctx.fillText("着色：绿=额外损耗低，橙/红=建筑额外损耗更强", 150, height - 16);
  }
  if (state.metric === "is_los_blocked_by_building") {
    ctx.fillText("着色：红=LOS 被建筑遮挡，绿=LOS 未遮挡", 150, height - 16);
  }
}

async function loadData() {
  els.status.textContent = "正在加载 Sionna 输出数据...";
  const [summaryResp, radioResp, meshResp] = await Promise.all([
    fetch(`${DATA_ROOT}/summary.json`),
    fetch(`${DATA_ROOT}/radio_map_points.json`),
    fetch(`${DATA_ROOT}/scene/meshes/local_buildings.ply`),
  ]);
  if (!summaryResp.ok || !radioResp.ok) {
    throw new Error(`数据加载失败：summary=${summaryResp.status}, radio=${radioResp.status}`);
  }
  state.summary = await summaryResp.json();
  state.radio = await radioResp.json();
  state.mesh = meshResp.ok ? parsePly(await meshResp.text()) : { vertices: [], faces: [] };
  updateHeightOptions();
  renderSummary();
  renderMap();
  const blocked = state.summary?.los_blocked_rx_points ?? 0;
  els.status.textContent = `三维数据已加载：建筑面片 ${state.mesh.faces.length}，LOS 遮挡点 ${blocked} 个。`;
}

els.heightFilter.addEventListener("change", (event) => {
  state.heightFilter = event.target.value;
  renderMap();
});

els.metricSelect.addEventListener("change", (event) => {
  state.metric = event.target.value;
  renderMap();
});

els.showLabels.addEventListener("change", (event) => {
  state.showLabels = event.target.checked;
  renderMap();
});

els.reloadBtn.addEventListener("click", () => {
  loadData().catch((error) => {
    els.status.textContent = error.message;
  });
});

els.canvas.addEventListener("pointerdown", (event) => {
  state.dragging = true;
  state.lastMouse = [event.clientX, event.clientY];
  els.canvas.setPointerCapture(event.pointerId);
});

els.canvas.addEventListener("pointermove", (event) => {
  if (!state.dragging || !state.lastMouse) return;
  const dx = event.clientX - state.lastMouse[0];
  const dy = event.clientY - state.lastMouse[1];
  state.yaw += dx * 0.008;
  state.pitch = Math.max(-1.35, Math.min(1.35, state.pitch + dy * 0.008));
  state.lastMouse = [event.clientX, event.clientY];
  renderMap();
});

els.canvas.addEventListener("pointerup", () => {
  state.dragging = false;
  state.lastMouse = null;
});

els.canvas.addEventListener("wheel", (event) => {
  event.preventDefault();
  state.zoom = Math.max(0.35, Math.min(3.5, state.zoom * (event.deltaY > 0 ? 0.9 : 1.1)));
  renderMap();
}, { passive: false });

els.canvas.addEventListener("click", (event) => {
  const rect = els.canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  let best = null;
  state.projectedPoints.forEach((candidate) => {
    const distance = Math.hypot(candidate.x - x, candidate.y - y);
    if (distance <= candidate.radius + 5 && (!best || distance < best.distance)) {
      best = { distance, point: candidate.point };
    }
  });
  if (best) {
    state.selectedPoint = best.point;
    els.rxInfo.textContent = JSON.stringify(best.point, null, 2);
    renderMap();
  }
});

window.addEventListener("resize", renderMap);

loadData().catch((error) => {
  els.status.textContent = error.message;
});
