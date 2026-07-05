#!/usr/bin/env python3
"""中文说明：将 UAV 城市航线采样点导出为无线电地图模型可读取的局部输入样本。"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_virtual_validation.artifacts.io import write_json
from uav_virtual_validation.simulators.simple import haversine_m
from uav_virtual_validation.world.geo import GeoOrigin, latlon_to_meters, meters_to_latlon


DEFAULT_M2_FEATURE_DIR = (
    REPO_ROOT
    / "modules/radio-map-estimation-workbench/modules/m2/runs/datas/features/v1_base_256_k1_landuse3"
)
DEFAULT_REAL_CITY_ROOT = ROOT / "outputs/real_city"
DEFAULT_OUTPUT_ROOT = ROOT / "outputs/radio_route_inputs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导出 UAV 航线中心局部无线电地图输入样本。")
    parser.add_argument("--city", default="manhattan_midtown", help="real_city 下的城市目录名。")
    parser.add_argument("--city-dir", default="", help="显式指定城市资产目录，优先于 --city。")
    parser.add_argument("--route", default="", help="显式指定 route.geojson 或航线草稿 geojson。")
    parser.add_argument("--output-dir", default="", help="输出目录，默认 outputs/radio_route_inputs/<城市>。")
    parser.add_argument("--m2-feature-dir", default=str(DEFAULT_M2_FEATURE_DIR), help="M2 特征目录，用于读取统计和通道契约。")
    parser.add_argument("--grid-size", type=int, default=256, help="模型输入栅格尺寸，默认 256。")
    parser.add_argument("--pixel-size-m", type=float, default=1.0, help="输出栅格米/像素，默认与 M2 一致为 1m。")
    parser.add_argument("--sample-step-m", type=float, default=160.0, help="沿航线采样间隔，默认 160m。")
    parser.add_argument("--max-samples", type=int, default=24, help="最大导出样本数，避免一次生成过多。")
    parser.add_argument("--tx-position", choices=["center", "route_point"], default="center", help="Tx 脉冲位置；默认固定在局部图中心。")
    parser.add_argument(
        "--road-mode",
        choices=["merge_to_other", "keep"],
        default="merge_to_other",
        help="道路通道处理方式；UAV 高度切片默认将道路合并到 other，避免地面道路被模型误判为负面阻挡。",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def route_coords(route_path: Path) -> list[list[float]]:
    geo = read_json(route_path)
    feature = (geo.get("features") or [None])[0]
    if not feature or feature.get("geometry", {}).get("type") != "LineString":
        raise ValueError(f"航线必须是 LineString GeoJSON：{route_path}")
    coords = feature["geometry"].get("coordinates") or []
    if len(coords) < 2:
        raise ValueError("航线至少需要两个航点。")
    return [[float(c[0]), float(c[1]), float(c[2] if len(c) > 2 else 120.0)] for c in coords]


def interpolate_route(coords: list[list[float]], step_m: float, max_samples: int) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    total = 0.0
    for idx in range(1, len(coords)):
        prev = coords[idx - 1]
        cur = coords[idx]
        length = haversine_m(prev[1], prev[0], cur[1], cur[0])
        segments.append({"start": prev, "end": cur, "length_m": length, "offset_m": total})
        total += length
    if total <= 0:
        raise ValueError("航线长度无效。")
    count = max(2, min(max_samples, int(math.floor(total / max(step_m, 1.0))) + 1))
    distances = np.linspace(0.0, total, count, dtype=np.float64).tolist()
    samples: list[dict[str, Any]] = []
    seg_idx = 0
    for sample_idx, dist in enumerate(distances):
        while seg_idx < len(segments) - 1 and dist > segments[seg_idx]["offset_m"] + segments[seg_idx]["length_m"]:
            seg_idx += 1
        seg = segments[seg_idx]
        frac = 0.0 if seg["length_m"] <= 0 else (dist - seg["offset_m"]) / seg["length_m"]
        frac = max(0.0, min(1.0, frac))
        start = seg["start"]
        end = seg["end"]
        lon = start[0] + (end[0] - start[0]) * frac
        lat = start[1] + (end[1] - start[1]) * frac
        alt = start[2] + (end[2] - start[2]) * frac
        samples.append({
            "sample_idx": sample_idx,
            "distance_along_route_m": round(float(dist), 3),
            "lon": round(float(lon), 7),
            "lat": round(float(lat), 7),
            "altitude_m": round(float(alt), 2),
        })
    return samples


def point_in_ring(x: float, y: float, ring_xy: list[tuple[float, float]]) -> bool:
    inside = False
    for idx in range(len(ring_xy) - 1):
        x1, y1 = ring_xy[idx]
        x2, y2 = ring_xy[idx + 1]
        if (y1 > y) != (y2 > y):
            cross_x = (x2 - x1) * (y - y1) / (y2 - y1 + 1e-30) + x1
            if x < cross_x:
                inside = not inside
    return inside


def rasterize_polygon(mask: np.ndarray, ring_xy: list[tuple[float, float]], cx: int, cy: int) -> None:
    h, w = mask.shape
    xs = [pt[0] for pt in ring_xy]
    ys = [pt[1] for pt in ring_xy]
    x0 = max(0, int(math.floor(min(xs) + cx)))
    x1 = min(w - 1, int(math.ceil(max(xs) + cx)))
    y0 = max(0, int(math.floor(cy - max(ys))))
    y1 = min(h - 1, int(math.ceil(cy - min(ys))))
    if x0 > x1 or y0 > y1:
        return
    for py in range(y0, y1 + 1):
        local_y = cy - py
        for px in range(x0, x1 + 1):
            local_x = px - cx
            if point_in_ring(local_x, local_y, ring_xy):
                mask[py, px] = 1.0


def rasterize_line(mask: np.ndarray, points_xy: list[tuple[float, float]], cx: int, cy: int, width_px: int) -> None:
    h, w = mask.shape
    radius = max(1, int(width_px))
    for idx in range(1, len(points_xy)):
        x0, y0 = points_xy[idx - 1]
        x1, y1 = points_xy[idx]
        length = max(1.0, math.hypot(x1 - x0, y1 - y0))
        steps = max(1, int(length * 1.5))
        for step in range(steps + 1):
            frac = step / steps
            px = int(round(cx + x0 + (x1 - x0) * frac))
            py = int(round(cy - (y0 + (y1 - y0) * frac)))
            for oy in range(-radius, radius + 1):
                for ox in range(-radius, radius + 1):
                    if ox * ox + oy * oy <= radius * radius:
                        qx = px + ox
                        qy = py + oy
                        if 0 <= qx < w and 0 <= qy < h:
                            mask[qy, qx] = 1.0


def load_building_features(path: Path) -> list[dict[str, Any]]:
    geo = read_json(path)
    return [
        feature
        for feature in geo.get("features", [])
        if feature.get("geometry", {}).get("type") == "Polygon"
        and len(feature.get("geometry", {}).get("coordinates", [[]])[0]) >= 4
    ]


def load_road_features(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    geo = read_json(path)
    return [
        feature
        for feature in geo.get("features", [])
        if feature.get("properties", {}).get("layer") == "road"
        and feature.get("geometry", {}).get("type") == "LineString"
    ]


def feature_ring_local(origin: GeoOrigin, ring: list[list[float]], pixel_size_m: float) -> list[tuple[float, float]]:
    return [
        tuple(value / pixel_size_m for value in latlon_to_meters(origin, float(lat), float(lon)))
        for lon, lat in ring
    ]


def feature_line_local(origin: GeoOrigin, coords: list[list[float]], pixel_size_m: float) -> list[tuple[float, float]]:
    return [
        tuple(value / pixel_size_m for value in latlon_to_meters(origin, float(lat), float(lon)))
        for lon, lat in coords
    ]


def build_land_channels(
    origin: GeoOrigin,
    buildings: list[dict[str, Any]],
    roads: list[dict[str, Any]],
    grid_size: int,
    pixel_size_m: float,
    uav_altitude_m: float,
    road_mode: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, int]]:
    bld = np.zeros((grid_size, grid_size), dtype=np.float32)
    road = np.zeros((grid_size, grid_size), dtype=np.float32)
    center = grid_size // 2
    used_buildings = 0
    skipped_below_uav_altitude = 0
    used_roads = 0
    half_span = grid_size * pixel_size_m / 2.0
    for feature in buildings:
        ring = feature["geometry"]["coordinates"][0]
        local = feature_ring_local(origin, ring, pixel_size_m)
        if not local:
            continue
        if max(abs(x) for x, _ in local) > half_span + 80 or max(abs(y) for _, y in local) > half_span + 80:
            continue
        height_m = float(feature.get("properties", {}).get("height_m") or 0.0)
        if height_m < uav_altitude_m:
            skipped_below_uav_altitude += 1
            continue
        rasterize_polygon(bld, local, center, center)
        used_buildings += 1
    for feature in roads:
        coords = feature["geometry"]["coordinates"]
        local = feature_line_local(origin, coords, pixel_size_m)
        if not local:
            continue
        if max(abs(x) for x, _ in local) > half_span + 80 or max(abs(y) for _, y in local) > half_span + 80:
            continue
        width_px = int(round(float(feature.get("properties", {}).get("width_px") or 2.0)))
        rasterize_line(road, local, center, center, width_px=max(1, width_px))
        used_roads += 1
    road = np.where(bld > 0, 0.0, road).astype(np.float32)
    road_pixels_merged_to_other = 0
    if road_mode == "merge_to_other":
        road_pixels_merged_to_other = int(road.sum())
        road = np.zeros_like(road, dtype=np.float32)
    other = (1.0 - np.clip(bld + road, 0.0, 1.0)).astype(np.float32)
    return bld, road, other, {
        "buildings_in_window": used_buildings,
        "buildings_skipped_below_uav_altitude": skipped_below_uav_altitude,
        "uav_altitude_filter_m": round(float(uav_altitude_m), 2),
        "roads_in_window": used_roads,
        "road_mode": road_mode,
        "road_pixels_merged_to_other": road_pixels_merged_to_other,
    }


def compute_dist_dir(grid_size: int, tx_xy: tuple[int, int], pixel_size_m: float, dmin: float, dmax: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x_tx, y_tx = tx_xy
    yy, xx = np.indices((grid_size, grid_size))
    dx = (xx - x_tx).astype(np.float32)
    dy = (yy - y_tx).astype(np.float32)
    dist_m = np.sqrt(dx * dx + dy * dy, dtype=np.float32) * float(pixel_size_m)
    ang = np.arctan2(dy, dx).astype(np.float32)
    sinv = np.sin(ang).astype(np.float32)
    cosv = np.cos(ang).astype(np.float32)
    dn = (dist_m - dmin) / max(1e-6, dmax - dmin)
    return np.clip(dn, 0.0, 1.0).astype(np.float32), sinv, cosv


def main() -> int:
    args = parse_args()
    city_dir = Path(args.city_dir) if args.city_dir else DEFAULT_REAL_CITY_ROOT / args.city
    route_path = Path(args.route) if args.route else city_dir / "route.geojson"
    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_OUTPUT_ROOT / city_dir.name
    m2_dir = Path(args.m2_feature_dir)
    stats = read_json(m2_dir / "stats.json")
    feature_spec = read_json(m2_dir / "feature_spec.json")
    dstat = stats.get("features", {}).get("dist_to_tx_m", {})
    dmin = float(dstat.get("min", 0.0))
    dmax = float(dstat.get("max", math.sqrt(2) * args.grid_size * args.pixel_size_m))
    if not city_dir.exists():
        raise FileNotFoundError(f"城市目录不存在：{city_dir}")
    buildings = load_building_features(city_dir / "real_buildings.geojson")
    roads = load_road_features(city_dir / "ground_layers.geojson")
    coords = route_coords(route_path)
    route_samples = interpolate_route(coords, args.sample_step_m, args.max_samples)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    manifest_samples: list[dict[str, Any]] = []
    center_px = args.grid_size // 2
    for item in route_samples:
        origin = GeoOrigin(float(item["lat"]), float(item["lon"]))
        bld, road, other, counts = build_land_channels(
            origin,
            buildings,
            roads,
            args.grid_size,
            args.pixel_size_m,
            float(item["altitude_m"]),
            args.road_mode,
        )
        tx_xy = (center_px, center_px) if args.tx_position == "center" else (center_px, center_px)
        tx_impulse = np.zeros((args.grid_size, args.grid_size), dtype=np.float32)
        tx_impulse[tx_xy[1], tx_xy[0]] = 1.0
        dist_norm, dir_sin, dir_cos = compute_dist_dir(args.grid_size, tx_xy, args.pixel_size_m, dmin, dmax)
        x = np.stack([bld, road, other, tx_impulse, dist_norm, dir_sin, dir_cos], axis=0).astype(np.float32)
        valid_mask = np.ones((args.grid_size, args.grid_size), dtype=bool)
        sample_id = f"{city_dir.name}_route_{item['sample_idx']:04d}"
        npz_path = output_dir / f"{sample_id}.npz"
        np.savez_compressed(npz_path, X=x, valid_mask=valid_mask)
        lat_south, lon_west = meters_to_latlon(origin, -args.grid_size * args.pixel_size_m / 2.0, -args.grid_size * args.pixel_size_m / 2.0)
        lat_north, lon_east = meters_to_latlon(origin, args.grid_size * args.pixel_size_m / 2.0, args.grid_size * args.pixel_size_m / 2.0)
        sample_meta = {
            **item,
            "sample_id": sample_id,
            "npz": npz_path.name,
            "shape": [7, args.grid_size, args.grid_size],
            "pixel_size_m": args.pixel_size_m,
            "tx_pixel_xy": [tx_xy[0], tx_xy[1]],
            "window_bbox": {"south": lat_south, "west": lon_west, "north": lat_north, "east": lon_east},
            "counts": counts,
            "channel_sums": {
                "land_building": float(bld.sum()),
                "land_road": float(road.sum()),
                "land_other": float(other.sum()),
                "tx_impulse": float(tx_impulse.sum()),
            },
        }
        manifest_samples.append(sample_meta)
        rows.append({
            "sample_id": sample_id,
            "city": city_dir.name,
            "sample_idx": item["sample_idx"],
            "lon": item["lon"],
            "lat": item["lat"],
            "altitude_m": item["altitude_m"],
            "distance_along_route_m": item["distance_along_route_m"],
            "npz": npz_path.name,
            "H": args.grid_size,
            "W": args.grid_size,
            "C": 7,
        })
    manifest = {
        "schema": "uav_route_radio_inputs_v1",
        "purpose": "UAV-centered local radio-map model inputs",
        "city": city_dir.name,
        "city_dir": str(city_dir),
        "route": str(route_path),
        "output_dir": str(output_dir),
        "m2_feature_dir": str(m2_dir),
        "feature_contract": {
            "shape": [7, args.grid_size, args.grid_size],
            "channels": feature_spec.get("channels", []),
            "distance_norm": {"min": dmin, "max": dmax, "source": str(m2_dir / "stats.json")},
            "label_y_dbm": stats.get("label_y_dbm", {}),
        },
        "sampling": {
            "sample_step_m": args.sample_step_m,
            "max_samples": args.max_samples,
            "actual_samples": len(manifest_samples),
            "pixel_size_m": args.pixel_size_m,
            "tx_position": args.tx_position,
        },
        "building_height_filter": {
            "mode": "uav_altitude_slice",
            "rule": "建筑 height_m 低于当前无人机 altitude_m 时，不写入 land_building 阻挡栅格。",
        },
        "road_channel_policy": {
            "mode": args.road_mode,
            "rule": "UAV 高度切片默认将地面道路合并到 land_other；仅在 --road-mode keep 时保留独立 land_road 通道。",
        },
        "samples": manifest_samples,
    }
    write_json(manifest, output_dir / "manifest.json")
    write_json({
        "schema": "uav_route_radio_model_output_expected_v1",
        "input_manifest": "manifest.json",
        "expected_from_model_module": {
            "per_sample_prediction": "<sample_id>_pred.npy 或统一 predictions.npz",
            "prediction_shape": [args.grid_size, args.grid_size],
            "prediction_unit": "dBm preferred; if normalized, include label_norm and normalized=true",
            "route_profile_json": "route_radio_profile.json",
        },
        "route_profile_required_fields": [
            "sample_id",
            "lon",
            "lat",
            "altitude_m",
            "distance_along_route_m",
            "pred_center_dbm",
            "coverage_ratio_gt_minus90",
            "weak_ratio_lt_minus100",
            "radio_score",
            "recommendation",
        ],
    }, output_dir / "expected_model_output_contract.json")
    write_csv(rows, output_dir / "samples.csv")
    print(json.dumps({
        "ok": True,
        "city": city_dir.name,
        "samples": len(manifest_samples),
        "output_dir": str(output_dir),
        "manifest": str(output_dir / "manifest.json"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
