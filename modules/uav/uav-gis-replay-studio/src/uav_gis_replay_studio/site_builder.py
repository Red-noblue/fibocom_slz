from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .map_renderer import render_prediction_map


def _sanitize_records(step_rows: pd.DataFrame) -> list[dict[str, Any]]:
    rows = step_rows.copy()
    if "time" in rows.columns:
        rows["time"] = pd.to_datetime(rows["time"], errors="coerce").astype(str)
    rows = rows.replace({np.nan: None})
    return rows.to_dict(orient="records")


def _build_site_html(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    summary_json = json.dumps(summary, ensure_ascii=False)
    rows_json = json.dumps(rows, ensure_ascii=False)
    route_length_km = float(summary.get("route_length_km", 0.0) or 0.0)
    predicted_range_km = float(summary.get("predicted_range_km", 0.0) or 0.0)
    completion_pct = (predicted_range_km / route_length_km * 100.0) if route_length_km > 0 else 0.0
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{summary["route_name"]} - UAV GIS Replay Studio</title>
  <style>
    :root {{
      --bg: #f3f6f8;
      --panel: #ffffff;
      --line: #d7e0e6;
      --text: #0f1720;
      --muted: #5d6b76;
      --accent: #0f7b6c;
      --accent-2: #d96c1f;
      --danger: #c53d2f;
      --shadow: 0 18px 48px rgba(15, 23, 32, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "PingFang SC", "Noto Sans SC", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(15,123,108,0.14), transparent 26%),
        radial-gradient(circle at bottom right, rgba(217,108,31,0.10), transparent 24%),
        var(--bg);
      color: var(--text);
    }}
    .page {{
      padding: 20px;
      display: grid;
      gap: 16px;
    }}
    .hero {{
      background: linear-gradient(130deg, #0f1720, #15493f 58%, #1b6d5f);
      color: #f7fbfc;
      border-radius: 24px;
      padding: 22px 24px;
      box-shadow: var(--shadow);
    }}
    .hero h1 {{
      margin: 0 0 8px;
      font-size: 28px;
      line-height: 1.1;
      letter-spacing: 0.02em;
    }}
    .hero p {{
      margin: 0;
      color: rgba(247,251,252,0.80);
      font-size: 14px;
    }}
    .stats {{
      margin-top: 16px;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
    }}
    .stat {{
      background: rgba(255,255,255,0.10);
      border: 1px solid rgba(255,255,255,0.14);
      border-radius: 18px;
      padding: 14px 16px;
    }}
    .stat .k {{
      display: block;
      font-size: 12px;
      color: rgba(247,251,252,0.66);
      margin-bottom: 8px;
    }}
    .stat .v {{
      font-size: 22px;
      font-weight: 700;
      letter-spacing: 0.01em;
    }}
    .notice-row {{
      margin-top: 14px;
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}
    .notice {{
      padding: 9px 12px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.01em;
      border: 1px solid rgba(255,255,255,0.14);
      background: rgba(255,255,255,0.10);
      color: rgba(247,251,252,0.92);
    }}
    .notice.warn {{
      background: rgba(197,61,47,0.18);
      color: #ffe0dc;
      border-color: rgba(255,224,220,0.18);
    }}
    .layout {{
      display: grid;
      grid-template-columns: 320px minmax(0, 1fr) 360px;
      gap: 16px;
      align-items: start;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: var(--shadow);
    }}
    .panel h2 {{
      margin: 0 0 12px;
      font-size: 15px;
      letter-spacing: 0.02em;
    }}
    .left, .right {{
      padding: 18px;
      display: grid;
      gap: 16px;
    }}
    .section + .section {{
      border-top: 1px solid var(--line);
      padding-top: 16px;
    }}
    .kv {{
      display: grid;
      grid-template-columns: 98px 1fr;
      row-gap: 10px;
      column-gap: 10px;
      font-size: 13px;
    }}
    .kv .k {{
      color: var(--muted);
    }}
    .kv .v {{
      font-weight: 600;
    }}
    .risk-list {{
      margin: 0;
      padding-left: 18px;
      color: var(--danger);
      font-size: 13px;
      line-height: 1.55;
    }}
    .hint-box {{
      padding: 12px 14px;
      border-radius: 16px;
      background: #f4f8fa;
      border: 1px solid #dfe8ed;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.55;
    }}
    .map-shell {{
      overflow: hidden;
      padding: 0;
      min-height: 860px;
    }}
    .map-shell iframe {{
      width: 100%;
      min-height: 860px;
      border: 0;
      display: block;
      background: #eef3f6;
    }}
    .controls {{
      display: grid;
      gap: 12px;
    }}
    .btn-row {{
      display: flex;
      gap: 10px;
      align-items: center;
    }}
    button {{
      border: 0;
      border-radius: 999px;
      padding: 10px 16px;
      background: var(--accent);
      color: #fff;
      font-weight: 700;
      cursor: pointer;
    }}
    button.secondary {{
      background: #dfe8ec;
      color: var(--text);
    }}
    input[type="range"] {{
      width: 100%;
      accent-color: var(--accent);
    }}
    .replay-card {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      background: linear-gradient(180deg, #fcfdfd, #f5f8fa);
    }}
    .battery {{
      margin: 12px 0 8px;
      height: 14px;
      border-radius: 999px;
      overflow: hidden;
      background: #dfe7eb;
    }}
    .battery > div {{
      height: 100%;
      width: 0%;
      background: var(--accent);
    }}
    .metric-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      font-size: 13px;
    }}
    .metric {{
      padding: 10px 12px;
      border-radius: 16px;
      background: #f6fafb;
      border: 1px solid #e2eaef;
    }}
    .metric span {{
      display: block;
    }}
    .metric .mk {{
      font-size: 11px;
      color: var(--muted);
      margin-bottom: 6px;
    }}
    .metric .mv {{
      font-weight: 700;
    }}
    .charts {{
      display: grid;
      gap: 12px;
    }}
    .chart {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 12px;
      background: #fbfcfd;
    }}
    .chart-head {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 8px;
      font-size: 12px;
    }}
    .chart-head strong {{
      font-size: 13px;
    }}
    svg {{
      width: 100%;
      height: 92px;
      display: block;
    }}
    .chart-vline {{
      stroke: #9fb0bb;
      stroke-width: 1.3;
      stroke-dasharray: 4 4;
      opacity: 0.85;
    }}
    .chart-dot {{
      fill: #ffffff;
      stroke-width: 3;
    }}
    .footer {{
      font-size: 12px;
      color: var(--muted);
      text-align: right;
      padding: 0 4px 6px;
    }}
    @media (max-width: 1500px) {{
      .layout {{
        grid-template-columns: 1fr;
      }}
      .map-shell iframe {{
        min-height: 720px;
      }}
    }}
    @media (max-width: 900px) {{
      .stats {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .page {{
        padding: 12px;
      }}
      .hero {{
        border-radius: 18px;
      }}
      .panel {{
        border-radius: 18px;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <h1>{summary["route_name"]}</h1>
      <p>固定航线天气驱动能耗预测网站展示页。当前页面消费 summary + timeseries 产物，可直接通过内网 HTTP 访问。</p>
      <div class="stats">
        <div class="stat"><span class="k">航线长度</span><span class="v">{summary["route_length_km"]:.2f} km</span></div>
        <div class="stat"><span class="k">预测总能耗</span><span class="v">{summary["predicted_total_energy_wh"]:.2f} Wh</span></div>
        <div class="stat"><span class="k">预测可达航程</span><span class="v">{summary["predicted_range_km"]:.2f} km</span></div>
        <div class="stat"><span class="k">天气来源</span><span class="v" style="font-size:16px">{summary["weather_source"]}</span></div>
      </div>
      <div class="notice-row">
        <div class="notice">当前地图航线为固定航线抽象轨迹，按起终点直连插值生成，不是实测 GPS 航迹</div>
        <div class="notice warn">该样例预计只能完成全程 {completion_pct:.1f}% ，因此电池会在前段耗尽</div>
      </div>
    </section>

    <section class="layout">
      <aside class="panel left">
        <div class="section">
          <h2>任务参数</h2>
          <div class="kv">
            <div class="k">起点</div><div class="v">{summary["route_start"]["lat"]:.5f}, {summary["route_start"]["lon"]:.5f}</div>
            <div class="k">终点</div><div class="v">{summary["route_end"]["lat"]:.5f}, {summary["route_end"]["lon"]:.5f}</div>
            <div class="k">航向角</div><div class="v">{summary["route_heading_deg"]:.2f}°</div>
            <div class="k">巡航速度</div><div class="v">{summary["cruise_speed_mps"]:.1f} m/s</div>
            <div class="k">巡航高度</div><div class="v">{summary["cruise_altitude_m"]:.1f} m</div>
            <div class="k">载荷重量</div><div class="v">{summary["payload_g"]:.1f} g</div>
            <div class="k">电池容量</div><div class="v">{summary["battery_wh"]:.1f} Wh</div>
            <div class="k">起飞时间</div><div class="v">{summary["departure_time"]}</div>
            <div class="k">计划时长</div><div class="v">{summary["planned_flight_time_s"]:.1f} s</div>
            <div class="k">可完成比例</div><div class="v">{completion_pct:.1f}%</div>
          </div>
        </div>
        <div class="section">
          <h2>当前说明</h2>
          <div class="hint-box">
            这个网站当前接的是旧 demo 样例产物。地图中的航迹点来自预测脚本按起点和终点做线性插值后的时序点，因此看起来是一条直线。
            如果后续接入真实航线几何或实测 GPS 轨迹，地图就会变成真实路线形状。
          </div>
        </div>
        <div class="section">
          <h2>风险提示</h2>
          <ul class="risk-list" id="risk-list"></ul>
        </div>
      </aside>

      <main class="panel map-shell">
        <iframe src="map.html" title="route-map"></iframe>
      </main>

      <aside class="panel right">
        <div class="controls">
          <div class="btn-row">
            <button id="play-btn">暂停</button>
            <button class="secondary" id="reset-btn">回到起点</button>
            <div id="step-text" style="font-size:12px;color:var(--muted);margin-left:auto">1 / 1</div>
          </div>
          <input type="range" min="0" max="0" value="0" id="step-range">
        </div>

        <div class="replay-card">
          <h2 style="margin-bottom:6px;">回放状态</h2>
          <div style="font-size:12px;color:var(--muted);" id="time-text">--</div>
          <div style="margin-top:10px;font-size:24px;font-weight:800;" id="status-text">可飞</div>
          <div style="margin-top:8px;font-size:13px;color:var(--muted);" id="progress-text">进度 0%</div>
          <div class="battery"><div id="battery-bar"></div></div>
          <div style="display:flex;justify-content:space-between;font-size:13px;">
            <span>剩余电池</span>
            <strong id="battery-text">0 Wh</strong>
          </div>
        </div>

        <div class="metric-grid">
          <div class="metric"><span class="mk">分段能耗</span><span class="mv" id="seg-energy">--</span></div>
          <div class="metric"><span class="mk">累计能耗</span><span class="mv" id="cum-energy">--</span></div>
          <div class="metric"><span class="mk">风速 / 风向</span><span class="mv" id="wind-text">--</span></div>
          <div class="metric"><span class="mk">温度 / 湿度</span><span class="mv" id="temp-text">--</span></div>
          <div class="metric"><span class="mk">降水 / 气压</span><span class="mv" id="atmo-text">--</span></div>
          <div class="metric"><span class="mk">能见度 / AQI</span><span class="mv" id="vis-aqi-text">--</span></div>
        </div>

        <div class="charts">
          <div class="chart">
            <div class="chart-head"><strong>电池余量</strong><span id="battery-chart-label">--</span></div>
            <svg viewBox="0 0 300 92">
              <polyline id="battery-poly" fill="none" stroke="#0f7b6c" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></polyline>
              <line id="battery-vline" class="chart-vline" x1="0" y1="8" x2="0" y2="84"></line>
              <circle id="battery-dot" class="chart-dot" stroke="#0f7b6c" cx="0" cy="0" r="5.5"></circle>
            </svg>
          </div>
          <div class="chart">
            <div class="chart-head"><strong>风速</strong><span id="wind-chart-label">--</span></div>
            <svg viewBox="0 0 300 92">
              <polyline id="wind-poly" fill="none" stroke="#d96c1f" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></polyline>
              <line id="wind-vline" class="chart-vline" x1="0" y1="8" x2="0" y2="84"></line>
              <circle id="wind-dot" class="chart-dot" stroke="#d96c1f" cx="0" cy="0" r="5.5"></circle>
            </svg>
          </div>
          <div class="chart">
            <div class="chart-head"><strong>温度</strong><span id="temp-chart-label">--</span></div>
            <svg viewBox="0 0 300 92">
              <polyline id="temp-poly" fill="none" stroke="#b33c29" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></polyline>
              <line id="temp-vline" class="chart-vline" x1="0" y1="8" x2="0" y2="84"></line>
              <circle id="temp-dot" class="chart-dot" stroke="#b33c29" cx="0" cy="0" r="5.5"></circle>
            </svg>
          </div>
          <div class="chart">
            <div class="chart-head"><strong>累计能耗</strong><span id="energy-chart-label">--</span></div>
            <svg viewBox="0 0 300 92">
              <polyline id="energy-poly" fill="none" stroke="#215a9c" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></polyline>
              <line id="energy-vline" class="chart-vline" x1="0" y1="8" x2="0" y2="84"></line>
              <circle id="energy-dot" class="chart-dot" stroke="#215a9c" cx="0" cy="0" r="5.5"></circle>
            </svg>
          </div>
        </div>
      </aside>
    </section>

    <div class="footer">Generated by uav-gis-replay-studio</div>
  </div>

  <script>
    const SUMMARY = {summary_json};
    const ROWS = {rows_json};
    const state = {{
      idx: 0,
      playing: true,
      timer: null,
    }};
    const chartDefs = {{}};

    const $ = (id) => document.getElementById(id);

    function fmt(v, digits = 1) {{
      const n = Number(v);
      return Number.isFinite(n) ? n.toFixed(digits) : "--";
    }}

    function clamp(v, lo, hi) {{
      return Math.max(lo, Math.min(hi, v));
    }}

    function batteryColor(pct) {{
      if (pct < 20) return "#c53d2f";
      if (pct < 40) return "#d96c1f";
      return "#0f7b6c";
    }}

    function aqiLevel(v) {{
      const aqi = Number(v);
      if (!Number.isFinite(aqi)) return "未知";
      if (aqi <= 50) return "优";
      if (aqi <= 100) return "良";
      if (aqi <= 150) return "轻度污染";
      if (aqi <= 200) return "中度污染";
      if (aqi <= 300) return "重度污染";
      return "严重污染";
    }}

    function renderRiskList() {{
      const items = (SUMMARY.risk_alerts || []).map((item) => `<li>${{item}}</li>`).join("");
      $("risk-list").innerHTML = items || "<li>暂无</li>";
    }}

    function polyPoints(rows, key, minValue, maxValue) {{
      const width = 300;
      const height = 92;
      const pad = 8;
      const span = Math.max(rows.length - 1, 1);
      const range = Math.max(maxValue - minValue, 1e-6);
      return rows.map((row, idx) => {{
        const x = pad + (idx / span) * (width - pad * 2);
        const raw = Number(row[key]);
        const val = Number.isFinite(raw) ? raw : minValue;
        const y = height - pad - ((val - minValue) / range) * (height - pad * 2);
        return {{ x, y }};
      }});
    }}

    function renderCharts() {{
      const safeRows = ROWS.length ? ROWS : [{{}}];
      const batteryVals = safeRows.map((r) => Number(r.battery_remaining_pct) || 0);
      const windVals = safeRows.map((r) => Number(r.wind_speed_mps) || 0);
      const tempVals = safeRows.map((r) => Number(r.temperature_c) || 0);
      const energyVals = safeRows.map((r) => Number(r.cumulative_energy_wh) || 0);
      chartDefs.battery = polyPoints(safeRows, "battery_remaining_pct", 0, Math.max(...batteryVals, 100));
      chartDefs.wind = polyPoints(safeRows, "wind_speed_mps", 0, Math.max(...windVals, 8));
      chartDefs.temp = polyPoints(safeRows, "temperature_c", Math.min(...tempVals, -5), Math.max(...tempVals, 35));
      chartDefs.energy = polyPoints(safeRows, "cumulative_energy_wh", 0, Math.max(...energyVals, 1));

      $("battery-poly").setAttribute("points", chartDefs.battery.map((p) => `${{p.x.toFixed(2)}},${{p.y.toFixed(2)}}`).join(" "));
      $("wind-poly").setAttribute("points", chartDefs.wind.map((p) => `${{p.x.toFixed(2)}},${{p.y.toFixed(2)}}`).join(" "));
      $("temp-poly").setAttribute("points", chartDefs.temp.map((p) => `${{p.x.toFixed(2)}},${{p.y.toFixed(2)}}`).join(" "));
      $("energy-poly").setAttribute("points", chartDefs.energy.map((p) => `${{p.x.toFixed(2)}},${{p.y.toFixed(2)}}`).join(" "));
    }}

    function updateChartMarker(name, idx, label) {{
      const pts = chartDefs[name] || [];
      if (!pts.length) return;
      const safeIdx = clamp(idx, 0, pts.length - 1);
      const p = pts[safeIdx];
      $(`${{name}}-dot`).setAttribute("cx", p.x.toFixed(2));
      $(`${{name}}-dot`).setAttribute("cy", p.y.toFixed(2));
      $(`${{name}}-vline`).setAttribute("x1", p.x.toFixed(2));
      $(`${{name}}-vline`).setAttribute("x2", p.x.toFixed(2));
      $(`${{name}}-chart-label`).textContent = label;
    }}

    function updateStep(idx) {{
      if (!ROWS.length) return;
      state.idx = clamp(idx, 0, ROWS.length - 1);
      const row = ROWS[state.idx];

      const batteryWh = Number(row.remaining_battery_wh) || 0;
      const batteryPct = clamp(Number(row.battery_remaining_pct) || 0, 0, 100);
      const routeLen = Number(SUMMARY.route_length_km) || 0;
      const doneKm = Number(row.distance_from_start_km) || 0;
      const progressPct = routeLen > 0 ? clamp((doneKm / routeLen) * 100, 0, 100) : 0;
      const warning = batteryPct < 20 || (Number(row.wind_speed_mps) || 0) > 8;

      $("step-text").textContent = `${{state.idx + 1}} / ${{ROWS.length}}`;
      $("step-range").value = String(state.idx);
      $("time-text").textContent = String(row.time || "--");
      $("status-text").textContent = warning ? "预警" : "可飞";
      $("status-text").style.color = warning ? "#c53d2f" : "#0f7b6c";
      $("progress-text").textContent = `进度 ${{fmt(progressPct, 1)}}% · ${{fmt(doneKm, 2)}} / ${{fmt(routeLen, 2)}} km`;
      $("battery-text").textContent = `${{fmt(batteryWh, 2)}} Wh / ${{fmt(SUMMARY.battery_wh, 1)}} Wh`;
      $("battery-bar").style.width = `${{fmt(batteryPct, 2)}}%`;
      $("battery-bar").style.background = batteryColor(batteryPct);

      $("seg-energy").textContent = `${{fmt(row.segment_energy_wh, 2)}} Wh`;
      $("cum-energy").textContent = `${{fmt(row.cumulative_energy_wh, 2)}} Wh`;
      $("wind-text").textContent = `${{fmt(row.wind_speed_mps, 1)}} m/s / ${{fmt(row.wind_dir_deg, 0)}}°`;
      $("temp-text").textContent = `${{fmt(row.temperature_c, 1)}}°C / ${{fmt(row.relative_humidity_pct, 0)}}%`;
      $("atmo-text").textContent = `${{fmt(row.precipitation_mm, 2)}} mm / ${{fmt(row.pressure_hpa, 1)}} hPa`;
      $("vis-aqi-text").textContent = `${{fmt(row.visibility_km, 1)}} km / ${{fmt(row.air_quality_index, 0)}} (${{aqiLevel(row.air_quality_index)}})`;

      updateChartMarker("battery", state.idx, `当前 ${{fmt(batteryPct, 1)}}%`);
      updateChartMarker("wind", state.idx, `当前 ${{fmt(row.wind_speed_mps, 1)}} m/s`);
      updateChartMarker("temp", state.idx, `当前 ${{fmt(row.temperature_c, 1)}}°C`);
      updateChartMarker("energy", state.idx, `当前 ${{fmt(row.cumulative_energy_wh, 1)}} Wh`);
    }}

    function playLoop() {{
      if (state.timer) window.clearInterval(state.timer);
      state.timer = window.setInterval(() => {{
        if (!state.playing || !ROWS.length) return;
        const next = state.idx + 1 < ROWS.length ? state.idx + 1 : 0;
        updateStep(next);
      }}, 1200);
    }}

    function bindEvents() {{
      $("play-btn").addEventListener("click", () => {{
        state.playing = !state.playing;
        $("play-btn").textContent = state.playing ? "暂停" : "播放";
      }});
      $("reset-btn").addEventListener("click", () => updateStep(0));
      $("step-range").addEventListener("input", (event) => {{
        state.playing = false;
        $("play-btn").textContent = "播放";
        updateStep(Number(event.target.value));
      }});
      $("step-range").max = String(Math.max(ROWS.length - 1, 0));
    }}

    renderRiskList();
    renderCharts();
    bindEvents();
    updateStep(0);
    playLoop();
  </script>
</body>
</html>
"""


def build_static_site(
    summary: dict[str, Any],
    step_rows: pd.DataFrame,
    output_dir: str | Path,
) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    render_prediction_map(summary, step_rows, output_path / "map.html")

    with (output_path / "summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, ensure_ascii=False)
    step_rows.to_csv(output_path / "timeseries.csv", index=False)
    with (output_path / "timeseries.json").open("w", encoding="utf-8") as fh:
        json.dump(_sanitize_records(step_rows), fh, ensure_ascii=False)

    index_html = _build_site_html(summary, _sanitize_records(step_rows))
    index_path = output_path / "index.html"
    index_path.write_text(index_html, encoding="utf-8")
    return index_path
