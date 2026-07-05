# 本脚本用于把 UAV 真实城市资产接入 Sionna RT：从 GeoJSON 建筑与航线生成局部三维场景，并计算稀疏 3D Radio Map 点云。
from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import drjit as dr
import numpy as np
from sionna.rt import PathSolver, PlanarArray, Receiver, Transmitter, load_scene


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CITY_DIR = REPO_ROOT / "modules/uav_virtual_validation/outputs/real_city/manhattan_midtown"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "modules/sionna-rt-workspace/outputs/uav_city_3d_radio_map"
EARTH_RADIUS_M = 6371000.0


@dataclass(frozen=True)
class GeoOrigin:
    lat: float
    lon: float


@dataclass(frozen=True)
class RouteSample:
    sample_idx: int
    lon: float
    lat: float
    altitude_m: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="基于 UAV 城市资产生成 Sionna RT 3D Radio Map 点云。")
    parser.add_argument("--city-dir", type=Path, default=DEFAULT_CITY_DIR, help="包含 route.geojson 与 real_buildings.geojson 的城市资产目录。")
    parser.add_argument("--route-sample-index", type=int, default=5, help="使用 route.geojson 中的第几个航线点作为 Tx。")
    parser.add_argument("--radius-m", type=float, default=120.0, help="仅导入 Tx 周围该半径内的建筑。")
    parser.add_argument("--rx-grid", type=int, default=5, help="x/y 方向接收点数量，默认 5x5。")
    parser.add_argument("--rx-span-m", type=float, default=120.0, help="接收点网格覆盖边长，单位米。")
    parser.add_argument("--rx-height-offsets", default="-30,0,30", help="Rx 高度相对 Tx 高度偏移，逗号分隔。")
    parser.add_argument("--max-buildings", type=int, default=160, help="最多写入局部建筑数量，避免验证过慢。")
    parser.add_argument("--frequency-hz", type=float, default=3.5e9, help="射线追踪频率。")
    parser.add_argument("--tx-power-dbm", type=float, default=30.0, help="Tx 发射功率，仅作为元数据记录。")
    parser.add_argument("--max-depth", type=int, default=1, help="Sionna PathSolver 最大反射深度。")
    parser.add_argument("--samples-per-src", type=int, default=3000, help="Sionna PathSolver 每个 Tx 采样数。")
    parser.add_argument("--output-dir", type=Path, default=None, help="输出目录，默认按城市名生成。")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latlon_to_meters(origin: GeoOrigin, lat: float, lon: float) -> tuple[float, float]:
    y_m = math.radians(lat - origin.lat) * EARTH_RADIUS_M
    x_m = math.radians(lon - origin.lon) * EARTH_RADIUS_M * math.cos(math.radians(origin.lat))
    return x_m, y_m


def tensor_to_list(value: Any) -> list[Any]:
    return np.asarray(value).tolist()


def count_valid_paths(paths: Any) -> int:
    if hasattr(paths, "valid"):
        return int(np.asarray(paths.valid).sum())
    return int(np.asarray(paths.tau).size)


def extract_path_gains_db(paths: Any) -> list[float]:
    amplitudes: list[np.ndarray] = []
    raw_amplitudes = paths.a if isinstance(paths.a, tuple) else (paths.a,)
    for item in raw_amplitudes:
        try:
            amplitudes.append(np.asarray(dr.abs(item), dtype=float))
        except Exception:
            continue
    if not amplitudes:
        return []
    merged = np.maximum.reduce([np.ravel(item) for item in amplitudes])
    positive = merged[merged > 0]
    return (20.0 * np.log10(positive)).round(3).tolist()


def extract_rx_path_gains_db(paths: Any, rx_count: int) -> list[list[float]]:
    per_rx: list[list[float]] = []
    raw_amplitudes = paths.a if isinstance(paths.a, tuple) else (paths.a,)
    amplitude_arrays: list[np.ndarray] = []
    for item in raw_amplitudes:
        try:
            amplitude_arrays.append(np.asarray(dr.abs(item), dtype=float))
        except Exception:
            continue

    for rx_idx in range(rx_count):
        values: list[float] = []
        for arr in amplitude_arrays:
            if arr.ndim == 0 or rx_idx >= arr.shape[0]:
                continue
            rx_values = np.ravel(arr[rx_idx])
            values.extend(float(value) for value in rx_values if value > 0)
        if values:
            gains = (20.0 * np.log10(np.asarray(values, dtype=float))).round(3).tolist()
            per_rx.append(sorted(gains, reverse=True))
        else:
            per_rx.append([])
    return per_rx


