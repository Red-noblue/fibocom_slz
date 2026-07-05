from __future__ import annotations

"""
replay_dashboard.py

从旧 demo 迁移出的独立回放仪表盘。
它直接消费预测子项目输出的 summary + timeseries 结果。
"""

import argparse
import json
import math
import os
import sys
from collections import deque
from pathlib import Path
from typing import Dict, Tuple

import matplotlib
if sys.platform != "win32" and not os.environ.get("DISPLAY"):
    matplotlib.use("Agg")
import matplotlib.animation as animation
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

matplotlib.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False


BG = "#0d1117"
PANEL_BG = "#161b22"
BORDER = "#30363d"
GREEN = "#3fb950"
RED = "#f85149"
YELLOW = "#d29922"
BLUE = "#58a6ff"
WHITE = "#e6edf3"
GRAY = "#8b949e"


def calculate_physics_features(
    temp_c: float,
    pressure_hpa: float,
    wind_speed: float,
    wind_dir_deg: float,
    heading_deg: float,
) -> Dict[str, float]:
    air_density = (pressure_hpa * 100.0) / (287.05 * (temp_c + 273.15))
    diff = math.radians(wind_dir_deg - heading_deg)
    headwind = wind_speed * math.cos(diff)
    crosswind = abs(wind_speed * math.sin(diff))
    return {
        "air_density": air_density,
        "headwind": headwind,
        "crosswind": crosswind,
    }


def _interp_column(src_x: np.ndarray, src_y: np.ndarray, tgt_x: np.ndarray, default: float) -> np.ndarray:
    valid = np.isfinite(src_y)
    if not np.any(valid):
        return np.full_like(tgt_x, default, dtype=float)
    x = src_x[valid]
    y = src_y[valid]
    if len(x) == 1:
        return np.full_like(tgt_x, float(y[0]), dtype=float)
    return np.interp(tgt_x, x, y)


