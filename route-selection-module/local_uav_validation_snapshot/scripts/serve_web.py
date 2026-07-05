"""无人机虚拟验证控制台服务：提供静态页面访问、城市要素纠错和航线草稿本地保存接口。"""

from __future__ import annotations

import argparse
import contextlib
import http.server
import json
import os
import shutil
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from uav_virtual_validation.tiles.gltf_tiles import build_city_tileset

CORRECTIONS_DIR = ROOT / "outputs" / "real_city_corrections"
CORRECTION_INDEX = CORRECTIONS_DIR / "version_index.json"
ROUTE_DRAFTS_DIR = ROOT / "outputs" / "route_drafts"
ROUTE_DRAFT_INDEX = ROUTE_DRAFTS_DIR / "route_index.json"
WORKBENCH_SETTINGS_DIR = ROOT / "outputs" / "workbench_settings"
WORKBENCH_SETTINGS_FILE = WORKBENCH_SETTINGS_DIR / "ui_settings.json"
REAL_CITY_DIR = ROOT / "outputs" / "real_city"
CORRECTION_COLOR_MODES = {"category", "ground", "pale", "muted", "contrast", "outline"}
RADIO_DENSITY_KEYS = {"sparse", "standard", "dense", "ultra", "extreme"}
NON_BUILDING_CORRECTION_CLASSES = {
    # 这些类别在修正版 3D Tiles 中移除原建筑体；桥墩/高架等立体交通结构需保留障碍高度。
    "road",
    "pedestrian",
    "green",
    "plaza",
    "water",
    "parking",
    "construction",
    "transport_facility",
    "other_ground",
    "suspect",
}


def read_json(path: Path, fallback: dict) -> dict:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_version_id(raw: str | None) -> str:
    value = (raw or "").strip()
    if not value:
        return ""
    allowed = []
    for char in value:
        if char.isalnum() or char in {"-", "_"}:
            allowed.append(char)
    return "".join(allowed)


def safe_color_mode(raw: str | None) -> str:
    value = safe_version_id(raw)
    return value if value in CORRECTION_COLOR_MODES else ""


def safe_radio_density(raw: str | None) -> str:
    value = safe_version_id(raw)
    return value if value in RADIO_DENSITY_KEYS else "standard"


def safe_sample_filter(raw: str | None) -> str:
    value = (raw or "").strip()
    if value == "all":
        return "all"
    parts = [safe_version_id(item) for item in value.split(",")]
    parts = [item for item in parts if item]
    return ",".join(parts) if parts else "all"


def version_dataset_key(version_item: dict) -> str:
    generated = version_item.get("generatedTiles") or {}
    return safe_version_id(version_item.get("datasetKey") or generated.get("datasetKey"))


def version_city_name(version_item: dict) -> str:
    generated = version_item.get("generatedTiles") or {}
    return safe_version_id(version_item.get("cityName") or generated.get("cityName"))


def is_local_version_id(value: str) -> bool:
    return len(value) > 1 and value[0] == "v" and value[1:].isdigit()


def version_local_id(version_item: dict) -> str:
    generated = version_item.get("generatedTiles") or {}
    candidates = [
        version_item.get("localVersion"),
        generated.get("version"),
        version_item.get("id"),
    ]
    for raw in candidates:
        value = safe_version_id(raw)
        if is_local_version_id(value):
            return value
        suffix = value.rsplit("_", 1)[-1]
        if is_local_version_id(suffix):
            return suffix
    return safe_version_id(version_item.get("id"))


def local_version_number(value: str) -> int:
    if is_local_version_id(value):
        return int(value[1:])
    return 10**9


def version_matches_dataset(version_item: dict, dataset_key: str, city_name: str) -> bool:
    if version_item.get("id") == "default":
        return False
    return (
        (dataset_key and version_dataset_key(version_item) == dataset_key)
        or (city_name and version_city_name(version_item) == city_name)
    )


def unique_internal_version_id(index: dict, dataset_key: str, city_name: str, local_version: str) -> str:
    existing = {safe_version_id(item.get("id")) for item in index.get("versions", [])}
    candidates = []
    if local_version not in existing:
        candidates.append(local_version)
    if dataset_key:
        candidates.append(f"{dataset_key}_{local_version}")
    if city_name:
        candidates.append(f"{city_name}_{local_version}")
    for candidate in candidates:
        if candidate and candidate not in existing:
            return candidate
    idx = 2
    stem = dataset_key or city_name or "city"
    while f"{stem}_{local_version}_{idx}" in existing:
        idx += 1
    return f"{stem}_{local_version}_{idx}"


