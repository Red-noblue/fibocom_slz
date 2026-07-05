"""复用现有 UAV 三维工作台的增强服务：在原页面上挂接候选航线规划插件与 API。"""

from __future__ import annotations

import argparse
import errno
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from route_selection import CityRoutePlanner, PlannerRequest
from route_selection.io import read_json, resolve_city_assets, route_result_to_geojson, write_json


UAV_ROOT = Path("/home/fibo/fibocom_slz/modules/uav_virtual_validation")
UAV_WEB_INDEX = UAV_ROOT / "web" / "index.html"
UAV_WEB_APP = UAV_ROOT / "web" / "static" / "app.js"
UAV_SERVE_WEB = UAV_ROOT / "scripts" / "serve_web.py"
PLUGIN_JS = ROOT / "web_integration" / "route_selection_plugin.js"
OUTPUT_ROOT = ROOT / "outputs" / "uav_workbench"
DEFAULT_WORKBENCH_PAGE = "/web/route_selection_combined.html"
DEFAULT_DATASET_KEY = "wuhan_central_urban"
PAGE_TO_MODE = {
    "/web/route_selection.html": CityRoutePlanner.PLANNING_MODE_COMBINED,
    "/web/route_selection_combined.html": CityRoutePlanner.PLANNING_MODE_COMBINED,
    "/web/route_selection_weather.html": CityRoutePlanner.PLANNING_MODE_WEATHER_ONLY,
    "/web/route_selection_building.html": CityRoutePlanner.PLANNING_MODE_BUILDING_ONLY,
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


def load_serve_web_module():
    if not UAV_SERVE_WEB.exists():
        raise RuntimeError(f"缺少本地 UAV 工作台服务快照：{UAV_SERVE_WEB}")
    spec = importlib.util.spec_from_file_location("uav_validation_serve_web", UAV_SERVE_WEB)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载现有工作台服务脚本：{UAV_SERVE_WEB}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SERVE_WEB_MODULE = load_serve_web_module()
BaseHandler = SERVE_WEB_MODULE.UavValidationHandler
ThreadingHTTPServer = SERVE_WEB_MODULE.http.server.ThreadingHTTPServer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="启动复用现有 UAV 三维工作台的路径选择增强服务。")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8091)
    parser.add_argument("--public-ip", default="")
    return parser.parse_args()