def load_inputs(
    summary_path: str,
    timeseries_path: str,
    target_steps: int,
    drain_to_zero: bool,
) -> Tuple[Dict, pd.DataFrame]:
    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    df = pd.read_csv(timeseries_path)
    if df.empty:
        raise ValueError("timeseries 为空，无法绘制仪表盘。")

    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df = df.sort_values("time").reset_index(drop=True)
    if df["time"].isna().all():
        # 兼容无时间字段的极端输入
        base = pd.Timestamp.now()
        df["time"] = [base + pd.Timedelta(seconds=i * 10) for i in range(len(df))]

    if "remaining_battery_wh" not in df.columns:
        df["remaining_battery_wh"] = (
            float(summary.get("battery_wh", 0.0)) - df["cumulative_energy_wh"].fillna(0.0)
        ).clip(lower=0.0)

    battery_wh = float(summary.get("battery_wh", 0.0))
    if "battery_remaining_pct" not in df.columns:
        if battery_wh > 0:
            df["battery_remaining_pct"] = (df["remaining_battery_wh"] / battery_wh * 100.0).clip(0.0, 100.0)
        else:
            df["battery_remaining_pct"] = 0.0

    target_steps = max(2, int(target_steps))
    battery_wh = float(summary.get("battery_wh", 0.0))
    route_len_km = float(summary.get("route_length_km", 0.0))
    payload_g = float(summary.get("payload_g", 0.0))
    altitude_m = float(summary.get("cruise_altitude_m", 0.0))
    heading_deg = float(summary.get("route_heading_deg", 0.0))
    pred_total_wh = float(summary.get("predicted_total_energy_wh", np.nan))

    if "distance_from_start_km" in df.columns and np.isfinite(df["distance_from_start_km"]).any():
        src_x = pd.to_numeric(df["distance_from_start_km"], errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(src_x).any() or float(np.nanmax(src_x) - np.nanmin(src_x)) < 1e-9:
            src_x = np.linspace(0.0, max(route_len_km, 1.0), len(df))
    else:
        src_x = np.linspace(0.0, max(route_len_km, 1.0), len(df))

    src_x = np.nan_to_num(src_x, nan=0.0)
    if route_len_km <= 0:
        route_len_km = max(float(np.max(src_x)), 1.0)
    tgt_x = np.linspace(0.0, route_len_km, target_steps)

    wind_base = _interp_column(
        src_x,
        pd.to_numeric(df.get("wind_speed_mps", 0.0), errors="coerce").to_numpy(dtype=float),
        tgt_x,
        default=3.0,
    )
    temp_base = _interp_column(
        src_x,
        pd.to_numeric(df.get("temperature_c", 20.0), errors="coerce").to_numpy(dtype=float),
        tgt_x,
        default=20.0,
    )
    pressure = _interp_column(
        src_x,
        pd.to_numeric(df.get("pressure_hpa", 1013.0), errors="coerce").to_numpy(dtype=float),
        tgt_x,
        default=1013.0,
    )
    wind_dir = _interp_column(
        src_x,
        pd.to_numeric(df.get("wind_dir_deg", heading_deg), errors="coerce").to_numpy(dtype=float),
        tgt_x,
        default=heading_deg,
    )
    pressure_alt = pressure * np.exp(-np.clip(altitude_m, 0.0, 6000.0) / 8434.5)

    planned_s = float(summary.get("planned_flight_time_s", 0.0))
    if not np.isfinite(planned_s) or planned_s <= 0:
        dt_s = df["time"].diff().dt.total_seconds().fillna(0.0).to_numpy(dtype=float)
        median_dt = float(np.median(dt_s[dt_s > 0])) if np.any(dt_s > 0) else 10.0
        planned_s = median_dt * (target_steps - 1)
    step_s = planned_s / max(target_steps - 1, 1)
    start_time = pd.to_datetime(df["time"].iloc[0])
    times = [start_time + pd.Timedelta(seconds=step_s * i) for i in range(target_steps)]

    # 动态波动建模：在插值基线之上叠加周期项、噪声和阵风突变，
    # 让风速/功率/温度在回放时保持连续变化效果。
    step_idx = np.arange(target_steps, dtype=float)
    t_norm = step_idx / max(target_steps - 1, 1)
    seed = int(abs(hash(str(summary.get("route_name", "route")))) % (2**32))
    rng = np.random.default_rng(seed)

    wind_wave = (
        0.90 * np.sin(2.0 * np.pi * (1.2 * t_norm + 0.08))
        + 0.45 * np.sin(2.0 * np.pi * (3.8 * t_norm + 0.31))
    )
    wind_noise = rng.normal(0.0, 0.28, size=target_steps)
    wind = wind_base + wind_wave + wind_noise
    gust_count = max(1, target_steps // 18)
    for _ in range(gust_count):
        center = int(rng.integers(low=4, high=max(5, target_steps - 4)))
        amp = float(rng.uniform(1.8, 3.6))
        width = float(rng.uniform(1.2, 2.4))
        wind += amp * np.exp(-0.5 * ((step_idx - center) / width) ** 2)
    wind = np.clip(wind, 0.0, None)

    # 温度显示改为空中温度：地面温度按巡航高度做 lapse rate 修正后再叠加扰动。
    lapse_rate_c_per_m = 0.0065
    temp_alt_base = temp_base - lapse_rate_c_per_m * np.clip(altitude_m, 0.0, 6000.0)
    temp_wave = (
        0.55 * np.sin(2.0 * np.pi * (0.85 * t_norm + 0.17))
        + 0.30 * np.sin(2.0 * np.pi * (2.9 * t_norm + 0.41))
    )
    temp_noise = rng.normal(0.0, 0.18, size=target_steps)
    temp_alt = temp_alt_base + temp_wave + temp_noise - 0.08 * (wind - np.mean(wind_base))
    temp_alt = np.clip(temp_alt, -35.0, 45.0)
    temp_ground = temp_alt + lapse_rate_c_per_m * np.clip(altitude_m, 0.0, 6000.0)

    rel = np.deg2rad((wind_dir - heading_deg) % 360.0)
    headwind = wind * np.cos(rel)
    crosswind = np.abs(wind * np.sin(rel))
    air_density = (pressure_alt * 100.0) / (287.05 * (temp_alt + 273.15))
    density_factor = np.clip(air_density / 1.225, 0.85, 1.25)

    power_nominal = 360.0 + payload_g * 0.05
    power_base = (
        power_nominal * density_factor
        + np.maximum(headwind, 0.0) * 10.0
        + crosswind * 2.8
        + np.maximum(0.0, 20.0 - temp_alt) * 2.2
        + np.maximum(0.0, temp_alt - 30.0) * 1.8
    )
    power_transient = 10.0 * np.sin(2.0 * np.pi * (2.2 * t_norm + 0.13)) + rng.normal(0.0, 5.0, size=target_steps)
    power_shape_w = np.clip(power_base + power_transient, 80.0, None)

    # 先把天气驱动功率形状与“全程预测总能耗”对齐，再做电池物理放电求解。
    if np.isfinite(pred_total_wh) and pred_total_wh > 0 and planned_s > 1e-6:
        avg_req_w = pred_total_wh * 3600.0 / planned_s
        load_power_w = power_shape_w * (avg_req_w / max(float(np.mean(power_shape_w)), 1e-6))
    else:
        load_power_w = power_shape_w.copy()
    load_power_w = np.clip(load_power_w, 50.0, None)

    # 二阶 Thevenin + 热耦合 + 截止判据（简化版）参数。
    pack_v_nom = float(summary.get("battery_nominal_voltage_v", 15.2))
    pack_v_nom = float(np.clip(pack_v_nom, 6.0, 60.0))
    cell_v_cut = float(summary.get("battery_cutoff_voltage_v", 3.3))
    cell_v_cut = float(np.clip(cell_v_cut, 2.8, 3.6))
    cell_count = int(round(float(summary.get("battery_cell_count", max(1, round(pack_v_nom / 3.8))))))
    cell_count = max(1, cell_count)
    pack_v_cut = cell_v_cut * cell_count
    soc_min = float(np.clip(float(summary.get("battery_soc_min_pct", 2.0)) / 100.0, 0.0, 0.20))
    soh = float(np.clip(float(summary.get("battery_soh", 0.97)), 0.75, 1.05))
    alpha_r = float(np.clip(float(summary.get("battery_alpha_r", 0.65)), 0.0, 2.5))

    q_nom_ah = battery_wh / max(pack_v_nom, 1e-6) if battery_wh > 0 else 0.0
    r0_ref = float(summary.get("battery_r0_ohm", 0.08 if pack_v_nom <= 20.0 else 0.16))
    r1 = float(summary.get("battery_r1_ohm", max(0.008, r0_ref * 0.38)))
    r2 = float(summary.get("battery_r2_ohm", max(0.015, r0_ref * 0.72)))
    c1 = float(summary.get("battery_c1_f", 1850.0))
    c2 = float(summary.get("battery_c2_f", 5200.0))
    c_th = float(summary.get("battery_cth_j_per_c", 280.0))
    h_a = float(summary.get("battery_hA_w_per_c", 2.1))
    alpha_chip = float(summary.get("battery_alpha_chip", 0.12))

    r0_ref = float(np.clip(r0_ref, 0.008, 1.20))
    r1 = float(np.clip(r1, 0.003, 2.00))
    r2 = float(np.clip(r2, 0.005, 3.00))
    c1 = float(np.clip(c1, 200.0, 20000.0))
    c2 = float(np.clip(c2, 500.0, 80000.0))
    c_th = float(np.clip(c_th, 60.0, 4000.0))
    h_a = float(np.clip(h_a, 0.2, 20.0))
    alpha_chip = float(np.clip(alpha_chip, 0.0, 0.8))

    def _simulate_discharge(power_series_w: np.ndarray):
        soc = 1.0
        if not drain_to_zero:
            try:
                soc0 = float(pd.to_numeric(df.get("battery_remaining_pct"), errors="coerce").iloc[0]) / 100.0
                if np.isfinite(soc0):
                    soc = float(np.clip(soc0, 0.0, 1.0))
            except Exception:
                pass

        u1 = 0.0
        u2 = 0.0
        temp_batt = float(temp_alt[0])

        rem_wh_arr = np.zeros(target_steps, dtype=float)
        seg_wh_arr = np.zeros(target_steps, dtype=float)
        curr_arr = np.zeros(target_steps, dtype=float)
        vterm_arr = np.zeros(target_steps, dtype=float)
        voc_arr = np.zeros(target_steps, dtype=float)
        temp_batt_arr = np.zeros(target_steps, dtype=float)
        delta_arr = np.zeros(target_steps, dtype=float)
        collapse_arr = np.zeros(target_steps, dtype=float)

        prev_rem_wh = soc * max(battery_wh, 0.0)
        for i in range(target_steps):
            p_req = float(max(power_series_w[i], 1.0))
            t_amb = float(temp_alt[i])

            cold_factor = float(np.exp(np.clip((15.0 - temp_batt) / 18.0, -1.2, 2.2)))
            hot_factor = 1.0 + 0.018 * max(0.0, temp_batt - 38.0)
            soc_factor = 1.0 + 0.36 * ((1.0 - soc) ** 1.6)
            r0_base = r0_ref * soc_factor * cold_factor * hot_factor
            r0 = float(np.clip(r0_base * (1.0 + alpha_r * (1.0 - soh)), 0.004, 3.0))

            ocv_cell = 3.0 + 1.18 * soc + 0.04 * math.tanh((temp_batt - 20.0) / 9.0)
            ocv = float(np.clip(ocv_cell, 3.0, 4.24) * cell_count)
            voc = max(ocv - u1 - u2, pack_v_cut + 0.05)

            delta = voc * voc - 4.0 * r0 * p_req
            p_max = (voc * voc) / max(4.0 * r0, 1e-9)
            unmet_ratio = max(0.0, (p_req - p_max) / max(p_req, 1e-9))
            if delta > 0.0:
                i_batt = (voc - math.sqrt(delta)) / max(2.0 * r0, 1e-9)
            else:
                i_batt = voc / max(2.0 * r0, 1e-9)
            i_batt = float(np.clip(i_batt, 0.0, 300.0))

            v_term = max(voc - i_batt * r0, 0.0)
            p_term = v_term * i_batt

            u1 += step_s * (-u1 / max(r1 * c1, 1e-9) + i_batt / max(c1, 1e-9))
            u2 += step_s * (-u2 / max(r2 * c2, 1e-9) + i_batt / max(c2, 1e-9))

            heat_w = i_batt * i_batt * r0 + alpha_chip * p_term
            temp_batt += step_s * (heat_w - h_a * (temp_batt - t_amb)) / max(c_th, 1e-9)
            temp_batt = float(np.clip(temp_batt, -25.0, 75.0))

            kq_t = math.exp(-0.018 * max(0.0, 15.0 - temp_batt)) * (1.0 - 0.002 * max(0.0, temp_batt - 35.0))
            kq_t = float(np.clip(kq_t, 0.52, 1.06))
            c_rate = i_batt / max(q_nom_ah, 1e-9) if q_nom_ah > 0 else 0.0
            k_c = 1.0 / (1.0 + 0.09 * max(0.0, c_rate - 1.0))
            q_eff_ah = max(q_nom_ah * soh * kq_t * k_c, 1e-6)

            soc_drop = (i_batt * step_s) / (q_eff_ah * 3600.0)
            if delta <= 0.0:
                soc_drop *= 1.0 + 1.8 * unmet_ratio
            soc = float(np.clip(soc - soc_drop, 0.0, 1.0))

            rem_wh = float(np.clip(soc * max(battery_wh, 0.0), 0.0, max(battery_wh, 0.0)))
            seg_wh = max(0.0, prev_rem_wh - rem_wh)
            prev_rem_wh = rem_wh

            rem_wh_arr[i] = rem_wh
            seg_wh_arr[i] = seg_wh
            curr_arr[i] = i_batt
            vterm_arr[i] = v_term
            voc_arr[i] = voc
            temp_batt_arr[i] = temp_batt
            delta_arr[i] = delta
            collapse_arr[i] = 1.0 if (delta <= 0.0 or v_term <= pack_v_cut or soc <= soc_min) else 0.0

        return {
            "remaining_wh": rem_wh_arr,
            "segment_wh": seg_wh_arr,
            "current_a": curr_arr,
            "vterm_v": vterm_arr,
            "voc_v": voc_arr,
            "temp_batt_c": temp_batt_arr,
            "delta_margin": delta_arr,
            "collapse_flag": collapse_arr,
            "soc_end": float(rem_wh_arr[-1] / max(battery_wh, 1e-9)) if battery_wh > 0 else 0.0,
        }

    scale = 1.0
    if drain_to_zero and battery_wh > 1e-9:
        soc_target_end = 5e-4
        low, high = 0.10, 1.0
        end_soc_high = _simulate_discharge(load_power_w * high)["soc_end"]
        grow_iter = 0
        while end_soc_high > soc_target_end and grow_iter < 14:
            high *= 1.7
            end_soc_high = _simulate_discharge(load_power_w * high)["soc_end"]
            grow_iter += 1

        if end_soc_high <= soc_target_end:
            for _ in range(18):
                mid = 0.5 * (low + high)
                end_soc_mid = _simulate_discharge(load_power_w * mid)["soc_end"]
                if end_soc_mid > soc_target_end:
                    low = mid
                else:
                    high = mid
            scale = high
        else:
            scale = high

    instant_power_w = load_power_w * scale
    sim = _simulate_discharge(instant_power_w)
    remaining_wh = sim["remaining_wh"].copy()
    if drain_to_zero and battery_wh > 0:
        remaining_wh[0] = max(battery_wh, 0.0)
        remaining_wh[-1] = 0.0
    cumulative_wh = np.clip(max(battery_wh, 0.0) - remaining_wh, 0.0, max(battery_wh, 0.0))
    segment_wh = np.diff(np.insert(cumulative_wh, 0, 0.0))
    battery_pct = np.divide(
        remaining_wh * 100.0,
        battery_wh if battery_wh > 0 else 1.0,
        out=np.zeros_like(remaining_wh),
        where=(battery_wh > 0),
    )
    battery_pct = np.clip(battery_pct, 0.0, 100.0)

    replay = pd.DataFrame(
        {
            "time": times,
            "distance_from_start_km": tgt_x,
            "wind_speed_mps": wind,
            "temperature_c": temp_alt,
            "temperature_ground_c": temp_ground,
            "pressure_hpa": pressure_alt,
            "wind_dir_deg": wind_dir,
            "headwind_mps": headwind,
            "crosswind_mps": crosswind,
            "air_density": air_density,
            "segment_energy_wh": segment_wh,
            "cumulative_energy_wh": cumulative_wh,
            "remaining_battery_wh": remaining_wh,
            "battery_remaining_pct": battery_pct,
            "instant_power_w": instant_power_w,
            "battery_current_a": sim["current_a"],
            "battery_terminal_voltage_v": sim["vterm_v"],
            "battery_effective_ocv_v": sim["voc_v"],
            "battery_core_temp_c": sim["temp_batt_c"],
            "power_margin_delta": sim["delta_margin"],
            "collapse_flag": sim["collapse_flag"],
        }
    )

    return summary, replay


class FlightPlaybackDashboard:
    MAX_POINTS = 80

    def __init__(self, summary: Dict, timeseries: pd.DataFrame, interval_ms: int, loop: bool):
        self.summary = summary
        self.ts = timeseries
        self.interval_ms = interval_ms
        self.loop = loop
        self.step = 0

        self.route_name = str(summary.get("route_name", "unknown_route"))
        self.route_len_km = float(summary.get("route_length_km", 0.0))
        self.heading_deg = float(summary.get("route_heading_deg", 0.0))
        self.speed_mps = float(summary.get("cruise_speed_mps", 0.0))
        self.altitude_m = float(summary.get("cruise_altitude_m", 0.0))
        self.payload_g = float(summary.get("payload_g", 0.0))
        self.battery_wh = float(summary.get("battery_wh", 0.0))
        self.pred_total_wh = float(summary.get("predicted_total_energy_wh", 0.0))
        self.pred_range_km = float(summary.get("predicted_range_km", 0.0))
        self.pred_time_s = float(summary.get("predicted_flight_time_s", 0.0))

        self.t_buf = deque(maxlen=self.MAX_POINTS)
        self.power_buf = deque(maxlen=self.MAX_POINTS)
        self.batt_buf = deque(maxlen=self.MAX_POINTS)
        self.wind_buf = deque(maxlen=self.MAX_POINTS)
        self.temp_buf = deque(maxlen=self.MAX_POINTS)

        self._build_figure()

    def _build_figure(self) -> None:
        self.fig = plt.figure(figsize=(16, 9), facecolor=BG)
        manager = getattr(self.fig.canvas, "manager", None)
        if manager is not None and hasattr(manager, "set_window_title"):
            manager.set_window_title("无人机飞行实时仪表盘（回放）")

        outer = gridspec.GridSpec(
            1,
            2,
            figure=self.fig,
            left=0.01,
            right=0.99,
            top=0.93,
            bottom=0.06,
            wspace=0.04,
            width_ratios=[1.05, 2.8],
        )

        left_gs = gridspec.GridSpecFromSubplotSpec(3, 1, subplot_spec=outer[0], hspace=0.08)
        self.ax_info = self.fig.add_subplot(left_gs[0])
        self.ax_gauge = self.fig.add_subplot(left_gs[1])
        self.ax_status = self.fig.add_subplot(left_gs[2])

        right_gs = gridspec.GridSpecFromSubplotSpec(2, 2, subplot_spec=outer[1], hspace=0.35, wspace=0.28)
        self.ax_power = self.fig.add_subplot(right_gs[0, 0])
        self.ax_batt = self.fig.add_subplot(right_gs[0, 1])
        self.ax_wind = self.fig.add_subplot(right_gs[1, 0])
        self.ax_temp = self.fig.add_subplot(right_gs[1, 1])

        for ax in [
            self.ax_info,
            self.ax_gauge,
            self.ax_status,
            self.ax_power,
            self.ax_batt,
            self.ax_wind,
            self.ax_temp,
        ]:
            ax.set_facecolor(PANEL_BG)
            for spine in ax.spines.values():
                spine.set_edgecolor(BORDER)
            ax.tick_params(colors=GRAY, labelsize=8)
            ax.xaxis.label.set_color(GRAY)
            ax.yaxis.label.set_color(GRAY)

        self.fig.text(
            0.5,
            0.97,
            f"{self.route_name}   无人机飞行实时仪表盘回放",
            ha="center",
            va="top",
            fontsize=13,
            fontweight="bold",
            color=WHITE,
        )

        self._init_info_panel()
        self._init_gauge_panel()
        self._init_status_panel()
        self._init_line_charts()

    def _init_info_panel(self) -> None:
        ax = self.ax_info
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.set_title("任务信息", color=WHITE, fontsize=10, fontweight="bold", pad=6, loc="left")

        row0 = self.ts.iloc[0]
        phys = calculate_physics_features(
            temp_c=float(row0.get("temperature_c", 20.0)),
            pressure_hpa=float(row0.get("pressure_hpa", 1013.0)),
            wind_speed=float(row0.get("wind_speed_mps", 0.0)),
            wind_dir_deg=float(row0.get("wind_dir_deg", 0.0)),
            heading_deg=self.heading_deg,
        )

        lines = [
            ("航线", self.route_name),
            ("距离", f"{self.route_len_km:.2f} km"),
            ("速度", f"{self.speed_mps:.1f} m/s   高度 {self.altitude_m:.1f} m"),
            ("载荷", f"{self.payload_g:.1f} g"),
            ("电池", f"{self.battery_wh:.1f} Wh"),
            ("预测总能耗", f"{self.pred_total_wh:.2f} Wh"),
            ("预测航程", f"{self.pred_range_km:.2f} km"),
            ("预测时长", f"{self.pred_time_s:.1f} s"),
            ("空气密度", f"{phys['air_density']:.4f} kg/m3"),
        ]
        for i, (k, v) in enumerate(lines):
            y = 0.95 - i * 0.105
            ax.text(0.02, y, k, color=GRAY, fontsize=8, va="top")
            ax.text(0.40, y, v, color=WHITE, fontsize=8, va="top", fontweight="bold")

    def _init_gauge_panel(self) -> None:
        ax = self.ax_gauge
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.set_title("电池状态", color=WHITE, fontsize=10, fontweight="bold", pad=6, loc="left")

        ax.add_patch(
            FancyBboxPatch((0.05, 0.55), 0.90, 0.22, boxstyle="round,pad=0.01", fc=BORDER, ec=BORDER, zorder=1)
        )
        self.battery_bar = ax.add_patch(
            FancyBboxPatch((0.05, 0.55), 0.90, 0.22, boxstyle="round,pad=0.01", fc=GREEN, ec="none", zorder=2)
        )
        self.battery_pct_text = ax.text(
            0.50, 0.66, "100%", ha="center", va="center", fontsize=16, fontweight="bold", color=WHITE, zorder=3
        )
        self.battery_label = ax.text(
            0.50, 0.38, f"剩余 {self.battery_wh:.1f} Wh / {self.battery_wh:.1f} Wh", ha="center", va="center", fontsize=9, color=GRAY
        )
        self.warn_text = ax.text(0.50, 0.15, "", ha="center", va="center", fontsize=10, fontweight="bold", color=RED)

    def _init_status_panel(self) -> None:
        ax = self.ax_status
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.set_title("飞行状态", color=WHITE, fontsize=10, fontweight="bold", pad=6, loc="left")

        self.state_text = ax.text(0.50, 0.80, "回放中", ha="center", va="center", fontsize=22, fontweight="bold", color=GREEN)
        self.current_text = ax.text(0.50, 0.56, "--", ha="center", va="center", fontsize=8, color=WHITE)
        self.progress_text = ax.text(0.50, 0.18, "进度: 0.0%", ha="center", va="center", fontsize=10, color=GRAY)
        self.phase_text = ax.text(0.50, 0.04, "阶段2：飞行中监控回放", ha="center", va="center", fontsize=8.5, color=YELLOW)

    def _init_line_charts(self) -> None:
        wind_ymax = max(9.5, 8.0 * 1.25, float(self.ts["wind_speed_mps"].max()) * 1.30)
        temp_ymin = min(float(self.ts["temperature_c"].min()) - 2.0, -5.0)
        temp_ymax = max(float(self.ts["temperature_c"].max()) + 2.0, 42.0)
        configs = [
            (self.ax_power, "瞬时功率 (W)", BLUE, 0, max(20.0, float(self.ts["instant_power_w"].max()) * 1.2)),
            (self.ax_batt, "剩余电量 (Wh)", GREEN, 0, max(10.0, self.battery_wh * 1.05)),
            (self.ax_wind, "风速 (m/s)", YELLOW, 0, wind_ymax),
            (self.ax_temp, "温度 (°C)", "#ff7b72", temp_ymin, temp_ymax),
        ]
        self.lines = {}
        for ax, title, color, ymin, ymax in configs:
            ax.set_title(title, color=WHITE, fontsize=9, fontweight="bold", pad=4, loc="left")
            ax.set_xlim(0, self.MAX_POINTS)
            ax.set_ylim(ymin, ymax)
            ax.set_xlabel("时间步", fontsize=7.5)
            ax.grid(True, color=BORDER, linewidth=0.5, alpha=0.6)
            line, = ax.plot([], [], color=color, linewidth=1.8, solid_capstyle="round")
            self.lines[title] = line

        self.ax_batt.axhline(y=max(0.0, self.battery_wh * 0.2), color=RED, linewidth=1, linestyle="--", alpha=0.6, label="20%警戒")
        self.ax_wind.axhline(y=8.0, color=RED, linewidth=1, linestyle="--", alpha=0.7, label="风速上限 8 m/s")
        self.ax_temp.axhline(y=0.0, color=YELLOW, linewidth=1, linestyle="--", alpha=0.7, label="温度下限 0°C")
        self.ax_temp.axhline(y=38.0, color=RED, linewidth=1, linestyle="--", alpha=0.7, label="温度上限 38°C")
        for ax in [self.ax_batt, self.ax_wind, self.ax_temp]:
            ax.legend(fontsize=6.5, loc="upper right", facecolor=PANEL_BG, edgecolor=BORDER, labelcolor=GRAY)

    def _advance_step(self) -> bool:
        if self.step >= len(self.ts):
            if self.loop:
                self.step = 0
            else:
                return False
        return True

    def update(self, _frame: int) -> None:
        if not self._advance_step():
            self.phase_text.set_text("飞行完成")
            self.phase_text.set_color(GREEN)
            return

        row = self.ts.iloc[self.step]
        dist_km = float(row.get("distance_from_start_km", 0.0))
        progress = (dist_km / self.route_len_km * 100.0) if self.route_len_km > 0 else 0.0

        power_w = float(row.get("instant_power_w", 0.0))
        battery_wh = max(0.0, float(row.get("remaining_battery_wh", 0.0)))
        if self.battery_wh > 0:
            battery_pct = float(np.clip(row.get("battery_remaining_pct", battery_wh / self.battery_wh * 100.0), 0.0, 100.0))
        else:
            battery_pct = 0.0
        wind_speed = float(row.get("wind_speed_mps", 0.0))
        temp_c = float(row.get("temperature_c", 0.0))
        time_str = str(pd.to_datetime(row.get("time")).strftime("%Y-%m-%d %H:%M:%S"))

        is_warn = (battery_pct < 20.0) or (wind_speed > 8.0) or (temp_c < 0.0) or (temp_c > 38.0)

        self.t_buf.append(self.step + 1)
        self.power_buf.append(power_w)
        self.batt_buf.append(battery_wh)
        self.wind_buf.append(wind_speed)
        self.temp_buf.append(temp_c)

        xs = list(range(len(self.t_buf)))
        self.lines["瞬时功率 (W)"].set_data(xs, list(self.power_buf))
        self.lines["剩余电量 (Wh)"].set_data(xs, list(self.batt_buf))
        self.lines["风速 (m/s)"].set_data(xs, list(self.wind_buf))
        self.lines["温度 (°C)"].set_data(xs, list(self.temp_buf))

        self.lines["瞬时功率 (W)"].set_color(RED if is_warn else BLUE)
        self.lines["风速 (m/s)"].set_color(RED if wind_speed > 8.0 else YELLOW)
        self.lines["温度 (°C)"].set_color(RED if (temp_c < 0.0 or temp_c > 38.0) else "#ff7b72")
        for ax in [self.ax_power, self.ax_batt, self.ax_wind, self.ax_temp]:
            ax.set_facecolor("#2d1b1b" if is_warn else PANEL_BG)

        bar_width = 0.90 * (battery_pct / 100.0)
        self.battery_bar.set_width(max(0.0, bar_width))
        bar_color = RED if battery_pct < 20 else (YELLOW if battery_pct < 40 else GREEN)
        self.battery_bar.set_facecolor(bar_color)
        self.battery_pct_text.set_text(f"{battery_pct:.1f}%")
        self.battery_pct_text.set_color(bar_color)
        self.battery_label.set_text(f"剩余 {battery_wh:.2f} Wh / {self.battery_wh:.1f} Wh")
        self.warn_text.set_text("!! 飞行预警 !!" if is_warn else "")

        state = "预警" if is_warn else "可飞"
        self.state_text.set_text(state)
        self.state_text.set_color(RED if is_warn else GREEN)
        self.current_text.set_text(f"{time_str}\n风速 {wind_speed:.2f}m/s | 温度 {temp_c:.1f}°C")
        self.progress_text.set_text(f"进度: {progress:.1f}%   位置: {dist_km:.2f}/{self.route_len_km:.2f} km")

        self.step += 1

    def run(self) -> None:
        self.ani = animation.FuncAnimation(
            self.fig,
            self.update,
            frames=max(len(self.ts), 1),
            interval=self.interval_ms,
            repeat=self.loop,
        )
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        plt.show()

    def render_preview(self, output_path: str | Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.step = 0
        self.update(0)
        self.fig.tight_layout(rect=[0, 0, 1, 0.95])
        self.fig.savefig(output_path, dpi=150, facecolor=self.fig.get_facecolor())
        plt.close(self.fig)
        return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="无人机实时仪表盘回放（基于 realtime_route_demo 输出）")
    parser.add_argument("--summary", default="outputs/realtime/realtime_route_summary.json")
    parser.add_argument("--timeseries", default="outputs/realtime/realtime_route_timeseries.csv")
    parser.add_argument("--steps", type=int, default=40, help="回放步数（默认 40）")
    parser.add_argument("--interval", type=float, default=1.0, help="更新间隔（秒）")
    parser.add_argument("--no-drain-to-zero", action="store_true", help="不强制电量从 100%% 下滑到 0%%")
    parser.add_argument("--loop", action="store_true", help="回放结束后循环")
    parser.add_argument("--preview-png", default=None, help="保存首帧预览 PNG，而不是打开交互式窗口")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary_path = Path(args.summary)
    timeseries_path = Path(args.timeseries)
    if not summary_path.exists() or not timeseries_path.exists():
        raise FileNotFoundError(
            f"未找到回放输入文件：\n- {summary_path}\n- {timeseries_path}\n请先运行预测子项目生成 summary 和 timeseries。"
        )

    summary, ts = load_inputs(
        str(summary_path),
        str(timeseries_path),
        target_steps=args.steps,
        drain_to_zero=not args.no_drain_to_zero,
    )
    dashboard = FlightPlaybackDashboard(
        summary=summary,
        timeseries=ts,
        interval_ms=max(100, int(args.interval * 1000)),
        loop=args.loop,
    )
    if args.preview_png:
        preview_path = dashboard.render_preview(args.preview_png)
        print(f"dashboard preview saved to: {preview_path}")
    else:
        dashboard.run()


if __name__ == "__main__":
    main()