def next_dataset_version(index: dict, dataset_key: str, city_name: str) -> tuple[str, str, str]:
    used_numbers = set()
    for item in index.get("versions", []):
        if not version_matches_dataset(item, dataset_key, city_name):
            continue
        number = local_version_number(version_local_id(item))
        if number < 10**9:
            used_numbers.add(number)
    idx = 1
    while idx in used_numbers:
        idx += 1
    local_version = f"v{idx}"
    version = unique_internal_version_id(index, dataset_key, city_name, local_version)
    path = f"{city_name}/{local_version}.json" if city_name else f"{version}.json"
    return version, local_version, path


def version_sort_key(item: dict) -> tuple:
    if item.get("id") == "default":
        return (0, "", "", 0, "")
    local_version = version_local_id(item)
    return (
        1,
        version_dataset_key(item),
        version_city_name(item),
        local_version_number(local_version),
        safe_version_id(item.get("id")),
    )


def feature_key(dataset_key: str, feature: dict) -> str | None:
    props = feature.get("properties") or {}
    if props.get("osm_id") is not None:
        osm_type = props.get("osm_type") or "way"
        return f"{dataset_key}:osm:{osm_type}:{props['osm_id']}"
    if props.get("id"):
        return f"{dataset_key}:id:{props['id']}"
    return None


def build_corrected_city_tiles(payload: dict, version: str) -> dict | None:
    dataset_key = safe_version_id(payload.get("datasetKey"))
    city_name = safe_version_id(payload.get("cityName"))
    records = payload.get("records") or {}
    if not dataset_key or not city_name or not records:
        return None
    city_dir = REAL_CITY_DIR / city_name
    buildings_path = city_dir / "real_buildings.geojson"
    summary_path = city_dir / "city_summary.json"
    if not buildings_path.exists() or not summary_path.exists():
        return None

    buildings = read_json(buildings_path, {"type": "FeatureCollection", "features": []})
    kept_features = []
    removed_count = 0
    for feature in buildings.get("features", []):
        key = feature_key(dataset_key, feature)
        record = records.get(key) if key else None
        if (
            isinstance(record, dict)
            and record.get("dataset") == dataset_key
            and record.get("classId") in NON_BUILDING_CORRECTION_CLASSES
        ):
            removed_count += 1
            continue
        kept_features.append(feature)
    if removed_count == 0:
        return {"datasetKey": dataset_key, "cityName": city_name, "removedCount": 0}

    corrected_dir = city_dir / "corrected_tiles" / version
    corrected_geojson = corrected_dir / "corrected_buildings.geojson"
    corrected_payload = {
        **buildings,
        "features": kept_features,
    }
    write_json(corrected_geojson, corrected_payload)
    paths = build_city_tileset(corrected_geojson, summary_path, corrected_dir)
    return {
        "datasetKey": dataset_key,
        "cityName": city_name,
        "version": version,
        "removedCount": removed_count,
        "tileset": str(Path(paths["tileset"]).relative_to(ROOT)),
    }


def remove_corrected_city_tiles(version_item: dict) -> None:
    generated = version_item.get("generatedTiles") or {}
    city_name = safe_version_id(generated.get("cityName"))
    version = safe_version_id(generated.get("version") or version_item.get("id"))
    if not city_name or not version:
        return
    corrected_dir = REAL_CITY_DIR / city_name / "corrected_tiles" / version
    if corrected_dir.exists():
        shutil.rmtree(corrected_dir)


def ensure_correction_index() -> dict:
    CORRECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    default_path = CORRECTIONS_DIR / "default.json"
    if not default_path.exists():
        write_json(default_path, {
            "schema": "uav_virtual_validation_city_feature_corrections_v1",
            "version": "default",
            "records": {},
        })
    index = read_json(CORRECTION_INDEX, {
        "defaultVersion": "default",
        "defaultVersions": {},
        "defaultColorMode": "category",
        "defaultColorModes": {},
        "versions": [{"id": "default", "label": "原始版本", "path": "default.json"}],
    })
    index.setdefault("defaultVersions", {})
    index.setdefault("defaultColorModes", {})
    index.setdefault("defaultColorMode", "category")
    if not any(item.get("id") == "default" for item in index.get("versions", [])):
        index.setdefault("versions", []).insert(0, {"id": "default", "label": "原始版本", "path": "default.json"})
    write_json(CORRECTION_INDEX, index)
    return index


