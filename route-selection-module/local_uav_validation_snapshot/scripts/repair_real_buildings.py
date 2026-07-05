"""清洗已生成真实城市建筑资产：删除被误归入建筑层的公园、道路、绿地等低矮面状要素。"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REAL_CITY_ROOT = ROOT / "outputs" / "real_city"

NON_BUILDING_NAME_KEYWORDS = (
    "公园",
    "绿地",
    "绿道",
    "广场",
    "遗址",
    "墓园",
    "陵园",
    "义园",
    "湖",
    "河",
    "江",
    "路",
    "街",
    "巷",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="清洗真实城市建筑 GeoJSON 中的非建筑伪几何。")
    parser.add_argument("--root", default=str(DEFAULT_REAL_CITY_ROOT), help="real_city 输出根目录。")
    parser.add_argument("--city-dir", action="append", default=[], help="只清洗指定城市目录，可重复传入。")
    parser.add_argument("--dry-run", action="store_true", help="只打印统计，不写入文件。")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def default_height(city_dir: Path) -> float:
    snapshot = city_dir / "city_config_snapshot.json"
    if not snapshot.exists():
        return 24.0
    cfg = read_json(snapshot)
    return float(cfg.get("osm", {}).get("default_building_height_m", 24.0))


def metric_stats(coords: list[list[float]]) -> dict[str, float]:
    if len(coords) < 4:
        return {"area_m2": 0.0, "width_m": 0.0, "depth_m": 0.0, "aspect": 1.0, "vertices": float(len(coords))}
    lons = [coord[0] for coord in coords]
    lats = [coord[1] for coord in coords]
    origin_lon = lons[0]
    origin_lat = lats[0]
    lon_scale = 111320.0 * max(0.2, math.cos(math.radians(sum(lats) / len(lats))))
    lat_scale = 111320.0
    points = [((lon - origin_lon) * lon_scale, (lat - origin_lat) * lat_scale) for lon, lat in coords]
    area = 0.0
    for current, nxt in zip(points, points[1:]):
        area += current[0] * nxt[1] - nxt[0] * current[1]
    width = (max(lons) - min(lons)) * lon_scale
    depth = (max(lats) - min(lats)) * lat_scale
    short_side = max(1.0, min(width, depth))
    return {
        "area_m2": abs(area) / 2.0,
        "width_m": width,
        "depth_m": depth,
        "aspect": max(width, depth) / short_side,
        "vertices": float(len(coords)),
    }


def has_non_building_name(name: str) -> bool:
    lowered = name.strip().lower()
    if not lowered:
        return False
    return any(keyword in lowered for keyword in NON_BUILDING_NAME_KEYWORDS)


def suspicious_default_lowrise(feature: dict[str, Any], fallback_height: float) -> tuple[bool, str]:
    props = feature.get("properties", {})
    geometry = feature.get("geometry", {})
    coords = geometry.get("coordinates", [[]])[0]
    height = float(props.get("height_m") or 0.0)
    levels = str(props.get("levels") or "").strip()
    name = str(props.get("name") or "").strip()
    if geometry.get("type") != "Polygon" or len(coords) < 4:
        return True, "invalid_polygon"
    if levels or abs(height - fallback_height) > 0.01:
        return False, ""
    stats = metric_stats(coords)
    area = stats["area_m2"]
    aspect = stats["aspect"]
    vertices = stats["vertices"]
    if has_non_building_name(name) and area > 1200.0:
        return True, "non_building_name"
    if area > 22000.0:
        return True, "large_default_area"
    if area > 7000.0 and (vertices > 28.0 or aspect > 6.0):
        return True, "complex_default_area"
    if area > 2500.0 and aspect > 12.0:
        return True, "skinny_surface"
    return False, ""


def clean_city(city_dir: Path, dry_run: bool) -> dict[str, Any] | None:
    buildings_path = city_dir / "real_buildings.geojson"
    summary_path = city_dir / "city_summary.json"
    if not buildings_path.exists():
        return None
    buildings = read_json(buildings_path)
    fallback_height = default_height(city_dir)
    kept: list[dict[str, Any]] = []
    reasons: dict[str, int] = {}
    removed_examples: list[dict[str, Any]] = []
    for feature in buildings.get("features", []):
        remove, reason = suspicious_default_lowrise(feature, fallback_height)
        if remove:
            reasons[reason] = reasons.get(reason, 0) + 1
            if len(removed_examples) < 8:
                removed_examples.append({
                    "name": feature.get("properties", {}).get("name", ""),
                    "osm_id": feature.get("properties", {}).get("osm_id"),
                    "reason": reason,
                })
            continue
        kept.append(feature)

    before = len(buildings.get("features", []))
    after = len(kept)
    if not dry_run and after != before:
        buildings["features"] = kept
        write_json(buildings_path, buildings)
        if summary_path.exists():
            summary = read_json(summary_path)
            summary["building_count"] = after
            summary["building_repair"] = {
                "removed_count": before - after,
                "source": "repair_real_buildings.py",
            }
            write_json(summary_path, summary)
    return {
        "city": city_dir.name,
        "before": before,
        "after": after,
        "removed": before - after,
        "reasons": reasons,
        "examples": removed_examples,
    }


def main() -> None:
    args = parse_args()
    if args.city_dir:
        city_dirs = [Path(item) for item in args.city_dir]
    else:
        city_dirs = sorted(path for path in Path(args.root).iterdir() if path.is_dir())

    reports = [report for city_dir in city_dirs if (report := clean_city(city_dir, args.dry_run))]
    print(json.dumps(reports, ensure_ascii=False, indent=2))
    if not args.dry_run:
        report_path = Path(args.root) / "building_repair_report.json"
        write_json(report_path, {"cities": reports})


if __name__ == "__main__":
    main()
