"""把 OSM 建筑 GeoJSON 转为 Cesium 可加载的本地 3D Tiles 1.1 glTF tile。"""

from __future__ import annotations

import base64
import json
import math
import struct
from pathlib import Path
from typing import Any

from uav_virtual_validation.world.geo import EARTH_RADIUS_M, GeoOrigin, latlon_to_meters


def _ecef(lat_deg: float, lon_deg: float, h_m: float = 0.0) -> tuple[float, float, float]:
    a = 6378137.0
    e2 = 6.69437999014e-3
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    n = a / math.sqrt(1.0 - e2 * math.sin(lat) ** 2)
    x = (n + h_m) * math.cos(lat) * math.cos(lon)
    y = (n + h_m) * math.cos(lat) * math.sin(lon)
    z = (n * (1.0 - e2) + h_m) * math.sin(lat)
    return x, y, z


def _enu_transform(lat_deg: float, lon_deg: float, h_m: float = 0.0) -> list[float]:
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    cx, cy, cz = _ecef(lat_deg, lon_deg, h_m)
    east = (-math.sin(lon), math.cos(lon), 0.0)
    north = (-math.sin(lat) * math.cos(lon), -math.sin(lat) * math.sin(lon), math.cos(lat))
    up = (math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat))
    # 3D Tiles matrices are column-major. Cesium converts glTF Y-up content into
    # the tile's Z-up local frame before applying this transform, so the tile
    # frame must be standard ENU: X=east, Y=north, Z=up.
    return [
        east[0], east[1], east[2], 0.0,
        north[0], north[1], north[2], 0.0,
        up[0], up[1], up[2], 0.0,
        cx, cy, cz, 1.0,
    ]


def _height_color(height: float) -> tuple[float, float, float, float]:
    if height >= 180:
        return (0.48, 0.25, 0.08, 1.0)
    if height >= 140:
        return (0.66, 0.36, 0.15, 1.0)
    if height >= 100:
        return (0.79, 0.48, 0.18, 1.0)
    if height >= 70:
        return (0.85, 0.63, 0.36, 1.0)
    if height >= 40:
        return (0.49, 0.61, 0.54, 1.0)
    return (0.66, 0.71, 0.68, 1.0)


def _signed_area(points: list[tuple[float, float]]) -> float:
    area = 0.0
    for idx, current in enumerate(points):
        nxt = points[(idx + 1) % len(points)]
        area += current[0] * nxt[1] - nxt[0] * current[1]
    return area / 2.0