def ensure_route_index() -> dict:
    ROUTE_DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    index = read_json(ROUTE_DRAFT_INDEX, {"routes": []})
    index.setdefault("routes", [])
    write_json(ROUTE_DRAFT_INDEX, index)
    return index


def ensure_workbench_settings() -> dict:
    settings = read_json(WORKBENCH_SETTINGS_FILE, {
        "schema": "uav_virtual_validation_workbench_settings_v1",
        "radioProfile": {
            "last": {
                "datasetKey": "",
                "densityKey": "standard",
                "sampleFilter": "all",
            },
            "datasets": {},
        },
    })
    settings.setdefault("schema", "uav_virtual_validation_workbench_settings_v1")
    radio_profile = settings.setdefault("radioProfile", {})
    radio_profile.setdefault("last", {"datasetKey": "", "densityKey": "standard", "sampleFilter": "all"})
    radio_profile.setdefault("datasets", {})
    write_json(WORKBENCH_SETTINGS_FILE, settings)
    return settings


def next_route_version(index: dict, dataset_key: str, city_name: str) -> tuple[str, str, str]:
    prefix = city_name or dataset_key or "route"
    used_numbers = set()
    for item in index.get("routes", []):
        if item.get("datasetKey") != dataset_key and item.get("cityName") != city_name:
            continue
        local = safe_version_id(item.get("localVersion") or "")
        if is_local_version_id(local):
            used_numbers.add(int(local[1:]))
    idx = 1
    while idx in used_numbers:
        idx += 1
    local_version = f"v{idx}"
    version = f"{prefix}_{local_version}"
    existing = {safe_version_id(item.get("id")) for item in index.get("routes", [])}
    suffix = 2
    unique_version = version
    while unique_version in existing:
        unique_version = f"{version}_{suffix}"
        suffix += 1
    path = f"{prefix}/{local_version}.geojson"
    return unique_version, local_version, path


def clean_route_coordinates(raw: list) -> list[list[float]]:
    if not isinstance(raw, list) or len(raw) < 2:
        raise ValueError("航线至少需要 2 个航点。")
    coords: list[list[float]] = []
    for item in raw:
        if not isinstance(item, list) or len(item) < 3:
            raise ValueError("航点必须包含经度、纬度和高度。")
        lon = float(item[0])
        lat = float(item[1])
        altitude = float(item[2])
        if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0 and 0.0 <= altitude <= 2000.0):
            raise ValueError("航点经纬度或高度超出允许范围。")
        coords.append([round(lon, 7), round(lat, 7), round(altitude, 2)])
    return coords


class UavValidationHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in {"/api/corrections", "/api/route-drafts", "/api/workbench-settings"}:
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length).decode("utf-8"))
            if parsed.path == "/api/corrections":
                response = self.handle_correction_api(request)
            elif parsed.path == "/api/route-drafts":
                response = self.handle_route_api(request)
            else:
                response = self.handle_workbench_settings_api(request)
            body = json.dumps(response, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            body = str(exc).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def handle_workbench_settings_api(self, request: dict) -> dict:
        action = request.get("action")
        payload = request.get("payload") or {}
        if action != "save_radio_profile":
            raise ValueError(f"不支持的工作台设置动作：{action}")
        dataset_key = safe_version_id(payload.get("datasetKey"))
        if not dataset_key:
            raise ValueError("缺少无线电画像数据集标识。")
        density_key = safe_radio_density(payload.get("densityKey"))
        sample_filter = safe_sample_filter(payload.get("sampleFilter"))
        settings = ensure_workbench_settings()
        radio_profile = settings.setdefault("radioProfile", {})
        radio_profile.setdefault("datasets", {})[dataset_key] = {
            "densityKey": density_key,
            "sampleFilter": sample_filter,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
        radio_profile["last"] = {
            "datasetKey": dataset_key,
            "densityKey": density_key,
            "sampleFilter": sample_filter,
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
        write_json(WORKBENCH_SETTINGS_FILE, settings)
        return {"ok": True, "radioProfile": radio_profile}

    def handle_route_api(self, request: dict) -> dict:
        action = request.get("action")
        payload = request.get("payload") or {}
        if action != "save_route":
            raise ValueError(f"不支持的航线动作：{action}")
        dataset_key = safe_version_id(payload.get("datasetKey"))
        city_name = safe_version_id(payload.get("cityName"))
        if not dataset_key or not city_name:
            raise ValueError("缺少城市数据集标识。")
        coordinates = clean_route_coordinates(payload.get("coordinates") or [])
        route_name = str(payload.get("routeName") or "用户绘制航线").strip()[:80]
        speed_mps = max(0.1, min(80.0, float(payload.get("defaultSpeedMps") or 8.0)))
        altitude_mode = safe_version_id(payload.get("altitudeMode")) or "relative_ground"
        index = ensure_route_index()
        version, local_version, path = next_route_version(index, dataset_key, city_name)
        feature = {
            "type": "Feature",
            "properties": {
                "layer": "user_drawn_route",
                "city": city_name,
                "datasetKey": dataset_key,
                "route_name": route_name,
                "version": version,
                "localVersion": local_version,
                "altitude_mode": altitude_mode,
                "default_speed_mps": round(speed_mps, 2),
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates,
            },
        }
        route_geojson = {
            "type": "FeatureCollection",
            "schema": "uav_virtual_validation_route_draft_v1",
            "name": version,
            "features": [feature],
        }
        write_json(ROUTE_DRAFTS_DIR / path, route_geojson)
        item = {
            "id": version,
            "localVersion": local_version,
            "label": f"航线草稿 {local_version}",
            "path": path,
            "datasetKey": dataset_key,
            "cityName": city_name,
            "routeName": route_name,
            "waypointCount": len(coordinates),
        }
        routes = [entry for entry in index.get("routes", []) if entry.get("id") != version]
        routes.append(item)
        index["routes"] = sorted(routes, key=lambda entry: (entry.get("cityName", ""), entry.get("localVersion", ""), entry.get("id", "")))
        write_json(ROUTE_DRAFT_INDEX, index)
        return {
            "ok": True,
            "version": version,
            "localVersion": local_version,
            "path": path,
            "waypointCount": len(coordinates),
        }

    def handle_correction_api(self, request: dict) -> dict:
        action = request.get("action")
        payload = request.get("payload") or {}
        index = ensure_correction_index()
        if action == "save_version":
            records = payload.get("records", {})
            if not isinstance(records, dict):
                raise ValueError("纠错记录必须是对象。")
            save_mode = payload.get("saveMode") or "new"
            requested_version = safe_version_id(payload.get("version"))
            requested_dataset = safe_version_id(payload.get("datasetKey"))
            requested_city = safe_version_id(payload.get("cityName"))
            if save_mode == "overwrite":
                if requested_version == "default":
                    raise ValueError("原始版本禁止覆盖，请保存为新版本。")
                if not requested_version:
                    raise ValueError("缺少需要覆盖的纠错版本。")
                current_item = next((item for item in index.get("versions", []) if item.get("id") == requested_version), None)
                if current_item is None:
                    raise ValueError(f"纠错版本不存在：{requested_version}")
                current_dataset = version_dataset_key(current_item)
                if requested_dataset and current_dataset and requested_dataset != current_dataset:
                    raise ValueError("不能用当前城市覆盖其他城市的纠错版本。")
                version = requested_version
                local_version = version_local_id(current_item) or version
                tile_version = (current_item.get("generatedTiles") or {}).get("version") or local_version
                path = str(current_item.get("path") or f"{version}.json")
            else:
                version, local_version, path = next_dataset_version(index, requested_dataset, requested_city)
                tile_version = local_version
            payload_to_save = dict(payload)
            payload_to_save.pop("saveMode", None)
            payload_to_save["version"] = version
            payload_to_save["localVersion"] = local_version
            write_json(CORRECTIONS_DIR / path, payload_to_save)
            generated_tiles = build_corrected_city_tiles(payload_to_save, tile_version)
            versions = [item for item in index.get("versions", []) if item.get("id") != version]
            version_item = {
                "id": version,
                "label": f"纠错版本 {local_version}",
                "path": path,
                "datasetKey": safe_version_id(payload_to_save.get("datasetKey")),
                "cityName": safe_version_id(payload_to_save.get("cityName")),
                "localVersion": local_version,
            }
            if generated_tiles:
                version_item["generatedTiles"] = generated_tiles
            versions.append(version_item)
            versions.sort(key=version_sort_key)
            index["versions"] = versions
            write_json(CORRECTION_INDEX, index)
            return {
                "ok": True,
                "version": version,
                "localVersion": local_version,
                "label": version_item["label"],
                "mode": "overwrite" if save_mode == "overwrite" else "new",
                "recordCount": len(records),
                "generatedTiles": generated_tiles,
            }
        if action == "set_default":
            version = safe_version_id(payload.get("version"))
            dataset_key = safe_version_id(payload.get("datasetKey"))
            color_mode = safe_color_mode(payload.get("colorMode"))
            if not version:
                raise ValueError("缺少纠错版本。")
            target = next((item for item in index.get("versions", []) if item.get("id") == version), None)
            if target is None:
                raise ValueError(f"纠错版本不存在：{version}")
            if dataset_key and version != "default":
                target_dataset = version_dataset_key(target)
                if target_dataset and target_dataset != dataset_key:
                    raise ValueError("不能把其他城市的纠错版本设为当前城市默认。")
            if dataset_key:
                index.setdefault("defaultVersions", {})[dataset_key] = version
                if color_mode:
                    index.setdefault("defaultColorModes", {})[dataset_key] = color_mode
            else:
                index["defaultVersion"] = version
                if color_mode:
                    index["defaultColorMode"] = color_mode
            write_json(CORRECTION_INDEX, index)
            return {
                "ok": True,
                "defaultVersion": version,
                "defaultColorMode": color_mode or index.get("defaultColorModes", {}).get(dataset_key, index.get("defaultColorMode", "category")),
            }
        if action == "delete_version":
            version = safe_version_id(payload.get("version"))
            if version == "default":
                raise ValueError("原始版本禁止删除。")
            if not version:
                raise ValueError("缺少需要删除的纠错版本。")
            versions = index.get("versions", [])
            target = next((item for item in versions if item.get("id") == version), None)
            if target is None:
                raise ValueError(f"纠错版本不存在：{version}")
            remove_corrected_city_tiles(target)
            version_file = CORRECTIONS_DIR / str(target.get("path") or f"{version}.json")
            if version_file.exists():
                version_file.unlink()
            index["versions"] = [item for item in versions if item.get("id") != version]
            if index.get("defaultVersion") == version:
                index["defaultVersion"] = "default"
            default_versions = index.setdefault("defaultVersions", {})
            for dataset_key, default_version in list(default_versions.items()):
                if default_version == version:
                    default_versions[dataset_key] = "default"
            write_json(CORRECTION_INDEX, index)
            target_dataset = version_dataset_key(target)
            return {
                "ok": True,
                "deletedVersion": version,
                "defaultVersion": default_versions.get(target_dataset, index.get("defaultVersion", "default")),
            }
        raise ValueError(f"不支持的纠错动作：{action}")

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/workbench-settings":
            body = json.dumps(ensure_workbench_settings(), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path in {"/", ""}:
            self.send_response(302)
            suffix = f"?{parsed.query}" if parsed.query else ""
            self.send_header("Location", f"/web/{suffix}")
            self.end_headers()
            return
        super().do_GET()

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", ""}:
            self.send_response(302)
            suffix = f"?{parsed.query}" if parsed.query else ""
            self.send_header("Location", f"/web/{suffix}")
            self.end_headers()
            return
        super().do_HEAD()


def detect_lan_ip() -> str:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as sock:
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        except OSError:
            return "127.0.0.1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="开放 UAV 虚拟验证 Web 控制台。")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--public-ip", default="")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    os.chdir(ROOT)
    server = http.server.ThreadingHTTPServer((args.host, args.port), UavValidationHandler)
    lan_ip = detect_lan_ip()
    public_ip = args.public_ip or lan_ip
    print(f"web root: {ROOT}")
    print(f"local:  http://127.0.0.1:{args.port}/")
    print(f"lan:    http://{lan_ip}:{args.port}/")
    print(f"public: http://{public_ip}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
