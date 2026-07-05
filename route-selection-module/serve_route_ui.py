"""路径选择可视化服务：提供本地页面、城市资产接口和候选航线规划接口。"""

from __future__ import annotations

import argparse
import http.server
import json
import mimetypes
import socketserver
import sys
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from route_selection import CityRoutePlanner, PlannerRequest
from route_selection.io import read_json, resolve_city_assets, route_result_to_geojson, write_json


WEB_ROOT = ROOT / "web"
OUTPUT_ROOT = ROOT / "outputs" / "ui_runs"
DEFAULT_PAGE = "/combined.html"
PAGE_TO_MODE = {
    "/combined.html": CityRoutePlanner.PLANNING_MODE_COMBINED,
    "/weather_only.html": CityRoutePlanner.PLANNING_MODE_WEATHER_ONLY,
    "/building_only.html": CityRoutePlanner.PLANNING_MODE_BUILDING_ONLY,
}


def optional_float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return float(text)


def normalize_planning_mode(value: Any) -> str:
    planning_mode = str(value or CityRoutePlanner.PLANNING_MODE_COMBINED).strip() or CityRoutePlanner.PLANNING_MODE_COMBINED
    if planning_mode not in CityRoutePlanner.PLANNING_MODES:
        raise ValueError(f"planning_mode 不支持：{planning_mode}")
    return planning_mode


REAL_CITY_ROOT = Path("/home/fibo/fibocom_slz/modules/uav_virtual_validation/outputs/real_city")
DEFAULT_CITY = "wuhan_central_urban"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="启动路径选择可视化界面本地服务。")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址。")
    parser.add_argument("--port", type=int, default=8765, help="监听端口。")
    return parser.parse_args()


@lru_cache(maxsize=512)
def read_json_cached(path: str) -> dict:
    return read_json(path)


def city_dirs() -> list[Path]:
    if not REAL_CITY_ROOT.exists():
        return []
    return sorted(path for path in REAL_CITY_ROOT.iterdir() if path.is_dir())


def discover_cities() -> list[dict]:
    cities: list[dict] = []
    for city_dir in city_dirs():
        summary_path = city_dir / "city_summary.json"
        config_path = city_dir / "city_config_snapshot.json"
        weather_path = city_dir / "real_weather_field.geojson"
        buildings_path = city_dir / "real_buildings.geojson"
        if not (summary_path.exists() and config_path.exists() and weather_path.exists() and buildings_path.exists()):
            continue
        summary = read_json_cached(str(summary_path))
        config = read_json_cached(str(config_path))
        cities.append(
            {
                "name": str(summary.get("name") or city_dir.name),
                "display_name": str(summary.get("display_name") or summary.get("name") or city_dir.name),
                "bbox": summary.get("bbox") or config.get("bbox"),
                "center": summary.get("center") or config.get("center"),
                "building_count": int(summary.get("building_count") or 0),
                "weather_sample_count": int(summary.get("weather_sample_count") or 0),
                "default_route": config.get("default_route") or [],
                "city_dir": str(city_dir),
            }
        )
    cities.sort(key=lambda item: (0 if item["name"] == DEFAULT_CITY else 1, not item["name"].startswith("wuhan"), item["display_name"]))
    return cities


def city_catalog() -> dict[str, dict]:
    return {item["name"]: item for item in discover_cities()}


def require_city(city_name: str) -> dict:
    catalog = city_catalog()
    city = catalog.get(city_name)
    if city is None:
        raise ValueError(f"城市不存在或缺少资产：{city_name}")
    return city