def _triangle_area2(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _clean_ring(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    cleaned: list[tuple[float, float]] = []
    for point in points:
        if not cleaned or math.hypot(point[0] - cleaned[-1][0], point[1] - cleaned[-1][1]) > 0.05:
            cleaned.append(point)
    if len(cleaned) > 1 and math.hypot(cleaned[0][0] - cleaned[-1][0], cleaned[0][1] - cleaned[-1][1]) <= 0.05:
        cleaned.pop()

    changed = True
    while changed and len(cleaned) >= 3:
        changed = False
        result: list[tuple[float, float]] = []
        for idx, point in enumerate(cleaned):
            prev_pt = cleaned[idx - 1]
            next_pt = cleaned[(idx + 1) % len(cleaned)]
            edge_len = max(1.0, math.hypot(next_pt[0] - prev_pt[0], next_pt[1] - prev_pt[1]))
            if abs(_triangle_area2(prev_pt, point, next_pt)) / edge_len < 0.03:
                changed = True
                continue
            result.append(point)
        cleaned = result
    return cleaned


def _point_in_triangle(
    point: tuple[float, float],
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
) -> bool:
    area = _triangle_area2(a, b, c)
    if abs(area) < 1e-9:
        return False
    w1 = _triangle_area2(point, b, c) / area
    w2 = _triangle_area2(a, point, c) / area
    w3 = _triangle_area2(a, b, point) / area
    return w1 >= -1e-7 and w2 >= -1e-7 and w3 >= -1e-7


def _triangulate_polygon(points: list[tuple[float, float]]) -> list[tuple[int, int, int]]:
    if len(points) < 3:
        return []
    order = list(range(len(points)))
    if _signed_area(points) < 0.0:
        order.reverse()

    triangles: list[tuple[int, int, int]] = []
    guard = 0
    while len(order) > 3 and guard < len(points) * len(points):
        guard += 1
        found_ear = False
        for pos, current_idx in enumerate(order):
            prev_idx = order[pos - 1]
            next_idx = order[(pos + 1) % len(order)]
            prev_pt = points[prev_idx]
            current_pt = points[current_idx]
            next_pt = points[next_idx]
            if _triangle_area2(prev_pt, current_pt, next_pt) <= 1e-7:
                continue
            has_inner_point = False
            for other_idx in order:
                if other_idx in {prev_idx, current_idx, next_idx}:
                    continue
                if _point_in_triangle(points[other_idx], prev_pt, current_pt, next_pt):
                    has_inner_point = True
                    break
            if has_inner_point:
                continue
            triangles.append((prev_idx, current_idx, next_idx))
            del order[pos]
            found_ear = True
            break
        if not found_ear:
            return []
    if len(order) == 3:
        triangles.append((order[0], order[1], order[2]))
    return triangles


def _add_top_edge_band(
    local: list[tuple[float, float]],
    base_height: float,
    height: float,
    positions: list[float],
    colors: list[float],
    indices: list[int],
) -> None:
    if height - base_height < 8.0:
        return
    edge_color = (0.12, 0.14, 0.13, 1.0)
    band_height = min(3.2, max(1.2, height * 0.018))
    outward_offset = 0.35
    area = _signed_area(local)
    for idx, current in enumerate(local):
        nxt = local[(idx + 1) % len(local)]
        dx = nxt[0] - current[0]
        dy = nxt[1] - current[1]
        length = math.hypot(dx, dy)
        if length < 0.8:
            continue
        if area >= 0.0:
            nx = dy / length * outward_offset
            ny = -dx / length * outward_offset
        else:
            nx = -dy / length * outward_offset
            ny = dx / length * outward_offset
        top = height + 0.03
        bottom = max(base_height, height - band_height)
        start = len(positions) // 3
        for x, y, z in [
            (current[0] + nx, top, current[1] + ny),
            (nxt[0] + nx, top, nxt[1] + ny),
            (nxt[0] + nx, bottom, nxt[1] + ny),
            (current[0] + nx, bottom, current[1] + ny),
        ]:
            positions.extend([x, y, -z])
        colors.extend(edge_color)
        indices.extend([start, start + 1, start + 2, start, start + 2, start + 3])


def _add_roof_edge_band(
    local: list[tuple[float, float]],
    base_height: float,
    height: float,
    positions: list[float],
    colors: list[float],
    indices: list[int],
) -> None:
    if height - base_height < 8.0:
        return
    edge_color = (0.08, 0.10, 0.09, 1.0)
    outer_offset = 0.42
    inner_offset = -0.72
    top = height + 0.18
    area = _signed_area(local)
    for idx, current in enumerate(local):
        nxt = local[(idx + 1) % len(local)]
        dx = nxt[0] - current[0]
        dy = nxt[1] - current[1]
        length = math.hypot(dx, dy)
        if length < 0.8:
            continue
        if area >= 0.0:
            nx = dy / length
            ny = -dx / length
        else:
            nx = -dy / length
            ny = dx / length
        start = len(positions) // 3
        for x, y in [
            (current[0] + nx * outer_offset, current[1] + ny * outer_offset),
            (nxt[0] + nx * outer_offset, nxt[1] + ny * outer_offset),
            (nxt[0] + nx * inner_offset, nxt[1] + ny * inner_offset),
            (current[0] + nx * inner_offset, current[1] + ny * inner_offset),
        ]:
            positions.extend([x, top, -y])
            colors.extend(edge_color)
        indices.extend([start, start + 1, start + 2, start, start + 2, start + 3])


def _add_vertical_corner_bands(
    local: list[tuple[float, float]],
    base_height: float,
    height: float,
    positions: list[float],
    colors: list[float],
    indices: list[int],
) -> None:
    if height - base_height < 8.0:
        return
    edge_color = (0.10, 0.12, 0.11, 1.0)
    width = 0.42
    area = _signed_area(local)
    for idx, current in enumerate(local):
        prev_pt = local[idx - 1]
        next_pt = local[(idx + 1) % len(local)]
        in_vec = (current[0] - prev_pt[0], current[1] - prev_pt[1])
        out_vec = (next_pt[0] - current[0], next_pt[1] - current[1])
        if math.hypot(*in_vec) < 0.8 or math.hypot(*out_vec) < 0.8:
            continue
        bisector = (in_vec[0] + out_vec[0], in_vec[1] + out_vec[1])
        bisector_len = math.hypot(*bisector)
        if bisector_len < 1e-6:
            bisector = out_vec
            bisector_len = math.hypot(*bisector)
        tx = bisector[0] / bisector_len
        ty = bisector[1] / bisector_len
        if area >= 0.0:
            nx = ty
            ny = -tx
        else:
            nx = -ty
            ny = tx
        start = len(positions) // 3
        for x, y, z in [
            (current[0] + nx * width - tx * width, height + 0.05, current[1] + ny * width - ty * width),
            (current[0] + nx * width + tx * width, height + 0.05, current[1] + ny * width + ty * width),
            (current[0] + nx * width + tx * width, base_height + 0.05, current[1] + ny * width + ty * width),
            (current[0] + nx * width - tx * width, base_height + 0.05, current[1] + ny * width - ty * width),
        ]:
            positions.extend([x, y, -z])
            colors.extend(edge_color)
        indices.extend([start, start + 1, start + 2, start, start + 2, start + 3])


def _polygon_to_mesh(
    coords: list[list[float]],
    origin: GeoOrigin,
    base_height: float,
    height: float,
    positions: list[float],
    colors: list[float],
    indices: list[int],
    edge_positions: list[float],
    edge_colors: list[float],
    edge_indices: list[int],
) -> None:
    if len(coords) < 4:
        return
    ring = coords[:-1] if coords[0] == coords[-1] else coords
    if len(ring) < 3:
        return

    local: list[tuple[float, float]] = []
    for lon, lat in ring:
        x, y = latlon_to_meters(origin, float(lat), float(lon))
        local.append((x, y))
    local = _clean_ring(local)
    if len(local) < 3:
        return
    roof_triangles = _triangulate_polygon(local)
    if not roof_triangles:
        return

    start = len(positions) // 3
    color = _height_color(height)
    for x, y in local:
        # glTF is Y-up. Store local ENU as X=east, Y=up, Z=-north.
        positions.extend([x, base_height, -y])
        colors.extend(color)
    for x, y in local:
        positions.extend([x, height, -y])
        colors.extend(color)

    n = len(local)
    for a, b, c in roof_triangles:
        indices.extend([start + n + a, start + n + b, start + n + c])
        indices.extend([start + a, start + c, start + b])
    for i in range(n):
        j = (i + 1) % n
        indices.extend([start + i, start + j, start + n + j])
        indices.extend([start + i, start + n + j, start + n + i])
    _add_top_edge_band(local, base_height, height, edge_positions, edge_colors, edge_indices)
    _add_roof_edge_band(local, base_height, height, edge_positions, edge_colors, edge_indices)
    _add_vertical_corner_bands(local, base_height, height, edge_positions, edge_colors, edge_indices)


def _mesh_bbox(coords: list[list[float]], origin: GeoOrigin) -> tuple[float, float, float]:
    xs = []
    ys = []
    for lon, lat in coords:
        x, y = latlon_to_meters(origin, float(lat), float(lon))
        xs.append(x)
        ys.append(y)
    width = max(xs) - min(xs)
    depth = max(ys) - min(ys)
    area = max(width, 0.0) * max(depth, 0.0)
    return width, depth, area


def _feature_bbox(feature: dict[str, Any], origin: GeoOrigin) -> tuple[float, float, float, float, float] | None:
    geom = feature.get("geometry", {})
    rings = geom.get("coordinates", [])
    if geom.get("type") != "Polygon" or not rings:
        return None
    xs = []
    ys = []
    for lon, lat in rings[0]:
        x, y = latlon_to_meters(origin, float(lat), float(lon))
        xs.append(x)
        ys.append(y)
    if not xs or not ys:
        return None
    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)
    return min_x, min_y, max_x, max_y, max(0.0, max_x - min_x) * max(0.0, max_y - min_y)


def _bbox_overlap_area(a: tuple[float, float, float, float, float], b: tuple[float, float, float, float, float]) -> float:
    x_overlap = min(a[2], b[2]) - max(a[0], b[0])
    y_overlap = min(a[3], b[3]) - max(a[1], b[1])
    if x_overlap <= 0.0 or y_overlap <= 0.0:
        return 0.0
    return x_overlap * y_overlap


def _point_in_polygon(point: tuple[float, float], ring: list[tuple[float, float]]) -> bool:
    x, y = point
    inside = False
    for idx in range(len(ring) - 1):
        x1, y1 = ring[idx]
        x2, y2 = ring[idx + 1]
        if (y1 > y) != (y2 > y):
            cross_x = (x2 - x1) * (y - y1) / (y2 - y1 + 1e-30) + x1
            if x < cross_x:
                inside = not inside
    return inside


def _centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
    ring = points[:-1] if points[0] == points[-1] else points
    return sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)


