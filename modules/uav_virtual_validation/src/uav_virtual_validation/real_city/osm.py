"""从 OpenStreetMap/Overpass 获取真实城市建筑。"""

from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from uav_virtual_validation.simulators.simple import haversine_m


OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def load_city_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def build_overpass_query(city: dict[str, Any]) -> str:
    bbox = city["bbox"]
    south = bbox["south"]
    west = bbox["west"]
    north = bbox["north"]
    east = bbox["east"]
    return f"""
[out:json][timeout:90];
(
  way["building"]({south},{west},{north},{east});
  relation["building"]({south},{west},{north},{east});
  way["building:part"]({south},{west},{north},{east});
  relation["building:part"]({south},{west},{north},{east});
  way["highway"]({south},{west},{north},{east});
  way["natural"="water"]({south},{west},{north},{east});
  way["waterway"="riverbank"]({south},{west},{north},{east});
  way["landuse"="grass"]({south},{west},{north},{east});
  way["leisure"="park"]({south},{west},{north},{east});
  way["natural"="wood"]({south},{west},{north},{east});
);
out body geom;
"""


def fetch_overpass(query: str, url: str = OVERPASS_URL, retries: int = 2) -> dict[str, Any]:
    payload = urllib.parse.urlencode({"data": query}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"User-Agent": "uav-virtual-validation/0.1"})
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(2.0 + attempt * 3.0)
    raise RuntimeError(f"Overpass request failed: {last_error}") from last_error


def parse_height_m(tags: dict[str, str], default_height_m: float, level_height_m: float) -> float:
    raw_height = str(tags.get("height") or tags.get("building:height") or "").lower().replace("meters", "").replace("m", "").strip()
    if raw_height:
        try:
            return max(3.0, float(raw_height.split(";")[0]))
        except ValueError:
            pass
    levels = tags.get("building:levels") or tags.get("levels")
    if levels:
        try:
            return max(3.0, float(str(levels).split(";")[0]) * level_height_m)
        except ValueError:
            pass
    return default_height_m


def is_building_way(tags: dict[str, str]) -> bool:
    building = str(tags.get("building") or tags.get("building:part") or "").strip().lower()
    if not building:
        return False
    return building not in {"no", "false", "0", "entrance", "roof", "ruins"}


def polygon_area_deg2(coords: list[list[float]]) -> float:
    area = 0.0
    for idx in range(len(coords) - 1):
        x1, y1 = coords[idx]
        x2, y2 = coords[idx + 1]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def overpass_to_building_geojson(city: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    osm_cfg = city.get("osm", {})
    default_height = float(osm_cfg.get("default_building_height_m", 24.0))
    level_height = float(osm_cfg.get("level_height_m", 3.2))
    max_buildings = int(osm_cfg.get("max_buildings", 2500))

    features: list[dict[str, Any]] = []
    for element in payload.get("elements", []):
        if element.get("type") != "way" or "geometry" not in element:
            continue
        tags = element.get("tags", {})
        if not is_building_way(tags):
            continue
        coords = [[pt["lon"], pt["lat"]] for pt in element["geometry"]]
        if len(coords) < 4:
            continue
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        height = parse_height_m(tags, default_height, level_height)
        area = polygon_area_deg2(coords)
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "layer": "real_building",
                    "source": "openstreetmap",
                    "osm_type": element.get("type"),
                    "osm_id": element.get("id"),
                    "name": tags.get("name", ""),
                    "height_m": round(height, 2),
                    "building": tags.get("building", "yes"),
                    "levels": tags.get("building:levels", ""),
                    "risk_score_add": round(max(0.0, height - 60.0) * 0.08, 2),
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords],
                },
                "_sort_area": area,
            }
        )

    features.sort(key=lambda item: item["_sort_area"], reverse=True)
    features = features[:max_buildings]
    for feature in features:
        feature.pop("_sort_area", None)
    return {
        "type": "FeatureCollection",
        "name": f"{city['name']}_osm_buildings",
        "features": features,
    }


def city_ground_geojson(city: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    bbox = city["bbox"]
    features: list[dict[str, Any]] = [
        {
            "type": "Feature",
            "properties": {
                "layer": "ground",
                "name": "city_extent_ground",
                "source": "city_config_bbox",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [bbox["west"], bbox["south"]],
                    [bbox["east"], bbox["south"]],
                    [bbox["east"], bbox["north"]],
                    [bbox["west"], bbox["north"]],
                    [bbox["west"], bbox["south"]],
                ]],
            },
        }
    ]

    for element in payload.get("elements", []):
        if element.get("type") != "way" or "geometry" not in element:
            continue
        tags = element.get("tags", {})
        coords = [[pt["lon"], pt["lat"]] for pt in element["geometry"]]
        if len(coords) < 2:
            continue
        if "highway" in tags:
            highway = tags.get("highway", "")
            width_px = 1.5
            if highway in {"motorway", "trunk", "primary"}:
                width_px = 4.0
            elif highway in {"secondary", "tertiary"}:
                width_px = 3.0
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "layer": "road",
                        "source": "openstreetmap",
                        "osm_id": element.get("id"),
                        "highway": highway,
                        "name": tags.get("name", ""),
                        "width_px": width_px,
                    },
                    "geometry": {"type": "LineString", "coordinates": coords},
                }
            )
            continue
        is_closed = coords[0] == coords[-1]
        if not is_closed or len(coords) < 4:
            continue
        layer = None
        if tags.get("natural") == "water" or tags.get("waterway") == "riverbank":
            layer = "water"
        elif tags.get("landuse") == "grass" or tags.get("leisure") == "park" or tags.get("natural") == "wood":
            layer = "green"
        if layer:
            features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "layer": layer,
                        "source": "openstreetmap",
                        "osm_id": element.get("id"),
                        "name": tags.get("name", ""),
                    },
                    "geometry": {"type": "Polygon", "coordinates": [coords]},
                }
            )
    return {
        "type": "FeatureCollection",
        "name": f"{city['name']}_ground",
        "features": features,
    }


def city_route_geojson(city: dict[str, Any]) -> dict[str, Any]:
    coords = [[point["lon"], point["lat"], point.get("altitude_m", 120.0)] for point in city["default_route"]]
    return {
        "type": "FeatureCollection",
        "name": f"{city['name']}_route",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "layer": "real_city_route",
                    "city": city["name"],
                    "display_name": city.get("display_name", city["name"]),
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords,
                },
            }
        ],
    }


def city_route_length_m(city: dict[str, Any]) -> float:
    points = city["default_route"]
    total = 0.0
    for idx in range(1, len(points)):
        prev = points[idx - 1]
        cur = points[idx]
        total += haversine_m(prev["lat"], prev["lon"], cur["lat"], cur["lon"])
    return total
