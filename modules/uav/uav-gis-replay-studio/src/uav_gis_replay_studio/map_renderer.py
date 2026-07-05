from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import folium
import numpy as np
import pandas as pd


def _haversine_m(lat1, lon1, lat2, lon2):
    radius_m = 6371000.0
    lat1 = np.deg2rad(lat1)
    lon1 = np.deg2rad(lon1)
    lat2 = np.deg2rad(lat2)
    lon2 = np.deg2rad(lon2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    c = 2.0 * np.arcsin(np.sqrt(a))
    return radius_m * c


def _polyline_length_km(points: list[tuple[float, float]]) -> float:
    if len(points) < 2:
        return 0.0
    total_m = 0.0
    for idx in range(1, len(points)):
        lat0, lon0 = points[idx - 1]
        lat1, lon1 = points[idx]
        total_m += float(_haversine_m(lat0, lon0, lat1, lon1))
    return total_m / 1000.0


def _format_datetime_cn(value: str) -> str:
    dt = pd.to_datetime(value).to_pydatetime()
    return f"{dt.year}年{dt.month}月{dt.day}日 {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"


def _compass_dir_cn(deg: float) -> str:
    if not np.isfinite(deg):
        return "--"
    dirs = ["北", "东北", "东", "东南", "南", "西南", "西", "西北"]
    idx = int(((deg % 360.0) + 22.5) // 45.0) % 8
    return dirs[idx]


def _aqi_level_cn(aqi: float) -> str:
    if not np.isfinite(aqi):
        return "未知"
    if aqi <= 50:
        return "优"
    if aqi <= 100:
        return "良"
    if aqi <= 150:
        return "轻度污染"
    if aqi <= 200:
        return "中度污染"
    if aqi <= 300:
        return "重度污染"
    return "严重污染"


def _uv_level_cn(uv: float) -> str:
    if not np.isfinite(uv):
        return "未知"
    if uv < 3:
        return "低"
    if uv < 6:
        return "中等"
    if uv < 8:
        return "高"
    if uv < 11:
        return "很高"
    return "极高"


def _estimate_visibility_km(rh: float, precip_mm: float, wind_mps: float) -> float:
    rh_v = float(rh) if np.isfinite(rh) else 65.0
    precip_v = float(precip_mm) if np.isfinite(precip_mm) else 0.0
    wind_v = float(wind_mps) if np.isfinite(wind_mps) else 3.0
    vis = 24.0 - 0.11 * rh_v - 5.0 * max(precip_v, 0.0) + 0.55 * min(max(wind_v, 0.0), 12.0)
    return float(np.clip(vis, 1.0, 25.0))


def _estimate_aqi(
    visibility_km: float,
    rh: float,
    wind_mps: float,
    precip_mm: float,
    pressure_hpa: float,
) -> float:
    score = 45.0
    if np.isfinite(visibility_km):
        score += max(0.0, 10.0 - visibility_km) * 5.2
    if np.isfinite(rh):
        score += max(0.0, rh - 65.0) * 0.55
    if np.isfinite(wind_mps):
        score += max(0.0, 2.5 - wind_mps) * 7.5
        score -= max(0.0, wind_mps - 6.0) * 1.9
    if np.isfinite(precip_mm):
        score -= min(max(precip_mm, 0.0), 2.0) * 5.0
    if np.isfinite(pressure_hpa):
        score += max(0.0, pressure_hpa - 1020.0) * 0.16
    return float(np.clip(score, 10.0, 300.0))


def load_prediction_artifacts(
    summary_path: str | Path,
    timeseries_path: str | Path,
) -> tuple[dict[str, Any], pd.DataFrame]:
    with Path(summary_path).open("r", encoding="utf-8") as fh:
        summary = json.load(fh)
    step_rows = pd.read_csv(timeseries_path)
    return summary, step_rows


def render_prediction_map(
    summary: dict[str, Any],
    step_rows: pd.DataFrame,
    out_html: str | Path,
) -> Path:
    step_rows = step_rows.copy()
    if "relative_humidity_pct" not in step_rows.columns:
        step_rows["relative_humidity_pct"] = np.nan
    if "visibility_km" not in step_rows.columns:
        if "visibility_m" in step_rows.columns:
            step_rows["visibility_km"] = pd.to_numeric(step_rows["visibility_m"], errors="coerce") / 1000.0
        else:
            ws = pd.to_numeric(step_rows.get("wind_speed_mps"), errors="coerce")
            rh = pd.to_numeric(step_rows.get("relative_humidity_pct"), errors="coerce")
            pr = pd.to_numeric(step_rows.get("precipitation_mm"), errors="coerce")
            step_rows["visibility_km"] = [
                _estimate_visibility_km(
                    float(h) if np.isfinite(h) else np.nan,
                    float(p) if np.isfinite(p) else np.nan,
                    float(w) if np.isfinite(w) else np.nan,
                )
                for h, p, w in zip(rh.fillna(np.nan), pr.fillna(np.nan), ws.fillna(np.nan))
            ]
    if "uv_index" not in step_rows.columns:
        if "time" in step_rows.columns:
            ts = pd.to_datetime(step_rows["time"], errors="coerce")
            step_rows["uv_index"] = [2.0 if (pd.notna(t) and 9 <= t.hour <= 16) else 0.0 for t in ts]
        else:
            step_rows["uv_index"] = 0.0
    if "air_quality_index" not in step_rows.columns:
        ws = pd.to_numeric(step_rows.get("wind_speed_mps"), errors="coerce")
        rh = pd.to_numeric(step_rows.get("relative_humidity_pct"), errors="coerce")
        pr = pd.to_numeric(step_rows.get("precipitation_mm"), errors="coerce")
        ps = pd.to_numeric(step_rows.get("pressure_hpa"), errors="coerce")
        vs = pd.to_numeric(step_rows.get("visibility_km"), errors="coerce")
        step_rows["air_quality_index"] = [
            _estimate_aqi(
                float(v) if np.isfinite(v) else np.nan,
                float(h) if np.isfinite(h) else np.nan,
                float(w) if np.isfinite(w) else np.nan,
                float(p) if np.isfinite(p) else np.nan,
                float(s) if np.isfinite(s) else np.nan,
            )
            for v, h, w, p, s in zip(vs.fillna(np.nan), rh.fillna(np.nan), ws.fillna(np.nan), pr.fillna(np.nan), ps.fillna(np.nan))
        ]

    points = []
    if {"lat", "lon"}.issubset(step_rows.columns):
        points = [
            (float(row["lat"]), float(row["lon"]))
            for _, row in step_rows[["lat", "lon"]].dropna().iterrows()
        ]
    if len(points) < 2:
        points = [
            (float(summary["route_start"]["lat"]), float(summary["route_start"]["lon"])),
            (float(summary["route_end"]["lat"]), float(summary["route_end"]["lon"])),
        ]

    center_lat = (points[0][0] + points[-1][0]) / 2.0
    center_lon = (points[0][1] + points[-1][1]) / 2.0
    actual_length_km = _polyline_length_km(points)

    m = folium.Map(location=[center_lat, center_lon], zoom_start=12, control_scale=True, tiles=None)
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
        attr="© CARTO © OpenStreetMap contributors",
        name="CartoDB Positron",
        show=True,
        max_zoom=19,
    ).add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles © Esri",
        name="Esri StreetMap",
        show=False,
        max_zoom=19,
    ).add_to(m)

    folium.PolyLine(
        [[float(lat), float(lon)] for lat, lon in points],
        color="#e63946",
        weight=5,
        opacity=0.9,
        tooltip=f"实际路径：{actual_length_km:.2f} km",
    ).add_to(m)

    folium.Marker(
        location=[points[0][0], points[0][1]],
        popup=f"起点：{summary['route_name']}",
        icon=folium.Icon(color="green", icon="play", prefix="fa"),
        tooltip="航线起点",
    ).add_to(m)
    folium.Marker(
        location=[points[-1][0], points[-1][1]],
        popup=f"终点：{summary['route_name']}",
        icon=folium.Icon(color="red", icon="flag-checkered", prefix="fa"),
        tooltip="航线终点",
    ).add_to(m)

    telemetry_group = folium.FeatureGroup(name="实时观测采样点", show=True)
    if not step_rows.empty and {"lat", "lon"}.issubset(step_rows.columns):
        step_interval = max(1, int(len(step_rows) / 20))
        for idx in range(0, len(step_rows), step_interval):
            row = step_rows.iloc[idx]
            popup = folium.Popup(
                (
                    f"时间: {row['time']}<br>"
                    f"风速: {row['wind_speed_mps']:.2f} m/s @ {row['wind_dir_deg']:.1f}°({_compass_dir_cn(float(row['wind_dir_deg']))})<br>"
                    f"温度: {row['temperature_c']:.1f} °C<br>"
                    f"湿度: {row['relative_humidity_pct']:.1f} %<br>"
                    f"降水: {row['precipitation_mm']:.2f} mm<br>"
                    f"气压: {row['pressure_hpa']:.1f} hPa<br>"
                    f"能见度: {row['visibility_km']:.1f} km<br>"
                    f"紫外线: {row['uv_index']:.1f}<br>"
                    f"空气质量指数(AQI): {row['air_quality_index']:.0f} ({_aqi_level_cn(float(row['air_quality_index']))})<br>"
                    f"分段能耗: {row['segment_energy_wh']:.2f} Wh<br>"
                    f"累计能耗: {row['cumulative_energy_wh']:.2f} Wh<br>"
                    f"剩余电池: {row['remaining_battery_wh']:.2f} Wh"
                ),
                max_width=320,
            )
            folium.CircleMarker(
                location=[float(row["lat"]), float(row["lon"])],
                radius=4,
                color="#f97316",
                fill=True,
                fill_opacity=0.85,
                tooltip=(
                    f"{row['time']} | T {row['temperature_c']:.1f}°C | "
                    f"H {row['relative_humidity_pct']:.0f}% | R {row['precipitation_mm']:.2f} mm"
                ),
                popup=popup,
            ).add_to(telemetry_group)
    telemetry_group.add_to(m)

    alerts = summary.get("risk_alerts", [])
    alert_html = "".join(f"<li style='margin-bottom:4px;color:#991b1b'>{msg}</li>" for msg in alerts)
    departure_cn = _format_datetime_cn(summary["departure_time"])

    temp_series = pd.to_numeric(step_rows.get("temperature_c"), errors="coerce")
    wind_series = pd.to_numeric(step_rows.get("wind_speed_mps"), errors="coerce")
    wind_dir_series = pd.to_numeric(step_rows.get("wind_dir_deg"), errors="coerce")
    rh_series = pd.to_numeric(step_rows.get("relative_humidity_pct"), errors="coerce")
    precip_series = pd.to_numeric(step_rows.get("precipitation_mm"), errors="coerce")
    pressure_series = pd.to_numeric(step_rows.get("pressure_hpa"), errors="coerce")
    vis_series = pd.to_numeric(step_rows.get("visibility_km"), errors="coerce")
    uv_series = pd.to_numeric(step_rows.get("uv_index"), errors="coerce")
    aqi_series = pd.to_numeric(step_rows.get("air_quality_index"), errors="coerce")

    def _fmt_stat(value: float, digits: int = 1, unit: str = "") -> str:
        return f"{value:.{digits}f}{unit}" if np.isfinite(value) else "--"

    temp_mean = float(temp_series.mean()) if len(temp_series) else np.nan
    temp_min = float(temp_series.min()) if len(temp_series) else np.nan
    temp_max = float(temp_series.max()) if len(temp_series) else np.nan
    wind_mean = float(wind_series.mean()) if len(wind_series) else np.nan
    wind_max = float(wind_series.max()) if len(wind_series) else np.nan
    rh_mean = float(rh_series.mean()) if len(rh_series) else np.nan
    rh_max = float(rh_series.max()) if len(rh_series) else np.nan
    precip_mean = float(precip_series.mean()) if len(precip_series) else np.nan
    precip_max = float(precip_series.max()) if len(precip_series) else np.nan
    pressure_mean = float(pressure_series.mean()) if len(pressure_series) else np.nan
    pressure_min = float(pressure_series.min()) if len(pressure_series) else np.nan
    pressure_max = float(pressure_series.max()) if len(pressure_series) else np.nan
    vis_mean = float(vis_series.mean()) if len(vis_series) else np.nan
    vis_min = float(vis_series.min()) if len(vis_series) else np.nan
    uv_mean = float(uv_series.mean()) if len(uv_series) else np.nan
    uv_max = float(uv_series.max()) if len(uv_series) else np.nan
    aqi_mean = float(aqi_series.mean()) if len(aqi_series) else np.nan
    aqi_max = float(aqi_series.max()) if len(aqi_series) else np.nan

    dir_mean = float("nan")
    valid_dirs = wind_dir_series.dropna().to_numpy(dtype=float)
    if len(valid_dirs) > 0:
        dir_mean = float(np.rad2deg(np.arctan2(np.mean(np.sin(np.deg2rad(valid_dirs))), np.mean(np.cos(np.deg2rad(valid_dirs))))))
        dir_mean = (dir_mean + 360.0) % 360.0

    info_html = f"""
    <div style="
        position: fixed;
        top: 10px; right: 10px;
        z-index: 9999;
        background: rgba(255,255,255,0.96);
        border: 1px solid #d1d5db;
        border-radius: 10px;
        padding: 12px 14px;
        font-family: Microsoft YaHei, sans-serif;
        font-size: 12px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.16);
        width: 360px;
        max-height: 92vh;
        overflow-y: auto;
    ">
      <div style="font-weight:700;font-size:14px;margin-bottom:8px;color:#111827;">无人机概览</div>
      <div style="font-weight:600;color:#1f2937;margin-bottom:4px;">航线信息</div>
      <table style="border-collapse:collapse;width:100%;margin-bottom:8px;">
        <tr><td style="color:#4b5563;">航线名称</td><td><b>{summary["route_name"]}</b></td></tr>
        <tr><td>起点坐标</td><td><b>{summary["route_start"]["lat"]:.5f}, {summary["route_start"]["lon"]:.5f}</b></td></tr>
        <tr><td>终点坐标</td><td><b>{summary["route_end"]["lat"]:.5f}, {summary["route_end"]["lon"]:.5f}</b></td></tr>
        <tr><td>航向角</td><td><b>{summary["route_heading_deg"]:.2f}°</b></td></tr>
        <tr><td>航线长度</td><td><b>{summary["route_length_km"]:.2f} km</b></td></tr>
      </table>
      <div style="font-weight:600;color:#1f2937;margin-bottom:4px;">飞行性能参数</div>
      <table style="border-collapse:collapse;width:100%;margin-bottom:8px;">
        <tr><td>巡航速度</td><td><b>{summary["cruise_speed_mps"]:.1f} m/s</b></td></tr>
        <tr><td>巡航高度</td><td><b>{summary["cruise_altitude_m"]:.1f} m</b></td></tr>
        <tr><td>载荷重量</td><td><b>{summary["payload_g"]:.1f} g</b></td></tr>
        <tr><td>电池容量</td><td><b>{summary["battery_wh"]:.1f} Wh</b></td></tr>
      </table>
      <div style="font-weight:600;color:#1f2937;margin-bottom:4px;">时间与预测数据</div>
      <table style="border-collapse:collapse;width:100%;margin-bottom:8px;">
        <tr><td>起飞时间</td><td><b>{departure_cn}</b></td></tr>
        <tr><td>计划飞行时长</td><td><b>{summary["planned_flight_time_s"]:.2f} s ({summary["planned_flight_time_s"]/60:.1f} 分钟)</b></td></tr>
        <tr><td>预测总能耗</td><td><b>{summary["predicted_total_energy_wh"]:.2f} Wh</b></td></tr>
        <tr><td>预测可达航程</td><td><b>{summary["predicted_range_km"]:.2f} km</b></td></tr>
        <tr><td>预测可飞时长</td><td><b>{summary["predicted_flight_time_s"]:.2f} s</b></td></tr>
        <tr><td>天气数据来源</td><td><b>{summary["weather_source"]}</b></td></tr>
      </table>
      <div style="font-weight:600;color:#1f2937;margin-bottom:4px;">天气概览（沿航线）</div>
      <table style="border-collapse:collapse;width:100%;margin-bottom:8px;">
        <tr><td>风速(均值/最大)</td><td><b>{_fmt_stat(wind_mean, 1)} / {_fmt_stat(wind_max, 1)} m/s</b></td></tr>
        <tr><td>主导风向</td><td><b>{_fmt_stat(dir_mean, 1)}° ({_compass_dir_cn(dir_mean)})</b></td></tr>
        <tr><td>气温(均值/范围)</td><td><b>{_fmt_stat(temp_mean, 1)} °C / {_fmt_stat(temp_min, 1)} ~ {_fmt_stat(temp_max, 1)} °C</b></td></tr>
        <tr><td>湿度(均值/最大)</td><td><b>{_fmt_stat(rh_mean, 1)} / {_fmt_stat(rh_max, 1)} %</b></td></tr>
        <tr><td>降水(均值/最大)</td><td><b>{_fmt_stat(precip_mean, 2)} / {_fmt_stat(precip_max, 2)} mm</b></td></tr>
        <tr><td>气压(均值/范围)</td><td><b>{_fmt_stat(pressure_mean, 1)} hPa / {_fmt_stat(pressure_min, 1)} ~ {_fmt_stat(pressure_max, 1)} hPa</b></td></tr>
        <tr><td>能见度(均值/最低)</td><td><b>{_fmt_stat(vis_mean, 1)} / {_fmt_stat(vis_min, 1)} km</b></td></tr>
        <tr><td>紫外线(均值/峰值)</td><td><b>{_fmt_stat(uv_mean, 1)} / {_fmt_stat(uv_max, 1)} ({_uv_level_cn(uv_max)})</b></td></tr>
        <tr><td>空气质量AQI(均值/峰值)</td><td><b>{_fmt_stat(aqi_mean, 0)} / {_fmt_stat(aqi_max, 0)} ({_aqi_level_cn(aqi_mean)})</b></td></tr>
      </table>
      <div style="font-weight:600;color:#1f2937;margin-bottom:4px;">风险提示</div>
      <ul style="margin:0 0 0 16px;padding:0;">{alert_html}</ul>
    </div>
    """
    m.get_root().html.add_child(folium.Element(info_html))

    folium.LayerControl(collapsed=False).add_to(m)
    output_path = Path(out_html)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    m.save(output_path)
    return output_path