def _edge_key(a: tuple[float, float], b: tuple[float, float]) -> tuple[tuple[float, float], tuple[float, float]]:
    pa = (round(a[0], 2), round(a[1], 2))
    pb = (round(b[0], 2), round(b[1], 2))
    return tuple(sorted((pa, pb)))  # type: ignore[return-value]


def _feature_ring_m(feature: dict[str, Any], origin: GeoOrigin) -> list[tuple[float, float]]:
    ring = feature.get("geometry", {}).get("coordinates", [[]])[0]
    return [latlon_to_meters(origin, float(lat), float(lon)) for lon, lat in ring]


def _visual_mesh_features(features: list[dict[str, Any]], origin: GeoOrigin) -> list[tuple[dict[str, Any], float]]:
    prepared: list[dict[str, Any]] = []
    for feature in features:
        bbox = _feature_bbox(feature, origin)
        if bbox is None:
            continue
        height = float(feature.get("properties", {}).get("height_m", 24.0) or 24.0)
        ring = _feature_ring_m(feature, origin)
        edges = {_edge_key(ring[idx], ring[idx + 1]) for idx in range(len(ring) - 1)}
        prepared.append(
            {
                "feature": feature,
                "height": height,
                "bbox": bbox,
                "ring": ring,
                "centroid": _centroid(ring),
                "edges": edges,
                "base_height": 0.0,
                "skip": False,
            }
        )

    for idx, parent in enumerate(prepared):
        parent_height = float(parent["height"])
        parent_bbox = parent["bbox"]
        for other_idx, child in enumerate(prepared):
            if idx == other_idx:
                continue
            child_height = float(child["height"])
            child_bbox = child["bbox"]
            if child_height <= parent_height + 10.0 or child_bbox[4] >= parent_bbox[4] * 0.95:
                continue
            overlap = _bbox_overlap_area(parent_bbox, child_bbox)
            if overlap <= min(parent_bbox[4], child_bbox[4]) * 0.18:
                continue
            if not _point_in_polygon(child["centroid"], parent["ring"]):
                continue
            area_ratio = child_bbox[4] / max(parent_bbox[4], 1.0)
            shared_edges = len(parent["edges"] & child["edges"])
            if area_ratio <= 0.35 and shared_edges == 0:
                child["base_height"] = max(float(child["base_height"]), parent_height + 0.2)
            elif shared_edges > 0 or area_ratio >= 0.75:
                parent["skip"] = True

    return [(item["feature"], float(item["base_height"])) for item in prepared if not item["skip"]]