def load_city_assets(city_name: str) -> dict:
    city = require_city(city_name)
    asset_paths = resolve_city_assets(city["city_dir"])
    tiles_dir = asset_paths["city_dir"] / "tiles"
    asset_urls = {
        "tileset": f"/assets/real_city/{city_name}/tiles/tileset.json" if (tiles_dir / "tileset.json").exists() else None,
        "ground_tileset": f"/assets/real_city/{city_name}/tiles/ground_tileset.json" if (tiles_dir / "ground_tileset.json").exists() else None,
        "outline_tileset": f"/assets/real_city/{city_name}/tiles/outline_tileset.json" if (tiles_dir / "outline_tileset.json").exists() else None,
    }
    return {
        "city": city,
        "city_config": read_json_cached(str(asset_paths["city_config"])),
        "city_summary": read_json_cached(str(asset_paths["city_summary"])),
        "weather": read_json_cached(str(asset_paths["weather"])),
        "buildings": read_json_cached(str(asset_paths["buildings"])),
        "ground": read_json_cached(str(asset_paths["ground"])) if asset_paths["ground"].exists() else None,
        "asset_paths": asset_paths,
        "asset_urls": asset_urls,
    }


def latest_plan_path(city_name: str, planning_mode: str) -> Path:
    return OUTPUT_ROOT / planning_mode / city_name / "route_candidates.json"


def latest_plan_geojson_path(city_name: str, planning_mode: str) -> Path:
    return OUTPUT_ROOT / planning_mode / city_name / "route_candidates.geojson"


def write_plan_outputs(city_name: str, planning_mode: str, result_payload: dict) -> dict:
    output_dir = OUTPUT_ROOT / planning_mode / city_name
    write_json(result_payload, output_dir / "route_candidates.json")
    geojson = route_result_to_geojson(result_payload)
    write_json(geojson, output_dir / "route_candidates.geojson")
    for route in result_payload.get("routes", []):
        write_json(
            {
                "type": "FeatureCollection",
                "name": route["route_id"],
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "route_id": route["route_id"],
                            "label": route["label"],
                            "strategy": route["strategy"],
                            "score": route["score"],
                            "topsis_score": route.get("topsis_score"),
                            "robustness_score": route.get("robustness_score"),
                            "reliability_ratio": route.get("reliability_ratio"),
                        },
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[point["lon"], point["lat"], point["altitude_m"]] for point in route["waypoints"]],
                        },
                    }
                ],
            },
            output_dir / f"{route['route_id']}.geojson",
        )
    return {
        "json": str(output_dir / "route_candidates.json"),
        "geojson": str(output_dir / "route_candidates.geojson"),
    }


class RouteUiHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, directory: str | None = None, **kwargs) -> None:
        super().__init__(*args, directory=str(WEB_ROOT), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"", "/"}:
            self.send_response(302)
            self.send_header("Location", DEFAULT_PAGE)
            self.end_headers()
            return
        if parsed.path in PAGE_TO_MODE:
            self.send_mode_page(PAGE_TO_MODE[parsed.path])
            return
        if parsed.path.startswith("/api/"):
            self.handle_api_get(parsed)
            return
        if parsed.path.startswith("/assets/real_city/"):
            self.handle_asset_get(parsed)
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/plan":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(length).decode("utf-8"))
            payload = self.handle_plan_request(request)
            self.send_json(payload)
        except Exception as exc:
            self.send_json({"error": str(exc)}, code=400)

    def handle_api_get(self, parsed) -> None:
        try:
            query = parse_qs(parsed.query)
            if parsed.path == "/api/cities":
                self.send_json({"cities": discover_cities(), "default_city": DEFAULT_CITY})
                return
            if parsed.path == "/api/city":
                city_name = self.require_query_value(query, "city")
                planning_mode = normalize_planning_mode((query.get("planning_mode") or [None])[0])
                assets = load_city_assets(city_name)
                latest = None
                latest_path = latest_plan_path(city_name, planning_mode)
                if latest_path.exists():
                    latest = read_json(str(latest_path))
                self.send_json(
                    {
                        "city": assets["city"],
                        "summary": assets["city_summary"],
                        "config": assets["city_config"],
                        "asset_urls": assets["asset_urls"],
                        "latest_plan": latest,
                    }
                )
                return
            if parsed.path == "/api/buildings":
                city_name = self.require_query_value(query, "city")
                self.send_json(load_city_assets(city_name)["buildings"])
                return
            if parsed.path == "/api/weather":
                city_name = self.require_query_value(query, "city")
                self.send_json(load_city_assets(city_name)["weather"])
                return
            if parsed.path == "/api/latest-plan":
                city_name = self.require_query_value(query, "city")
                planning_mode = normalize_planning_mode((query.get("planning_mode") or [None])[0])
                latest_path = latest_plan_path(city_name, planning_mode)
                if not latest_path.exists():
                    self.send_json({"routes": []})
                    return
                self.send_json(read_json(str(latest_path)))
                return
            self.send_error(404)
        except Exception as exc:
            self.send_json({"error": str(exc)}, code=400)

    def handle_asset_get(self, parsed) -> None:
        raw_relative = parsed.path[len("/assets/real_city/") :].strip("/")
        if not raw_relative:
            self.send_error(404)
            return
        candidate = (REAL_CITY_ROOT / raw_relative).resolve()
        root_resolved = REAL_CITY_ROOT.resolve()
        if root_resolved not in candidate.parents and candidate != root_resolved:
            self.send_error(403)
            return
        if not candidate.exists() or not candidate.is_file():
            self.send_error(404)
            return
        self.send_local_file(candidate)

    def handle_plan_request(self, request: dict) -> dict:
        city_name = str(request.get("city") or "").strip()
        if not city_name:
            raise ValueError("缺少城市名称。")
        planning_mode = normalize_planning_mode(request.get("planning_mode"))
        assets = load_city_assets(city_name)
        planner = CityRoutePlanner.from_payloads(
            city_config=assets["city_config"],
            city_summary=assets["city_summary"],
            buildings_geojson=assets["buildings"],
            weather_geojson=assets["weather"],
            ground_geojson=assets.get("ground"),
        )
        plan_request = PlannerRequest(
            start_lat=float(request["start_lat"]),
            start_lon=float(request["start_lon"]),
            end_lat=float(request["end_lat"]),
            end_lon=float(request["end_lon"]),
            planning_mode=planning_mode,
            start_altitude_m=float(request.get("start_altitude_m") or 120.0),
            end_altitude_m=float(request.get("end_altitude_m") or 120.0),
            min_altitude_m=float(request.get("min_altitude_m") or 0.0),
            candidate_count=int(request.get("candidate_count") or 5),
            cell_m=float(request.get("cell_m") or 220.0),
            safety_clearance_m=float(request.get("safety_clearance_m") or 25.0),
            cruise_speed_mps=float(request.get("cruise_speed_mps") or 14.0),
            climb_speed_mps=float(request.get("climb_speed_mps") or 4.0),
            descend_speed_mps=float(request.get("descend_speed_mps") or 5.0),
            max_altitude_m=optional_float(request.get("max_altitude_m")),
        )
        result = planner.plan(plan_request)
        result_payload = result.to_dict()
        output_paths = write_plan_outputs(city_name, planning_mode, result_payload)
        result_payload["output_paths"] = output_paths
        return result_payload

    @staticmethod
    def require_query_value(query: dict[str, list[str]], key: str) -> str:
        values = query.get(key) or []
        value = values[0].strip() if values else ""
        if not value:
            raise ValueError(f"缺少查询参数：{key}")
        return value

    def send_json(self, payload: dict, code: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_local_file(self, path: Path) -> None:
        data = path.read_bytes()
        content_type, _encoding = mimetypes.guess_type(str(path))
        self.send_response(200)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_mode_page(self, planning_mode: str) -> None:
        html = (WEB_ROOT / "index.html").read_text(encoding="utf-8")
        body = html.replace('data-planning-mode="combined"', f'data-planning-mode="{planning_mode}"').encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        super().log_message(fmt, *args)


class ThreadingHttpServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def build_server(host: str, port: int) -> ThreadingHttpServer:
    return ThreadingHttpServer((host, port), RouteUiHandler)


def main() -> None:
    args = parse_args()
    server = build_server(args.host, args.port)
    print(f"route_ui_combined=http://{args.host}:{args.port}/combined.html")
    print(f"route_ui_weather_only=http://{args.host}:{args.port}/weather_only.html")
    print(f"route_ui_building_only=http://{args.host}:{args.port}/building_only.html")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