def fspl_db(distance_m: float, frequency_hz: float) -> float:
    distance_m = max(distance_m, 1e-3)
    wavelength_m = 299792458.0 / frequency_hz
    return 20.0 * math.log10(4.0 * math.pi * distance_m / wavelength_m)


def point_in_polygon_2d(point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
    x, y = point
    inside = False
    count = len(polygon)
    for idx in range(count):
        x1, y1 = polygon[idx]
        x2, y2 = polygon[(idx + 1) % count]
        intersects = ((y1 > y) != (y2 > y)) and (x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-12) + x1)
        if intersects:
            inside = not inside
    return inside


def los_obstruction(tx_xyz: tuple[float, float, float], rx_xyz: tuple[float, float, float], buildings: list[dict[str, Any]]) -> dict[str, Any]:
    x0, y0, z0 = tx_xyz
    x1, y1, z1 = rx_xyz
    samples = 80
    blockers: list[dict[str, Any]] = []
    for building in buildings:
        polygon = building["points"]
        if polygon[0] == polygon[-1]:
            polygon = polygon[:-1]
        height_m = float(building["height_m"])
        hit_fraction: float | None = None
        for step in range(1, samples):
            t = step / samples
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t
            z = z0 + (z1 - z0) * t
            if z <= height_m and point_in_polygon_2d((x, y), polygon):
                hit_fraction = t
                break
        if hit_fraction is not None:
            blockers.append({
                "name": building.get("name") or "",
                "osm_id": building.get("osm_id") or "",
                "height_m": round(height_m, 3),
                "fraction": round(hit_fraction, 3),
            })
    blockers.sort(key=lambda item: item["fraction"])
    return {
        "is_los_blocked_by_building": bool(blockers),
        "blocking_building_count": len(blockers),
        "first_blocking_building": blockers[0] if blockers else None,
    }


def route_samples(route_path: Path) -> list[RouteSample]:
    geo = read_json(route_path)
    feature = (geo.get("features") or [None])[0]
    if not feature or feature.get("geometry", {}).get("type") != "LineString":
        raise ValueError(f"航线必须是 LineString GeoJSON：{route_path}")
    samples: list[RouteSample] = []
    for idx, coord in enumerate(feature["geometry"].get("coordinates") or []):
        if len(coord) < 2:
            continue
        samples.append(RouteSample(idx, float(coord[0]), float(coord[1]), float(coord[2] if len(coord) > 2 else 120.0)))
    if not samples:
        raise ValueError(f"航线没有有效坐标：{route_path}")
    return samples


def load_local_buildings(buildings_path: Path, origin: GeoOrigin, radius_m: float, max_buildings: int) -> list[dict[str, Any]]:
    geo = read_json(buildings_path)
    local_buildings: list[dict[str, Any]] = []
    for feature in geo.get("features", []):
        geom = feature.get("geometry", {})
        if geom.get("type") != "Polygon":
            continue
        ring = (geom.get("coordinates") or [[]])[0]
        if len(ring) < 4:
            continue
        points = [latlon_to_meters(origin, float(lat), float(lon)) for lon, lat in ring]
        if not points:
            continue
        cx = sum(x for x, _ in points) / len(points)
        cy = sum(y for _, y in points) / len(points)
        if math.hypot(cx, cy) > radius_m:
            continue
        height_m = float(feature.get("properties", {}).get("height_m") or 0.0)
        if height_m <= 1.0:
            continue
        local_buildings.append({
            "height_m": max(1.0, height_m),
            "centroid_distance_m": math.hypot(cx, cy),
            "points": points,
            "name": feature.get("properties", {}).get("name") or "",
            "osm_id": feature.get("properties", {}).get("osm_id") or "",
        })
    local_buildings.sort(key=lambda item: item["centroid_distance_m"])
    return local_buildings[:max_buildings]


def add_face(faces: list[tuple[int, int, int]], a: int, b: int, c: int) -> None:
    if a != b and b != c and a != c:
        faces.append((a, b, c))


def build_city_mesh(buildings: list[dict[str, Any]]) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    for building in buildings:
        ring = building["points"]
        if ring[0] == ring[-1]:
            ring = ring[:-1]
        if len(ring) < 3:
            continue
        base = len(vertices)
        height_m = float(building["height_m"])
        for x_m, y_m in ring:
            vertices.append((x_m, y_m, 0.0))
        for x_m, y_m in ring:
            vertices.append((x_m, y_m, height_m))
        n = len(ring)
        for idx in range(n):
            nxt = (idx + 1) % n
            add_face(faces, base + idx, base + nxt, base + n + nxt)
            add_face(faces, base + idx, base + n + nxt, base + n + idx)
        for idx in range(1, n - 1):
            add_face(faces, base + n, base + n + idx, base + n + idx + 1)
            add_face(faces, base, base + idx + 1, base + idx)
    return vertices, faces