def list_port_listeners(port: int) -> list[str]:
    try:
        result = subprocess.run(
            ["ss", "-ltnp", f"sport = :{port}"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return []
    if result.returncode != 0:
        return []
    listeners: list[str] = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("State"):
            continue
        pids = re.findall(r"pid=(\d+)", line)
        if not pids:
            listeners.append(line)
            continue
        for pid_text in pids:
            cmdline_path = Path(f"/proc/{pid_text}/cmdline")
            try:
                cmdline_raw = cmdline_path.read_bytes()
            except OSError:
                listeners.append(f"PID {pid_text}")
                continue
            cmdline = " ".join(part for part in cmdline_raw.decode("utf-8", errors="replace").split("\x00") if part)
            listeners.append(f"PID {pid_text}: {cmdline}" if cmdline else f"PID {pid_text}")
    return listeners


def format_bind_error(host: str, port: int) -> str:
    lines = [f"无法启动服务：{host}:{port} 已被占用。"]
    listeners = list_port_listeners(port)
    if listeners:
        lines.append("当前监听进程：")
        lines.extend(f"  - {item}" for item in listeners)
    lines.append(f"如需继续，可先停止现有进程，或改用其他端口，例如：--port {port + 1}")
    return "\n".join(lines)


def parse_dataset_map(app_js_text: str) -> dict[str, dict[str, str]]:
    dataset_map: dict[str, dict[str, str]] = {}
    current_key = ""
    current_lines: list[str] = []
    brace_depth = 0
    in_datasets = False
    for raw_line in app_js_text.splitlines():
        line = raw_line.rstrip()
        if not in_datasets:
            if line.strip().startswith("const DATASETS = {"):
                in_datasets = True
            continue
        if current_key:
            current_lines.append(line)
            brace_depth += line.count("{") - line.count("}")
            if brace_depth <= 0:
                block = "\n".join(current_lines)
                name_match = re.search(r'name:\s*"([^"]+)"', block)
                route_match = re.search(r'route:\s*"([^"]+)"', block)
                if name_match:
                    dataset_map[current_key] = {
                        "dataset_key": current_key,
                        "city_name": name_match.group(1),
                        "route_asset": route_match.group(1) if route_match else "",
                    }
                current_key = ""
                current_lines = []
            continue
        if line.strip() == "};":
            break
        match = re.match(r"\s*([A-Za-z0-9_]+):\s*\{\s*$", line)
        if match:
            current_key = match.group(1)
            current_lines = [line]
            brace_depth = line.count("{") - line.count("}")
    return dataset_map


def dataset_catalog() -> dict[str, dict[str, Any]]:
    app_js_text = UAV_WEB_APP.read_text(encoding="utf-8")
    parsed = parse_dataset_map(app_js_text)
    catalog: dict[str, dict[str, Any]] = {}
    for dataset_key, item in parsed.items():
        city_name = item["city_name"]
        city_dir = UAV_ROOT / "outputs" / "real_city" / city_name
        config_path = city_dir / "city_config_snapshot.json"
        summary_path = city_dir / "city_summary.json"
        weather_path = city_dir / "real_weather_field.geojson"
        buildings_path = city_dir / "real_buildings.geojson"
        supported = all(path.exists() for path in (config_path, summary_path, weather_path, buildings_path))
        payload: dict[str, Any] = {
            "dataset_key": dataset_key,
            "city_name": city_name,
            "supported": supported,
        }
        if supported:
            summary = read_json(summary_path)
            config = read_json(config_path)
            payload.update(
                {
                    "display_name": summary.get("display_name", city_name),
                    "bbox": summary.get("bbox") or config.get("bbox"),
                    "center": summary.get("center") or config.get("center"),
                    "default_route": config.get("default_route") or [],
                }
            )
        catalog[dataset_key] = payload
    return catalog


def require_supported_dataset(dataset_key: str) -> dict[str, Any]:
    catalog = dataset_catalog()
    item = catalog.get(dataset_key)
    if item is None:
        raise ValueError(f"数据集不存在：{dataset_key}")
    if not item.get("supported"):
        raise ValueError(f"当前数据集不支持候选航线规划：{dataset_key}")
    return item


def load_city_assets_from_dataset(dataset_key: str) -> dict[str, Any]:
    item = require_supported_dataset(dataset_key)
    city_dir = UAV_ROOT / "outputs" / "real_city" / item["city_name"]
    asset_paths = resolve_city_assets(city_dir)
    return {
        "dataset": item,
        "asset_paths": asset_paths,
        "city_config": read_json(asset_paths["city_config"]),
        "city_summary": read_json(asset_paths["city_summary"]),
        "weather": read_json(asset_paths["weather"]),
        "buildings": read_json(asset_paths["buildings"]),
        "ground": read_json(asset_paths["ground"]) if asset_paths["ground"].exists() else None,
    }


def write_plan_outputs(dataset_key: str, city_name: str, planning_mode: str, payload: dict[str, Any]) -> dict[str, str]:
    output_dir = OUTPUT_ROOT / planning_mode / dataset_key
    write_json(payload, output_dir / "route_candidates.json")
    write_json(route_result_to_geojson(payload), output_dir / "route_candidates.geojson")
    for route in payload.get("routes", []):
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
                            "max_precipitation_mm": route.get("max_precipitation_mm"),
                            "max_weather_risk_score": route.get("max_weather_risk_score"),
                            "high_risk_exposure_ratio": route.get("high_risk_exposure_ratio"),
                            "city": city_name,
                            "dataset_key": dataset_key,
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


def injected_index_html(planning_mode: str) -> str:
    html = UAV_WEB_INDEX.read_text(encoding="utf-8")
    body_marker = "</body>"
    refreshed_app_script = '<script src="./static/app.js?v=20260704-combined-fusion-v21"></script>'
    page_config = {
        "defaultDatasetKey": DEFAULT_DATASET_KEY,
        "hideDefaultRoute": True,
    }
    plugin_config = {
        "planning_mode": planning_mode,
        "show_buildings": planning_mode != CityRoutePlanner.PLANNING_MODE_WEATHER_ONLY,
        "show_weather": planning_mode != CityRoutePlanner.PLANNING_MODE_BUILDING_ONLY,
    }
    app_script_pattern = re.compile(r'<script\s+src="\.\/static\/app\.js\?v=[^"]+"><\/script>')
    app_script_match = app_script_pattern.search(html)
    if app_script_match is None:
        raise RuntimeError("现有工作台 index.html 缺少 app.js 脚本标记，无法注入路线选择配置。")
    app_injection = (
        f'  <script>window.ROUTE_SELECTION_PAGE_CONFIG = {json.dumps(page_config, ensure_ascii=False)};</script>\n'
        f"  {refreshed_app_script}"
    )
    html = html[: app_script_match.start()] + app_injection + html[app_script_match.end() :]
    plugin_injection = (
        "\n"
        f"  <script>window.ROUTE_SELECTION_PLUGIN_CONFIG = {json.dumps(plugin_config, ensure_ascii=False)};</script>\n"
        '  <script src="/route-selection-plugin.js?v=20260704-combined-fusion-v21"></script>\n'
    )
    if body_marker not in html:
        raise RuntimeError("现有工作台 index.html 缺少 </body> 标记，无法注入插件。")
    return html.replace(body_marker, plugin_injection + body_marker)


class RouteSelectionWorkbenchHandler(BaseHandler):
    def send_injected_index(self, planning_mode: str, *, include_body: bool) -> None:
        body = injected_index_html(planning_mode).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if include_body:
            self.wfile.write(body)

    def send_plugin_js(self, *, include_body: bool) -> None:
        body = PLUGIN_JS.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/javascript; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if include_body:
            self.wfile.write(body)

    def do_HEAD(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", ""}:
            self.send_response(302)
            self.send_header("Location", DEFAULT_WORKBENCH_PAGE)
            self.end_headers()
            return
        if parsed.path in PAGE_TO_MODE:
            self.send_injected_index(PAGE_TO_MODE[parsed.path], include_body=False)
            return
        if parsed.path == "/route-selection-plugin.js":
            self.send_plugin_js(include_body=False)
            return
        super().do_HEAD()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", ""}:
            self.send_response(302)
            self.send_header("Location", DEFAULT_WORKBENCH_PAGE)
            self.end_headers()
            return
        if parsed.path in PAGE_TO_MODE:
            self.send_injected_index(PAGE_TO_MODE[parsed.path], include_body=True)
            return
        if parsed.path == "/route-selection-plugin.js":
            self.send_plugin_js(include_body=True)
            return
        if parsed.path == "/api/route-selection/datasets":
            self.send_json({"datasets": list(dataset_catalog().values())})
            return
        if parsed.path == "/api/route-selection/current":
            query = parse_qs(parsed.query)
            dataset_key = self.require_query_value(query, "dataset_key")
            self.send_json(require_supported_dataset(dataset_key))
            return
        if parsed.path == "/api/route-selection/weather":
            query = parse_qs(parsed.query)
            dataset_key = self.require_query_value(query, "dataset_key")
            self.send_json(load_city_assets_from_dataset(dataset_key)["weather"])
            return
        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/route-selection/plan":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                request = json.loads(self.rfile.read(length).decode("utf-8"))
                payload = self.handle_route_selection_plan(request)
                self.send_json(payload)
            except Exception as exc:
                self.send_json({"error": str(exc)}, code=400)
            return
        super().do_POST()

    @staticmethod
    def require_query_value(query: dict[str, list[str]], key: str) -> str:
        values = query.get(key) or []
        value = values[0].strip() if values else ""
        if not value:
            raise ValueError(f"缺少查询参数：{key}")
        return value

    def handle_route_selection_plan(self, request: dict[str, Any]) -> dict[str, Any]:
        dataset_key = str(request.get("dataset_key") or "").strip()
        if not dataset_key:
            raise ValueError("缺少 dataset_key。")
        planning_mode = normalize_planning_mode(request.get("planning_mode"))
        explicit_max_altitude_m = optional_float(request.get("max_altitude_m"))
        assets = load_city_assets_from_dataset(dataset_key)
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
            max_altitude_m=explicit_max_altitude_m,
        )
        planning = planner.plan(plan_request)
        max_altitude_relaxed = False
        if not planning.routes:
            hint = planner.explain_empty_result(plan_request)
            if hint:
                raise ValueError(hint)
        payload = planning.to_dict()
        payload["dataset_key"] = dataset_key
        payload["output_paths"] = write_plan_outputs(dataset_key, assets["dataset"]["city_name"], planning_mode, payload)
        payload.setdefault("planner", {})
        payload["planner"]["requested_max_altitude_m"] = explicit_max_altitude_m
        payload["planner"]["max_altitude_relaxed"] = max_altitude_relaxed
        return payload

    def send_json(self, payload: dict[str, Any], code: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    args = parse_args()
    os.chdir(UAV_ROOT)
    try:
        server = ThreadingHTTPServer((args.host, args.port), RouteSelectionWorkbenchHandler)
    except OSError as exc:
        if exc.errno == errno.EADDRINUSE:
            print(format_bind_error(args.host, args.port), file=sys.stderr)
            raise SystemExit(1) from None
        raise
    lan_ip = SERVE_WEB_MODULE.detect_lan_ip()
    public_ip = args.public_ip or lan_ip
    public_base = f"http://{public_ip}:{args.port}"
    print(f"web root: {UAV_ROOT}")
    print(f"route selection combined: {public_base}/web/route_selection_combined.html")
    print(f"route selection weather:  {public_base}/web/route_selection_weather.html")
    print(f"route selection building: {public_base}/web/route_selection_building.html")
    print(f"local:  http://127.0.0.1:{args.port}/")
    print(f"lan:    http://{lan_ip}:{args.port}/")
    print(f"public: http://{public_ip}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
