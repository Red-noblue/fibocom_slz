"""基于真实建筑轮廓生成避开建筑的默认无人机航线。"""

from __future__ import annotations

import argparse
import heapq
import json
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_virtual_validation.artifacts.io import write_json
from uav_virtual_validation.real_city.osm import city_route_length_m
from uav_virtual_validation.world.geo import GeoOrigin, latlon_to_meters, meters_to_latlon


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="用建筑多边形避障生成真实城市航线。")
    parser.add_argument("--city-dir", default=str(ROOT / "outputs/real_city/manhattan_midtown"))
    parser.add_argument("--cell-m", type=float, default=45.0)
    parser.add_argument("--min-blocking-height-m", type=float, default=80.0)
    return parser.parse_args()


def point_in_poly(point: tuple[float, float], poly: list[tuple[float, float]]) -> bool:
    x, y = point
    inside = False
    for idx in range(len(poly) - 1):
        x1, y1 = poly[idx]
        x2, y2 = poly[idx + 1]
        if (y1 > y) != (y2 > y):
            cross_x = (x2 - x1) * (y - y1) / (y2 - y1 + 1e-30) + x1
            if x < cross_x:
                inside = not inside
    return inside


def orient(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def on_segment(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> bool:
    return (
        min(a[0], b[0]) <= c[0] <= max(a[0], b[0])
        and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])
        and abs(orient(a, b, c)) < 1e-9
    )


def segments_intersect(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    d: tuple[float, float],
) -> bool:
    o1 = orient(a, b, c)
    o2 = orient(a, b, d)
    o3 = orient(c, d, a)
    o4 = orient(c, d, b)
    if o1 * o2 < 0 and o3 * o4 < 0:
        return True
    return on_segment(a, b, c) or on_segment(a, b, d) or on_segment(c, d, a) or on_segment(c, d, b)


def segment_hits_poly(a: tuple[float, float], b: tuple[float, float], poly: list[tuple[float, float]]) -> bool:
    if point_in_poly(a, poly) or point_in_poly(b, poly):
        return True
    for idx in range(len(poly) - 1):
        if segments_intersect(a, b, poly[idx], poly[idx + 1]):
            return True
    return False


def load_building_polys(city_dir: Path, origin: GeoOrigin, min_height_m: float) -> list[list[tuple[float, float]]]:
    geo = json.loads((city_dir / "real_buildings.geojson").read_text(encoding="utf-8"))
    polys: list[list[tuple[float, float]]] = []
    for feature in geo.get("features", []):
        height = float(feature.get("properties", {}).get("height_m") or 0.0)
        if height < min_height_m:
            continue
        geom = feature.get("geometry", {})
        if geom.get("type") != "Polygon":
            continue
        ring = geom.get("coordinates", [[]])[0]
        poly = []
        for lon, lat in ring:
            poly.append(latlon_to_meters(origin, float(lat), float(lon)))
        if len(poly) >= 4:
            polys.append(poly)
    return polys


def is_blocked(point: tuple[float, float], polys: list[list[tuple[float, float]]]) -> bool:
    return any(point_in_poly(point, poly) for poly in polys)


def nearest_free(
    point: tuple[float, float],
    x_values: list[float],
    y_values: list[float],
    blocked: set[tuple[int, int]],
) -> tuple[int, int]:
    best = None
    best_dist = float("inf")
    for ix, x in enumerate(x_values):
        for iy, y in enumerate(y_values):
            if (ix, iy) in blocked:
                continue
            dist = (x - point[0]) ** 2 + (y - point[1]) ** 2
            if dist < best_dist:
                best = (ix, iy)
                best_dist = dist
    if best is None:
        raise RuntimeError("没有可用的自由栅格点。")
    return best


def astar(
    start: tuple[int, int],
    goal: tuple[int, int],
    x_values: list[float],
    y_values: list[float],
    blocked: set[tuple[int, int]],
    polys: list[list[tuple[float, float]]],
) -> list[tuple[int, int]]:
    def h(node: tuple[int, int]) -> float:
        return math.hypot(node[0] - goal[0], node[1] - goal[1])

    open_set = [(h(start), 0.0, start)]
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    cost = {start: 0.0}
    moves = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    while open_set:
        _, cur_cost, cur = heapq.heappop(open_set)
        if cur == goal:
            path = [cur]
            while cur in came_from:
                cur = came_from[cur]
                path.append(cur)
            return list(reversed(path))
        for dx, dy in moves:
            nxt = (cur[0] + dx, cur[1] + dy)
            if nxt[0] < 0 or nxt[0] >= len(x_values) or nxt[1] < 0 or nxt[1] >= len(y_values):
                continue
            if nxt in blocked:
                continue
            a = (x_values[cur[0]], y_values[cur[1]])
            b = (x_values[nxt[0]], y_values[nxt[1]])
            if any(segment_hits_poly(a, b, poly) for poly in polys):
                continue
            step = math.hypot(dx, dy)
            new_cost = cur_cost + step
            if new_cost < cost.get(nxt, float("inf")):
                cost[nxt] = new_cost
                came_from[nxt] = cur
                heapq.heappush(open_set, (new_cost + h(nxt), new_cost, nxt))
    raise RuntimeError("未找到避障航线。")