def write_ply(path: Path, vertices: list[tuple[float, float, float]], faces: list[tuple[int, int, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="ascii", newline="\n") as fh:
        fh.write("ply\n")
        fh.write("format ascii 1.0\n")
        fh.write(f"element vertex {len(vertices)}\n")
        fh.write("property float x\nproperty float y\nproperty float z\n")
        fh.write(f"element face {len(faces)}\n")
        fh.write("property list uchar int vertex_indices\n")
        fh.write("end_header\n")
        for x_m, y_m, z_m in vertices:
            fh.write(f"{x_m:.6f} {y_m:.6f} {z_m:.6f}\n")
        for a, b, c in faces:
            fh.write(f"3 {a} {b} {c}\n")


def write_scene_xml(path: Path, mesh_filename: str) -> None:
    path.write_text(
        "\n".join([
            '<scene version="2.1.0">',
            "  <bsdf type=\"itu-radio-material\" id=\"concrete\">",
            "    <string name=\"type\" value=\"concrete\"/>",
            "    <float name=\"thickness\" value=\"0.2\"/>",
            "  </bsdf>",
            "  <shape type=\"ply\" id=\"local-city-buildings\">",
            f"    <string name=\"filename\" value=\"meshes/{mesh_filename}\"/>",
            "    <boolean name=\"face_normals\" value=\"true\"/>",
            "    <ref id=\"concrete\" name=\"bsdf\"/>",
            "  </shape>",
            "</scene>",
            "",
        ]),
        encoding="utf-8",
    )


def rx_offsets(grid_count: int, span_m: float, height_offsets: list[float]) -> list[tuple[float, float, float]]:
    lateral = np.linspace(-span_m / 2.0, span_m / 2.0, grid_count, dtype=np.float64)
    return [(float(x_m), float(y_m), float(z_m)) for z_m in height_offsets for y_m in lateral for x_m in lateral]


def run(args: argparse.Namespace) -> dict[str, Any]:
    city_dir = args.city_dir.resolve()
    city_name = city_dir.name
    output_dir = (args.output_dir or (DEFAULT_OUTPUT_ROOT / city_name)).resolve()
    scene_dir = output_dir / "scene"
    mesh_dir = scene_dir / "meshes"
    output_dir.mkdir(parents=True, exist_ok=True)

    samples = route_samples(city_dir / "route.geojson")
    if args.route_sample_index < 0 or args.route_sample_index >= len(samples):
        raise IndexError(f"route-sample-index 超出范围：{args.route_sample_index}，可用范围 0..{len(samples)-1}")
    tx_sample = samples[args.route_sample_index]
    origin = GeoOrigin(tx_sample.lat, tx_sample.lon)

    buildings = load_local_buildings(city_dir / "real_buildings.geojson", origin, args.radius_m, args.max_buildings)
    vertices, faces = build_city_mesh(buildings)
    if not vertices or not faces:
        raise ValueError("局部范围内没有可生成 mesh 的建筑，请增大 --radius-m 或更换航线点。")

    mesh_path = mesh_dir / "local_buildings.ply"
    scene_path = scene_dir / "scene.xml"
    write_ply(mesh_path, vertices, faces)
    write_scene_xml(scene_path, mesh_path.name)

    height_offsets = [float(item.strip()) for item in args.rx_height_offsets.split(",") if item.strip()]
    rx_positions = [(x_m, y_m, max(1.5, tx_sample.altitude_m + z_m)) for x_m, y_m, z_m in rx_offsets(args.rx_grid, args.rx_span_m, height_offsets)]

    scene = load_scene(str(scene_path))
    scene.frequency = args.frequency_hz
    scene.tx_array = PlanarArray(num_rows=1, num_cols=1, vertical_spacing=0.5, horizontal_spacing=0.5, pattern="iso", polarization="V")
    scene.rx_array = PlanarArray(num_rows=1, num_cols=1, vertical_spacing=0.5, horizontal_spacing=0.5, pattern="iso", polarization="V")
    scene.add(Transmitter(name="tx_uav_route_sample", position=[0.0, 0.0, tx_sample.altitude_m], power_dbm=args.tx_power_dbm))
    for idx, position in enumerate(rx_positions):
        scene.add(Receiver(name=f"rx_{idx:04d}", position=list(position)))

    paths = PathSolver()(
        scene,
        max_depth=args.max_depth,
        samples_per_src=args.samples_per_src,
        los=True,
        specular_reflection=True,
        diffuse_reflection=False,
        diffraction=False,
        seed=1,
    )

    delays = np.asarray(paths.tau)
    valid = np.asarray(paths.valid) if hasattr(paths, "valid") else np.isfinite(delays)
    gains = extract_path_gains_db(paths)
    rx_gains = extract_rx_path_gains_db(paths, len(rx_positions))
    point_rows: list[dict[str, Any]] = []
    tx_xyz = (0.0, 0.0, tx_sample.altitude_m)
    for idx, position in enumerate(rx_positions):
        per_rx_delay = delays[idx, 0].tolist() if delays.ndim >= 3 and idx < delays.shape[0] else []
        per_rx_valid = valid[idx, 0].tolist() if valid.ndim >= 3 and idx < valid.shape[0] else []
        valid_count = int(np.asarray(per_rx_valid).sum()) if per_rx_valid else 0
        per_rx_gains = rx_gains[idx] if idx < len(rx_gains) else []
        best_gain = max(per_rx_gains) if per_rx_gains else None
        distance_m = math.dist(tx_xyz, position)
        free_space_path_loss_db = fspl_db(distance_m, args.frequency_hz)
        free_space_path_gain_db = -free_space_path_loss_db
        path_loss_db = round(-best_gain, 3) if best_gain is not None else None
        excess_loss_db = round(path_loss_db - free_space_path_loss_db, 3) if path_loss_db is not None else None
        obstruction = los_obstruction(tx_xyz, position, buildings)
        point_rows.append({
            "rx_id": f"rx_{idx:04d}",
            "rx_xyz_m": [round(float(value), 3) for value in position],
            "tx_rx_distance_m": round(distance_m, 3),
            "path_loss_db": path_loss_db,
            "free_space_path_loss_db": round(free_space_path_loss_db, 3),
            "free_space_path_gain_db": round(free_space_path_gain_db, 3),
            "excess_loss_db": excess_loss_db,
            **obstruction,
            "valid_path_count": valid_count,
            "path_gain_db": per_rx_gains,
            "best_path_gain_db": best_gain,
            "estimated_rx_power_dbm": round(args.tx_power_dbm + best_gain, 3) if best_gain is not None else None,
            "delay_s": per_rx_delay,
        })

    rx_csv = output_dir / "rx_points.csv"
    with rx_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["rx_id", "x_m", "y_m", "z_m"])
        writer.writeheader()
        for idx, position in enumerate(rx_positions):
            writer.writerow({"rx_id": f"rx_{idx:04d}", "x_m": position[0], "y_m": position[1], "z_m": position[2]})

    radio_map = {
        "schema": "uav_city_sionna_3d_radio_map_v1",
        "city": city_name,
        "city_dir": str(city_dir),
        "scene_xml": str(scene_path),
        "building_mesh": str(mesh_path),
        "tx": {
            "route_sample_index": tx_sample.sample_idx,
            "lon": tx_sample.lon,
            "lat": tx_sample.lat,
            "xyz_m": [0.0, 0.0, tx_sample.altitude_m],
            "power_dbm": args.tx_power_dbm,
        },
        "solver": {
            "frequency_hz": args.frequency_hz,
            "max_depth": args.max_depth,
            "samples_per_src": args.samples_per_src,
        },
        "rx_grid": {
            "grid": args.rx_grid,
            "span_m": args.rx_span_m,
            "height_offsets_m": height_offsets,
            "point_count": len(rx_positions),
        },
        "global_path_gain_db_values": gains,
        "points": point_rows,
    }
    (output_dir / "radio_map_points.json").write_text(json.dumps(radio_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "ok": True,
        "city": city_name,
        "output_dir": str(output_dir),
        "scene_xml": str(scene_path),
        "rx_points": len(rx_positions),
        "buildings_imported": len(buildings),
        "mesh_vertices": len(vertices),
        "mesh_faces": len(faces),
        "valid_path_count_total": count_valid_paths(paths),
        "global_path_gain_db_count": len(gains),
        "global_path_gain_db_min": min(gains) if gains else None,
        "global_path_gain_db_max": max(gains) if gains else None,
        "los_blocked_rx_points": sum(1 for point in point_rows if point["is_los_blocked_by_building"]),
        "excess_loss_db_min": min((point["excess_loss_db"] for point in point_rows if point["excess_loss_db"] is not None), default=None),
        "excess_loss_db_max": max((point["excess_loss_db"] for point in point_rows if point["excess_loss_db"] is not None), default=None),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    args = parse_args()
    summary = run(args)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