def _should_skip_building(feature: dict[str, Any], origin: GeoOrigin) -> bool:
    geom = feature.get("geometry", {})
    rings = geom.get("coordinates", [])
    if not rings:
        return True
    return False


def _add_ground_plane(
    origin: GeoOrigin,
    summary: dict[str, Any],
    positions: list[float],
    colors: list[float],
    indices: list[int],
) -> None:
    bbox = summary.get("bbox")
    if not bbox:
        return
    lat_margin = max(0.002, (bbox["north"] - bbox["south"]) * 0.18)
    lon_margin = max(0.002, (bbox["east"] - bbox["west"]) * 0.18)
    west = bbox["west"] - lon_margin
    east = bbox["east"] + lon_margin
    south = bbox["south"] - lat_margin
    north = bbox["north"] + lat_margin
    corners_ll = [
        (west, south),
        (east, south),
        (east, north),
        (west, north),
    ]
    start = len(positions) // 3
    color = (0.78, 0.82, 0.76, 1.0)
    for lon, lat in corners_ll:
        x, y = latlon_to_meters(origin, float(lat), float(lon))
        positions.extend([x, -6.0, -y])
        colors.extend(color)
    indices.extend([start, start + 1, start + 2, start, start + 2, start + 3])


def _pad4(data: bytes) -> bytes:
    return data + b"\x00" * ((4 - len(data) % 4) % 4)