def simplify_path(
    path: list[tuple[int, int]],
    x_values: list[float],
    y_values: list[float],
    polys: list[list[tuple[float, float]]],
) -> list[tuple[float, float]]:
    points = [(x_values[ix], y_values[iy]) for ix, iy in path]
    simplified = [points[0]]
    idx = 0
    while idx < len(points) - 1:
        nxt = len(points) - 1
        while nxt > idx + 1:
            if not any(segment_hits_poly(points[idx], points[nxt], poly) for poly in polys):
                break
            nxt -= 1
        simplified.append(points[nxt])
        idx = nxt
    return simplified


def main() -> None:
    args = parse_args()
    city_dir = Path(args.city_dir)
    city = json.loads((city_dir / "city_config_snapshot.json").read_text(encoding="utf-8"))
    summary = json.loads((city_dir / "city_summary.json").read_text(encoding="utf-8"))
    origin = GeoOrigin(float(summary["center"]["lat"]), float(summary["center"]["lon"]))
    bbox = summary["bbox"]
    west_south = latlon_to_meters(origin, float(bbox["south"]), float(bbox["west"]))
    east_north = latlon_to_meters(origin, float(bbox["north"]), float(bbox["east"]))
    margin = args.cell_m * 1.5
    x_min, x_max = west_south[0] - margin, east_north[0] + margin
    y_min, y_max = west_south[1] - margin, east_north[1] + margin
    x_values = [x_min + i * args.cell_m for i in range(int((x_max - x_min) / args.cell_m) + 1)]
    y_values = [y_min + i * args.cell_m for i in range(int((y_max - y_min) / args.cell_m) + 1)]
    polys = load_building_polys(city_dir, origin, args.min_blocking_height_m)
    blocked = {
        (ix, iy)
        for ix, x in enumerate(x_values)
        for iy, y in enumerate(y_values)
        if is_blocked((x, y), polys)
    }

    route = city["default_route"]
    start_ll = route[0]
    goal_ll = route[-1]
    start = nearest_free(latlon_to_meters(origin, start_ll["lat"], start_ll["lon"]), x_values, y_values, blocked)
    goal = nearest_free(latlon_to_meters(origin, goal_ll["lat"], goal_ll["lon"]), x_values, y_values, blocked)
    path = astar(start, goal, x_values, y_values, blocked, polys)
    simplified = simplify_path(path, x_values, y_values, polys)
    altitudes = [170.0, 185.0, 200.0, 190.0, 175.0]
    coords = []
    for idx, (x, y) in enumerate(simplified):
        lat, lon = meters_to_latlon(origin, x, y)
        frac = idx / max(len(simplified) - 1, 1)
        alt_idx = min(round(frac * (len(altitudes) - 1)), len(altitudes) - 1)
        coords.append([lon, lat, altitudes[alt_idx]])

    route_geojson = {
        "type": "FeatureCollection",
        "name": f"{city['name']}_clear_route",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "layer": "real_city_route",
                    "city": city["name"],
                    "display_name": city.get("display_name", city["name"]),
                    "generator": "build_clear_route",
                    "cell_m": args.cell_m,
                    "min_blocking_height_m": args.min_blocking_height_m,
                },
                "geometry": {"type": "LineString", "coordinates": coords},
            }
        ],
    }
    write_json(route_geojson, city_dir / "route.geojson")
    city["default_route"] = [
        {"lat": lat, "lon": lon, "altitude_m": alt, "label": f"避障点{idx + 1}"}
        for idx, (lon, lat, alt) in enumerate(coords)
    ]
    summary["route_length_m"] = city_route_length_m(city)
    summary["route_waypoint_count"] = len(city["default_route"])
    write_json(summary, city_dir / "city_summary.json")
    print(f"route: {city_dir / 'route.geojson'} ({len(coords)} waypoints)")


if __name__ == "__main__":
    main()