def _colored_triangle_gltf(
    positions: list[float],
    colors: list[float],
    indices: list[int],
    generator: str,
    roughness: float,
) -> dict[str, Any]:
    pos_bytes = struct.pack("<" + "f" * len(positions), *positions)
    color_bytes = struct.pack("<" + "f" * len(colors), *colors)
    idx_bytes = struct.pack("<" + "I" * len(indices), *indices)
    pos_offset = 0
    color_offset = len(_pad4(pos_bytes))
    idx_offset = color_offset + len(_pad4(color_bytes))
    blob = _pad4(pos_bytes) + _pad4(color_bytes) + _pad4(idx_bytes)
    encoded = base64.b64encode(blob).decode("ascii")

    xs = positions[0::3]
    ys = positions[1::3]
    zs = positions[2::3]
    return {
        "asset": {"version": "2.0", "generator": generator},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [
            {
                "primitives": [
                    {
                        "attributes": {"POSITION": 0, "COLOR_0": 1},
                        "indices": 2,
                        "material": 0,
                        "mode": 4,
                    }
                ]
            }
        ],
        "buffers": [{"uri": f"data:application/octet-stream;base64,{encoded}", "byteLength": len(blob)}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": pos_offset, "byteLength": len(pos_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": color_offset, "byteLength": len(color_bytes), "target": 34962},
            {"buffer": 0, "byteOffset": idx_offset, "byteLength": len(idx_bytes), "target": 34963},
        ],
        "accessors": [
            {
                "bufferView": 0,
                "componentType": 5126,
                "count": len(positions) // 3,
                "type": "VEC3",
                "min": [min(xs), min(ys), min(zs)],
                "max": [max(xs), max(ys), max(zs)],
            },
            {
                "bufferView": 1,
                "componentType": 5126,
                "count": len(colors) // 4,
                "type": "VEC4",
            },
            {
                "bufferView": 2,
                "componentType": 5125,
                "count": len(indices),
                "type": "SCALAR",
            },
        ],
        "materials": [
            {
                "pbrMetallicRoughness": {
                    "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
                    "metallicFactor": 0.0,
                    "roughnessFactor": roughness,
                },
                "alphaMode": "OPAQUE",
                "doubleSided": True,
            }
        ],
    }


def _tileset_json(origin: GeoOrigin, positions: list[float], uri: str) -> dict[str, Any]:
    xs = positions[0::3]
    ys = positions[1::3]
    zs = positions[2::3]
    max_x = max(abs(min(xs)), abs(max(xs)))
    max_north = max(abs(min(zs)), abs(max(zs)))
    min_up = min(ys)
    max_up = max(ys)
    center_up = (min_up + max_up) / 2.0
    half_up = max(1.0, (max_up - min_up) / 2.0)
    return {
        "asset": {"version": "1.1", "tilesetVersion": "0.1.0"},
        "geometricError": 500,
        "root": {
            "boundingVolume": {
                "box": [
                    0, 0, center_up,
                    max_x, 0, 0,
                    0, max_north, 0,
                    0, 0, half_up,
                ]
            },
            "geometricError": 0,
            "refine": "ADD",
            "transform": _enu_transform(origin.lat, origin.lon, 0.0),
            "content": {"uri": uri},
        },
    }


def build_city_tileset(buildings_geojson: str | Path, city_summary: str | Path, output_dir: str | Path) -> dict[str, str]:
    buildings = json.loads(Path(buildings_geojson).read_text(encoding="utf-8"))
    summary = json.loads(Path(city_summary).read_text(encoding="utf-8"))
    center = summary["center"]
    origin = GeoOrigin(float(center["lat"]), float(center["lon"]))

    ground_positions: list[float] = []
    ground_colors: list[float] = []
    ground_indices: list[int] = []
    positions: list[float] = []
    colors: list[float] = []
    indices: list[int] = []
    edge_positions: list[float] = []
    edge_colors: list[float] = []
    edge_indices: list[int] = []
    _add_ground_plane(origin, summary, ground_positions, ground_colors, ground_indices)
    for feature, base_height in _visual_mesh_features(buildings.get("features", []), origin):
        geom = feature.get("geometry", {})
        if geom.get("type") != "Polygon":
            continue
        rings = geom.get("coordinates", [])
        if not rings:
            continue
        if _should_skip_building(feature, origin):
            continue
        height = float(feature.get("properties", {}).get("height_m", 24.0) or 24.0)
        if height <= base_height + 1.0:
            continue
        _polygon_to_mesh(rings[0], origin, base_height, height, positions, colors, indices, edge_positions, edge_colors, edge_indices)

    if not positions or not indices:
        raise ValueError("No building mesh was generated.")

    gltf = _colored_triangle_gltf(positions, colors, indices, "uav_virtual_validation", 0.86)
    ground_gltf = _colored_triangle_gltf(ground_positions, ground_colors, ground_indices, "uav_virtual_validation_ground", 0.94) if ground_positions and ground_indices else None
    index_component = 5125

    edge_pos_bytes = struct.pack("<" + "f" * len(edge_positions), *edge_positions) if edge_positions else b""
    edge_idx_bytes = struct.pack("<" + "I" * len(edge_indices), *edge_indices) if edge_indices else b""
    edge_pos_offset = 0
    edge_idx_offset = len(_pad4(edge_pos_bytes)) if edge_pos_bytes else 0
    edge_blob = _pad4(edge_pos_bytes) + _pad4(edge_idx_bytes) if edge_pos_bytes and edge_idx_bytes else b""
    edge_encoded = base64.b64encode(edge_blob).decode("ascii") if edge_blob else ""
    edge_gltf = None
    if edge_positions and edge_indices:
        exs = edge_positions[0::3]
        eys = edge_positions[1::3]
        ezs = edge_positions[2::3]
        edge_gltf = {
            "asset": {"version": "2.0", "generator": "uav_virtual_validation_edges"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [{"mesh": 0}],
            "meshes": [
                {
                    "primitives": [
                        {
                            "attributes": {"POSITION": 0},
                            "indices": 1,
                            "material": 0,
                            "mode": 4,
                        }
                    ]
                }
            ],
            "buffers": [{"uri": f"data:application/octet-stream;base64,{edge_encoded}", "byteLength": len(edge_blob)}],
            "bufferViews": [
                {"buffer": 0, "byteOffset": edge_pos_offset, "byteLength": len(edge_pos_bytes), "target": 34962},
                {"buffer": 0, "byteOffset": edge_idx_offset, "byteLength": len(edge_idx_bytes), "target": 34963},
            ],
            "accessors": [
                {
                    "bufferView": 0,
                    "componentType": 5126,
                    "count": len(edge_positions) // 3,
                    "type": "VEC3",
                    "min": [min(exs), min(eys), min(ezs)],
                    "max": [max(exs), max(eys), max(ezs)],
                },
                {
                    "bufferView": 1,
                    "componentType": index_component,
                    "count": len(edge_indices),
                    "type": "SCALAR",
                },
            ],
            "materials": [
                {
                    "pbrMetallicRoughness": {
                        "baseColorFactor": [0.12, 0.14, 0.13, 1.0],
                        "metallicFactor": 0.0,
                        "roughnessFactor": 0.95,
                    },
                    "alphaMode": "OPAQUE",
                    "doubleSided": True,
                }
            ],
        }

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    gltf_path = out / "buildings.gltf"
    ground_gltf_path = out / "ground.gltf"
    edge_gltf_path = out / "edges.gltf"
    tileset_path = out / "tileset.json"
    ground_tileset_path = out / "ground_tileset.json"
    outline_tileset_path = out / "outline_tileset.json"
    gltf_path.write_text(json.dumps(gltf, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    if ground_gltf is not None:
        ground_gltf_path.write_text(json.dumps(ground_gltf, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    if edge_gltf is not None:
        edge_gltf_path.write_text(json.dumps(edge_gltf, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    tileset = _tileset_json(origin, positions, "buildings.gltf")
    ground_tileset = _tileset_json(origin, ground_positions, "ground.gltf") if ground_gltf is not None else None
    outline_tileset = _tileset_json(origin, edge_positions, "edges.gltf") if edge_positions else json.loads(json.dumps(tileset))
    tileset_path.write_text(json.dumps(tileset, indent=2, ensure_ascii=False), encoding="utf-8")
    if ground_tileset is not None:
        ground_tileset_path.write_text(json.dumps(ground_tileset, indent=2, ensure_ascii=False), encoding="utf-8")
    outline_tileset_path.write_text(json.dumps(outline_tileset, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "tileset": str(tileset_path),
        "gltf": str(gltf_path),
        "ground_tileset": str(ground_tileset_path),
        "ground_gltf": str(ground_gltf_path),
        "outline_tileset": str(outline_tileset_path),
        "outline_gltf": str(edge_gltf_path),
    }
