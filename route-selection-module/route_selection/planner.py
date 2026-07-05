"""路径规划核心：融合 A*、连通性/可达性、蒙特卡洛鲁棒性和熵权法-TOPSIS 排序。"""

from __future__ import annotations

import heapq
import math
import random
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any

from .geo import GeoOrigin, bbox_intersects, latlon_to_meters, meters_to_latlon, point_in_poly, segment_hits_poly


@dataclass(frozen=True)
class PlannerRequest:
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    planning_mode: str = "combined"
    start_altitude_m: float = 120.0
    end_altitude_m: float = 120.0
    min_altitude_m: float = 0.0
    candidate_count: int = 5
    cell_m: float = 220.0
    safety_clearance_m: float = 25.0
    cruise_speed_mps: float = 14.0
    climb_speed_mps: float = 4.0
    descend_speed_mps: float = 5.0
    max_altitude_m: float | None = None


@dataclass(frozen=True)
class WeatherState:
    wind_east_mps: float
    wind_north_mps: float
    wind_speed_mps: float
    turbulence_index: float
    precipitation_mm: float
    pressure_hpa: float
    temperature_c: float
    cloud_cover_pct: float = 0.0


@dataclass(frozen=True)
class Building:
    points_xy: list[tuple[float, float]]
    height_m: float
    bbox: tuple[float, float, float, float]


@dataclass(frozen=True)
class WeatherSample:
    x_m: float
    y_m: float
    altitude_m: float
    wind_speed_mps: float
    wind_dir_deg: float
    turbulence_index: float
    precipitation_mm: float
    pressure_hpa: float
    temperature_c: float
    cloud_cover_pct: float = 0.0

    @property
    def wind_east_mps(self) -> float:
        return -self.wind_speed_mps * math.sin(math.radians(self.wind_dir_deg))

    @property
    def wind_north_mps(self) -> float:
        return -self.wind_speed_mps * math.cos(math.radians(self.wind_dir_deg))


@dataclass(frozen=True)
class CostProfile:
    strategy: str
    label: str
    preferred_altitude_m: float
    headwind_factor: float
    crosswind_factor: float
    tailwind_credit: float
    turbulence_factor: float
    precipitation_factor: float
    urban_density_factor: float
    connectivity_factor: float
    reachability_factor: float
    line_deviation_factor: float
    low_progress_factor: float
    reverse_progress_factor: float
    overflight_factor: float
    turn_penalty_factor: float
    rejoin_factor: float
    reuse_penalty_s: float


@dataclass(frozen=True)
class SegmentStats:
    horizontal_m: float
    vertical_m: float
    wind_speed_mps: float
    headwind_mps: float
    tailwind_mps: float
    crosswind_mps: float
    turbulence_index: float
    precipitation_mm: float
    mean_density: float
    mean_connectivity: float
    mean_reachability: float


@dataclass(frozen=True)
class RankingMetric:
    field: str
    benefit: bool


@dataclass(frozen=True)
class RoadGraph:
    nodes_xy: list[tuple[float, float]]
    edges: dict[int, list[tuple[int, float]]]


@dataclass
class RouteCandidate:
    route_id: str
    label: str
    strategy: str
    score: float
    base_cost: float
    topsis_score: float
    robustness_score: float
    reliability_ratio: float
    duration_p95_s: float
    expected_delay_ratio: float
    distance_m: float
    estimated_duration_s: float
    max_wind_speed_mps: float
    max_headwind_mps: float
    max_crosswind_mps: float
    max_turbulence_index: float
    max_precipitation_mm: float
    max_weather_risk_score: float
    high_risk_exposure_ratio: float
    average_urban_density: float
    average_connectivity_index: float
    minimum_connectivity_index: float
    average_reachability_index: float
    corridor_diversity_index: float
    overflight_building_count: int
    overflight_exposure_index: float
    waypoint_count: int
    recommended_rank: int
    waypoints: list[dict[str, float | str]]


@dataclass
class PlanningResult:
    city: dict[str, Any]
    request: dict[str, Any]
    planner: dict[str, Any]
    routes: list[RouteCandidate]

    def to_dict(self) -> dict[str, Any]:
        return {
            "city": self.city,
            "request": self.request,
            "planner": self.planner,
            "routes": [asdict(route) for route in self.routes],
        }


class BuildingIndex:
    def __init__(self, buildings: list[Building], bucket_m: float) -> None:
        self.buildings = buildings
        self.bucket_m = max(40.0, float(bucket_m))
        self.cells: dict[tuple[int, int], list[int]] = {}
        for idx, building in enumerate(buildings):
            left, bottom, right, top = building.bbox
            bx0 = math.floor(left / self.bucket_m)
            by0 = math.floor(bottom / self.bucket_m)
            bx1 = math.floor(right / self.bucket_m)
            by1 = math.floor(top / self.bucket_m)
            for bx in range(bx0, bx1 + 1):
                for by in range(by0, by1 + 1):
                    self.cells.setdefault((bx, by), []).append(idx)

    def _bucket_range(self, left: float, bottom: float, right: float, top: float) -> list[tuple[int, int]]:
        bx0 = math.floor(left / self.bucket_m)
        by0 = math.floor(bottom / self.bucket_m)
        bx1 = math.floor(right / self.bucket_m)
        by1 = math.floor(top / self.bucket_m)
        cells: list[tuple[int, int]] = []
        for bx in range(bx0, bx1 + 1):
            for by in range(by0, by1 + 1):
                cells.append((bx, by))
        return cells

    def query_bbox(self, left: float, bottom: float, right: float, top: float) -> list[Building]:
        seen: set[int] = set()
        matches: list[Building] = []
        for key in self._bucket_range(left, bottom, right, top):
            for idx in self.cells.get(key, []):
                if idx in seen:
                    continue
                seen.add(idx)
                building = self.buildings[idx]
                if bbox_intersects(left, bottom, right, top, *building.bbox):
                    matches.append(building)
        return matches


class WeatherField:
    def __init__(self, samples: list[WeatherSample]) -> None:
        if not samples:
            raise ValueError("天气场为空，无法规划航线。")
        self.samples = samples
        self.altitude_levels_m = sorted({round(sample.altitude_m, 6) for sample in samples})
        self.by_altitude: dict[float, list[WeatherSample]] = {}
        for level in self.altitude_levels_m:
            self.by_altitude[level] = [sample for sample in samples if round(sample.altitude_m, 6) == level]
        self.reference_pressure_by_altitude_hpa = {
            level: sorted(sample.pressure_hpa for sample in self.by_altitude[level])[len(self.by_altitude[level]) // 2]
            for level in self.altitude_levels_m
        }

    def interpolate(self, x_m: float, y_m: float, altitude_m: float) -> WeatherState:
        lower = None
        upper = None
        for level in self.altitude_levels_m:
            if level <= altitude_m:
                lower = level
            if level >= altitude_m and upper is None:
                upper = level
        if lower is None:
            lower = self.altitude_levels_m[0]
        if upper is None:
            upper = self.altitude_levels_m[-1]
        low_state = self._interpolate_2d(self.by_altitude[lower], x_m, y_m)
        high_state = self._interpolate_2d(self.by_altitude[upper], x_m, y_m)
        if abs(upper - lower) < 1e-6:
            state = low_state
        else:
            weight = (altitude_m - lower) / (upper - lower)
            state = WeatherState(
                wind_east_mps=low_state.wind_east_mps * (1.0 - weight) + high_state.wind_east_mps * weight,
                wind_north_mps=low_state.wind_north_mps * (1.0 - weight) + high_state.wind_north_mps * weight,
                wind_speed_mps=low_state.wind_speed_mps * (1.0 - weight) + high_state.wind_speed_mps * weight,
                turbulence_index=low_state.turbulence_index * (1.0 - weight) + high_state.turbulence_index * weight,
                precipitation_mm=low_state.precipitation_mm * (1.0 - weight) + high_state.precipitation_mm * weight,
                pressure_hpa=low_state.pressure_hpa * (1.0 - weight) + high_state.pressure_hpa * weight,
                temperature_c=low_state.temperature_c * (1.0 - weight) + high_state.temperature_c * weight,
                cloud_cover_pct=low_state.cloud_cover_pct * (1.0 - weight) + high_state.cloud_cover_pct * weight,
            )
        if altitude_m > self.altitude_levels_m[-1]:
            ref_alt = max(self.altitude_levels_m[-1], 10.0)
            scale = math.log(max(altitude_m, 11.0) / 10.0) / max(math.log(ref_alt / 10.0), 1e-6)
            scale = max(1.0, min(scale, 1.35))
            state = WeatherState(
                wind_east_mps=state.wind_east_mps * scale,
                wind_north_mps=state.wind_north_mps * scale,
                wind_speed_mps=state.wind_speed_mps * scale,
                turbulence_index=min(1.0, state.turbulence_index * (1.0 + (scale - 1.0) * 0.3)),
                precipitation_mm=state.precipitation_mm,
                pressure_hpa=max(80.0, state.pressure_hpa * math.exp(-(altitude_m - self.altitude_levels_m[-1]) / 8200.0)),
                temperature_c=state.temperature_c - (altitude_m - self.altitude_levels_m[-1]) * 0.004,
                cloud_cover_pct=state.cloud_cover_pct,
            )
        return state

    def reference_pressure_hpa(self, altitude_m: float) -> float:
        lower = None
        upper = None
        for level in self.altitude_levels_m:
            if level <= altitude_m:
                lower = level
            if level >= altitude_m and upper is None:
                upper = level
        if lower is None:
            lower = self.altitude_levels_m[0]
        if upper is None:
            upper = self.altitude_levels_m[-1]
        if abs(upper - lower) < 1e-6:
            return self.reference_pressure_by_altitude_hpa[lower]
        weight = (altitude_m - lower) / (upper - lower)
        return self.reference_pressure_by_altitude_hpa[lower] * (1.0 - weight) + self.reference_pressure_by_altitude_hpa[upper] * weight

    @staticmethod
    def _interpolate_2d(samples: list[WeatherSample], x_m: float, y_m: float) -> WeatherState:
        weights: list[tuple[float, WeatherSample]] = []
        for sample in samples:
            dist_sq = (sample.x_m - x_m) ** 2 + (sample.y_m - y_m) ** 2
            if dist_sq < 1e-6:
                return WeatherState(
                    wind_east_mps=sample.wind_east_mps,
                    wind_north_mps=sample.wind_north_mps,
                    wind_speed_mps=sample.wind_speed_mps,
                    turbulence_index=sample.turbulence_index,
                    precipitation_mm=sample.precipitation_mm,
                    pressure_hpa=sample.pressure_hpa,
                    temperature_c=sample.temperature_c,
                    cloud_cover_pct=sample.cloud_cover_pct,
                )
            weights.append((1.0 / dist_sq, sample))
        weights.sort(key=lambda item: item[0], reverse=True)
        nearest = weights[:4]
        total = sum(weight for weight, _sample in nearest)
        return WeatherState(
            wind_east_mps=sum(weight * sample.wind_east_mps for weight, sample in nearest) / total,
            wind_north_mps=sum(weight * sample.wind_north_mps for weight, sample in nearest) / total,
            wind_speed_mps=sum(weight * sample.wind_speed_mps for weight, sample in nearest) / total,
            turbulence_index=sum(weight * sample.turbulence_index for weight, sample in nearest) / total,
            precipitation_mm=sum(weight * sample.precipitation_mm for weight, sample in nearest) / total,
            pressure_hpa=sum(weight * sample.pressure_hpa for weight, sample in nearest) / total,
            temperature_c=sum(weight * sample.temperature_c for weight, sample in nearest) / total,
            cloud_cover_pct=sum(weight * sample.cloud_cover_pct for weight, sample in nearest) / total,
        )


class CityRoutePlanner:
    PLANNING_MODE_COMBINED = "combined"
    PLANNING_MODE_WEATHER_ONLY = "weather_only"
    PLANNING_MODE_BUILDING_ONLY = "building_only"
    PLANNING_MODES = {
        PLANNING_MODE_COMBINED,
        PLANNING_MODE_WEATHER_ONLY,
        PLANNING_MODE_BUILDING_ONLY,
    }
    MONTE_CARLO_RUNS = 36
    RANKING_METRICS = [
        RankingMetric("distance_m", benefit=False),
        RankingMetric("estimated_duration_s", benefit=False),
        RankingMetric("max_headwind_mps", benefit=False),
        RankingMetric("max_crosswind_mps", benefit=False),
        RankingMetric("max_turbulence_index", benefit=False),
        RankingMetric("max_precipitation_mm", benefit=False),
        RankingMetric("max_weather_risk_score", benefit=False),
        RankingMetric("high_risk_exposure_ratio", benefit=False),
        RankingMetric("average_urban_density", benefit=False),
        RankingMetric("overflight_exposure_index", benefit=False),
        RankingMetric("average_reachability_index", benefit=True),
        RankingMetric("corridor_diversity_index", benefit=True),
        RankingMetric("robustness_score", benefit=True),
    ]
    STRATEGY_ROLE_ORDER = [
        ("fastest", "最快到达"),
        ("safest", "低风险"),
        ("energy_saving", "能耗最少"),
        ("balanced_stable", "均衡稳定推荐"),
        ("most_accessible", "最畅通路线"),
    ]
    DEFAULT_PROFILES = [
        CostProfile(
            strategy="fastest",
            label="最快到达",
            preferred_altitude_m=130.0,
            headwind_factor=0.45,
            crosswind_factor=0.20,
            tailwind_credit=0.18,
            turbulence_factor=0.30,
            precipitation_factor=0.25,
            urban_density_factor=0.18,
            connectivity_factor=0.10,
            reachability_factor=0.12,
            line_deviation_factor=0.26,
            low_progress_factor=0.42,
            reverse_progress_factor=1.20,
            overflight_factor=2.30,
            turn_penalty_factor=0.24,
            rejoin_factor=0.36,
            reuse_penalty_s=0.0,
        ),
        CostProfile(
            strategy="safest",
            label="低风险",
            preferred_altitude_m=220.0,
            headwind_factor=0.74,
            crosswind_factor=0.60,
            tailwind_credit=0.08,
            turbulence_factor=1.22,
            precipitation_factor=0.92,
            urban_density_factor=1.10,
            connectivity_factor=0.68,
            reachability_factor=0.90,
            line_deviation_factor=0.12,
            low_progress_factor=0.18,
            reverse_progress_factor=0.88,
            overflight_factor=6.20,
            turn_penalty_factor=0.34,
            rejoin_factor=0.12,
            reuse_penalty_s=16.0,
        ),
        CostProfile(
            strategy="energy_saving",
            label="能耗最少",
            preferred_altitude_m=160.0,
            headwind_factor=0.82,
            crosswind_factor=0.24,
            tailwind_credit=0.22,
            turbulence_factor=0.36,
            precipitation_factor=0.18,
            urban_density_factor=0.28,
            connectivity_factor=0.18,
            reachability_factor=0.22,
            line_deviation_factor=0.44,
            low_progress_factor=0.92,
            reverse_progress_factor=2.20,
            overflight_factor=2.20,
            turn_penalty_factor=0.82,
            rejoin_factor=0.44,
            reuse_penalty_s=26.0,
        ),
        CostProfile(
            strategy="balanced_stable",
            label="均衡稳定推荐",
            preferred_altitude_m=150.0,
            headwind_factor=0.60,
            crosswind_factor=0.38,
            tailwind_credit=0.14,
            turbulence_factor=1.05,
            precipitation_factor=1.05,
            urban_density_factor=0.52,
            connectivity_factor=0.38,
            reachability_factor=0.46,
            line_deviation_factor=0.20,
            low_progress_factor=0.34,
            reverse_progress_factor=1.05,
            overflight_factor=4.20,
            turn_penalty_factor=0.30,
            rejoin_factor=0.24,
            reuse_penalty_s=12.0,
        ),
        CostProfile(
            strategy="most_accessible",
            label="最畅通路线",
            preferred_altitude_m=100.0,
            headwind_factor=0.54,
            crosswind_factor=0.30,
            tailwind_credit=0.12,
            turbulence_factor=0.38,
            precipitation_factor=0.20,
            urban_density_factor=1.05,
            connectivity_factor=1.20,
            reachability_factor=1.36,
            line_deviation_factor=0.06,
            low_progress_factor=0.12,
            reverse_progress_factor=0.72,
            overflight_factor=5.40,
            turn_penalty_factor=0.28,
            rejoin_factor=0.08,
            reuse_penalty_s=40.0,
        ),
    ]
    CONNECTIVITY_MOVES = [
        (-1, 0, 0),
        (1, 0, 0),
        (0, -1, 0),
        (0, 1, 0),
        (-1, -1, 0),
        (-1, 1, 0),
        (1, -1, 0),
        (1, 1, 0),
    ]
    ASTAR_MOVES = CONNECTIVITY_MOVES + [(0, 0, -1), (0, 0, 1)]

    def __init__(
        self,
        *,
        city_config: dict[str, Any],
        city_summary: dict[str, Any],
        buildings_geojson: dict[str, Any],
        weather_geojson: dict[str, Any],
        ground_geojson: dict[str, Any] | None = None,
    ) -> None:
        self.city_config = city_config
        self.city_summary = city_summary
        center = city_summary.get("center") or city_config.get("center")
        if not center:
            raise ValueError("城市配置缺少 center 字段。")
        self.origin = GeoOrigin(float(center["lat"]), float(center["lon"]))
        self.bbox = city_summary.get("bbox") or city_config.get("bbox")
        if not self.bbox:
            raise ValueError("城市配置缺少 bbox 字段。")
        self.buildings = self._load_buildings(buildings_geojson)
        self.building_heights_m = sorted(building.height_m for building in self.buildings)
        self.weather_field = self._load_weather_field(weather_geojson)
        self.road_graph = self._load_road_graph(ground_geojson)
        self._building_detour_projection_cache: dict[tuple[Any, ...], Any] = {}
        self._building_detour_node_clear_cache: dict[tuple[Any, ...], dict[tuple[int, int], bool]] = {}
        self._building_detour_edge_clear_cache: dict[tuple[Any, ...], dict[tuple[int, int, int, int], bool]] = {}
        self._building_detour_clearance_cache: dict[tuple[Any, ...], dict[tuple[int, int], float]] = {}

    @classmethod
    def from_payloads(
        cls,
        city_config: dict[str, Any],
        city_summary: dict[str, Any],
        buildings_geojson: dict[str, Any],
        weather_geojson: dict[str, Any],
        ground_geojson: dict[str, Any] | None = None,
    ) -> "CityRoutePlanner":
        return cls(
            city_config=city_config,
            city_summary=city_summary,
            buildings_geojson=buildings_geojson,
            weather_geojson=weather_geojson,
            ground_geojson=ground_geojson,
        )

    def plan(self, request: PlannerRequest) -> PlanningResult:
        request = self._normalize_request(request)
        self._validate_request(request)
        consider_buildings = self._consider_buildings(request.planning_mode)
        consider_weather = self._consider_weather(request.planning_mode)
        strict_building_avoidance = self._strict_building_avoidance(request.planning_mode)
        x_values, y_values = self._grid_axes(request.cell_m)
        altitude_layers_m = self._altitude_layers(request)
        building_index = BuildingIndex(self.buildings, bucket_m=max(request.cell_m * 1.75, 120.0))
        start_xy = latlon_to_meters(self.origin, request.start_lat, request.start_lon)
        end_xy = latlon_to_meters(self.origin, request.end_lat, request.end_lon)
        corridor_dx = end_xy[0] - start_xy[0]
        corridor_dy = end_xy[1] - start_xy[1]
        corridor_length_m = max(math.hypot(corridor_dx, corridor_dy), 1e-6)
        corridor_unit = (corridor_dx / corridor_length_m, corridor_dy / corridor_length_m)

        @lru_cache(maxsize=None)
        def node_weather(ix: int, iy: int, iz: int) -> WeatherState:
            return self.weather_field.interpolate(x_values[ix], y_values[iy], altitude_layers_m[iz])

        @lru_cache(maxsize=None)
        def xy_urban_density(ix: int, iy: int) -> float:
            if not consider_buildings:
                return 0.0
            x_m = x_values[ix]
            y_m = y_values[iy]
            radius = max(request.cell_m * 1.8, 200.0)
            nearby = building_index.query_bbox(x_m - radius, y_m - radius, x_m + radius, y_m + radius)
            if not nearby:
                return 0.0
            score = 0.0
            for building in nearby:
                dx = max(0.0, max(building.bbox[0] - x_m, x_m - building.bbox[2]))
                dy = max(0.0, max(building.bbox[1] - y_m, y_m - building.bbox[3]))
                dist = math.hypot(dx, dy)
                score += max(0.0, 1.0 - dist / radius) * min(1.0, building.height_m / 180.0)
            return min(1.0, score / 6.0)

        @lru_cache(maxsize=None)
        def point_in_building_footprint(ix: int, iy: int) -> bool:
            if not consider_buildings:
                return False
            point = (x_values[ix], y_values[iy])
            for building in building_index.query_bbox(point[0], point[1], point[0], point[1]):
                if point_in_poly(point, building.points_xy):
                    return True
            return False

        @lru_cache(maxsize=None)
        def blocked_height(ix: int, iy: int) -> float:
            if not consider_buildings:
                return 0.0
            best = 0.0
            point = (x_values[ix], y_values[iy])
            for building in building_index.query_bbox(point[0], point[1], point[0], point[1]):
                if point_in_poly(point, building.points_xy):
                    best = max(best, building.height_m + request.safety_clearance_m)
            return best

        @lru_cache(maxsize=None)
        def node_is_blocked(ix: int, iy: int, iz: int) -> bool:
            if not consider_buildings:
                return False
            if strict_building_avoidance and point_in_building_footprint(ix, iy):
                return True
            return altitude_layers_m[iz] <= blocked_height(ix, iy) + 1e-6

        @lru_cache(maxsize=None)
        def node_connectivity(ix: int, iy: int, iz: int) -> float:
            if node_is_blocked(ix, iy, iz):
                return 0.0
            current = (ix, iy, iz)
            possible = 0
            free = 0
            for dx, dy, dz in self.CONNECTIVITY_MOVES:
                nxt = (ix + dx, iy + dy, iz + dz)
                if nxt[0] < 0 or nxt[0] >= len(x_values) or nxt[1] < 0 or nxt[1] >= len(y_values):
                    continue
                possible += 1
                if not node_is_blocked(*nxt):
                    free += 1
            if possible == 0:
                return 0.0
            clearance_m = max(0.0, node_building_clearance(ix, iy) - request.safety_clearance_m) if consider_buildings else request.cell_m
            clearance_factor = min(1.0, clearance_m / max(request.cell_m * 1.1, 1.0))
            return max(0.0, min(1.0, (free / possible) * (0.55 + 0.45 * clearance_factor)))

        @lru_cache(maxsize=None)
        def node_reachability(ix: int, iy: int, iz: int) -> float:
            if node_is_blocked(ix, iy, iz):
                return 0.0
            clearance_factor = 1.0
            if consider_buildings:
                clearance_m = max(0.0, altitude_layers_m[iz] - blocked_height(ix, iy))
                clearance_factor = min(1.0, clearance_m / max(request.safety_clearance_m + 70.0, 1.0))
            weather_factor = 1.0
            if consider_weather:
                weather = node_weather(ix, iy, iz)
                weather_factor = self._weather_reachability_factor(
                    wind_speed_mps=weather.wind_speed_mps,
                    turbulence_index=weather.turbulence_index,
                    precipitation_mm=weather.precipitation_mm,
                )
            connectivity = node_connectivity(ix, iy, iz)
            return max(0.0, min(1.0, connectivity * (0.25 + 0.35 * clearance_factor + 0.40 * weather_factor)))

        @lru_cache(maxsize=None)
        def node_line_offset(ix: int, iy: int) -> float:
            return self._point_to_segment_distance(
                point=(x_values[ix], y_values[iy]),
                start=start_xy,
                end=end_xy,
            )

        @lru_cache(maxsize=None)
        def node_building_clearance(ix: int, iy: int) -> float:
            if not consider_buildings:
                return max(request.cell_m * 2.4, 120.0)
            point = (x_values[ix], y_values[iy])
            radius = max(request.cell_m * 2.4, 120.0)
            nearby = building_index.query_bbox(point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius)
            if not nearby:
                return radius
            best = radius
            for building in nearby:
                if point_in_poly(point, building.points_xy):
                    return 0.0
                best = min(best, self._point_to_poly_distance(point=point, poly=building.points_xy))
            return best

        @lru_cache(maxsize=None)
        def edge_footprint_hits(ix1: int, iy1: int, ix2: int, iy2: int) -> tuple[Building, ...]:
            if not consider_buildings:
                return ()
            if (ix2, iy2) < (ix1, iy1):
                ix1, iy1, ix2, iy2 = ix2, iy2, ix1, iy1
            x1 = x_values[ix1]
            y1 = y_values[iy1]
            x2 = x_values[ix2]
            y2 = y_values[iy2]
            if ix1 == ix2 and iy1 == iy2:
                point = (x1, y1)
                return tuple(
                    building
                    for building in building_index.query_bbox(point[0], point[1], point[0], point[1])
                    if point_in_poly(point, building.points_xy)
                )
            left = min(x1, x2)
            right = max(x1, x2)
            bottom = min(y1, y2)
            top = max(y1, y2)
            return tuple(
                building
                for building in building_index.query_bbox(left, bottom, right, top)
                if segment_hits_poly((x1, y1), (x2, y2), building.points_xy)
            )

        @lru_cache(maxsize=None)
        def edge_overflight(ix1: int, iy1: int, iz1: int, ix2: int, iy2: int, iz2: int) -> tuple[int, float]:
            if not consider_buildings or not self._building_overflight_allowed(request.planning_mode):
                return 0, 0.0
            min_altitude = min(altitude_layers_m[iz1], altitude_layers_m[iz2])
            building_count = 0
            exposure = 0.0
            for building in edge_footprint_hits(ix1, iy1, ix2, iy2):
                required_altitude = building.height_m + request.safety_clearance_m
                if min_altitude <= required_altitude + 1e-6:
                    continue
                building_count += 1
                clearance_m = min_altitude - required_altitude
                exposure += (1.0 + min(building.height_m, 240.0) / 120.0) / (1.0 + clearance_m / 35.0)
            return building_count, exposure

        @lru_cache(maxsize=None)
        def edge_is_clear(ix1: int, iy1: int, iz1: int, ix2: int, iy2: int, iz2: int) -> bool:
            if not consider_buildings:
                return True
            min_altitude = min(altitude_layers_m[iz1], altitude_layers_m[iz2])
            if ix1 == ix2 and iy1 == iy2:
                if self._strict_building_avoidance(request.planning_mode) and edge_footprint_hits(ix1, iy1, ix2, iy2):
                    return False
                return min_altitude > blocked_height(ix1, iy1) + 1e-6
            allow_overflight = self._segment_allows_overflight(min_altitude_m=min_altitude, request=request)
            for building in edge_footprint_hits(ix1, iy1, ix2, iy2):
                if self._strict_building_avoidance(request.planning_mode):
                    return False
                required_altitude = building.height_m + request.safety_clearance_m
                if min_altitude <= required_altitude + 1e-6:
                    return False
                if not allow_overflight:
                    return False
            return True

        @lru_cache(maxsize=None)
        def edge_weather(ix1: int, iy1: int, iz1: int, ix2: int, iy2: int, iz2: int) -> tuple[bool, float]:
            return self._edge_weather_stats(
                current=(ix1, iy1, iz1),
                nxt=(ix2, iy2, iz2),
                x_values=x_values,
                y_values=y_values,
                altitude_layers_m=altitude_layers_m,
                node_weather=node_weather,
                request=request,
                consider_weather=consider_weather,
            )

        @lru_cache(maxsize=None)
        def xy_segment_clear(
            start_xy: tuple[float, float],
            end_xy: tuple[float, float],
            altitude_m: float,
        ) -> bool:
            return self._xy_segment_clear_at_altitude(
                start_xy=start_xy,
                end_xy=end_xy,
                altitude_m=altitude_m,
                building_index=building_index,
                request=request,
                consider_buildings=consider_buildings,
            )

        routes: list[RouteCandidate] = []
        used_corridors: list[set[tuple[int, int]]] = []
        accepted_paths: list[list[tuple[int, int, int]] | None] = []
        accepted_signatures: list[set[tuple[int, int]]] = []
        duplicate_candidates: list[tuple[RouteCandidate, list[tuple[int, int, int]], set[tuple[int, int]]]] = []
        internal_candidate_target = request.candidate_count
        profiles = self.DEFAULT_PROFILES[: max(1, min(request.candidate_count, len(self.DEFAULT_PROFILES)))]
        skip_air_grid_profiles = (
            request.planning_mode == self.PLANNING_MODE_BUILDING_ONLY
            and self.road_graph is not None
            and request.max_altitude_m <= max(60.0, request.min_altitude_m + 60.0)
        )
        for profile in profiles:
            if skip_air_grid_profiles:
                continue
            if self.road_graph is not None and self._prefer_road_fallback_for_profile(request.planning_mode, profile.strategy):
                continue
            altitude_attempts = self._route_altitude_attempts(
                request,
                max(request.start_altitude_m, request.end_altitude_m, min(profile.preferred_altitude_m, request.max_altitude_m)),
                profile.strategy,
            )
            raw_path = None
            selected_raw_path = None
            selected_path = None
            for attempt_start_altitude_m, attempt_end_altitude_m in altitude_attempts:
                start = self._nearest_free_node(
                    point_xy=start_xy,
                    preferred_altitude_m=attempt_start_altitude_m,
                    x_values=x_values,
                    y_values=y_values,
                    altitude_layers_m=altitude_layers_m,
                    node_is_blocked=node_is_blocked,
                )
                end = self._nearest_free_node(
                    point_xy=end_xy,
                    preferred_altitude_m=attempt_end_altitude_m,
                    x_values=x_values,
                    y_values=y_values,
                    altitude_layers_m=altitude_layers_m,
                    node_is_blocked=node_is_blocked,
                )
                direct_weather_blocked, direct_weather_pressure = edge_weather(*start, *end)
                if edge_is_clear(*start, *end) and not direct_weather_blocked and self._direct_edge_weather_allowed(
                    profile=profile,
                    weather_pressure=direct_weather_pressure,
                    consider_weather=consider_weather,
                ):
                    raw_path = [start, end]
                else:
                    try:
                        raw_path = self._astar(
                            start=start,
                            goal=end,
                            x_values=x_values,
                            y_values=y_values,
                            altitude_layers_m=altitude_layers_m,
                            node_is_blocked=node_is_blocked,
                            blocked_height=blocked_height,
                            node_weather=node_weather,
                            xy_urban_density=xy_urban_density,
                            node_connectivity=node_connectivity,
                            node_reachability=node_reachability,
                            node_line_offset=node_line_offset,
                            node_building_clearance=node_building_clearance,
                            edge_overflight=edge_overflight,
                            edge_weather=edge_weather,
                            edge_is_clear=edge_is_clear,
                            corridor_unit=corridor_unit,
                            building_index=building_index,
                            request=request,
                            consider_buildings=consider_buildings,
                            profile=profile,
                            used_corridors=used_corridors,
                            allow_vertical_moves=True,
                        )
                    except RuntimeError:
                        raw_path = None
                if raw_path is not None:
                    raw_path = self._with_endpoint_altitude_transitions(
                        path=raw_path,
                        requested_start_altitude_m=request.start_altitude_m,
                        requested_end_altitude_m=request.end_altitude_m,
                        altitude_layers_m=altitude_layers_m,
                        x_values=x_values,
                        y_values=y_values,
                        blocked_height=blocked_height,
                        building_index=building_index,
                        edge_weather=edge_weather,
                        edge_is_clear=edge_is_clear,
                        request=request,
                        consider_buildings=consider_buildings,
                        node_is_blocked=node_is_blocked,
                    )
                    path = self._simplify_path(
                        path=raw_path,
                        x_values=x_values,
                        y_values=y_values,
                        altitude_layers_m=altitude_layers_m,
                        blocked_height=blocked_height,
                        building_index=building_index,
                        edge_weather=edge_weather,
                        edge_is_clear=edge_is_clear,
                        request=request,
                        consider_buildings=consider_buildings,
                        weather_pressure_limit=self._direct_edge_weather_limit(profile=profile, consider_weather=consider_weather),
                    )
                    selected_raw_path = raw_path
                    selected_path = path
                    break
            if raw_path is None and request.planning_mode == self.PLANNING_MODE_BUILDING_ONLY:
                for attempt_start_altitude_m, attempt_end_altitude_m in altitude_attempts:
                    start = self._nearest_free_node(
                        point_xy=start_xy,
                        preferred_altitude_m=attempt_start_altitude_m,
                        x_values=x_values,
                        y_values=y_values,
                        altitude_layers_m=altitude_layers_m,
                        node_is_blocked=node_is_blocked,
                    )
                    end = self._nearest_free_node(
                        point_xy=end_xy,
                        preferred_altitude_m=attempt_end_altitude_m,
                        x_values=x_values,
                        y_values=y_values,
                        altitude_layers_m=altitude_layers_m,
                        node_is_blocked=node_is_blocked,
                    )
                    try:
                        raw_path = self._astar(
                            start=start,
                            goal=end,
                            x_values=x_values,
                            y_values=y_values,
                            altitude_layers_m=altitude_layers_m,
                            node_is_blocked=node_is_blocked,
                            blocked_height=blocked_height,
                            node_weather=node_weather,
                            xy_urban_density=xy_urban_density,
                            node_connectivity=node_connectivity,
                            node_reachability=node_reachability,
                            node_line_offset=node_line_offset,
                            node_building_clearance=node_building_clearance,
                            edge_overflight=edge_overflight,
                            edge_weather=edge_weather,
                            edge_is_clear=edge_is_clear,
                            corridor_unit=corridor_unit,
                            building_index=building_index,
                            request=request,
                            consider_buildings=consider_buildings,
                            profile=profile,
                            used_corridors=used_corridors,
                            allow_vertical_moves=True,
                        )
                    except RuntimeError:
                        raw_path = None
                    if raw_path is not None:
                        raw_path = self._with_endpoint_altitude_transitions(
                            path=raw_path,
                            requested_start_altitude_m=request.start_altitude_m,
                            requested_end_altitude_m=request.end_altitude_m,
                            altitude_layers_m=altitude_layers_m,
                            x_values=x_values,
                            y_values=y_values,
                            blocked_height=blocked_height,
                            building_index=building_index,
                            edge_weather=edge_weather,
                            edge_is_clear=edge_is_clear,
                            request=request,
                            consider_buildings=consider_buildings,
                            node_is_blocked=node_is_blocked,
                        )
                        path = self._simplify_path(
                            path=raw_path,
                            x_values=x_values,
                            y_values=y_values,
                            altitude_layers_m=altitude_layers_m,
                            blocked_height=blocked_height,
                            building_index=building_index,
                            edge_weather=edge_weather,
                            edge_is_clear=edge_is_clear,
                            request=request,
                            consider_buildings=consider_buildings,
                            weather_pressure_limit=self._direct_edge_weather_limit(profile=profile, consider_weather=consider_weather),
                        )
                        selected_raw_path = raw_path
                        selected_path = path
                        break
            if selected_raw_path is None or selected_path is None:
                continue
            raw_path = selected_raw_path
            path = selected_path
            xy_signature = {(ix, iy) for ix, iy, _iz in raw_path}
            candidate = self._build_candidate(
                route_id=f"route_{len(routes) + 1}",
                profile=profile,
                path=path,
                x_values=x_values,
                y_values=y_values,
                altitude_layers_m=altitude_layers_m,
                node_weather=node_weather,
                xy_urban_density=xy_urban_density,
                node_connectivity=node_connectivity,
                node_reachability=node_reachability,
                edge_overflight=edge_overflight,
                request=request,
                consider_weather=consider_weather,
            )
            if consider_buildings and not self._route_segments_clear_buildings(
                route=candidate,
                request=request,
                building_index=building_index,
            ):
                continue
            signature = {(ix, iy) for ix, iy, _iz in path}
            if any(path == accepted_path for accepted_path in accepted_paths):
                duplicate_candidates.append((candidate, path, signature))
                continue
            routes.append(candidate)
            used_corridors.append(xy_signature)
            accepted_paths.append(path)
            accepted_signatures.append(signature)

        if len(routes) < internal_candidate_target and self.road_graph is not None:
            fallback_paths, fallback_signatures = self._append_road_fallback_routes(
                routes=routes,
                profiles=profiles,
                accepted_signatures=accepted_signatures,
                x_values=x_values,
                y_values=y_values,
                altitude_layers_m=altitude_layers_m,
                node_weather=node_weather,
                xy_urban_density=xy_urban_density,
                node_connectivity=node_connectivity,
                node_reachability=node_reachability,
                start_xy=start_xy,
                end_xy=end_xy,
                building_index=building_index,
                target_count=internal_candidate_target,
                blocked_height=blocked_height,
                edge_weather=edge_weather,
                xy_segment_clear=xy_segment_clear,
                request=request,
                consider_buildings=consider_buildings,
                consider_weather=consider_weather,
            )
            accepted_paths.extend(fallback_paths)
            accepted_signatures.extend(fallback_signatures)

        if request.planning_mode == self.PLANNING_MODE_COMBINED and consider_weather and consider_buildings:
            safest_profile = next((profile for profile in profiles if profile.strategy == "safest"), None)
            if safest_profile is not None:
                weather_safe_path_xy = self._combined_weather_safe_detour_path(
                    start_xy=start_xy,
                    end_xy=end_xy,
                    profile=safest_profile,
                    building_index=building_index,
                    request=request,
                    used_signatures=accepted_signatures,
                )
                if weather_safe_path_xy is not None and len(weather_safe_path_xy) >= 2:
                    fallback_altitude_m = self._fallback_profile_altitude_m(profile=safest_profile, request=request)
                    weather_safe_candidate = self._build_candidate_from_xy_path(
                        route_id=f"route_{len(routes) + 1}",
                        profile=safest_profile,
                        path_xy=weather_safe_path_xy,
                        altitude_m=fallback_altitude_m,
                        x_values=x_values,
                        y_values=y_values,
                        altitude_layers_m=altitude_layers_m,
                        node_weather=node_weather,
                        xy_urban_density=xy_urban_density,
                        node_connectivity=node_connectivity,
                        node_reachability=node_reachability,
                        building_index=building_index,
                        request=request,
                        consider_weather=consider_weather,
                    )
                    weather_safe_signature = {
                        (
                            int(round(point_xy[0] / max(request.cell_m, 1.0))),
                            int(round(point_xy[1] / max(request.cell_m, 1.0))),
                        )
                        for point_xy in weather_safe_path_xy
                    }
                    weather_safe_duplicate = any(
                        self._corridor_overlap_ratio(weather_safe_signature, signature) > 0.985
                        for signature in accepted_signatures
                    )
                    if (
                        not weather_safe_duplicate
                        and self._route_segments_clear_buildings(
                            route=weather_safe_candidate,
                            request=request,
                            building_index=building_index,
                        )
                    ):
                        current_safest_risk = min(
                            (
                                (
                                    route.high_risk_exposure_ratio,
                                    route.max_weather_risk_score,
                                    route.max_precipitation_mm,
                                    route.overflight_exposure_index,
                                )
                                for route in routes
                            ),
                            default=(float("inf"), float("inf"), float("inf"), float("inf")),
                        )
                        candidate_risk = (
                            weather_safe_candidate.high_risk_exposure_ratio,
                            weather_safe_candidate.max_weather_risk_score,
                            weather_safe_candidate.max_precipitation_mm,
                            weather_safe_candidate.overflight_exposure_index,
                        )
                        if len(routes) < internal_candidate_target:
                            routes.append(weather_safe_candidate)
                            accepted_paths.append(None)
                            accepted_signatures.append(weather_safe_signature)
                        elif candidate_risk < current_safest_risk:
                            replace_idx = max(
                                range(len(routes)),
                                key=lambda idx: (
                                    routes[idx].high_risk_exposure_ratio,
                                    routes[idx].max_weather_risk_score,
                                    routes[idx].max_precipitation_mm,
                                    -routes[idx].corridor_diversity_index,
                                ),
                            )
                            weather_safe_candidate.route_id = routes[replace_idx].route_id
                            routes[replace_idx] = weather_safe_candidate
                            if replace_idx < len(accepted_paths):
                                accepted_paths[replace_idx] = None
                            if replace_idx < len(accepted_signatures):
                                accepted_signatures[replace_idx] = weather_safe_signature

        while len(routes) < request.candidate_count and duplicate_candidates:
            candidate, path, signature = duplicate_candidates.pop(0)
            candidate.route_id = f"route_{len(routes) + 1}"
            routes.append(candidate)
            accepted_paths.append(path)
            accepted_signatures.append(signature)

        ranking_weights = self._finalize_routes(
            routes=routes,
            paths=accepted_paths,
            signatures=accepted_signatures,
            x_values=x_values,
            y_values=y_values,
            altitude_layers_m=altitude_layers_m,
            node_weather=node_weather,
            xy_urban_density=xy_urban_density,
            node_connectivity=node_connectivity,
            node_reachability=node_reachability,
            request=request,
        )

        return PlanningResult(
            city={
                "name": self.city_config["name"],
                "display_name": self.city_config.get("display_name", self.city_config["name"]),
                "center": self.city_summary.get("center", self.city_config.get("center")),
                "bbox": self.bbox,
            },
            request={
                "start": {"lat": request.start_lat, "lon": request.start_lon, "altitude_m": request.start_altitude_m},
                "end": {"lat": request.end_lat, "lon": request.end_lon, "altitude_m": request.end_altitude_m},
                "planning_mode": request.planning_mode,
            },
            planner={
                "planning_mode": request.planning_mode,
                "min_altitude_m": request.min_altitude_m,
                "max_altitude_m": request.max_altitude_m,
                "cell_m": request.cell_m,
                "safety_clearance_m": request.safety_clearance_m,
                "cruise_speed_mps": request.cruise_speed_mps,
                "altitude_layers_m": altitude_layers_m,
                "candidate_count": len(routes),
                "ranking_method": "entropy_weight_topsis",
                "monte_carlo_runs": self.MONTE_CARLO_RUNS,
                "ranking_weights": ranking_weights,
            },
            routes=routes,
        )

    def _normalize_request(self, request: PlannerRequest) -> PlannerRequest:
        south = float(self.bbox["south"])
        north = float(self.bbox["north"])
        west = float(self.bbox["west"])
        east = float(self.bbox["east"])
        start_lat = min(max(request.start_lat, south), north)
        start_lon = min(max(request.start_lon, west), east)
        end_lat = min(max(request.end_lat, south), north)
        end_lon = min(max(request.end_lon, west), east)
        explicit_max = request.max_altitude_m
        normalized_max = explicit_max if explicit_max is not None and explicit_max > 0.0 else self._adaptive_max_altitude_m(request)
        return PlannerRequest(
            start_lat=start_lat,
            start_lon=start_lon,
            end_lat=end_lat,
            end_lon=end_lon,
            planning_mode=request.planning_mode,
            start_altitude_m=request.start_altitude_m,
            end_altitude_m=request.end_altitude_m,
            min_altitude_m=request.min_altitude_m,
            candidate_count=request.candidate_count,
            cell_m=request.cell_m,
            safety_clearance_m=request.safety_clearance_m,
            cruise_speed_mps=request.cruise_speed_mps,
            climb_speed_mps=request.climb_speed_mps,
            descend_speed_mps=request.descend_speed_mps,
            max_altitude_m=normalized_max,
        )

    def _adaptive_max_altitude_m(self, request: PlannerRequest) -> float:
        highest_weather = max(self.weather_field.altitude_levels_m)
        tallest_building = max((building.height_m for building in self.buildings), default=0.0) if self._consider_buildings(request.planning_mode) else 0.0
        preferred_peak = max(profile.preferred_altitude_m for profile in self.DEFAULT_PROFILES[: max(1, request.candidate_count)])
        inferred_max = max(
            highest_weather + 80.0,
            tallest_building + request.safety_clearance_m + 80.0,
            max(request.start_altitude_m, request.end_altitude_m) + 60.0,
            preferred_peak + 60.0,
            request.min_altitude_m + 120.0,
        )
        return max(request.min_altitude_m + 20.0, round(inferred_max / 10.0) * 10.0)

    def _majority_overflight_altitude_m(self, request: PlannerRequest) -> float:
        if not self.building_heights_m:
            return request.min_altitude_m
        majority_height_m = self._percentile(self.building_heights_m, 0.65)
        return majority_height_m + request.safety_clearance_m

    @staticmethod
    def _building_low_cruise_altitude_m(request: PlannerRequest) -> float:
        return max(request.min_altitude_m, request.start_altitude_m, request.end_altitude_m)

    def _building_altitude_attempts(self, request: PlannerRequest, preferred_altitude_m: float) -> list[float]:
        if request.planning_mode != self.PLANNING_MODE_BUILDING_ONLY:
            return [preferred_altitude_m]
        low_cruise_altitude_m = self._building_low_cruise_altitude_m(request)
        majority_altitude_m = max(
            low_cruise_altitude_m,
            self._majority_overflight_altitude_m(request),
        )
        attempts = [
            low_cruise_altitude_m,
            low_cruise_altitude_m + 20.0,
            low_cruise_altitude_m + 40.0,
            majority_altitude_m,
            preferred_altitude_m,
            min(request.max_altitude_m, majority_altitude_m + 80.0),
            request.max_altitude_m,
        ]
        deduped: list[float] = []
        seen: set[float] = set()
        for altitude_m in attempts:
            altitude_m = max(request.min_altitude_m, min(request.max_altitude_m, altitude_m))
            key = round(altitude_m, 2)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(key)
        return deduped

    def _route_altitude_attempts(self, request: PlannerRequest, preferred_altitude_m: float, strategy: str) -> list[tuple[float, float]]:
        """Try actual endpoint heights first, then strategy cruise heights for climb/descent profiles."""
        actual_endpoint_attempt = (request.start_altitude_m, request.end_altitude_m)
        if request.planning_mode == self.PLANNING_MODE_BUILDING_ONLY:
            cruise_attempts = [
                (cruise_altitude_m, cruise_altitude_m)
                for cruise_altitude_m in self._building_altitude_attempts(request, preferred_altitude_m)
            ]
            attempts = [actual_endpoint_attempt] + cruise_attempts
        elif request.planning_mode == self.PLANNING_MODE_WEATHER_ONLY:
            # Weather-only routing ignores buildings, so avoid trying every weather altitude level for
            # every profile. Keep enough representative heights for climb/descent weather avoidance.
            midpoint_altitude_m = (request.start_altitude_m + request.end_altitude_m) / 2.0
            altitude_span_m = max(0.0, request.max_altitude_m - request.min_altitude_m)
            cruise_candidates = [
                preferred_altitude_m,
                midpoint_altitude_m,
                max(request.start_altitude_m, request.end_altitude_m),
                request.min_altitude_m + altitude_span_m * 0.50,
                request.min_altitude_m + altitude_span_m * 0.75,
                request.max_altitude_m,
            ]
            in_range_weather_levels = [
                level
                for level in self.weather_field.altitude_levels_m
                if request.min_altitude_m <= level <= request.max_altitude_m
            ]
            if in_range_weather_levels:
                cruise_candidates.extend(
                    [
                        min(in_range_weather_levels, key=lambda level: abs(level - preferred_altitude_m)),
                        min(in_range_weather_levels, key=lambda level: abs(level - midpoint_altitude_m)),
                    ]
                )
            cruise_attempts = [(cruise_altitude_m, cruise_altitude_m) for cruise_altitude_m in cruise_candidates]
            if strategy in {"safest", "balanced_stable", "most_accessible"}:
                attempts = cruise_attempts + [actual_endpoint_attempt]
            else:
                attempts = [actual_endpoint_attempt] + cruise_attempts
        else:
            cruise_candidates = [
                preferred_altitude_m,
                (request.start_altitude_m + request.end_altitude_m) / 2.0,
                max(request.start_altitude_m, request.end_altitude_m),
            ]
            if self._consider_weather(request.planning_mode):
                cruise_candidates.extend(self.weather_field.altitude_levels_m)
                cruise_candidates.extend(
                    [
                        request.min_altitude_m,
                        request.min_altitude_m + (request.max_altitude_m - request.min_altitude_m) * 0.50,
                        request.min_altitude_m + (request.max_altitude_m - request.min_altitude_m) * 0.75,
                        request.max_altitude_m,
                    ]
                )
            if self._consider_buildings(request.planning_mode):
                cruise_candidates.extend(self._building_altitude_attempts(request, preferred_altitude_m))

            cruise_attempts = [(cruise_altitude_m, cruise_altitude_m) for cruise_altitude_m in cruise_candidates]
            if strategy in {"safest", "balanced_stable", "most_accessible"}:
                attempts = cruise_attempts + [actual_endpoint_attempt]
            elif strategy == "energy_saving":
                attempts = [actual_endpoint_attempt] + cruise_attempts
            else:
                attempts = [actual_endpoint_attempt] + cruise_attempts

        deduped: list[tuple[float, float]] = []
        seen: set[tuple[float, float]] = set()
        for start_altitude_m, end_altitude_m in attempts:
            start_altitude_m = max(request.min_altitude_m, min(request.max_altitude_m, start_altitude_m))
            end_altitude_m = max(request.min_altitude_m, min(request.max_altitude_m, end_altitude_m))
            key = (round(start_altitude_m, 2), round(end_altitude_m, 2))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(key)
        return deduped

    def _segment_allows_overflight(self, *, min_altitude_m: float, request: PlannerRequest) -> bool:
        return self._building_overflight_allowed(request.planning_mode)

    def explain_empty_result(self, request: PlannerRequest) -> str | None:
        if request.planning_mode != self.PLANNING_MODE_BUILDING_ONLY or request.max_altitude_m is None:
            return None
        normalized_request = self._normalize_request(request)
        suggested_altitude_m = None
        default_route = self.city_config.get("default_route") or []
        if default_route:
            suggested_altitude_m = round(
                max(float(point.get("altitude_m") or 0.0) for point in default_route) / 10.0
            ) * 10.0
        if suggested_altitude_m is None:
            diagnostic_request = PlannerRequest(
                start_lat=normalized_request.start_lat,
                start_lon=normalized_request.start_lon,
                end_lat=normalized_request.end_lat,
                end_lon=normalized_request.end_lon,
                planning_mode=normalized_request.planning_mode,
                start_altitude_m=normalized_request.start_altitude_m,
                end_altitude_m=normalized_request.end_altitude_m,
                min_altitude_m=normalized_request.min_altitude_m,
                candidate_count=1,
                cell_m=normalized_request.cell_m,
                safety_clearance_m=normalized_request.safety_clearance_m,
                cruise_speed_mps=normalized_request.cruise_speed_mps,
                climb_speed_mps=normalized_request.climb_speed_mps,
                descend_speed_mps=normalized_request.descend_speed_mps,
                max_altitude_m=None,
            )
            try:
                diagnostic_result = self.plan(diagnostic_request)
                if diagnostic_result.routes:
                    suggested_altitude_m = round(
                        max(
                            float(point["altitude_m"])
                            for route in diagnostic_result.routes
                            for point in route.waypoints
                        )
                        / 10.0
                    ) * 10.0
            except Exception:
                suggested_altitude_m = None
        if suggested_altitude_m is None:
            suggested_altitude_m = round(
                max(
                    self._majority_overflight_altitude_m(normalized_request),
                    normalized_request.start_altitude_m,
                    normalized_request.end_altitude_m,
                )
                / 10.0
            ) * 10.0
        if suggested_altitude_m <= normalized_request.max_altitude_m + 1e-6:
            return (
                f"当前最大高度 {normalized_request.max_altitude_m:.0f}m 是硬约束，"
                "在该高度范围内未找到满足建筑避障和安全净空的候选航线。"
                "可提高最大高度，或清空“最大高度”字段使用自动高度。"
            )
        return (
            f"当前最大高度 {normalized_request.max_altitude_m:.0f}m 是硬约束，"
            "系统不会生成超过该高度的航线。"
            f"该区域按当前起终点和建筑净空估算，建议至少允许升到 {suggested_altitude_m:.0f}m，"
            "或清空“最大高度”字段使用自动高度。"
        )

    def _validate_request(self, request: PlannerRequest) -> None:
        if request.planning_mode not in self.PLANNING_MODES:
            raise ValueError(f"planning_mode 不支持：{request.planning_mode}")
        if request.candidate_count < 1:
            raise ValueError("candidate_count 必须大于 0。")
        if request.cell_m <= 0.0:
            raise ValueError("cell_m 必须大于 0。")
        if request.cruise_speed_mps <= 0.0:
            raise ValueError("cruise_speed_mps 必须大于 0。")
        if request.min_altitude_m < 0.0:
            raise ValueError("min_altitude_m 不能小于 0。")
        for altitude_m, label in (
            (request.start_altitude_m, "起点高度"),
            (request.end_altitude_m, "终点高度"),
        ):
            if altitude_m < request.min_altitude_m:
                raise ValueError(f"{label}低于最低规划高度。")
            if request.max_altitude_m is not None and altitude_m > request.max_altitude_m:
                raise ValueError(f"{label}高于最大规划高度。")
        west = float(self.bbox["west"])
        east = float(self.bbox["east"])
        south = float(self.bbox["south"])
        north = float(self.bbox["north"])
        for lat, lon, label in (
            (request.start_lat, request.start_lon, "起点"),
            (request.end_lat, request.end_lon, "终点"),
        ):
            if not (south <= lat <= north and west <= lon <= east):
                raise ValueError(f"{label}不在当前城市范围内。")

    def _grid_axes(self, cell_m: float) -> tuple[list[float], list[float]]:
        west_south = latlon_to_meters(self.origin, float(self.bbox["south"]), float(self.bbox["west"]))
        east_north = latlon_to_meters(self.origin, float(self.bbox["north"]), float(self.bbox["east"]))
        margin = cell_m * 1.5
        x_min = west_south[0] - margin
        x_max = east_north[0] + margin
        y_min = west_south[1] - margin
        y_max = east_north[1] + margin
        x_values = [x_min + idx * cell_m for idx in range(int((x_max - x_min) / cell_m) + 1)]
        y_values = [y_min + idx * cell_m for idx in range(int((y_max - y_min) / cell_m) + 1)]
        return x_values, y_values

    def _altitude_layers(self, request: PlannerRequest) -> list[float]:
        if request.planning_mode == self.PLANNING_MODE_BUILDING_ONLY:
            raw_levels = [
                round(request.min_altitude_m, 2),
                round(request.start_altitude_m, 2),
                round(request.end_altitude_m, 2),
                round(request.max_altitude_m, 2),
            ]
            current = request.min_altitude_m
            while current <= min(request.max_altitude_m, 120.0) + 1e-6:
                raw_levels.append(round(current, 2))
                current += 20.0
            for anchor in (request.start_altitude_m, request.end_altitude_m):
                for delta in (-40.0, -20.0, 0.0, 20.0, 40.0):
                    raw_levels.append(round(anchor + delta, 2))
            for profile in self.DEFAULT_PROFILES:
                if request.min_altitude_m <= profile.preferred_altitude_m <= request.max_altitude_m:
                    raw_levels.append(round(profile.preferred_altitude_m, 2))
            if self.building_heights_m:
                for quantile in (0.50, 0.65, 0.80, 0.90, 1.0):
                    clearance_level = self._percentile(self.building_heights_m, quantile) + request.safety_clearance_m
                    raw_levels.append(round(clearance_level / 10.0) * 10.0)
                tallest_clearance = max(self.building_heights_m) + request.safety_clearance_m
                ladder_start = max(request.min_altitude_m, round(self._majority_overflight_altitude_m(request) / 10.0) * 10.0)
                ladder_top = min(request.max_altitude_m, round((tallest_clearance + 80.0) / 10.0) * 10.0)
                current = ladder_start
                while current <= ladder_top + 1e-6:
                    raw_levels.append(round(current, 2))
                    current += 40.0
            levels = sorted({level for level in raw_levels if request.min_altitude_m <= level <= request.max_altitude_m})
            if not levels:
                levels = [min(request.max_altitude_m, max(request.min_altitude_m, 0.0))]
            return levels
        raw_levels = [
            round(level, 2)
            for level in self.weather_field.altitude_levels_m
            if request.min_altitude_m <= level <= request.max_altitude_m
        ]
        current = request.min_altitude_m
        while current <= min(request.max_altitude_m, 120.0) + 1e-6:
            raw_levels.append(round(current, 2))
            current += 20.0
        for level in (150.0, 180.0, 220.0, 260.0, 300.0):
            if request.min_altitude_m <= level <= request.max_altitude_m:
                raw_levels.append(level)
        raw_levels.extend(
            [
                round(request.start_altitude_m, 2),
                round(request.end_altitude_m, 2),
            ]
        )
        for profile in self.DEFAULT_PROFILES:
            if request.min_altitude_m <= profile.preferred_altitude_m <= request.max_altitude_m:
                raw_levels.append(round(profile.preferred_altitude_m, 2))
        if self._consider_buildings(request.planning_mode):
            max_building = max((building.height_m for building in self.buildings), default=0.0)
            safe_top = min(request.max_altitude_m, max_building + request.safety_clearance_m + 40.0)
            if safe_top >= request.min_altitude_m:
                raw_levels.append(round(safe_top / 10.0) * 10.0)
        levels = sorted({level for level in raw_levels if request.min_altitude_m <= level <= request.max_altitude_m})
        if not levels:
            levels = [min(request.max_altitude_m, max(request.min_altitude_m, 0.0))]
        return levels

    @classmethod
    def _consider_buildings(cls, planning_mode: str) -> bool:
        return planning_mode in {cls.PLANNING_MODE_COMBINED, cls.PLANNING_MODE_BUILDING_ONLY}

    @classmethod
    def _consider_weather(cls, planning_mode: str) -> bool:
        return planning_mode in {cls.PLANNING_MODE_COMBINED, cls.PLANNING_MODE_WEATHER_ONLY}

    @classmethod
    def _building_overflight_allowed(cls, planning_mode: str) -> bool:
        return False

    @classmethod
    def _strict_building_avoidance(cls, planning_mode: str) -> bool:
        return planning_mode in {cls.PLANNING_MODE_COMBINED, cls.PLANNING_MODE_BUILDING_ONLY}

    @classmethod
    def _prefer_road_fallback_for_profile(cls, planning_mode: str, strategy: str) -> bool:
        return False

    def _load_buildings(self, geojson: dict[str, Any]) -> list[Building]:
        buildings: list[Building] = []
        for feature in geojson.get("features", []):
            geom = feature.get("geometry", {})
            if geom.get("type") != "Polygon":
                continue
            ring = geom.get("coordinates", [[]])[0]
            if len(ring) < 4:
                continue
            points_xy = [latlon_to_meters(self.origin, float(lat), float(lon)) for lon, lat in ring]
            if points_xy and points_xy[0] != points_xy[-1]:
                points_xy.append(points_xy[0])
            height_m = float(feature.get("properties", {}).get("height_m") or 0.0)
            xs = [point[0] for point in points_xy]
            ys = [point[1] for point in points_xy]
            buildings.append(
                Building(
                    points_xy=points_xy,
                    height_m=height_m,
                    bbox=(min(xs), min(ys), max(xs), max(ys)),
                )
            )
        return buildings

    def _load_weather_field(self, geojson: dict[str, Any]) -> WeatherField:
        samples: list[WeatherSample] = []
        for feature in geojson.get("features", []):
            geom = feature.get("geometry", {})
            if geom.get("type") != "Point":
                continue
            coords = geom.get("coordinates", [])
            if len(coords) < 3:
                continue
            lon, lat, altitude_m = coords[:3]
            props = feature.get("properties", {})
            x_m, y_m = latlon_to_meters(self.origin, float(lat), float(lon))
            samples.append(
                WeatherSample(
                    x_m=x_m,
                    y_m=y_m,
                    altitude_m=float(props.get("altitude_m", altitude_m)),
                    wind_speed_mps=float(props.get("wind_speed_mps") or 0.0),
                    wind_dir_deg=float(props.get("wind_dir_deg") or 0.0),
                    turbulence_index=float(props.get("turbulence_index") or 0.0),
                    precipitation_mm=float(props.get("precipitation_mm") or 0.0),
                    pressure_hpa=float(props.get("pressure_hpa") or 1013.25),
                    temperature_c=float(props.get("temperature_c") or 0.0),
                    cloud_cover_pct=float(props.get("cloud_cover_pct") or props.get("cloud_cover") or props.get("cloud_cover_percent") or 0.0),
                )
            )
        return WeatherField(samples)

    def _load_road_graph(self, geojson: dict[str, Any] | None) -> RoadGraph | None:
        if not geojson:
            return None
        node_index: dict[tuple[float, float], int] = {}
        nodes_xy: list[tuple[float, float]] = []
        edges: dict[int, list[tuple[int, float]]] = {}

        def add_node(point_xy: tuple[float, float]) -> int:
            key = (round(point_xy[0], 3), round(point_xy[1], 3))
            idx = node_index.get(key)
            if idx is None:
                idx = len(nodes_xy)
                node_index[key] = idx
                nodes_xy.append(point_xy)
                edges[idx] = []
            return idx

        for feature in geojson.get("features", []):
            props = feature.get("properties", {})
            if props.get("layer") != "road":
                continue
            geom = feature.get("geometry", {})
            if geom.get("type") != "LineString":
                continue
            prev_idx = None
            for lon, lat, *_rest in geom.get("coordinates", []):
                current_idx = add_node(latlon_to_meters(self.origin, float(lat), float(lon)))
                if prev_idx is not None and prev_idx != current_idx:
                    weight = math.hypot(
                        nodes_xy[current_idx][0] - nodes_xy[prev_idx][0],
                        nodes_xy[current_idx][1] - nodes_xy[prev_idx][1],
                    )
                    edges[prev_idx].append((current_idx, weight))
                    edges[current_idx].append((prev_idx, weight))
                prev_idx = current_idx
        if not nodes_xy:
            return None
        return RoadGraph(nodes_xy=nodes_xy, edges=edges)

    @staticmethod
    def _nearest_free_node(
        *,
        point_xy: tuple[float, float],
        preferred_altitude_m: float,
        x_values: list[float],
        y_values: list[float],
        altitude_layers_m: list[float],
        node_is_blocked: Any,
    ) -> tuple[int, int, int]:
        best_node = None
        best_cost = float("inf")
        for ix, x_m in enumerate(x_values):
            for iy, y_m in enumerate(y_values):
                horiz_sq = (x_m - point_xy[0]) ** 2 + (y_m - point_xy[1]) ** 2
                for iz, altitude_m in enumerate(altitude_layers_m):
                    if node_is_blocked(ix, iy, iz):
                        continue
                    altitude_cost = abs(altitude_m - preferred_altitude_m) * 12.0
                    score = horiz_sq + altitude_cost**2
                    if score < best_cost:
                        best_cost = score
                        best_node = (ix, iy, iz)
        if best_node is None:
            raise RuntimeError("当前城市栅格中找不到可用起终点。")
        return best_node

    def _astar(
        self,
        *,
        start: tuple[int, int, int],
        goal: tuple[int, int, int],
        x_values: list[float],
        y_values: list[float],
        altitude_layers_m: list[float],
        node_is_blocked: Any,
        blocked_height: Any,
        node_weather: Any,
        xy_urban_density: Any,
        node_connectivity: Any,
        node_reachability: Any,
        node_line_offset: Any,
        node_building_clearance: Any,
        edge_overflight: Any,
        edge_weather: Any,
        edge_is_clear: Any,
        corridor_unit: tuple[float, float],
        building_index: BuildingIndex,
        request: PlannerRequest,
        consider_buildings: bool,
        profile: CostProfile,
        used_corridors: list[set[tuple[int, int]]],
        allow_vertical_moves: bool,
    ) -> list[tuple[int, int, int]]:
        open_set: list[tuple[float, float, tuple[int, int, int]]] = [
            (self._heuristic(start, goal, x_values, y_values, altitude_layers_m, request), 0.0, start)
        ]
        came_from: dict[tuple[int, int, int], tuple[int, int, int]] = {}
        best_cost = {start: 0.0}
        visited: set[tuple[int, int, int]] = set()
        moves = self.ASTAR_MOVES if allow_vertical_moves else self.CONNECTIVITY_MOVES
        while open_set:
            _priority, current_cost, current = heapq.heappop(open_set)
            if current in visited:
                continue
            visited.add(current)
            if current == goal:
                path = [current]
                node = current
                while node in came_from:
                    node = came_from[node]
                    path.append(node)
                return list(reversed(path))
            for dx, dy, dz in moves:
                nxt = (current[0] + dx, current[1] + dy, current[2] + dz)
                if nxt[0] < 0 or nxt[0] >= len(x_values) or nxt[1] < 0 or nxt[1] >= len(y_values) or nxt[2] < 0 or nxt[2] >= len(altitude_layers_m):
                    continue
                if node_is_blocked(*nxt):
                    continue
                if not edge_is_clear(*current, *nxt):
                    continue
                weather_blocked, _weather_pressure = edge_weather(*current, *nxt)
                if weather_blocked and request.planning_mode != self.PLANNING_MODE_COMBINED:
                    continue
                step_cost = self._edge_cost(
                    prev=came_from.get(current),
                    current=current,
                    nxt=nxt,
                    x_values=x_values,
                    y_values=y_values,
                    altitude_layers_m=altitude_layers_m,
                    node_weather=node_weather,
                    xy_urban_density=xy_urban_density,
                    node_connectivity=node_connectivity,
                    node_reachability=node_reachability,
                    node_line_offset=node_line_offset,
                    node_building_clearance=node_building_clearance,
                    edge_overflight=edge_overflight,
                    edge_weather=edge_weather,
                    corridor_unit=corridor_unit,
                    request=request,
                    consider_weather=self._consider_weather(request.planning_mode),
                    profile=profile,
                    used_corridors=used_corridors,
                )
                new_cost = current_cost + step_cost
                if new_cost >= best_cost.get(nxt, float("inf")):
                    continue
                best_cost[nxt] = new_cost
                came_from[nxt] = current
                heapq.heappush(
                    open_set,
                    (
                        new_cost + self._heuristic(nxt, goal, x_values, y_values, altitude_layers_m, request),
                        new_cost,
                        nxt,
                    ),
                )
        raise RuntimeError(f"未找到 {profile.label} 候选航线。")

    def _edge_cost(
        self,
        *,
        prev: tuple[int, int, int] | None,
        current: tuple[int, int, int],
        nxt: tuple[int, int, int],
        x_values: list[float],
        y_values: list[float],
        altitude_layers_m: list[float],
        node_weather: Any,
        xy_urban_density: Any,
        node_connectivity: Any,
        node_reachability: Any,
        node_line_offset: Any,
        node_building_clearance: Any,
        edge_overflight: Any,
        edge_weather: Any,
        corridor_unit: tuple[float, float],
        request: PlannerRequest,
        consider_weather: bool,
        profile: CostProfile,
        used_corridors: list[set[tuple[int, int]]],
    ) -> float:
        x1 = x_values[current[0]]
        y1 = y_values[current[1]]
        x2 = x_values[nxt[0]]
        y2 = y_values[nxt[1]]
        segment = self._segment_stats(
            current=current,
            nxt=nxt,
            x_values=x_values,
            y_values=y_values,
            altitude_layers_m=altitude_layers_m,
            node_weather=node_weather,
            xy_urban_density=xy_urban_density,
            node_connectivity=node_connectivity,
            node_reachability=node_reachability,
            consider_weather=consider_weather,
        )
        target_altitude = (altitude_layers_m[current[2]] + altitude_layers_m[nxt[2]]) / 2.0
        preferred_altitude_m = profile.preferred_altitude_m
        if (
            request.planning_mode == self.PLANNING_MODE_BUILDING_ONLY
            and profile.preferred_altitude_m > request.max_altitude_m
        ):
            preferred_altitude_m = self._building_low_cruise_altitude_m(request)
        altitude_bias = abs(target_altitude - preferred_altitude_m) / max(preferred_altitude_m, 1.0)
        weather_blocked, weather_pressure = edge_weather(*current, *nxt)
        forced_weather_penalty_s = 0.0
        if weather_blocked:
            if request.planning_mode != self.PLANNING_MODE_COMBINED:
                return float("inf")
            weather_pressure = max(weather_pressure, 1.25)
            forced_weather_penalty_s = segment.horizontal_m / max(request.cruise_speed_mps, 0.1) * 4.5
        if not consider_weather:
            weather_pressure = 0.0
        if weather_blocked and request.planning_mode != self.PLANNING_MODE_COMBINED:
            return float("inf")
        speed_loss = (
            segment.headwind_mps * profile.headwind_factor
            + segment.crosswind_mps * profile.crosswind_factor
            + segment.turbulence_index * request.cruise_speed_mps * profile.turbulence_factor
            + segment.precipitation_mm * 6.0 * profile.precipitation_factor
        )
        ground_speed = max(4.0, request.cruise_speed_mps - speed_loss + segment.tailwind_mps * profile.tailwind_credit)
        travel_time_s = segment.horizontal_m / max(ground_speed, 0.1)
        if segment.vertical_m > 0.0:
            vertical_speed = request.climb_speed_mps if altitude_layers_m[nxt[2]] >= altitude_layers_m[current[2]] else request.descend_speed_mps
            travel_time_s += segment.vertical_m / max(vertical_speed, 0.1)
        base_cruise_time = segment.horizontal_m / max(request.cruise_speed_mps, 0.1)
        vertical_base_time = segment.vertical_m / max(request.climb_speed_mps, request.descend_speed_mps, 0.1) if segment.vertical_m > 0.0 else 0.0
        weather_penalty_base = base_cruise_time + vertical_base_time * 0.70
        travel_time_s += (
            weather_penalty_base * weather_pressure * (0.85 + profile.turbulence_factor + profile.precipitation_factor)
            + forced_weather_penalty_s
        )
        if consider_weather:
            visual_risk = self._edge_visual_weather_risk_score(
                current=current,
                nxt=nxt,
                x_values=x_values,
                y_values=y_values,
                altitude_layers_m=altitude_layers_m,
                node_weather=node_weather,
            )
            red_zone_excess = max(0.0, visual_risk - 0.46)
            severe_zone_excess = max(0.0, visual_risk - 0.72)
            strategy_risk_factor = {
                "fastest": 1.15,
                "safest": 8.50,
                "energy_saving": 2.10,
                "balanced_stable": 5.40,
                "most_accessible": 3.35,
            }.get(profile.strategy, 2.0)
            red_zone_penalty = weather_penalty_base * strategy_risk_factor * (
                red_zone_excess * 7.0 + severe_zone_excess * 14.0
            )
            if self._weather_segment_high_risk(segment):
                red_zone_penalty += weather_penalty_base * strategy_risk_factor * 1.9
            travel_time_s += red_zone_penalty
        if consider_weather:
            pressure_limit = self._direct_edge_weather_limit(profile=profile, consider_weather=True)
            pressure_excess = max(0.0, weather_pressure - pressure_limit)
            if pressure_excess > 0.0:
                strictness = 10.0 if profile.strategy in {"safest", "balanced_stable"} else 5.5
                travel_time_s += weather_penalty_base * pressure_excess * strictness
        if segment.horizontal_m > 1e-6:
            delta_x = x2 - x1
            delta_y = y2 - y1
            forward_progress_m = delta_x * corridor_unit[0] + delta_y * corridor_unit[1]
            progress_ratio = max(0.0, min(1.0, forward_progress_m / segment.horizontal_m))
            current_line_offset = node_line_offset(current[0], current[1])
            next_line_offset = node_line_offset(nxt[0], nxt[1])
            mean_line_offset = (current_line_offset + next_line_offset) / 2.0
            mean_building_clearance = (node_building_clearance(current[0], current[1]) + node_building_clearance(nxt[0], nxt[1])) / 2.0
            free_space_factor = min(
                1.0,
                max(0.0, (mean_building_clearance - max(request.safety_clearance_m + 6.0, request.cell_m * 0.30)) / max(request.cell_m, 1.0)),
            )
            line_penalty_scale = 0.32 + 0.68 * free_space_factor
            offset_ratio = mean_line_offset / max(request.cell_m, 1.0)
            if offset_ratio <= 1.0:
                deviation_penalty = offset_ratio
            else:
                deviation_penalty = 1.0 + (offset_ratio - 1.0) * (offset_ratio - 1.0) * 0.85
            travel_time_s += base_cruise_time * deviation_penalty * profile.line_deviation_factor * line_penalty_scale
            travel_time_s += base_cruise_time * (1.0 - progress_ratio) * profile.low_progress_factor
            if forward_progress_m < -1e-6:
                travel_time_s += abs(forward_progress_m) / max(request.cruise_speed_mps, 0.1) * profile.reverse_progress_factor
            if next_line_offset > current_line_offset + 1e-6:
                travel_time_s += (
                    base_cruise_time
                    * ((next_line_offset - current_line_offset) / max(request.cell_m, 1.0))
                    * profile.rejoin_factor
                    * free_space_factor
                )
            elif current_line_offset > request.cell_m * 0.35 and next_line_offset > request.cell_m * 0.35:
                travel_time_s += (
                    base_cruise_time
                    * (next_line_offset / max(request.cell_m, 1.0))
                    * profile.rejoin_factor
                    * 0.18
                    * free_space_factor
                )
            _count, overflight_exposure = edge_overflight(*current, *nxt)
            travel_time_s += base_cruise_time * overflight_exposure * profile.overflight_factor
            if prev is not None:
                turn_penalty = self._turn_penalty(
                    prev=prev,
                    current=current,
                    nxt=nxt,
                    x_values=x_values,
                    y_values=y_values,
                )
                travel_time_s += base_cruise_time * turn_penalty * profile.turn_penalty_factor
        travel_time_s += base_cruise_time * segment.mean_density * profile.urban_density_factor
        travel_time_s += base_cruise_time * (1.0 - segment.mean_connectivity) * profile.connectivity_factor
        travel_time_s += base_cruise_time * (1.0 - segment.mean_reachability) * profile.reachability_factor
        travel_time_s += altitude_bias * 2.5
        for corridor in used_corridors:
            if self._is_near_used_corridor(nxt[0], nxt[1], corridor):
                travel_time_s += profile.reuse_penalty_s
                break
        return travel_time_s

    @staticmethod
    def _heuristic(
        node: tuple[int, int, int],
        goal: tuple[int, int, int],
        x_values: list[float],
        y_values: list[float],
        altitude_layers_m: list[float],
        request: PlannerRequest,
    ) -> float:
        horizontal_m = math.hypot(x_values[goal[0]] - x_values[node[0]], y_values[goal[1]] - y_values[node[1]])
        vertical_m = abs(altitude_layers_m[goal[2]] - altitude_layers_m[node[2]])
        return horizontal_m / max(request.cruise_speed_mps, 0.1) + vertical_m / max(request.climb_speed_mps, request.descend_speed_mps, 0.1)

    def _edge_is_clear(
        self,
        *,
        current: tuple[int, int, int],
        nxt: tuple[int, int, int],
        x_values: list[float],
        y_values: list[float],
        altitude_layers_m: list[float],
        blocked_height: Any,
        building_index: BuildingIndex,
        request: PlannerRequest,
        consider_buildings: bool,
    ) -> bool:
        if not consider_buildings:
            return True
        x1 = x_values[current[0]]
        y1 = y_values[current[1]]
        x2 = x_values[nxt[0]]
        y2 = y_values[nxt[1]]
        min_altitude = min(altitude_layers_m[current[2]], altitude_layers_m[nxt[2]])
        if current[0] == nxt[0] and current[1] == nxt[1]:
            if self._strict_building_avoidance(request.planning_mode):
                point = (x1, y1)
                for building in building_index.query_bbox(point[0], point[1], point[0], point[1]):
                    if point_in_poly(point, building.points_xy):
                        return False
            return min_altitude > blocked_height(current[0], current[1]) + 1e-6
        left = min(x1, x2)
        right = max(x1, x2)
        bottom = min(y1, y2)
        top = max(y1, y2)
        allow_overflight = self._segment_allows_overflight(min_altitude_m=min_altitude, request=request)
        for building in building_index.query_bbox(left, bottom, right, top):
            if not segment_hits_poly((x1, y1), (x2, y2), building.points_xy):
                continue
            if self._strict_building_avoidance(request.planning_mode):
                return False
            required_altitude = building.height_m + request.safety_clearance_m
            if min_altitude <= required_altitude + 1e-6:
                return False
            if not allow_overflight:
                return False
        return True

    def _edge_overflight_stats(
        self,
        *,
        current: tuple[int, int, int],
        nxt: tuple[int, int, int],
        x_values: list[float],
        y_values: list[float],
        altitude_layers_m: list[float],
        building_index: BuildingIndex,
        request: PlannerRequest,
        consider_buildings: bool,
    ) -> tuple[int, float]:
        if not consider_buildings or not self._building_overflight_allowed(request.planning_mode):
            return 0, 0.0
        x1 = x_values[current[0]]
        y1 = y_values[current[1]]
        x2 = x_values[nxt[0]]
        y2 = y_values[nxt[1]]
        if math.isclose(x1, x2, abs_tol=1e-9) and math.isclose(y1, y2, abs_tol=1e-9):
            return 0, 0.0
        min_altitude = min(altitude_layers_m[current[2]], altitude_layers_m[nxt[2]])
        left = min(x1, x2)
        right = max(x1, x2)
        bottom = min(y1, y2)
        top = max(y1, y2)
        building_count = 0
        exposure = 0.0
        for building in building_index.query_bbox(left, bottom, right, top):
            if not segment_hits_poly((x1, y1), (x2, y2), building.points_xy):
                continue
            required_altitude = building.height_m + request.safety_clearance_m
            if min_altitude <= required_altitude + 1e-6:
                continue
            building_count += 1
            clearance_m = min_altitude - required_altitude
            exposure += (1.0 + min(building.height_m, 240.0) / 120.0) / (1.0 + clearance_m / 35.0)
        return building_count, exposure

    def _with_endpoint_altitude_transitions(
        self,
        *,
        path: list[tuple[int, int, int]],
        requested_start_altitude_m: float,
        requested_end_altitude_m: float,
        altitude_layers_m: list[float],
        x_values: list[float],
        y_values: list[float],
        blocked_height: Any,
        building_index: BuildingIndex,
        edge_weather: Any,
        edge_is_clear: Any,
        request: PlannerRequest,
        consider_buildings: bool,
        node_is_blocked: Any,
    ) -> list[tuple[int, int, int]]:
        if not path:
            return path
        adjusted = list(path)
        start_idx = self._nearest_axis_index(altitude_layers_m, requested_start_altitude_m)
        requested_start = (adjusted[0][0], adjusted[0][1], start_idx)
        if (
            requested_start != adjusted[0]
            and not node_is_blocked(*requested_start)
            and edge_is_clear(*requested_start, *adjusted[0])
            and not edge_weather(*requested_start, *adjusted[0])[0]
        ):
            adjusted.insert(0, requested_start)
        end_idx = self._nearest_axis_index(altitude_layers_m, requested_end_altitude_m)
        requested_end = (adjusted[-1][0], adjusted[-1][1], end_idx)
        if (
            requested_end != adjusted[-1]
            and not node_is_blocked(*requested_end)
            and edge_is_clear(*adjusted[-1], *requested_end)
            and not edge_weather(*adjusted[-1], *requested_end)[0]
        ):
            adjusted.append(requested_end)
        return adjusted

    @staticmethod
    def _point_to_segment_distance(
        *,
        point: tuple[float, float],
        start: tuple[float, float],
        end: tuple[float, float],
    ) -> float:
        segment_dx = end[0] - start[0]
        segment_dy = end[1] - start[1]
        length_sq = segment_dx * segment_dx + segment_dy * segment_dy
        if length_sq <= 1e-12:
            return math.hypot(point[0] - start[0], point[1] - start[1])
        projection = ((point[0] - start[0]) * segment_dx + (point[1] - start[1]) * segment_dy) / length_sq
        projection = max(0.0, min(1.0, projection))
        closest = (start[0] + projection * segment_dx, start[1] + projection * segment_dy)
        return math.hypot(point[0] - closest[0], point[1] - closest[1])

    @classmethod
    def _point_to_poly_distance(cls, *, point: tuple[float, float], poly: list[tuple[float, float]]) -> float:
        if len(poly) < 2:
            return float("inf")
        best = float("inf")
        for idx in range(len(poly) - 1):
            best = min(
                best,
                cls._point_to_segment_distance(
                    point=point,
                    start=poly[idx],
                    end=poly[idx + 1],
                ),
            )
        return best

    @staticmethod
    def _turn_penalty(
        *,
        prev: tuple[int, int, int],
        current: tuple[int, int, int],
        nxt: tuple[int, int, int],
        x_values: list[float],
        y_values: list[float],
    ) -> float:
        vx1 = x_values[current[0]] - x_values[prev[0]]
        vy1 = y_values[current[1]] - y_values[prev[1]]
        vx2 = x_values[nxt[0]] - x_values[current[0]]
        vy2 = y_values[nxt[1]] - y_values[current[1]]
        norm1 = math.hypot(vx1, vy1)
        norm2 = math.hypot(vx2, vy2)
        if norm1 <= 1e-6 or norm2 <= 1e-6:
            return 0.0
        cosine = max(-1.0, min(1.0, (vx1 * vx2 + vy1 * vy2) / (norm1 * norm2)))
        angle = math.acos(cosine)
        return angle / math.pi

    def _simplify_path(
        self,
        *,
        path: list[tuple[int, int, int]],
        x_values: list[float],
        y_values: list[float],
        altitude_layers_m: list[float],
        blocked_height: Any,
        building_index: BuildingIndex,
        edge_weather: Any,
        edge_is_clear: Any,
        request: PlannerRequest,
        consider_buildings: bool,
        weather_pressure_limit: float,
    ) -> list[tuple[int, int, int]]:
        if len(path) <= 2:
            return path
        simplified = [path[0]]
        idx = 0
        while idx < len(path) - 1:
            nxt = len(path) - 1
            while nxt > idx + 1:
                span_altitudes = [altitude_layers_m[node[2]] for node in path[idx : nxt + 1]]
                start_altitude_m = span_altitudes[0]
                end_altitude_m = span_altitudes[-1]
                internal_altitudes = span_altitudes[1:-1]
                if internal_altitudes and (
                    max(internal_altitudes) > max(start_altitude_m, end_altitude_m) + 1e-6
                    or min(internal_altitudes) < min(start_altitude_m, end_altitude_m) - 1e-6
                ):
                    nxt -= 1
                    continue
                weather_blocked, weather_pressure = edge_weather(*path[idx], *path[nxt])
                if edge_is_clear(*path[idx], *path[nxt]) and not weather_blocked and weather_pressure <= weather_pressure_limit:
                    break
                nxt -= 1
            simplified.append(path[nxt])
            idx = nxt
        return simplified

    def _build_candidate(
        self,
        *,
        route_id: str,
        profile: CostProfile,
        path: list[tuple[int, int, int]],
        x_values: list[float],
        y_values: list[float],
        altitude_layers_m: list[float],
        node_weather: Any,
        xy_urban_density: Any,
        node_connectivity: Any,
        node_reachability: Any,
        edge_overflight: Any,
        request: PlannerRequest,
        consider_weather: bool,
    ) -> RouteCandidate:
        total_distance_m = 0.0
        estimated_duration_s = 0.0
        max_wind = 0.0
        max_headwind = 0.0
        max_crosswind = 0.0
        max_turbulence = 0.0
        max_precipitation = 0.0
        max_weather_risk = 0.0
        high_risk_segment_count = 0
        segment_count = 0
        density_sum = 0.0
        connectivity_sum = 0.0
        reachability_sum = 0.0
        min_connectivity = 1.0
        overflight_building_count = 0
        overflight_exposure = 0.0
        waypoints: list[dict[str, float | str]] = []
        for idx, node in enumerate(path):
            x_m = x_values[node[0]]
            y_m = y_values[node[1]]
            altitude_m = altitude_layers_m[node[2]]
            lat, lon = meters_to_latlon(self.origin, x_m, y_m)
            waypoints.append(
                {
                    "lat": round(lat, 9),
                    "lon": round(lon, 9),
                    "altitude_m": round(altitude_m, 1),
                    "label": f"航点{idx + 1}",
                }
            )
            weather = (
                node_weather(*node)
                if consider_weather
                else WeatherState(
                    wind_east_mps=0.0,
                    wind_north_mps=0.0,
                    wind_speed_mps=0.0,
                    turbulence_index=0.0,
                    precipitation_mm=0.0,
                    pressure_hpa=1013.25,
                    temperature_c=0.0,
                    cloud_cover_pct=0.0,
                )
            )
            density = xy_urban_density(node[0], node[1])
            connectivity = node_connectivity(node[0], node[1], node[2])
            reachability = node_reachability(node[0], node[1], node[2])
            density_sum += density
            connectivity_sum += connectivity
            reachability_sum += reachability
            min_connectivity = min(min_connectivity, connectivity)
            max_wind = max(max_wind, weather.wind_speed_mps)
            max_turbulence = max(max_turbulence, weather.turbulence_index)
            max_precipitation = max(max_precipitation, weather.precipitation_mm)
            if consider_weather:
                max_weather_risk = max(max_weather_risk, self._visual_weather_risk_score(weather=weather, altitude_m=altitude_m))
            if idx == 0:
                continue
            prev = path[idx - 1]
            segment = self._segment_stats(
                current=prev,
                nxt=node,
                x_values=x_values,
                y_values=y_values,
                altitude_layers_m=altitude_layers_m,
                node_weather=node_weather,
                xy_urban_density=xy_urban_density,
                node_connectivity=node_connectivity,
                node_reachability=node_reachability,
                consider_weather=consider_weather,
            )
            segment_overflight_count, segment_overflight_exposure = edge_overflight(*prev, *node)
            overflight_building_count += segment_overflight_count
            overflight_exposure += segment_overflight_exposure
            total_distance_m += math.hypot(segment.horizontal_m, segment.vertical_m)
            max_wind = max(max_wind, segment.wind_speed_mps)
            max_headwind = max(max_headwind, segment.headwind_mps)
            max_crosswind = max(max_crosswind, segment.crosswind_mps)
            max_turbulence = max(max_turbulence, segment.turbulence_index)
            max_precipitation = max(max_precipitation, segment.precipitation_mm)
            if consider_weather:
                max_weather_risk = max(
                    max_weather_risk,
                    self._edge_visual_weather_risk_score(
                        current=prev,
                        nxt=node,
                        x_values=x_values,
                        y_values=y_values,
                        altitude_layers_m=altitude_layers_m,
                        node_weather=node_weather,
                    ),
                )
            segment_count += 1
            if consider_weather and self._weather_segment_high_risk(segment):
                high_risk_segment_count += 1
            estimated_duration_s += self._evaluate_segment_duration(
                segment=segment,
                current_altitude_m=altitude_layers_m[prev[2]],
                next_altitude_m=altitude_layers_m[node[2]],
                request=request,
                consider_weather=consider_weather,
            )
        average_density = density_sum / max(len(path), 1)
        average_connectivity = connectivity_sum / max(len(path), 1)
        average_reachability = reachability_sum / max(len(path), 1)
        base_cost = round(
            estimated_duration_s
            + max_headwind * 7.5
            + max_crosswind * 4.5
            + max_turbulence * 110.0
            + max_precipitation * 38.0
            + max_weather_risk * 160.0
            + (high_risk_segment_count / max(segment_count, 1)) * 320.0
            + average_density * 70.0
            + overflight_exposure * 16.0
            + (1.0 - average_reachability) * 80.0,
            2,
        )
        candidate = RouteCandidate(
            route_id=route_id,
            label=profile.label,
            strategy=profile.strategy,
            score=0.0,
            base_cost=base_cost,
            topsis_score=0.0,
            robustness_score=0.0,
            reliability_ratio=0.0,
            duration_p95_s=0.0,
            expected_delay_ratio=0.0,
            distance_m=round(total_distance_m, 2),
            estimated_duration_s=round(estimated_duration_s, 2),
            max_wind_speed_mps=round(max_wind, 2),
            max_headwind_mps=round(max_headwind, 2),
            max_crosswind_mps=round(max_crosswind, 2),
            max_turbulence_index=round(max_turbulence, 3),
            max_precipitation_mm=round(max_precipitation, 3),
            max_weather_risk_score=round(max_weather_risk, 3),
            high_risk_exposure_ratio=round(high_risk_segment_count / max(segment_count, 1), 3),
            average_urban_density=round(average_density, 3),
            average_connectivity_index=round(average_connectivity, 3),
            minimum_connectivity_index=round(min_connectivity if path else 0.0, 3),
            average_reachability_index=round(average_reachability, 3),
            corridor_diversity_index=0.0,
            overflight_building_count=overflight_building_count,
            overflight_exposure_index=round(overflight_exposure, 3),
            waypoint_count=len(waypoints),
            recommended_rank=0,
            waypoints=waypoints,
        )
        return self._with_request_endpoint_anchors(route=candidate, request=request)

    def _segment_stats(
        self,
        *,
        current: tuple[int, int, int],
        nxt: tuple[int, int, int],
        x_values: list[float],
        y_values: list[float],
        altitude_layers_m: list[float],
        node_weather: Any,
        xy_urban_density: Any,
        node_connectivity: Any,
        node_reachability: Any,
        consider_weather: bool,
        rng: random.Random | None = None,
    ) -> SegmentStats:
        x1 = x_values[current[0]]
        y1 = y_values[current[1]]
        x2 = x_values[nxt[0]]
        y2 = y_values[nxt[1]]
        horizontal_m = math.hypot(x2 - x1, y2 - y1)
        vertical_m = abs(altitude_layers_m[nxt[2]] - altitude_layers_m[current[2]])
        if consider_weather:
            weather_samples = self._edge_weather_samples(
                current=current,
                nxt=nxt,
                x_values=x_values,
                y_values=y_values,
                altitude_layers_m=altitude_layers_m,
                node_weather=node_weather,
            )
            wind_east = sum(weather.wind_east_mps for weather, _altitude_m in weather_samples) / max(len(weather_samples), 1)
            wind_north = sum(weather.wind_north_mps for weather, _altitude_m in weather_samples) / max(len(weather_samples), 1)
            wind_speed = max((weather.wind_speed_mps for weather, _altitude_m in weather_samples), default=0.0)
            turbulence = max((weather.turbulence_index for weather, _altitude_m in weather_samples), default=0.0)
            precipitation = max((weather.precipitation_mm for weather, _altitude_m in weather_samples), default=0.0)
        else:
            wind_east = 0.0
            wind_north = 0.0
            wind_speed = 0.0
            turbulence = 0.0
            precipitation = 0.0
        if consider_weather and rng is not None:
            wind_east, wind_north, wind_speed = self._perturb_wind_vector(wind_east, wind_north, rng)
            turbulence = min(1.0, max(0.0, turbulence + rng.uniform(-0.12, 0.16)))
            precipitation = max(0.0, precipitation * (1.0 + rng.uniform(-0.30, 0.55)))
        if horizontal_m > 1e-6:
            unit_x = (x2 - x1) / horizontal_m
            unit_y = (y2 - y1) / horizontal_m
            wind_along = wind_east * unit_x + wind_north * unit_y
            headwind = max(0.0, -wind_along)
            tailwind = max(0.0, wind_along)
            crosswind = abs(wind_east * unit_y - wind_north * unit_x)
        else:
            headwind = 0.0
            tailwind = 0.0
            crosswind = 0.0
        return SegmentStats(
            horizontal_m=horizontal_m,
            vertical_m=vertical_m,
            wind_speed_mps=wind_speed,
            headwind_mps=headwind,
            tailwind_mps=tailwind,
            crosswind_mps=crosswind,
            turbulence_index=turbulence,
            precipitation_mm=precipitation,
            mean_density=(xy_urban_density(current[0], current[1]) + xy_urban_density(nxt[0], nxt[1])) / 2.0,
            mean_connectivity=(node_connectivity(current[0], current[1], current[2]) + node_connectivity(nxt[0], nxt[1], nxt[2])) / 2.0,
            mean_reachability=(node_reachability(current[0], current[1], current[2]) + node_reachability(nxt[0], nxt[1], nxt[2])) / 2.0,
        )

    def _edge_weather_samples(
        self,
        *,
        current: tuple[int, int, int],
        nxt: tuple[int, int, int],
        x_values: list[float],
        y_values: list[float],
        altitude_layers_m: list[float],
        node_weather: Any,
    ) -> list[tuple[WeatherState, float]]:
        x1 = x_values[current[0]]
        y1 = y_values[current[1]]
        z1 = altitude_layers_m[current[2]]
        x2 = x_values[nxt[0]]
        y2 = y_values[nxt[1]]
        z2 = altitude_layers_m[nxt[2]]
        horizontal_m = math.hypot(x2 - x1, y2 - y1)
        vertical_m = abs(z2 - z1)
        is_neighbor_edge = (
            abs(current[0] - nxt[0]) <= 1
            and abs(current[1] - nxt[1]) <= 1
            and abs(current[2] - nxt[2]) <= 1
        )
        steps = 1 if is_neighbor_edge else max(1, min(32, math.ceil(max(horizontal_m / 120.0, vertical_m / 40.0))))
        samples: list[tuple[WeatherState, float]] = []
        for step in range(steps + 1):
            if step == 0:
                samples.append((node_weather(*current), z1))
                continue
            if step == steps:
                samples.append((node_weather(*nxt), z2))
                continue
            ratio = step / steps
            x_m = x1 + (x2 - x1) * ratio
            y_m = y1 + (y2 - y1) * ratio
            altitude_m = z1 + (z2 - z1) * ratio
            samples.append((self.weather_field.interpolate(x_m, y_m, altitude_m), altitude_m))
        return samples

    def _edge_visual_weather_risk_score(
        self,
        *,
        current: tuple[int, int, int],
        nxt: tuple[int, int, int],
        x_values: list[float],
        y_values: list[float],
        altitude_layers_m: list[float],
        node_weather: Any,
    ) -> float:
        return max(
            (
                self._visual_weather_risk_score(weather=weather, altitude_m=altitude_m)
                for weather, altitude_m in self._edge_weather_samples(
                    current=current,
                    nxt=nxt,
                    x_values=x_values,
                    y_values=y_values,
                    altitude_layers_m=altitude_layers_m,
                    node_weather=node_weather,
                )
            ),
            default=0.0,
        )

    @staticmethod
    def _perturb_wind_vector(wind_east: float, wind_north: float, rng: random.Random) -> tuple[float, float, float]:
        speed = math.hypot(wind_east, wind_north)
        if speed < 1e-6:
            return 0.0, 0.0, 0.0
        angle = math.atan2(wind_north, wind_east) + rng.uniform(-0.35, 0.35)
        speed *= 1.0 + rng.uniform(-0.18, 0.28)
        speed = max(0.0, speed)
        return speed * math.cos(angle), speed * math.sin(angle), speed

    @staticmethod
    def _soft_hard_ratio(value: float, soft_limit: float, hard_limit: float) -> float:
        if value <= soft_limit:
            return 0.0
        if hard_limit <= soft_limit + 1e-6:
            return 1.0
        return max(0.0, min(1.6, (value - soft_limit) / (hard_limit - soft_limit)))

    @staticmethod
    def _weather_thresholds(request: PlannerRequest) -> dict[str, float]:
        cruise_speed = max(request.cruise_speed_mps, 1.0)
        return {
            "wind_soft": max(6.0, cruise_speed * 0.50),
            "wind_hard": max(10.0, cruise_speed * 0.82),
            "headwind_soft": max(4.0, cruise_speed * 0.32),
            "headwind_hard": max(7.5, cruise_speed * 0.58),
            "crosswind_soft": max(4.5, cruise_speed * 0.36),
            "crosswind_hard": max(8.0, cruise_speed * 0.68),
            "turbulence_soft": 0.28,
            "turbulence_hard": 0.58,
            "precipitation_soft": 0.6,
            "precipitation_hard": 3.5,
            "convective_turbulence": 0.45,
            "convective_precipitation": 1.8,
            "pressure_anomaly_soft": 3.0,
            "pressure_anomaly_hard": 7.5,
            "pressure_gradient_soft": 1.6,
            "pressure_gradient_hard": 4.2,
        }

    def _pressure_anomaly_hpa(self, *, weather: WeatherState, altitude_m: float) -> float:
        return abs(weather.pressure_hpa - self.weather_field.reference_pressure_hpa(altitude_m))

    def _visual_weather_risk_score(self, *, weather: WeatherState, altitude_m: float) -> float:
        """Mirror the Cesium risk overlay so ranking and visualization speak the same language."""
        rain = min(1.0, max(0.0, weather.precipitation_mm) / 2.2)
        convective = min(1.0, max(0.0, weather.turbulence_index) / 0.72)
        wind = min(1.0, max(0.0, weather.wind_speed_mps) / 14.0)
        cloud = min(1.0, max(0.0, weather.cloud_cover_pct) / 100.0)
        pressure = min(1.0, self._pressure_anomaly_hpa(weather=weather, altitude_m=altitude_m) / 8.0)
        return max(0.0, min(1.0, rain * 0.34 + convective * 0.28 + wind * 0.18 + cloud * 0.12 + pressure * 0.08))

    @staticmethod
    def _direct_edge_weather_limit(*, profile: CostProfile, consider_weather: bool) -> float:
        if not consider_weather:
            return float("inf")
        limits = {
            "fastest": 0.82,
            "energy_saving": 0.72,
            "most_accessible": 0.72,
            "balanced_stable": 0.72,
            "safest": 0.52,
        }
        return limits.get(profile.strategy, 0.85)

    @classmethod
    def _direct_edge_weather_allowed(cls, *, profile: CostProfile, weather_pressure: float, consider_weather: bool) -> bool:
        return weather_pressure <= cls._direct_edge_weather_limit(profile=profile, consider_weather=consider_weather)

    def _node_weather_pressure(self, *, weather: WeatherState, altitude_m: float, request: PlannerRequest) -> float:
        thresholds = self._weather_thresholds(request)
        wind_ratio = self._soft_hard_ratio(weather.wind_speed_mps, thresholds["wind_soft"], thresholds["wind_hard"])
        turbulence_ratio = self._soft_hard_ratio(
            weather.turbulence_index,
            thresholds["turbulence_soft"],
            thresholds["turbulence_hard"],
        )
        precipitation_ratio = self._soft_hard_ratio(
            weather.precipitation_mm,
            thresholds["precipitation_soft"],
            thresholds["precipitation_hard"],
        )
        pressure_ratio = self._soft_hard_ratio(
            self._pressure_anomaly_hpa(weather=weather, altitude_m=altitude_m),
            thresholds["pressure_anomaly_soft"],
            thresholds["pressure_anomaly_hard"],
        )
        convective_bonus = (
            0.35
            if weather.turbulence_index >= thresholds["convective_turbulence"]
            and weather.precipitation_mm >= thresholds["convective_precipitation"]
            else 0.0
        )
        return min(1.8, wind_ratio * 0.34 + turbulence_ratio * 0.26 + precipitation_ratio * 0.18 + pressure_ratio * 0.22 + convective_bonus)

    def _node_weather_blocked(self, *, weather: WeatherState, altitude_m: float, request: PlannerRequest) -> bool:
        thresholds = self._weather_thresholds(request)
        return (
            weather.wind_speed_mps >= thresholds["wind_hard"]
            or weather.turbulence_index >= thresholds["turbulence_hard"]
            or weather.precipitation_mm >= thresholds["precipitation_hard"]
            or self._pressure_anomaly_hpa(weather=weather, altitude_m=altitude_m) >= thresholds["pressure_anomaly_hard"]
            or (
                weather.turbulence_index >= thresholds["convective_turbulence"]
                and weather.precipitation_mm >= thresholds["convective_precipitation"]
            )
        )

    def _edge_weather_stats(
        self,
        *,
        current: tuple[int, int, int],
        nxt: tuple[int, int, int],
        x_values: list[float],
        y_values: list[float],
        altitude_layers_m: list[float],
        node_weather: Any,
        request: PlannerRequest,
        consider_weather: bool,
    ) -> tuple[bool, float]:
        if not consider_weather:
            return False, 0.0
        current_weather = node_weather(*current)
        next_weather = node_weather(*nxt)
        current_altitude_m = altitude_layers_m[current[2]]
        next_altitude_m = altitude_layers_m[nxt[2]]
        current_pressure = self._node_weather_pressure(weather=current_weather, altitude_m=current_altitude_m, request=request)
        next_pressure = self._node_weather_pressure(weather=next_weather, altitude_m=next_altitude_m, request=request)
        current_blocked = self._node_weather_blocked(weather=current_weather, altitude_m=current_altitude_m, request=request)
        next_blocked = self._node_weather_blocked(weather=next_weather, altitude_m=next_altitude_m, request=request)
        if current[0] == nxt[0] and current[1] == nxt[1]:
            blocked = next_blocked and next_pressure >= current_pressure - 0.15
            return blocked, max(0.0, (current_pressure + next_pressure) / 2.0)

        x1 = x_values[current[0]]
        y1 = y_values[current[1]]
        x2 = x_values[nxt[0]]
        y2 = y_values[nxt[1]]
        horizontal_m = math.hypot(x2 - x1, y2 - y1)
        weather_samples = self._edge_weather_samples(
            current=current,
            nxt=nxt,
            x_values=x_values,
            y_values=y_values,
            altitude_layers_m=altitude_layers_m,
            node_weather=node_weather,
        )
        wind_speed = max((weather.wind_speed_mps for weather, _altitude_m in weather_samples), default=0.0)
        turbulence = max((weather.turbulence_index for weather, _altitude_m in weather_samples), default=0.0)
        precipitation = max((weather.precipitation_mm for weather, _altitude_m in weather_samples), default=0.0)
        visual_risk = max(
            (
                self._visual_weather_risk_score(weather=weather, altitude_m=altitude_m)
                for weather, altitude_m in weather_samples
            ),
            default=0.0,
        )
        mean_pressure_anomaly = max(
            (self._pressure_anomaly_hpa(weather=weather, altitude_m=altitude_m) for weather, altitude_m in weather_samples),
            default=0.0,
        )
        excess_pressure_gap = 0.0
        for sample_idx in range(1, len(weather_samples)):
            prev_weather, prev_altitude_m = weather_samples[sample_idx - 1]
            sample_weather, sample_altitude_m = weather_samples[sample_idx]
            expected_pressure_gap = abs(
                self.weather_field.reference_pressure_hpa(prev_altitude_m)
                - self.weather_field.reference_pressure_hpa(sample_altitude_m)
            )
            actual_pressure_gap = abs(prev_weather.pressure_hpa - sample_weather.pressure_hpa)
            excess_pressure_gap = max(excess_pressure_gap, max(0.0, actual_pressure_gap - expected_pressure_gap))
        if horizontal_m > 1e-6:
            unit_x = (x2 - x1) / horizontal_m
            unit_y = (y2 - y1) / horizontal_m
            headwind = 0.0
            crosswind = 0.0
            for weather, _altitude_m in weather_samples:
                wind_along = weather.wind_east_mps * unit_x + weather.wind_north_mps * unit_y
                headwind = max(headwind, max(0.0, -wind_along))
                crosswind = max(crosswind, abs(weather.wind_east_mps * unit_y - weather.wind_north_mps * unit_x))
        else:
            headwind = 0.0
            crosswind = 0.0
        thresholds = self._weather_thresholds(request)
        wind_ratio = self._soft_hard_ratio(wind_speed, thresholds["wind_soft"], thresholds["wind_hard"])
        headwind_ratio = self._soft_hard_ratio(headwind, thresholds["headwind_soft"], thresholds["headwind_hard"])
        crosswind_ratio = self._soft_hard_ratio(crosswind, thresholds["crosswind_soft"], thresholds["crosswind_hard"])
        turbulence_ratio = self._soft_hard_ratio(
            turbulence,
            thresholds["turbulence_soft"],
            thresholds["turbulence_hard"],
        )
        precipitation_ratio = self._soft_hard_ratio(
            precipitation,
            thresholds["precipitation_soft"],
            thresholds["precipitation_hard"],
        )
        pressure_anomaly_ratio = self._soft_hard_ratio(
            mean_pressure_anomaly,
            thresholds["pressure_anomaly_soft"],
            thresholds["pressure_anomaly_hard"],
        )
        pressure_gradient_ratio = self._soft_hard_ratio(
            excess_pressure_gap,
            thresholds["pressure_gradient_soft"],
            thresholds["pressure_gradient_hard"],
        )
        convective_bonus = (
            0.28
            if turbulence >= thresholds["convective_turbulence"] and precipitation >= thresholds["convective_precipitation"]
            else 0.0
        )
        raw_weather_pressure = (
            wind_ratio * 0.18
            + headwind_ratio * 0.28
            + crosswind_ratio * 0.16
            + turbulence_ratio * 0.24
            + precipitation_ratio * 0.14
            + pressure_anomaly_ratio * 0.18
            + pressure_gradient_ratio * 0.16
            + convective_bonus
        )
        weather_pressure = min(1.8, max(raw_weather_pressure, visual_risk * 1.15))
        blocked = (
            wind_speed >= thresholds["wind_hard"]
            or headwind >= thresholds["headwind_hard"]
            or crosswind >= thresholds["crosswind_hard"]
            or turbulence >= thresholds["turbulence_hard"]
            or precipitation >= thresholds["precipitation_hard"]
            or mean_pressure_anomaly >= thresholds["pressure_anomaly_hard"]
            or excess_pressure_gap >= thresholds["pressure_gradient_hard"]
            or (
                turbulence >= thresholds["convective_turbulence"]
                and precipitation >= thresholds["convective_precipitation"]
            )
        )
        if blocked and next_pressure + 0.12 < current_pressure and weather_pressure < 1.25:
            blocked = False
        if blocked and current_blocked and not next_blocked and next_pressure + 0.05 < current_pressure:
            blocked = False
        if blocked:
            sampled_blocked = [
                idx
                for idx, (weather, altitude_m) in enumerate(weather_samples)
                if self._node_weather_blocked(weather=weather, altitude_m=altitude_m, request=request)
            ]
            if sampled_blocked == [0] and next_pressure + 0.05 < current_pressure:
                blocked = False
        return blocked, weather_pressure

    @staticmethod
    def _weather_reachability_factor(*, wind_speed_mps: float, turbulence_index: float, precipitation_mm: float) -> float:
        wind_term = max(0.0, 1.0 - wind_speed_mps / 18.0)
        turbulence_term = max(0.0, 1.0 - turbulence_index)
        precipitation_term = max(0.0, 1.0 - min(precipitation_mm, 10.0) / 10.0)
        return max(0.0, min(1.0, wind_term * 0.45 + turbulence_term * 0.35 + precipitation_term * 0.20))

    @staticmethod
    def _weather_segment_high_risk(segment: SegmentStats) -> bool:
        return (
            segment.wind_speed_mps >= 10.0
            or segment.headwind_mps >= 7.0
            or segment.crosswind_mps >= 7.0
            or segment.precipitation_mm >= 1.8
            or (segment.turbulence_index >= 0.42 and segment.precipitation_mm >= 1.2)
        )

    @staticmethod
    def _evaluate_segment_duration(
        *,
        segment: SegmentStats,
        current_altitude_m: float,
        next_altitude_m: float,
        request: PlannerRequest,
        consider_weather: bool,
    ) -> float:
        speed_loss = 0.0
        if consider_weather:
            speed_loss = (
                segment.headwind_mps * 0.35
                + segment.crosswind_mps * 0.18
                + segment.turbulence_index * request.cruise_speed_mps * 0.22
                + segment.precipitation_mm * 0.55
            )
        ground_speed = max(4.0, request.cruise_speed_mps - speed_loss + segment.tailwind_mps * 0.10)
        duration_s = segment.horizontal_m / max(ground_speed, 0.1)
        if segment.vertical_m > 0.0:
            vertical_speed = request.climb_speed_mps if next_altitude_m >= current_altitude_m else request.descend_speed_mps
            duration_s += segment.vertical_m / max(vertical_speed, 0.1)
        base_cruise_time = segment.horizontal_m / max(request.cruise_speed_mps, 0.1)
        duration_s += base_cruise_time * segment.mean_density * 0.18
        duration_s += base_cruise_time * (1.0 - segment.mean_connectivity) * 0.20
        duration_s += base_cruise_time * (1.0 - segment.mean_reachability) * 0.28
        return duration_s

    def _finalize_routes(
        self,
        *,
        routes: list[RouteCandidate],
        paths: list[list[tuple[int, int, int]] | None],
        signatures: list[set[tuple[int, int]]],
        x_values: list[float],
        y_values: list[float],
        altitude_layers_m: list[float],
        node_weather: Any,
        xy_urban_density: Any,
        node_connectivity: Any,
        node_reachability: Any,
        request: PlannerRequest,
    ) -> dict[str, float]:
        if not routes:
            return {metric.field: 0.0 for metric in self.RANKING_METRICS}
        average_altitudes = [
            (
                sum(altitude_layers_m[node[2]] for node in path) / max(len(path), 1)
                if path is not None
                else sum(float(point["altitude_m"]) for point in routes[idx].waypoints) / max(len(routes[idx].waypoints), 1)
            )
            for idx, path in enumerate(paths)
        ]
        for idx, route in enumerate(routes):
            diversity_values = [
                self._pairwise_diversity_index(
                    overlap_ratio=self._corridor_overlap_ratio(signatures[idx], signatures[other_idx]),
                    altitude_gap_m=abs(average_altitudes[idx] - average_altitudes[other_idx]),
                    request=request,
                )
                for other_idx in range(len(signatures))
                if other_idx != idx
            ]
            route.corridor_diversity_index = round(
                sum(diversity_values) / len(diversity_values) if diversity_values else 1.0,
                3,
            )
            if paths[idx] is None:
                robustness = self._evaluate_waypoint_route_robustness(
                    route=route,
                    request=request,
                )
            else:
                robustness = self._evaluate_route_robustness(
                    path=paths[idx],
                    x_values=x_values,
                    y_values=y_values,
                    altitude_layers_m=altitude_layers_m,
                    node_weather=node_weather,
                    xy_urban_density=xy_urban_density,
                    node_connectivity=node_connectivity,
                    node_reachability=node_reachability,
                    request=request,
                    route=route,
                )
            route.robustness_score = robustness["robustness_score"]
            route.reliability_ratio = robustness["reliability_ratio"]
            route.duration_p95_s = robustness["duration_p95_s"]
            route.expected_delay_ratio = robustness["expected_delay_ratio"]
        weights, closeness_values = self._entropy_weight_topsis(routes)
        for route, closeness in zip(routes, closeness_values):
            route.topsis_score = round(closeness * 100.0, 2)
            route.score = round(route.topsis_score * 0.70 + route.robustness_score * 0.30, 2)
        routes[:] = self._assign_route_roles(routes=routes, request=request)
        routes.sort(key=lambda item: (item.score, item.robustness_score, -item.base_cost), reverse=True)
        for idx, route in enumerate(routes, start=1):
            route.recommended_rank = idx
        return {key: round(value, 4) for key, value in weights.items()}

    @staticmethod
    def _normalized_metric(values: list[float], *, benefit: bool) -> list[float]:
        if not values:
            return []
        low = min(values)
        high = max(values)
        if abs(high - low) <= 1e-9:
            return [1.0] * len(values)
        if benefit:
            return [(value - low) / (high - low) for value in values]
        return [(high - value) / (high - low) for value in values]

    @staticmethod
    def _route_turn_count(route: RouteCandidate) -> int:
        turns = 0
        prev = None
        prev2 = None
        for point in route.waypoints:
            current = (float(point["lon"]), float(point["lat"]))
            if prev2 is not None and prev is not None:
                ax = prev[0] - prev2[0]
                ay = prev[1] - prev2[1]
                bx = current[0] - prev[0]
                by = current[1] - prev[1]
                if abs(ax * by - ay * bx) > 1e-12:
                    turns += 1
            prev2 = prev
            prev = current
        return turns

    @staticmethod
    def _route_average_altitude_m(route: RouteCandidate) -> float:
        if not route.waypoints:
            return 0.0
        return sum(float(point["altitude_m"]) for point in route.waypoints) / len(route.waypoints)

    def _route_energy_proxy(self, route: RouteCandidate, request: PlannerRequest) -> float:
        average_altitude_m = self._route_average_altitude_m(route)
        turn_count = self._route_turn_count(route)
        baseline_altitude_m = (request.start_altitude_m + request.end_altitude_m) / 2.0
        climb_penalty_m = max(0.0, average_altitude_m - baseline_altitude_m)
        return (
            route.distance_m
            + route.estimated_duration_s * 0.65
            + climb_penalty_m * 3.0
            + turn_count * 75.0
            + route.max_headwind_mps * 70.0
            + route.max_crosswind_mps * 45.0
            + route.max_turbulence_index * 180.0
            + route.max_precipitation_mm * 80.0
            + route.max_weather_risk_score * 360.0
            + route.high_risk_exposure_ratio * 680.0
            + route.overflight_exposure_index * 12.0
        )

    def _assign_route_roles(self, *, routes: list[RouteCandidate], request: PlannerRequest) -> list[RouteCandidate]:
        if not routes:
            return []
        role_defs = self.STRATEGY_ROLE_ORDER[: len(routes)]
        remaining = set(range(len(routes)))
        labels = {strategy: label for strategy, label in role_defs}
        energy_proxy = {
            idx: self._route_energy_proxy(route, request)
            for idx, route in enumerate(routes)
        }
        risk_proxy = {
            idx: (
                route.overflight_building_count * 22.0
                + route.overflight_exposure_index * 70.0
                + route.average_urban_density * 95.0
                + route.max_weather_risk_score * 720.0
                + route.high_risk_exposure_ratio * 1850.0
                + route.max_precipitation_mm * 190.0
                + route.max_turbulence_index * 420.0
                + route.max_wind_speed_mps * 18.0
                + route.max_headwind_mps * 24.0
                + route.max_crosswind_mps * 22.0
                + (1.0 - route.average_reachability_index) * 90.0
                + (1.0 - route.reliability_ratio) * 60.0
            )
            for idx, route in enumerate(routes)
        }
        access_proxy = {
            idx: (
                route.average_connectivity_index * 0.34
                + route.average_reachability_index * 0.56
                + route.corridor_diversity_index * 0.10
            )
            for idx, route in enumerate(routes)
        }
        selected_signatures: set[tuple[tuple[float, float, float], ...]] = set()

        def route_signature(idx: int) -> tuple[tuple[float, float, float], ...]:
            return tuple(
                (
                    round(float(point["lat"]), 7),
                    round(float(point["lon"]), 7),
                    round(float(point["altitude_m"]), 1),
                )
                for point in routes[idx].waypoints
            )

        def candidate_pool() -> set[int]:
            diverse = {idx for idx in remaining if route_signature(idx) not in selected_signatures}
            return diverse if diverse else set(remaining)

        def pick_min(key_fn):
            best_idx = min(candidate_pool(), key=key_fn)
            remaining.remove(best_idx)
            selected_signatures.add(route_signature(best_idx))
            return best_idx

        def pick_max(key_fn):
            best_idx = max(candidate_pool(), key=key_fn)
            remaining.remove(best_idx)
            selected_signatures.add(route_signature(best_idx))
            return best_idx

        assigned: dict[str, int] = {}
        if "fastest" in labels and remaining:
            assigned["fastest"] = pick_min(
                lambda idx: (
                    routes[idx].estimated_duration_s,
                    routes[idx].distance_m,
                    energy_proxy[idx],
                    routes[idx].overflight_exposure_index,
                )
            )
        if "safest" in labels and remaining:
            assigned["safest"] = pick_min(
                lambda idx: (
                    routes[idx].high_risk_exposure_ratio,
                    routes[idx].max_weather_risk_score,
                    routes[idx].max_precipitation_mm,
                    routes[idx].max_turbulence_index,
                    routes[idx].max_wind_speed_mps,
                    routes[idx].overflight_exposure_index,
                    risk_proxy[idx],
                    routes[idx].estimated_duration_s,
                    routes[idx].distance_m,
                )
            )
        if "energy_saving" in labels and remaining:
            assigned["energy_saving"] = pick_min(
                lambda idx: (
                    energy_proxy[idx],
                    routes[idx].estimated_duration_s,
                    routes[idx].overflight_exposure_index,
                    routes[idx].distance_m,
                )
            )
        if "balanced_stable" in labels and remaining:
            assigned["balanced_stable"] = pick_max(
                lambda idx: (
                    -risk_proxy[idx],
                    access_proxy[idx],
                    routes[idx].score,
                    routes[idx].robustness_score,
                    routes[idx].reliability_ratio,
                    -routes[idx].estimated_duration_s,
                )
            )
        if "most_accessible" in labels and remaining:
            assigned["most_accessible"] = pick_max(
                lambda idx: (
                    access_proxy[idx],
                    routes[idx].average_connectivity_index,
                    routes[idx].average_reachability_index,
                    -routes[idx].estimated_duration_s,
                    -routes[idx].overflight_exposure_index,
                )
            )
        selected_routes: list[RouteCandidate] = []
        for strategy, route_idx in assigned.items():
            routes[route_idx].strategy = strategy
            routes[route_idx].label = labels[strategy]
            selected_routes.append(routes[route_idx])
        return selected_routes

    def _evaluate_route_robustness(
        self,
        *,
        path: list[tuple[int, int, int]],
        x_values: list[float],
        y_values: list[float],
        altitude_layers_m: list[float],
        node_weather: Any,
        xy_urban_density: Any,
        node_connectivity: Any,
        node_reachability: Any,
        request: PlannerRequest,
        route: RouteCandidate,
    ) -> dict[str, float]:
        if len(path) <= 1:
            return {
                "robustness_score": 100.0,
                "reliability_ratio": 1.0,
                "duration_p95_s": route.estimated_duration_s,
                "expected_delay_ratio": 0.0,
            }
        seed = len(path) * 104729
        for idx, (ix, iy, iz) in enumerate(path, start=1):
            seed ^= ((ix + 17) * 73856093) ^ ((iy + 31) * 19349663) ^ ((iz + idx) * 83492791)
        rng = random.Random(seed & 0xFFFFFFFF)
        durations: list[float] = []
        delay_ratios: list[float] = []
        safe_count = 0
        for _ in range(self.MONTE_CARLO_RUNS):
            total_duration = 0.0
            risk_pressure = 0.0
            for segment_idx in range(1, len(path)):
                prev = path[segment_idx - 1]
                node = path[segment_idx]
                segment = self._segment_stats(
                    current=prev,
                    nxt=node,
                    x_values=x_values,
                    y_values=y_values,
                    altitude_layers_m=altitude_layers_m,
                    node_weather=node_weather,
                    xy_urban_density=xy_urban_density,
                    node_connectivity=node_connectivity,
                    node_reachability=node_reachability,
                    consider_weather=self._consider_weather(request.planning_mode),
                    rng=rng,
                )
                total_duration += self._evaluate_segment_duration(
                    segment=segment,
                    current_altitude_m=altitude_layers_m[prev[2]],
                    next_altitude_m=altitude_layers_m[node[2]],
                    request=request,
                    consider_weather=self._consider_weather(request.planning_mode),
                )
                risk_pressure = max(
                    risk_pressure,
                    segment.headwind_mps / max(request.cruise_speed_mps * 0.78, 1.0),
                    segment.crosswind_mps / max(request.cruise_speed_mps * 0.90, 1.0),
                    segment.turbulence_index / 0.72,
                    segment.precipitation_mm / 3.5,
                    (1.0 - segment.mean_reachability) / 0.70,
                )
            durations.append(total_duration)
            delay_ratio = max(0.0, (total_duration - route.estimated_duration_s) / max(route.estimated_duration_s, 1.0))
            delay_ratios.append(delay_ratio)
            if risk_pressure <= 1.0 and delay_ratio <= 0.35:
                safe_count += 1
        reliability_ratio = safe_count / max(self.MONTE_CARLO_RUNS, 1)
        expected_delay_ratio = sum(delay_ratios) / max(len(delay_ratios), 1)
        delay_p95 = self._percentile(delay_ratios, 0.95)
        robustness_score = 100.0 * (
            0.55 * reliability_ratio
            + 0.25 * (1.0 - min(expected_delay_ratio, 0.80) / 0.80)
            + 0.20 * (1.0 - min(delay_p95, 1.20) / 1.20)
        )
        return {
            "robustness_score": round(max(0.0, min(100.0, robustness_score)), 2),
            "reliability_ratio": round(reliability_ratio, 3),
            "duration_p95_s": round(self._percentile(durations, 0.95), 2),
            "expected_delay_ratio": round(expected_delay_ratio, 3),
        }

    @staticmethod
    def _evaluate_waypoint_route_robustness(
        *,
        route: RouteCandidate,
        request: PlannerRequest,
    ) -> dict[str, float]:
        baseline = max(route.estimated_duration_s, 1.0)
        exposure_penalty = min(1.0, route.overflight_exposure_index / 3.0)
        density_penalty = min(1.0, route.average_urban_density)
        reliability_ratio = max(0.55, 0.98 - 0.28 * exposure_penalty - 0.12 * density_penalty)
        expected_delay_ratio = min(0.35, 0.03 + exposure_penalty * 0.10 + density_penalty * 0.06)
        duration_p95_s = baseline * (1.0 + expected_delay_ratio * 1.65)
        robustness_score = 100.0 * (
            0.55 * reliability_ratio
            + 0.25 * (1.0 - min(expected_delay_ratio, 0.80) / 0.80)
            + 0.20 * (1.0 - min(expected_delay_ratio * 1.4, 1.20) / 1.20)
        )
        return {
            "robustness_score": round(max(0.0, min(100.0, robustness_score)), 2),
            "reliability_ratio": round(reliability_ratio, 3),
            "duration_p95_s": round(duration_p95_s, 2),
            "expected_delay_ratio": round(expected_delay_ratio, 3),
        }

    def _append_road_fallback_routes(
        self,
        *,
        routes: list[RouteCandidate],
        profiles: list[CostProfile],
        accepted_signatures: list[set[tuple[int, int]]],
        x_values: list[float],
        y_values: list[float],
        altitude_layers_m: list[float],
        node_weather: Any,
        xy_urban_density: Any,
        node_connectivity: Any,
        node_reachability: Any,
        start_xy: tuple[float, float],
        end_xy: tuple[float, float],
        building_index: BuildingIndex,
        target_count: int,
        blocked_height: Any,
        edge_weather: Any,
        xy_segment_clear: Any,
        request: PlannerRequest,
        consider_buildings: bool,
        consider_weather: bool,
    ) -> tuple[list[None], list[set[tuple[int, int]]]]:
        if self.road_graph is None:
            return [], []
        road_paths: list[None] = []
        road_signatures: list[set[tuple[int, int]]] = []
        used_edge_sets: list[set[tuple[int, int]]] = []
        existing_strategies = {route.strategy for route in routes}
        pending_profiles = [profile for profile in profiles if profile.strategy not in existing_strategies]
        if not pending_profiles:
            pending_profiles = profiles
        road_path_cache: dict[tuple[str, float, int], tuple[list[tuple[float, float]], set[tuple[int, int]]] | None] = {}
        xy_detour_path_cache: dict[tuple[str, float, int], list[tuple[float, float]] | None] = {}
        threading_path_cache: dict[tuple[str, float, int], list[tuple[float, float]] | None] = {}
        trusted_road_path_cache: dict[tuple[str, float, int], list[tuple[float, float]] | None] = {}

        def waypoint_signature(route: RouteCandidate) -> tuple[tuple[float, float, float], ...]:
            return tuple(
                (
                    round(float(point["lat"]), 7),
                    round(float(point["lon"]), 7),
                    round(float(point["altitude_m"]), 1),
                )
                for point in route.waypoints
            )

        def xy_signature_from_path(path_xy: list[tuple[float, float]]) -> set[tuple[int, int]]:
            return {
                (
                    int(round(point_xy[0] / max(request.cell_m, 1.0))),
                    int(round(point_xy[1] / max(request.cell_m, 1.0))),
                )
                for point_xy in path_xy
            }

        for profile in pending_profiles:
            if len(routes) >= target_count:
                break
            fallback_altitude_m = self._fallback_profile_altitude_m(profile=profile, request=request)
            altitude_key = round(fallback_altitude_m, 2)
            route_cache_key = (profile.strategy, altitude_key, len(accepted_signatures) + len(road_signatures))
            low_altitude_direct = (
                request.planning_mode == self.PLANNING_MODE_BUILDING_ONLY
                and not consider_weather
                and request.max_altitude_m <= max(60.0, request.min_altitude_m + 60.0)
            )
            road_result = None
            if not consider_weather and not low_altitude_direct:
                if route_cache_key not in road_path_cache:
                    road_path_cache[route_cache_key] = self._road_graph_path(
                        start_xy=start_xy,
                        end_xy=end_xy,
                        profile=profile,
                        altitude_m=fallback_altitude_m,
                        building_index=building_index,
                        xy_segment_clear=xy_segment_clear,
                        request=request,
                        used_edge_sets=used_edge_sets,
                    )
                road_result = road_path_cache[route_cache_key]
            path_xy = None
            edge_signature = set()
            if road_result is not None:
                path_xy, edge_signature = road_result
            else:
                if low_altitude_direct:
                    path_xy = self._building_footprint_detour_path(
                        start_xy=start_xy,
                        end_xy=end_xy,
                        profile=profile,
                        building_index=building_index,
                        request=request,
                        used_signatures=accepted_signatures + road_signatures,
                    )
                    if path_xy is None and route_cache_key not in threading_path_cache:
                        threading_path_cache[route_cache_key] = self._low_altitude_threading_path(
                            start_xy=start_xy,
                            end_xy=end_xy,
                            profile=profile,
                            altitude_m=fallback_altitude_m,
                            building_index=building_index,
                            xy_segment_clear=xy_segment_clear,
                            request=request,
                            used_signatures=accepted_signatures + road_signatures,
                        )
                    if path_xy is None:
                        path_xy = threading_path_cache[route_cache_key]
                    if path_xy is None:
                        if route_cache_key not in trusted_road_path_cache:
                            trusted_road_path_cache[route_cache_key] = self._trusted_road_corridor_path(
                                start_xy=start_xy,
                                end_xy=end_xy,
                                profile=profile,
                                altitude_m=fallback_altitude_m,
                                xy_segment_clear=xy_segment_clear,
                                request=request,
                                used_edge_sets=used_edge_sets,
                            )
                        path_xy = trusted_road_path_cache[route_cache_key]
                else:
                    if route_cache_key not in xy_detour_path_cache:
                        xy_detour_path_cache[route_cache_key] = self._xy_detour_path(
                            start_xy=start_xy,
                            end_xy=end_xy,
                            profile=profile,
                            x_values=x_values,
                            y_values=y_values,
                            altitude_layers_m=altitude_layers_m,
                            blocked_height=blocked_height,
                            building_index=building_index,
                            node_weather=node_weather,
                            edge_weather=edge_weather,
                            xy_segment_clear=xy_segment_clear,
                            request=request,
                            consider_buildings=consider_buildings,
                            consider_weather=consider_weather,
                        )
                    path_xy = xy_detour_path_cache[route_cache_key]
                    if path_xy is None and request.planning_mode == self.PLANNING_MODE_BUILDING_ONLY and not consider_weather:
                        if route_cache_key not in threading_path_cache:
                            threading_path_cache[route_cache_key] = self._low_altitude_threading_path(
                                start_xy=start_xy,
                                end_xy=end_xy,
                                profile=profile,
                                altitude_m=fallback_altitude_m,
                                building_index=building_index,
                                xy_segment_clear=xy_segment_clear,
                                request=request,
                                used_signatures=accepted_signatures + road_signatures,
                            )
                        path_xy = threading_path_cache[route_cache_key]
                    if path_xy is None and request.planning_mode == self.PLANNING_MODE_BUILDING_ONLY and not consider_weather:
                        if route_cache_key not in trusted_road_path_cache:
                            trusted_road_path_cache[route_cache_key] = self._trusted_road_corridor_path(
                                start_xy=start_xy,
                                end_xy=end_xy,
                                profile=profile,
                                altitude_m=fallback_altitude_m,
                                xy_segment_clear=xy_segment_clear,
                                request=request,
                                used_edge_sets=used_edge_sets,
                            )
                        path_xy = trusted_road_path_cache[route_cache_key]
                    if path_xy is None and request.planning_mode == self.PLANNING_MODE_BUILDING_ONLY and not consider_weather:
                        path_xy = self._building_footprint_detour_path(
                            start_xy=start_xy,
                            end_xy=end_xy,
                            profile=profile,
                            building_index=building_index,
                            request=request,
                            used_signatures=accepted_signatures + road_signatures,
                        )
                    if path_xy is None and request.planning_mode == self.PLANNING_MODE_COMBINED:
                        path_xy = self._building_footprint_detour_path(
                            start_xy=start_xy,
                            end_xy=end_xy,
                            profile=profile,
                            building_index=building_index,
                            request=request,
                            used_signatures=accepted_signatures + road_signatures,
                        )
            if path_xy is None:
                continue
            if request.planning_mode == self.PLANNING_MODE_BUILDING_ONLY:
                if any(
                    self._xy_segment_required_altitude_m(
                        start_xy=path_xy[idx - 1],
                        end_xy=path_xy[idx],
                        building_index=building_index,
                        request=request,
                        consider_buildings=consider_buildings,
                    )
                    > request.max_altitude_m + 1e-6
                    for idx in range(1, len(path_xy))
                ):
                    continue
            elif any(
                not xy_segment_clear(path_xy[idx - 1], path_xy[idx], fallback_altitude_m)
                for idx in range(1, len(path_xy))
            ):
                continue
            signature = xy_signature_from_path(path_xy)
            overlaps_existing = any(
                self._corridor_overlap_ratio(signature, existing) > 0.96
                for existing in accepted_signatures + road_signatures
            )
            if overlaps_existing and not (
                request.planning_mode == self.PLANNING_MODE_BUILDING_ONLY
                and request.max_altitude_m <= max(60.0, request.min_altitude_m + 60.0)
            ):
                continue
            candidate = self._build_candidate_from_xy_path(
                route_id=f"route_{len(routes) + 1}",
                profile=profile,
                path_xy=path_xy,
                altitude_m=fallback_altitude_m,
                x_values=x_values,
                y_values=y_values,
                altitude_layers_m=altitude_layers_m,
                node_weather=node_weather,
                xy_urban_density=xy_urban_density,
                node_connectivity=node_connectivity,
                node_reachability=node_reachability,
                building_index=building_index,
                request=request,
                consider_weather=consider_weather,
            )
            if consider_buildings and not self._route_segments_clear_buildings(
                route=candidate,
                request=request,
                building_index=building_index,
            ):
                continue
            if waypoint_signature(candidate) in {waypoint_signature(route) for route in routes}:
                continue
            routes.append(candidate)
            road_paths.append(None)
            road_signatures.append(signature)
            used_edge_sets.append(edge_signature)
        if (
            request.planning_mode in {self.PLANNING_MODE_COMBINED, self.PLANNING_MODE_BUILDING_ONLY}
            and len(routes) < target_count
            and routes
        ):
            source_routes = list(routes)
            existing_signatures = {waypoint_signature(route) for route in routes}
            existing_strategies = {route.strategy for route in routes}
            refill_profiles = [profile for profile in profiles if profile.strategy not in existing_strategies]
            if not refill_profiles:
                refill_profiles = profiles
            made_progress = True
            while len(routes) < target_count and made_progress:
                made_progress = False
                for profile in refill_profiles:
                    if len(routes) >= target_count:
                        break
                    if any(route.strategy == profile.strategy for route in routes) and len(refill_profiles) < len(profiles):
                        continue
                    for source_route in source_routes:
                        path_xy = [
                            latlon_to_meters(self.origin, float(point["lat"]), float(point["lon"]))
                            for point in source_route.waypoints
                        ]
                        if len(path_xy) < 2:
                            continue
                        fallback_altitude_m = self._fallback_profile_altitude_m(profile=profile, request=request)
                        candidate = self._build_candidate_from_xy_path(
                            route_id=f"route_{len(routes) + 1}",
                            profile=profile,
                            path_xy=path_xy,
                            altitude_m=fallback_altitude_m,
                            x_values=x_values,
                            y_values=y_values,
                            altitude_layers_m=altitude_layers_m,
                            node_weather=node_weather,
                            xy_urban_density=xy_urban_density,
                            node_connectivity=node_connectivity,
                            node_reachability=node_reachability,
                            building_index=building_index,
                            request=request,
                            consider_weather=consider_weather,
                        )
                        candidate_signature = waypoint_signature(candidate)
                        if candidate_signature in existing_signatures:
                            continue
                        if consider_buildings and not self._route_segments_clear_buildings(
                            route=candidate,
                            request=request,
                            building_index=building_index,
                        ):
                            continue
                        routes.append(candidate)
                        existing_signatures.add(candidate_signature)
                        signature = xy_signature_from_path(path_xy)
                        road_paths.append(None)
                        road_signatures.append(signature)
                        made_progress = True
                        break
                refill_profiles = profiles
            if len(routes) < target_count:
                duplicate_refill_profiles = [
                    profile for profile in profiles if profile.strategy not in {route.strategy for route in routes}
                ] + profiles
                for profile in duplicate_refill_profiles:
                    if len(routes) >= target_count:
                        break
                    for source_route in source_routes:
                        path_xy = [
                            latlon_to_meters(self.origin, float(point["lat"]), float(point["lon"]))
                            for point in source_route.waypoints
                        ]
                        if len(path_xy) < 2:
                            continue
                        fallback_altitude_m = self._fallback_profile_altitude_m(profile=profile, request=request)
                        candidate = self._build_candidate_from_xy_path(
                            route_id=f"route_{len(routes) + 1}",
                            profile=profile,
                            path_xy=path_xy,
                            altitude_m=fallback_altitude_m,
                            x_values=x_values,
                            y_values=y_values,
                            altitude_layers_m=altitude_layers_m,
                            node_weather=node_weather,
                            xy_urban_density=xy_urban_density,
                            node_connectivity=node_connectivity,
                            node_reachability=node_reachability,
                            building_index=building_index,
                            request=request,
                            consider_weather=consider_weather,
                        )
                        if consider_buildings and not self._route_segments_clear_buildings(
                            route=candidate,
                            request=request,
                            building_index=building_index,
                        ):
                            continue
                        routes.append(candidate)
                        road_paths.append(None)
                        road_signatures.append(xy_signature_from_path(path_xy))
                        break
        return road_paths, road_signatures

    def _combined_weather_safe_detour_path(
        self,
        *,
        start_xy: tuple[float, float],
        end_xy: tuple[float, float],
        profile: CostProfile,
        building_index: BuildingIndex,
        request: PlannerRequest,
        used_signatures: list[set[tuple[int, int]]],
    ) -> list[tuple[float, float]] | None:
        if request.planning_mode != self.PLANNING_MODE_COMBINED:
            return None

        west_south = latlon_to_meters(self.origin, float(self.bbox["south"]), float(self.bbox["west"]))
        east_north = latlon_to_meters(self.origin, float(self.bbox["north"]), float(self.bbox["east"]))
        route_distance_m = self._xy_distance(start_xy, end_xy)
        corridor_margin = max(1200.0, route_distance_m * 1.25)
        cell_m = max(34.0, min(58.0, request.cell_m * 0.22))
        x_min = max(west_south[0] - cell_m, min(start_xy[0], end_xy[0]) - corridor_margin)
        x_max = min(east_north[0] + cell_m, max(start_xy[0], end_xy[0]) + corridor_margin)
        y_min = max(west_south[1] - cell_m, min(start_xy[1], end_xy[1]) - corridor_margin)
        y_max = min(east_north[1] + cell_m, max(start_xy[1], end_xy[1]) + corridor_margin)
        estimated_nodes = max(1, int((x_max - x_min) / cell_m) + 1) * max(1, int((y_max - y_min) / cell_m) + 1)
        if estimated_nodes > 42000:
            cell_m *= math.sqrt(estimated_nodes / 42000)
        x_values = [x_min + idx * cell_m for idx in range(int((x_max - x_min) / cell_m) + 1)]
        y_values = [y_min + idx * cell_m for idx in range(int((y_max - y_min) / cell_m) + 1)]
        if len(x_values) < 2 or len(y_values) < 2:
            return None

        local_building_index = BuildingIndex(building_index.buildings, bucket_m=max(80.0, cell_m * 4.0))
        sample_altitude_m = max(
            request.min_altitude_m,
            min(
                request.max_altitude_m,
                max(request.start_altitude_m, request.end_altitude_m, profile.preferred_altitude_m),
            ),
        )
        used_cells = set().union(*used_signatures) if used_signatures else set()
        corridor_dx = end_xy[0] - start_xy[0]
        corridor_dy = end_xy[1] - start_xy[1]
        corridor_len = max(math.hypot(corridor_dx, corridor_dy), 1e-6)
        corridor_unit = (corridor_dx / corridor_len, corridor_dy / corridor_len)

        @lru_cache(maxsize=None)
        def node_is_clear(ix: int, iy: int) -> bool:
            return (
                self._xy_point_required_altitude_m(
                    point_xy=(x_values[ix], y_values[iy]),
                    building_index=local_building_index,
                    request=request,
                    consider_buildings=True,
                )
                <= request.max_altitude_m + 1e-6
            )

        @lru_cache(maxsize=None)
        def edge_is_clear(ix1: int, iy1: int, ix2: int, iy2: int) -> bool:
            return (
                self._xy_segment_required_altitude_m(
                    start_xy=(x_values[ix1], y_values[iy1]),
                    end_xy=(x_values[ix2], y_values[iy2]),
                    building_index=local_building_index,
                    request=request,
                    consider_buildings=True,
                )
                <= request.max_altitude_m + 1e-6
            )

        @lru_cache(maxsize=None)
        def node_building_clearance(ix: int, iy: int) -> float:
            point_xy = (x_values[ix], y_values[iy])
            radius = max(cell_m * 5.0, 180.0)
            nearby = local_building_index.query_bbox(
                point_xy[0] - radius,
                point_xy[1] - radius,
                point_xy[0] + radius,
                point_xy[1] + radius,
            )
            if not nearby:
                return radius
            best = radius
            for building in nearby:
                if point_in_poly(point_xy, building.points_xy):
                    return 0.0
                best = min(best, self._point_to_poly_distance(point=point_xy, poly=building.points_xy))
            return best

        @lru_cache(maxsize=None)
        def node_weather_risk(ix: int, iy: int) -> tuple[float, float, float, float]:
            weather = self.weather_field.interpolate(x_values[ix], y_values[iy], sample_altitude_m)
            risk = self._visual_weather_risk_score(weather=weather, altitude_m=sample_altitude_m)
            return risk, weather.precipitation_mm, weather.turbulence_index, weather.wind_speed_mps

        def point_is_clear(point_xy: tuple[float, float]) -> bool:
            return (
                self._xy_point_required_altitude_m(
                    point_xy=point_xy,
                    building_index=local_building_index,
                    request=request,
                    consider_buildings=True,
                )
                <= request.max_altitude_m + 1e-6
            )

        def segment_is_clear(a: tuple[float, float], b: tuple[float, float]) -> bool:
            return (
                self._xy_segment_required_altitude_m(
                    start_xy=a,
                    end_xy=b,
                    building_index=local_building_index,
                    request=request,
                    consider_buildings=True,
                )
                <= request.max_altitude_m + 1e-6
            )

        def nearest_grid_index(point_xy: tuple[float, float]) -> tuple[int, int]:
            return (
                self._nearest_axis_index(x_values, point_xy[0]),
                self._nearest_axis_index(y_values, point_xy[1]),
            )

        def nearest_clear_nodes(point_xy: tuple[float, float], limit: int) -> list[tuple[int, int]]:
            center = nearest_grid_index(point_xy)
            scored: list[tuple[float, tuple[int, int]]] = []
            max_radius = max(len(x_values), len(y_values))
            for radius in range(max_radius):
                for ix in range(max(0, center[0] - radius), min(len(x_values), center[0] + radius + 1)):
                    for iy in range(max(0, center[1] - radius), min(len(y_values), center[1] + radius + 1)):
                        if max(abs(ix - center[0]), abs(iy - center[1])) != radius:
                            continue
                        if not node_is_clear(ix, iy):
                            continue
                        candidate_xy = (x_values[ix], y_values[iy])
                        if not segment_is_clear(point_xy, candidate_xy):
                            continue
                        risk, precipitation, turbulence, wind = node_weather_risk(ix, iy)
                        distance = self._xy_distance(point_xy, candidate_xy)
                        scored.append(
                            (
                                distance
                                + risk * 520.0
                                + max(0.0, risk - 0.46) * 1800.0
                                + max(0.0, precipitation - 1.2) * 220.0
                                + max(0.0, turbulence - 0.34) * 800.0
                                + max(0.0, wind - 7.0) * 70.0,
                                (ix, iy),
                            )
                        )
                if len(scored) >= limit and radius >= 2:
                    break
                if radius >= 18 and scored:
                    break
            scored.sort(key=lambda item: item[0])
            return [node for _score, node in scored[:limit]]

        def nearest_clear_point(point_xy: tuple[float, float]) -> tuple[float, float] | None:
            center = nearest_grid_index(point_xy)
            best: tuple[float, tuple[float, float]] | None = None
            max_radius = max(len(x_values), len(y_values))
            for radius in range(max_radius):
                for ix in range(max(0, center[0] - radius), min(len(x_values), center[0] + radius + 1)):
                    for iy in range(max(0, center[1] - radius), min(len(y_values), center[1] + radius + 1)):
                        if max(abs(ix - center[0]), abs(iy - center[1])) != radius:
                            continue
                        if not node_is_clear(ix, iy):
                            continue
                        candidate_xy = (x_values[ix], y_values[iy])
                        distance = self._xy_distance(point_xy, candidate_xy)
                        if best is None or distance < best[0]:
                            best = (distance, candidate_xy)
                if best is not None:
                    return best[1]
            return None

        effective_start_xy = start_xy if point_is_clear(start_xy) else nearest_clear_point(start_xy)
        effective_end_xy = end_xy if point_is_clear(end_xy) else nearest_clear_point(end_xy)
        if effective_start_xy is None or effective_end_xy is None:
            return None
        start_nodes = nearest_clear_nodes(effective_start_xy, 10)
        end_nodes = nearest_clear_nodes(effective_end_xy, 10)
        if not start_nodes or not end_nodes:
            return None

        moves = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]

        def segment_weather_penalty(current: tuple[int, int], nxt: tuple[int, int], step_m: float) -> float:
            current_risk, current_precipitation, current_turbulence, current_wind = node_weather_risk(*current)
            next_risk, next_precipitation, next_turbulence, next_wind = node_weather_risk(*nxt)
            max_risk = max(current_risk, next_risk)
            max_precipitation = max(current_precipitation, next_precipitation)
            max_turbulence = max(current_turbulence, next_turbulence)
            max_wind = max(current_wind, next_wind)
            red_excess = max(0.0, max_risk - 0.46)
            severe_excess = max(0.0, max_risk - 0.72)
            return step_m * (
                max_risk * 4.5
                + red_excess * 34.0
                + severe_excess * 78.0
                + max(0.0, max_precipitation - 1.20) * 4.2
                + max(0.0, max_turbulence - 0.34) * 22.0
                + max(0.0, max_wind - 7.0) * 1.4
            )

        def search_path(
            route_start_xy: tuple[float, float],
            route_end_xy: tuple[float, float],
            search_start_nodes: list[tuple[int, int]],
            search_end_nodes: list[tuple[int, int]],
        ) -> list[tuple[int, int]] | None:
            if not search_start_nodes or not search_end_nodes:
                return None
            end_set = set(search_end_nodes)
            route_dx = route_end_xy[0] - route_start_xy[0]
            route_dy = route_end_xy[1] - route_start_xy[1]
            route_len = max(math.hypot(route_dx, route_dy), 1e-6)
            route_unit = (route_dx / route_len, route_dy / route_len)

            def heuristic(node: tuple[int, int]) -> float:
                node_xy = (x_values[node[0]], y_values[node[1]])
                return min(self._xy_distance(node_xy, (x_values[end[0]], y_values[end[1]])) for end in search_end_nodes)

            def signed_offset(point_xy: tuple[float, float]) -> float:
                rel_x = point_xy[0] - route_start_xy[0]
                rel_y = point_xy[1] - route_start_xy[1]
                return rel_x * route_unit[1] - rel_y * route_unit[0]

            open_set: list[tuple[float, float, tuple[int, int]]] = []
            came_from: dict[tuple[int, int], tuple[int, int]] = {}
            best_cost: dict[tuple[int, int], float] = {}
            for node in search_start_nodes:
                node_xy = (x_values[node[0]], y_values[node[1]])
                start_cost = self._xy_distance(route_start_xy, node_xy)
                best_cost[node] = min(best_cost.get(node, float("inf")), start_cost)
                heapq.heappush(open_set, (start_cost + heuristic(node), start_cost, node))

            found: tuple[int, int] | None = None
            visited: set[tuple[int, int]] = set()
            while open_set:
                _priority, current_cost, current = heapq.heappop(open_set)
                if current in visited:
                    continue
                visited.add(current)
                if current in end_set:
                    found = current
                    break
                current_xy = (x_values[current[0]], y_values[current[1]])
                for dx, dy in moves:
                    nxt = (current[0] + dx, current[1] + dy)
                    if nxt[0] < 0 or nxt[0] >= len(x_values) or nxt[1] < 0 or nxt[1] >= len(y_values):
                        continue
                    if not node_is_clear(*nxt) or not edge_is_clear(current[0], current[1], nxt[0], nxt[1]):
                        continue
                    next_xy = (x_values[nxt[0]], y_values[nxt[1]])
                    step = self._xy_distance(current_xy, next_xy)
                    progress = (next_xy[0] - current_xy[0]) * route_unit[0] + (next_xy[1] - current_xy[1]) * route_unit[1]
                    reverse_penalty = abs(min(0.0, progress)) * 1.2
                    offset_ratio = self._point_to_segment_distance(
                        point=next_xy,
                        start=route_start_xy,
                        end=route_end_xy,
                    ) / max(route_len, 1.0)
                    deviation_penalty = step * max(0.0, offset_ratio - 0.55) * 2.2
                    side_bias = abs(signed_offset(next_xy)) * 0.015
                    coarse_cell = (
                        int(round(next_xy[0] / max(request.cell_m, 1.0))),
                        int(round(next_xy[1] / max(request.cell_m, 1.0))),
                    )
                    reuse_penalty = 80.0 if coarse_cell in used_cells else 0.0
                    clearance_m = min(node_building_clearance(*current), node_building_clearance(*nxt))
                    clearance_penalty = step * max(0.0, 1.0 - clearance_m / max(cell_m * 3.0, 1.0)) * 1.4
                    turn_penalty = 0.0
                    prev = came_from.get(current)
                    if prev is not None:
                        prev_xy = (x_values[prev[0]], y_values[prev[1]])
                        turn_penalty = step * self._xy_turn_penalty(prev_xy, current_xy, next_xy) * 0.55
                    new_cost = (
                        current_cost
                        + step
                        + segment_weather_penalty(current, nxt, step)
                        + reverse_penalty
                        + deviation_penalty
                        + side_bias
                        + reuse_penalty
                        + clearance_penalty
                        + turn_penalty
                    )
                    if new_cost >= best_cost.get(nxt, float("inf")):
                        continue
                    best_cost[nxt] = new_cost
                    came_from[nxt] = current
                    heapq.heappush(open_set, (new_cost + heuristic(nxt), new_cost, nxt))

            if found is None:
                return None
            node_path = [found]
            while node_path[-1] in came_from:
                node_path.append(came_from[node_path[-1]])
            node_path.reverse()
            return node_path

        node_path = search_path(effective_start_xy, effective_end_xy, start_nodes, end_nodes)
        if node_path is None:
            assigned: set[tuple[int, int]] = set()
            best_component: tuple[float, tuple[float, float], tuple[float, float], tuple[int, int], tuple[int, int]] | None = None
            for ix in range(len(x_values)):
                for iy in range(len(y_values)):
                    seed = (ix, iy)
                    if seed in assigned or not node_is_clear(ix, iy):
                        continue
                    component: list[tuple[int, int]] = []
                    queue = [seed]
                    assigned.add(seed)
                    while queue:
                        current = queue.pop()
                        component.append(current)
                        for dx, dy in moves:
                            nxt = (current[0] + dx, current[1] + dy)
                            if nxt[0] < 0 or nxt[0] >= len(x_values) or nxt[1] < 0 or nxt[1] >= len(y_values):
                                continue
                            if nxt in assigned or not node_is_clear(*nxt):
                                continue
                            if not edge_is_clear(current[0], current[1], nxt[0], nxt[1]):
                                continue
                            assigned.add(nxt)
                            queue.append(nxt)
                    if len(component) < 8:
                        continue
                    start_node = min(
                        component,
                        key=lambda node: self._xy_distance(start_xy, (x_values[node[0]], y_values[node[1]])),
                    )
                    end_node = min(
                        component,
                        key=lambda node: self._xy_distance(end_xy, (x_values[node[0]], y_values[node[1]])),
                    )
                    start_node_xy = (x_values[start_node[0]], y_values[start_node[1]])
                    end_node_xy = (x_values[end_node[0]], y_values[end_node[1]])
                    start_gap_m = self._xy_distance(start_xy, start_node_xy)
                    end_gap_m = self._xy_distance(end_xy, end_node_xy)
                    if start_gap_m + end_gap_m > route_distance_m * 2.2 + 1200.0:
                        continue
                    sample_nodes = component[:: max(1, len(component) // 28)]
                    mean_risk = sum(node_weather_risk(*node)[0] for node in sample_nodes) / max(len(sample_nodes), 1)
                    red_share = sum(1 for node in sample_nodes if node_weather_risk(*node)[0] >= 0.46) / max(len(sample_nodes), 1)
                    score = (
                        start_gap_m
                        + end_gap_m
                        + max(start_gap_m, end_gap_m) * 0.35
                        + mean_risk * route_distance_m * 0.90
                        + red_share * route_distance_m * 1.35
                        - min(len(component), 6000) * 0.015
                    )
                    if best_component is None or score < best_component[0]:
                        route_start_xy = start_xy if segment_is_clear(start_xy, start_node_xy) else start_node_xy
                        route_end_xy = end_xy if segment_is_clear(end_node_xy, end_xy) else end_node_xy
                        best_component = (score, route_start_xy, route_end_xy, start_node, end_node)
            if best_component is None:
                return None
            _score, effective_start_xy, effective_end_xy, start_node, end_node = best_component
            node_path = search_path(effective_start_xy, effective_end_xy, [start_node], [end_node])
            if node_path is None:
                return None

        path_xy = [effective_start_xy]
        for ix, iy in node_path:
            point_xy = (x_values[ix], y_values[iy])
            if self._xy_distance(path_xy[-1], point_xy) > 1e-6:
                path_xy.append(point_xy)
        if self._xy_distance(path_xy[-1], effective_end_xy) > 1e-6:
            path_xy.append(effective_end_xy)
        if start_xy != effective_start_xy and segment_is_clear(start_xy, effective_start_xy):
            path_xy.insert(0, start_xy)
        if end_xy != effective_end_xy and segment_is_clear(path_xy[-1], end_xy):
            path_xy.append(end_xy)
        if len(path_xy) < 2 or not all(segment_is_clear(path_xy[idx - 1], path_xy[idx]) for idx in range(1, len(path_xy))):
            return None
        simplified = self._simplify_xy_path(
            path_xy,
            building_index=local_building_index,
            strict_building_avoidance=True,
            xy_segment_clear=lambda a, b, _altitude_m: segment_is_clear(a, b),
            altitude_m=sample_altitude_m,
            request=request,
            consider_buildings=True,
        )
        if all(segment_is_clear(simplified[idx - 1], simplified[idx]) for idx in range(1, len(simplified))):
            return simplified
        return path_xy

    def _xy_detour_path(
        self,
        *,
        start_xy: tuple[float, float],
        end_xy: tuple[float, float],
        profile: CostProfile,
        x_values: list[float],
        y_values: list[float],
        altitude_layers_m: list[float],
        blocked_height: Any,
        building_index: BuildingIndex,
        node_weather: Any,
        edge_weather: Any,
        xy_segment_clear: Any,
        request: PlannerRequest,
        consider_buildings: bool,
        consider_weather: bool,
    ) -> list[tuple[float, float]] | None:
        strict_building_avoidance = self._strict_building_avoidance(request.planning_mode)
        if request.planning_mode == self.PLANNING_MODE_BUILDING_ONLY:
            attempted_altitudes = self._building_altitude_attempts(
                request,
                min(profile.preferred_altitude_m, request.max_altitude_m),
            )
        else:
            attempted_altitudes = [
                max(
                    request.start_altitude_m,
                    request.end_altitude_m,
                    min(profile.preferred_altitude_m, request.max_altitude_m),
                )
            ]
            if request.max_altitude_m is not None:
                attempted_altitudes.append(request.max_altitude_m)
        deduped_altitudes: list[float] = []
        seen_altitudes: set[float] = set()
        for altitude_m in attempted_altitudes:
            altitude_m = max(request.min_altitude_m, min(request.max_altitude_m, altitude_m))
            key = round(altitude_m, 2)
            if key in seen_altitudes:
                continue
            seen_altitudes.add(key)
            deduped_altitudes.append(key)

        for altitude_m in deduped_altitudes:
            altitude_idx = self._nearest_axis_index(altitude_layers_m, altitude_m)
            start_candidates = self._nearest_visible_xy_nodes(
                point_xy=start_xy,
                altitude_idx=altitude_idx,
                x_values=x_values,
                y_values=y_values,
                altitude_layers_m=altitude_layers_m,
                blocked_height=blocked_height,
                building_index=building_index,
                xy_segment_clear=xy_segment_clear,
                request=request,
                consider_buildings=consider_buildings,
                limit=4,
            )
            end_candidates = self._nearest_visible_xy_nodes(
                point_xy=end_xy,
                altitude_idx=altitude_idx,
                x_values=x_values,
                y_values=y_values,
                altitude_layers_m=altitude_layers_m,
                blocked_height=blocked_height,
                building_index=building_index,
                xy_segment_clear=xy_segment_clear,
                request=request,
                consider_buildings=consider_buildings,
                limit=4,
            )
            if not start_candidates or not end_candidates:
                continue
            for start_node in start_candidates:
                for end_node in end_candidates:
                    node_path = self._xy_astar_path(
                        start=start_node,
                        goal=end_node,
                        altitude_idx=altitude_idx,
                        x_values=x_values,
                        y_values=y_values,
                        altitude_layers_m=altitude_layers_m,
                        blocked_height=blocked_height,
                        building_index=building_index,
                        node_weather=node_weather,
                        edge_weather=edge_weather,
                        request=request,
                        consider_buildings=consider_buildings,
                        consider_weather=consider_weather,
                    )
                    if node_path is None:
                        continue
                    path_xy = [start_xy]
                    for ix, iy in node_path:
                        point_xy = (x_values[ix], y_values[iy])
                        if path_xy and self._xy_distance(path_xy[-1], point_xy) <= 1e-6:
                            continue
                        path_xy.append(point_xy)
                    if self._xy_distance(path_xy[-1], end_xy) > 1e-6:
                        path_xy.append(end_xy)
                    if any(
                        not xy_segment_clear(path_xy[idx - 1], path_xy[idx], altitude_m)
                        for idx in range(1, len(path_xy))
                    ):
                        continue
                    return self._simplify_xy_path(
                        path_xy,
                        building_index=building_index,
                        strict_building_avoidance=strict_building_avoidance,
                        xy_segment_clear=xy_segment_clear,
                        altitude_m=altitude_m,
                        request=request,
                        consider_buildings=consider_buildings,
                    )
        return None

    def _low_altitude_threading_path(
        self,
        *,
        start_xy: tuple[float, float],
        end_xy: tuple[float, float],
        profile: CostProfile,
        altitude_m: float,
        building_index: BuildingIndex,
        xy_segment_clear: Any,
        request: PlannerRequest,
        used_signatures: list[set[tuple[int, int]]],
    ) -> list[tuple[float, float]] | None:
        cell_m = min(request.cell_m, 40.0)
        west_south = latlon_to_meters(self.origin, float(self.bbox["south"]), float(self.bbox["west"]))
        east_north = latlon_to_meters(self.origin, float(self.bbox["north"]), float(self.bbox["east"]))
        margin = cell_m * 1.5
        x_min = west_south[0] - margin
        x_max = east_north[0] + margin
        y_min = west_south[1] - margin
        y_max = east_north[1] + margin
        estimated_nodes = max(1, int((x_max - x_min) / cell_m) + 1) * max(1, int((y_max - y_min) / cell_m) + 1)
        if estimated_nodes > 26000:
            corridor_margin = max(900.0, self._xy_distance(start_xy, end_xy) * 0.45)
            x_min = max(x_min, min(start_xy[0], end_xy[0]) - corridor_margin)
            x_max = min(x_max, max(start_xy[0], end_xy[0]) + corridor_margin)
            y_min = max(y_min, min(start_xy[1], end_xy[1]) - corridor_margin)
            y_max = min(y_max, max(start_xy[1], end_xy[1]) + corridor_margin)
        x_values = [x_min + idx * cell_m for idx in range(int((x_max - x_min) / cell_m) + 1)]
        y_values = [y_min + idx * cell_m for idx in range(int((y_max - y_min) / cell_m) + 1)]
        if not x_values or not y_values:
            return None

        @lru_cache(maxsize=None)
        def point_required_altitude(ix: int, iy: int) -> float:
            return self._xy_point_required_altitude_m(
                point_xy=(x_values[ix], y_values[iy]),
                building_index=building_index,
                request=request,
                consider_buildings=True,
            )

        @lru_cache(maxsize=None)
        def edge_required_altitude(ix1: int, iy1: int, ix2: int, iy2: int) -> float:
            return self._xy_segment_required_altitude_m(
                start_xy=(x_values[ix1], y_values[iy1]),
                end_xy=(x_values[ix2], y_values[iy2]),
                building_index=building_index,
                request=request,
                consider_buildings=True,
            )

        @lru_cache(maxsize=None)
        def node_is_clear(ix: int, iy: int) -> bool:
            return point_required_altitude(ix, iy) <= request.max_altitude_m + 1e-6

        @lru_cache(maxsize=None)
        def edge_is_clear(ix1: int, iy1: int, ix2: int, iy2: int) -> bool:
            return edge_required_altitude(ix1, iy1, ix2, iy2) <= request.max_altitude_m + 1e-6

        @lru_cache(maxsize=None)
        def node_building_clearance(ix: int, iy: int) -> float:
            point = (x_values[ix], y_values[iy])
            radius = max(cell_m * 4.0, 120.0)
            nearby = building_index.query_bbox(point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius)
            if not nearby:
                return radius
            best = radius
            for building in nearby:
                if point_in_poly(point, building.points_xy):
                    return 0.0
                best = min(best, self._point_to_poly_distance(point=point, poly=building.points_xy))
            return best

        def segment_is_feasible(start: tuple[float, float], end: tuple[float, float], _altitude_m: float) -> bool:
            return (
                self._xy_segment_required_altitude_m(
                    start_xy=start,
                    end_xy=end,
                    building_index=building_index,
                    request=request,
                    consider_buildings=True,
                )
                <= request.max_altitude_m + 1e-6
            )

        def nearest_visible_nodes(point_xy: tuple[float, float], limit: int) -> list[tuple[int, int]]:
            scored: list[tuple[float, tuple[int, int]]] = []
            for ix, x_m in enumerate(x_values):
                for iy, y_m in enumerate(y_values):
                    if not node_is_clear(ix, iy):
                        continue
                    candidate_xy = (x_m, y_m)
                    scored.append((self._xy_distance(point_xy, candidate_xy), (ix, iy)))
            scored.sort(key=lambda item: item[0])
            visible: list[tuple[int, int]] = []
            for _score, node in scored[: max(limit * 20, 80)]:
                candidate_xy = (x_values[node[0]], y_values[node[1]])
                if segment_is_feasible(point_xy, candidate_xy, altitude_m):
                    visible.append(node)
                    if len(visible) >= limit:
                        break
            return visible

        def nearest_clear_point(point_xy: tuple[float, float]) -> tuple[float, float] | None:
            scored: list[tuple[float, tuple[float, float]]] = []
            for ix, x_m in enumerate(x_values):
                for iy, y_m in enumerate(y_values):
                    if not node_is_clear(ix, iy):
                        continue
                    candidate_xy = (x_m, y_m)
                    scored.append((self._xy_distance(point_xy, candidate_xy), candidate_xy))
            if not scored:
                return None
            scored.sort(key=lambda item: item[0])
            return scored[0][1]

        effective_start_xy = (
            start_xy
            if self._xy_point_required_altitude_m(
                point_xy=start_xy,
                building_index=building_index,
                request=request,
                consider_buildings=True,
            )
            <= request.max_altitude_m + 1e-6
            else nearest_clear_point(start_xy)
        )
        effective_end_xy = (
            end_xy
            if self._xy_point_required_altitude_m(
                point_xy=end_xy,
                building_index=building_index,
                request=request,
                consider_buildings=True,
            )
            <= request.max_altitude_m + 1e-6
            else nearest_clear_point(end_xy)
        )
        if effective_start_xy is None or effective_end_xy is None:
            return None

        start_nodes = nearest_visible_nodes(effective_start_xy, 10)
        end_nodes = nearest_visible_nodes(effective_end_xy, 10)
        if not start_nodes or not end_nodes:
            return None
        end_set = set(end_nodes)

        def heuristic_to_end(node: tuple[int, int]) -> float:
            node_xy = (x_values[node[0]], y_values[node[1]])
            return min(self._xy_distance(node_xy, (x_values[end[0]], y_values[end[1]])) for end in end_nodes)

        open_set: list[tuple[float, float, tuple[int, int]]] = []
        came_from: dict[tuple[int, int], tuple[int, int]] = {}
        best_cost: dict[tuple[int, int], float] = {}
        used_cells = set().union(*used_signatures) if used_signatures else set()
        for node in start_nodes:
            node_xy = (x_values[node[0]], y_values[node[1]])
            access_cost = self._xy_distance(effective_start_xy, node_xy)
            best_cost[node] = access_cost
            heapq.heappush(open_set, (access_cost + heuristic_to_end(node), access_cost, node))

        visited: set[tuple[int, int]] = set()
        moves = [
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
            (-1, -1),
            (-1, 1),
            (1, -1),
            (1, 1),
        ]
        strategy_params = {
            "fastest": {
                "line": 0.10,
                "clearance": 0.10,
                "overflight": 0.20,
                "turn": 0.06,
                "reuse": 0.60,
                "offset": 0.10,
                "preferred_side": 0.0,
            },
            "safest": {
                "line": 0.02,
                "clearance": 2.80,
                "overflight": 2.20,
                "turn": 0.14,
                "reuse": 2.40,
                "offset": 0.18,
                "preferred_side": 2.4,
            },
            "energy_saving": {
                "line": 0.22,
                "clearance": 0.24,
                "overflight": 1.70,
                "turn": 1.10,
                "reuse": 1.25,
                "offset": 0.16,
                "preferred_side": -0.8,
            },
            "balanced_stable": {
                "line": 0.08,
                "clearance": 1.20,
                "overflight": 1.10,
                "turn": 0.32,
                "reuse": 1.80,
                "offset": 0.16,
                "preferred_side": -1.8,
            },
            "most_accessible": {
                "line": 0.03,
                "clearance": 1.85,
                "overflight": 1.35,
                "turn": 0.22,
                "reuse": 3.20,
                "offset": 0.20,
                "preferred_side": 3.2,
            },
        }.get(profile.strategy, {})
        corridor_dx = effective_end_xy[0] - effective_start_xy[0]
        corridor_dy = effective_end_xy[1] - effective_start_xy[1]
        corridor_len = max(math.hypot(corridor_dx, corridor_dy), 1e-6)
        corridor_unit = (corridor_dx / corridor_len, corridor_dy / corridor_len)
        preferred_side_m = float(strategy_params.get("preferred_side", 0.0)) * cell_m

        def signed_line_offset(point_xy: tuple[float, float]) -> float:
            rel_x = point_xy[0] - effective_start_xy[0]
            rel_y = point_xy[1] - effective_start_xy[1]
            return rel_x * corridor_unit[1] - rel_y * corridor_unit[0]

        def line_offset(point_xy: tuple[float, float]) -> float:
            return self._point_to_segment_distance(point=point_xy, start=effective_start_xy, end=effective_end_xy)

        found: tuple[int, int] | None = None
        while open_set:
            _priority, current_cost, current = heapq.heappop(open_set)
            if current in visited:
                continue
            visited.add(current)
            if current in end_set:
                found = current
                break
            for dx, dy in moves:
                nxt = (current[0] + dx, current[1] + dy)
                if nxt[0] < 0 or nxt[0] >= len(x_values) or nxt[1] < 0 or nxt[1] >= len(y_values):
                    continue
                if not node_is_clear(*nxt) or not edge_is_clear(current[0], current[1], nxt[0], nxt[1]):
                    continue
                current_xy = (x_values[current[0]], y_values[current[1]])
                next_xy = (x_values[nxt[0]], y_values[nxt[1]])
                step_cost = self._xy_distance(current_xy, next_xy)
                required_altitude_m = edge_required_altitude(current[0], current[1], nxt[0], nxt[1])
                overflight_m = max(0.0, required_altitude_m - altitude_m)
                clearance_m = min(node_building_clearance(*current), node_building_clearance(*nxt))
                clearance_pressure = max(0.0, 1.0 - clearance_m / max(cell_m * 2.2, 1.0))
                line_pressure = line_offset(next_xy) / max(cell_m * 3.0, 1.0)
                side_pressure = abs(signed_line_offset(next_xy) - preferred_side_m) / max(cell_m * 4.0, 1.0)
                coarse_cell = (
                    int(round(next_xy[0] / max(request.cell_m, 1.0))),
                    int(round(next_xy[1] / max(request.cell_m, 1.0))),
                )
                reuse_penalty = (
                    profile.reuse_penalty_s * float(strategy_params.get("reuse", 1.0))
                    if coarse_cell in used_cells
                    else 0.0
                )
                turn_cost = 0.0
                prev = came_from.get(current)
                if prev is not None:
                    turn_cost = step_cost * self._xy_turn_penalty(
                        (x_values[prev[0]], y_values[prev[1]]),
                        current_xy,
                        next_xy,
                    )
                new_cost = (
                    current_cost
                    + step_cost
                    + reuse_penalty
                    + step_cost * line_pressure * float(strategy_params.get("line", 0.1))
                    + step_cost * clearance_pressure * float(strategy_params.get("clearance", 0.2))
                    + overflight_m * float(strategy_params.get("overflight", 1.0))
                    + turn_cost * float(strategy_params.get("turn", 0.2))
                    + step_cost * side_pressure * float(strategy_params.get("offset", 0.1))
                )
                if new_cost >= best_cost.get(nxt, float("inf")):
                    continue
                best_cost[nxt] = new_cost
                came_from[nxt] = current
                heapq.heappush(open_set, (new_cost + heuristic_to_end(nxt), new_cost, nxt))

        if found is None:
            return None
        node_path = [found]
        while node_path[-1] in came_from:
            node_path.append(came_from[node_path[-1]])
        node_path.reverse()
        path_xy = [effective_start_xy]
        for ix, iy in node_path:
            point_xy = (x_values[ix], y_values[iy])
            if self._xy_distance(path_xy[-1], point_xy) > 1e-6:
                path_xy.append(point_xy)
        if self._xy_distance(path_xy[-1], effective_end_xy) > 1e-6:
            path_xy.append(effective_end_xy)
        if any(not segment_is_feasible(path_xy[idx - 1], path_xy[idx], altitude_m) for idx in range(1, len(path_xy))):
            return None
        simplified_path = self._simplify_xy_path(
            path_xy,
            building_index=building_index,
            strict_building_avoidance=profile.strategy in {"safest", "most_accessible"},
            xy_segment_clear=segment_is_feasible,
            altitude_m=altitude_m,
            request=request,
            consider_buildings=True,
        )
        if all(
            segment_is_feasible(simplified_path[idx - 1], simplified_path[idx], altitude_m)
            for idx in range(1, len(simplified_path))
        ):
            return simplified_path
        return path_xy

    def _xy_astar_path(
        self,
        *,
        start: tuple[int, int],
        goal: tuple[int, int],
        altitude_idx: int,
        x_values: list[float],
        y_values: list[float],
        altitude_layers_m: list[float],
        blocked_height: Any,
        building_index: BuildingIndex,
        node_weather: Any,
        edge_weather: Any,
        request: PlannerRequest,
        consider_buildings: bool,
        consider_weather: bool,
    ) -> list[tuple[int, int]] | None:
        start_node = (start[0], start[1], altitude_idx)
        goal_node = (goal[0], goal[1], altitude_idx)
        open_set: list[tuple[float, float, tuple[int, int]]] = [
            (self._xy_distance((x_values[start[0]], y_values[start[1]]), (x_values[goal[0]], y_values[goal[1]])), 0.0, start)
        ]
        came_from: dict[tuple[int, int], tuple[int, int]] = {}
        best_cost = {start: 0.0}
        visited: set[tuple[int, int]] = set()
        while open_set:
            _priority, current_cost, current = heapq.heappop(open_set)
            if current in visited:
                continue
            visited.add(current)
            if current == goal:
                path = [current]
                while path[-1] in came_from:
                    path.append(came_from[path[-1]])
                path.reverse()
                return path
            current_node = (current[0], current[1], altitude_idx)
            for dx, dy, _dz in self.CONNECTIVITY_MOVES:
                nxt = (current[0] + dx, current[1] + dy)
                if nxt[0] < 0 or nxt[0] >= len(x_values) or nxt[1] < 0 or nxt[1] >= len(y_values):
                    continue
                nxt_node = (nxt[0], nxt[1], altitude_idx)
                if not self._edge_is_clear(
                    current=current_node,
                    nxt=nxt_node,
                    x_values=x_values,
                    y_values=y_values,
                    altitude_layers_m=altitude_layers_m,
                    blocked_height=blocked_height,
                    building_index=building_index,
                    request=request,
                    consider_buildings=consider_buildings,
                ):
                    continue
                step_distance = self._xy_distance(
                    (x_values[current[0]], y_values[current[1]]),
                    (x_values[nxt[0]], y_values[nxt[1]]),
                )
                weather_blocked, weather_pressure = edge_weather(*current_node, *nxt_node)
                weather_blocked_penalty = 0.0
                if consider_weather and weather_blocked:
                    if request.planning_mode != self.PLANNING_MODE_COMBINED:
                        continue
                    weather_pressure = max(weather_pressure, 1.25)
                    weather_blocked_penalty = step_distance * 4.5
                if not consider_weather:
                    weather_pressure = 0.0
                if consider_weather:
                    sample_segment = self._segment_stats(
                        current=current_node,
                        nxt=nxt_node,
                        x_values=x_values,
                        y_values=y_values,
                        altitude_layers_m=altitude_layers_m,
                        node_weather=node_weather,
                        xy_urban_density=lambda _ix, _iy: 0.0,
                        node_connectivity=lambda _ix, _iy, _iz: 1.0,
                        node_reachability=lambda _ix, _iy, _iz: 1.0,
                        consider_weather=True,
                    )
                    visual_risk = self._edge_visual_weather_risk_score(
                        current=current_node,
                        nxt=nxt_node,
                        x_values=x_values,
                        y_values=y_values,
                        altitude_layers_m=altitude_layers_m,
                        node_weather=node_weather,
                    )
                    red_zone_excess = max(0.0, visual_risk - 0.46)
                    severe_zone_excess = max(0.0, visual_risk - 0.72)
                    weather_pressure += red_zone_excess * 2.8 + severe_zone_excess * 4.6
                    if self._weather_segment_high_risk(sample_segment):
                        weather_pressure += 1.35
                new_cost = current_cost + step_distance * (1.0 + weather_pressure * 0.75) + weather_blocked_penalty
                if new_cost >= best_cost.get(nxt, float("inf")):
                    continue
                best_cost[nxt] = new_cost
                came_from[nxt] = current
                heuristic = self._xy_distance(
                    (x_values[nxt[0]], y_values[nxt[1]]),
                    (x_values[goal[0]], y_values[goal[1]]),
                )
                heapq.heappush(open_set, (new_cost + heuristic, new_cost, nxt))
        return None

    def _nearest_visible_xy_nodes(
        self,
        *,
        point_xy: tuple[float, float],
        altitude_idx: int,
        x_values: list[float],
        y_values: list[float],
        altitude_layers_m: list[float],
        blocked_height: Any,
        building_index: BuildingIndex,
        xy_segment_clear: Any,
        request: PlannerRequest,
        consider_buildings: bool,
        limit: int,
    ) -> list[tuple[int, int]]:
        scored: list[tuple[float, tuple[int, int]]] = []
        altitude_m = altitude_layers_m[altitude_idx]
        for ix, x_m in enumerate(x_values):
            for iy, y_m in enumerate(y_values):
                node = (ix, iy, altitude_idx)
                if not self._edge_is_clear(
                    current=node,
                    nxt=node,
                    x_values=x_values,
                    y_values=y_values,
                    altitude_layers_m=altitude_layers_m,
                    blocked_height=blocked_height,
                    building_index=building_index,
                    request=request,
                    consider_buildings=consider_buildings,
                ):
                    continue
                node_xy = (x_m, y_m)
                if not xy_segment_clear(point_xy, node_xy, altitude_m):
                    continue
                score = self._xy_distance(point_xy, node_xy)
                scored.append((score, (ix, iy)))
        scored.sort(key=lambda item: item[0])
        return [node for _score, node in scored[: max(1, limit)]]

    def _road_graph_path(
        self,
        *,
        start_xy: tuple[float, float],
        end_xy: tuple[float, float],
        profile: CostProfile,
        altitude_m: float,
        building_index: BuildingIndex,
        xy_segment_clear: Any,
        request: PlannerRequest,
        used_edge_sets: list[set[tuple[int, int]]],
    ) -> tuple[list[tuple[float, float]], set[tuple[int, int]]] | None:
        if self.road_graph is None:
            return None
        start_candidates = self._nearest_visible_road_node_indices(
            point_xy=start_xy,
            altitude_m=altitude_m,
            xy_segment_clear=xy_segment_clear,
            limit=12,
        )
        end_candidates = self._nearest_visible_road_node_indices(
            point_xy=end_xy,
            altitude_m=altitude_m,
            xy_segment_clear=xy_segment_clear,
            limit=12,
        )
        if not start_candidates or not end_candidates:
            return None
        end_candidate_set = set(end_candidates)

        def heuristic_to_end(node_idx: int) -> float:
            node_xy = self.road_graph.nodes_xy[node_idx]
            return min(self._xy_distance(node_xy, self.road_graph.nodes_xy[end_idx]) for end_idx in end_candidates)

        open_set: list[tuple[float, float, int]] = []
        best_cost: dict[int, float] = {}
        for start_idx in start_candidates:
            access_cost = self._xy_distance(start_xy, self.road_graph.nodes_xy[start_idx])
            best_cost[start_idx] = min(best_cost.get(start_idx, float("inf")), access_cost)
            heapq.heappush(open_set, (access_cost + heuristic_to_end(start_idx), access_cost, start_idx))
        came_from: dict[int, int] = {}
        visited: set[int] = set()
        while open_set:
            _priority, current_cost, current = heapq.heappop(open_set)
            if current in visited:
                continue
            visited.add(current)
            if current in end_candidate_set:
                node_path = [current]
                while node_path[-1] in came_from:
                    node_path.append(came_from[node_path[-1]])
                node_path.reverse()
                edge_signature = {
                    tuple(sorted((node_path[idx - 1], node_path[idx])))
                    for idx in range(1, len(node_path))
                }
                path_xy = [start_xy] + [self.road_graph.nodes_xy[idx] for idx in node_path] + [end_xy]
                if any(
                    not xy_segment_clear(path_xy[idx - 1], path_xy[idx], altitude_m)
                    for idx in range(1, len(path_xy))
                ):
                    continue
                return (
                    self._simplify_xy_path(
                        path_xy,
                        building_index=building_index,
                        strict_building_avoidance=self._strict_building_avoidance(request.planning_mode),
                        xy_segment_clear=xy_segment_clear,
                        altitude_m=altitude_m,
                        request=request,
                        consider_buildings=self._consider_buildings(request.planning_mode),
                    ),
                    edge_signature,
                )
            for nxt, weight in self.road_graph.edges[current]:
                edge_key = tuple(sorted((current, nxt)))
                if not xy_segment_clear(
                    self.road_graph.nodes_xy[current],
                    self.road_graph.nodes_xy[nxt],
                    altitude_m,
                ):
                    continue
                edge_cost = weight
                for used_edges in used_edge_sets:
                    if edge_key in used_edges:
                        edge_cost += max(profile.reuse_penalty_s * 6.0, 80.0)
                        break
                new_cost = current_cost + edge_cost
                if new_cost >= best_cost.get(nxt, float("inf")):
                    continue
                best_cost[nxt] = new_cost
                came_from[nxt] = current
                heuristic = heuristic_to_end(nxt)
                heapq.heappush(open_set, (new_cost + heuristic, new_cost, nxt))
        return None

    def _building_footprint_detour_path(
        self,
        *,
        start_xy: tuple[float, float],
        end_xy: tuple[float, float],
        profile: CostProfile,
        building_index: BuildingIndex,
        request: PlannerRequest,
        used_signatures: list[set[tuple[int, int]]],
    ) -> list[tuple[float, float]] | None:
        if request.planning_mode not in {self.PLANNING_MODE_COMBINED, self.PLANNING_MODE_BUILDING_ONLY}:
            return None
        west_south = latlon_to_meters(self.origin, float(self.bbox["south"]), float(self.bbox["west"]))
        east_north = latlon_to_meters(self.origin, float(self.bbox["north"]), float(self.bbox["east"]))
        route_distance_m = self._xy_distance(start_xy, end_xy)
        attempts = [
            (max(22.0, min(36.0, request.cell_m * 0.16)), 0.50, 80000),
            (max(24.0, min(46.0, request.cell_m * 0.22)), 1.00, 90000),
            (16.0, 0.62, 110000),
            (14.0, 1.00, 130000),
        ]

        for cell_m, bbox_fraction, max_nodes in attempts:
            if bbox_fraction >= 0.99:
                x_min = west_south[0] - cell_m
                x_max = east_north[0] + cell_m
                y_min = west_south[1] - cell_m
                y_max = east_north[1] + cell_m
            else:
                corridor_margin = max(700.0, route_distance_m * bbox_fraction)
                x_min = max(west_south[0] - cell_m, min(start_xy[0], end_xy[0]) - corridor_margin)
                x_max = min(east_north[0] + cell_m, max(start_xy[0], end_xy[0]) + corridor_margin)
                y_min = max(west_south[1] - cell_m, min(start_xy[1], end_xy[1]) - corridor_margin)
                y_max = min(east_north[1] + cell_m, max(start_xy[1], end_xy[1]) + corridor_margin)
            estimated_nodes = max(1, int((x_max - x_min) / cell_m) + 1) * max(1, int((y_max - y_min) / cell_m) + 1)
            if estimated_nodes > max_nodes:
                scale = math.sqrt(estimated_nodes / max_nodes)
                cell_m *= max(1.0, scale)
            x_values = [x_min + idx * cell_m for idx in range(int((x_max - x_min) / cell_m) + 1)]
            y_values = [y_min + idx * cell_m for idx in range(int((y_max - y_min) / cell_m) + 1)]
            if len(x_values) < 2 or len(y_values) < 2:
                continue
            local_building_index = BuildingIndex(building_index.buildings, bucket_m=max(60.0, cell_m * 4.0))
            grid_cache_key = (
                round(x_min, 1),
                round(y_min, 1),
                round(cell_m, 2),
                len(x_values),
                len(y_values),
                round(request.max_altitude_m, 1),
                round(request.safety_clearance_m, 1),
                len(building_index.buildings),
            )
            node_clear_cache = self._building_detour_node_clear_cache.setdefault(grid_cache_key, {})
            edge_clear_cache = self._building_detour_edge_clear_cache.setdefault(grid_cache_key, {})
            clearance_cache = self._building_detour_clearance_cache.setdefault(grid_cache_key, {})

            @lru_cache(maxsize=None)
            def node_is_clear(ix: int, iy: int) -> bool:
                cache_key = (ix, iy)
                cached = node_clear_cache.get(cache_key)
                if cached is not None:
                    return cached
                clear = (
                    self._xy_point_required_altitude_m(
                        point_xy=(x_values[ix], y_values[iy]),
                        building_index=local_building_index,
                        request=request,
                        consider_buildings=True,
                    )
                    <= request.max_altitude_m + 1e-6
                )
                node_clear_cache[cache_key] = clear
                return clear

            @lru_cache(maxsize=None)
            def edge_is_clear(ix1: int, iy1: int, ix2: int, iy2: int) -> bool:
                if (ix2, iy2) < (ix1, iy1):
                    ix1, iy1, ix2, iy2 = ix2, iy2, ix1, iy1
                cache_key = (ix1, iy1, ix2, iy2)
                cached = edge_clear_cache.get(cache_key)
                if cached is not None:
                    return cached
                clear = (
                    self._xy_segment_required_altitude_m(
                        start_xy=(x_values[ix1], y_values[iy1]),
                        end_xy=(x_values[ix2], y_values[iy2]),
                        building_index=local_building_index,
                        request=request,
                        consider_buildings=True,
                    )
                    <= request.max_altitude_m + 1e-6
                )
                edge_clear_cache[cache_key] = clear
                return clear

            @lru_cache(maxsize=None)
            def node_building_clearance(ix: int, iy: int) -> float:
                cache_key = (ix, iy)
                cached = clearance_cache.get(cache_key)
                if cached is not None:
                    return cached
                point_xy = (x_values[ix], y_values[iy])
                radius = max(cell_m * 5.0, 120.0)
                nearby = local_building_index.query_bbox(
                    point_xy[0] - radius,
                    point_xy[1] - radius,
                    point_xy[0] + radius,
                    point_xy[1] + radius,
                )
                if not nearby:
                    clearance_cache[cache_key] = radius
                    return radius
                best = radius
                for building in nearby:
                    left, bottom, right, top = building.bbox
                    dx = max(0.0, max(left - point_xy[0], point_xy[0] - right))
                    dy = max(0.0, max(bottom - point_xy[1], point_xy[1] - top))
                    best = min(best, math.hypot(dx, dy))
                    if best <= 1e-6:
                        break
                clearance_cache[cache_key] = best
                return best

            def point_is_clear(point_xy: tuple[float, float]) -> bool:
                return (
                    self._xy_point_required_altitude_m(
                        point_xy=point_xy,
                        building_index=local_building_index,
                        request=request,
                        consider_buildings=True,
                    )
                    <= request.max_altitude_m + 1e-6
                )

            def segment_is_clear(a: tuple[float, float], b: tuple[float, float]) -> bool:
                return (
                    self._xy_segment_required_altitude_m(
                        start_xy=a,
                        end_xy=b,
                        building_index=local_building_index,
                        request=request,
                        consider_buildings=True,
                    )
                    <= request.max_altitude_m + 1e-6
                )

            def nearest_grid_index(point_xy: tuple[float, float]) -> tuple[int, int]:
                return (
                    self._nearest_axis_index(x_values, point_xy[0]),
                    self._nearest_axis_index(y_values, point_xy[1]),
                )

            def ring_nodes(center: tuple[int, int], radius: int):
                ix0, iy0 = center
                for ix in range(max(0, ix0 - radius), min(len(x_values), ix0 + radius + 1)):
                    for iy in range(max(0, iy0 - radius), min(len(y_values), iy0 + radius + 1)):
                        if max(abs(ix - ix0), abs(iy - iy0)) == radius:
                            yield ix, iy

            def nearest_clear_point(point_xy: tuple[float, float]) -> tuple[float, float] | None:
                center = nearest_grid_index(point_xy)
                max_radius = max(len(x_values), len(y_values))
                best_distance = float("inf")
                best: tuple[float, float] | None = None
                for radius in range(max_radius):
                    for ix, iy in ring_nodes(center, radius):
                        if not node_is_clear(ix, iy):
                            continue
                        candidate = (x_values[ix], y_values[iy])
                        distance = self._xy_distance(point_xy, candidate)
                        if distance < best_distance:
                            best_distance = distance
                            best = candidate
                    if best is not None:
                        return best
                return best

            effective_start_xy = start_xy if point_is_clear(start_xy) else nearest_clear_point(start_xy)
            effective_end_xy = end_xy if point_is_clear(end_xy) else nearest_clear_point(end_xy)
            if effective_start_xy is None or effective_end_xy is None:
                continue

            def nearest_nodes(point_xy: tuple[float, float], limit: int) -> list[tuple[int, int]]:
                center = nearest_grid_index(point_xy)
                max_radius = max(len(x_values), len(y_values))
                scored: list[tuple[float, tuple[int, int]]] = []
                fallback: list[tuple[float, tuple[int, int]]] = []
                for radius in range(max_radius):
                    for ix, iy in ring_nodes(center, radius):
                        if not node_is_clear(ix, iy):
                            continue
                        candidate = (x_values[ix], y_values[iy])
                        distance = self._xy_distance(point_xy, candidate)
                        if segment_is_clear(point_xy, candidate):
                            scored.append((distance, (ix, iy)))
                        elif radius <= 2:
                            fallback.append((distance, (ix, iy)))
                    if len(scored) >= limit and radius >= 1:
                        break
                    if radius >= 24 and scored:
                        break
                scored.sort(key=lambda item: item[0])
                if scored:
                    return [node for _score, node in scored[:limit]]
                fallback.sort(key=lambda item: item[0])
                return [node for _score, node in fallback[:limit]]

            start_nodes = nearest_nodes(effective_start_xy, 12)
            end_nodes = nearest_nodes(effective_end_xy, 12)
            if not start_nodes or not end_nodes:
                continue
            used_cells = set().union(*used_signatures) if used_signatures else set()
            moves = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
            projection_cache_key = (
                round(start_xy[0], 1),
                round(start_xy[1], 1),
                round(end_xy[0], 1),
                round(end_xy[1], 1),
                round(x_min, 1),
                round(y_min, 1),
                round(cell_m, 2),
                len(x_values),
                len(y_values),
                round(request.max_altitude_m, 1),
                round(request.safety_clearance_m, 1),
            )

            def search_path(
                route_start_xy: tuple[float, float],
                route_end_xy: tuple[float, float],
                search_start_nodes: list[tuple[int, int]],
                search_end_nodes: list[tuple[int, int]],
            ) -> list[tuple[int, int]] | None:
                end_set = set(search_end_nodes)
                corridor_dx = route_end_xy[0] - route_start_xy[0]
                corridor_dy = route_end_xy[1] - route_start_xy[1]
                corridor_len = max(math.hypot(corridor_dx, corridor_dy), 1e-6)
                corridor_unit = (corridor_dx / corridor_len, corridor_dy / corridor_len)
                preferred_side = {
                    "fastest": 0.0,
                    "safest": 3.0,
                    "energy_saving": -1.0,
                    "balanced_stable": -2.2,
                    "most_accessible": 2.2,
                }.get(profile.strategy, 0.0) * cell_m

                def heuristic(node: tuple[int, int]) -> float:
                    node_xy = (x_values[node[0]], y_values[node[1]])
                    return min(self._xy_distance(node_xy, (x_values[end[0]], y_values[end[1]])) for end in search_end_nodes)

                def line_offset(point_xy: tuple[float, float]) -> float:
                    return self._point_to_segment_distance(point=point_xy, start=route_start_xy, end=route_end_xy)

                def signed_offset(point_xy: tuple[float, float]) -> float:
                    rel_x = point_xy[0] - route_start_xy[0]
                    rel_y = point_xy[1] - route_start_xy[1]
                    return rel_x * corridor_unit[1] - rel_y * corridor_unit[0]

                def combined_weather_penalty(a: tuple[float, float], b: tuple[float, float], step_m: float) -> float:
                    if request.planning_mode != self.PLANNING_MODE_COMBINED:
                        return 0.0
                    sample_altitude_m = max(
                        request.min_altitude_m,
                        min(
                            request.max_altitude_m,
                            max(request.start_altitude_m, request.end_altitude_m, profile.preferred_altitude_m),
                        ),
                    )
                    samples = []
                    for ratio in (0.25, 0.50, 0.75):
                        x_m = a[0] + (b[0] - a[0]) * ratio
                        y_m = a[1] + (b[1] - a[1]) * ratio
                        weather = self.weather_field.interpolate(x_m, y_m, sample_altitude_m)
                        samples.append(
                            (
                                self._visual_weather_risk_score(weather=weather, altitude_m=sample_altitude_m),
                                weather,
                            )
                        )
                    max_risk = max((risk for risk, _weather in samples), default=0.0)
                    max_precipitation = max((weather.precipitation_mm for _risk, weather in samples), default=0.0)
                    max_turbulence = max((weather.turbulence_index for _risk, weather in samples), default=0.0)
                    max_wind = max((weather.wind_speed_mps for _risk, weather in samples), default=0.0)
                    red_excess = max(0.0, max_risk - 0.46)
                    severe_excess = max(0.0, max_risk - 0.72)
                    strategy_factor = {
                        "fastest": 0.85,
                        "safest": 9.50,
                        "energy_saving": 1.80,
                        "balanced_stable": 5.80,
                        "most_accessible": 3.20,
                    }.get(profile.strategy, 2.0)
                    weather_pressure = (
                        max_risk * 0.80
                        + red_excess * 7.50
                        + severe_excess * 16.0
                        + max(0.0, max_precipitation - 1.20) * 0.85
                        + max(0.0, max_turbulence - 0.34) * 4.0
                        + max(0.0, max_wind - 7.0) * 0.22
                    )
                    return step_m * strategy_factor * weather_pressure

                open_set: list[tuple[float, float, tuple[int, int]]] = []
                best_cost: dict[tuple[int, int], float] = {}
                came_from: dict[tuple[int, int], tuple[int, int]] = {}
                for node in search_start_nodes:
                    node_xy = (x_values[node[0]], y_values[node[1]])
                    access_cost = self._xy_distance(route_start_xy, node_xy)
                    best_cost[node] = min(best_cost.get(node, float("inf")), access_cost)
                    heapq.heappush(open_set, (access_cost + heuristic(node), access_cost, node))
                found: tuple[int, int] | None = None
                visited: set[tuple[int, int]] = set()
                while open_set:
                    _priority, current_cost, current = heapq.heappop(open_set)
                    if current in visited:
                        continue
                    visited.add(current)
                    if current in end_set:
                        found = current
                        break
                    current_xy = (x_values[current[0]], y_values[current[1]])
                    for dx, dy in moves:
                        nxt = (current[0] + dx, current[1] + dy)
                        if nxt[0] < 0 or nxt[0] >= len(x_values) or nxt[1] < 0 or nxt[1] >= len(y_values):
                            continue
                        if not node_is_clear(*nxt) or not edge_is_clear(current[0], current[1], nxt[0], nxt[1]):
                            continue
                        next_xy = (x_values[nxt[0]], y_values[nxt[1]])
                        step = self._xy_distance(current_xy, next_xy)
                        coarse_cell = (
                            int(round(next_xy[0] / max(request.cell_m, 1.0))),
                            int(round(next_xy[1] / max(request.cell_m, 1.0))),
                        )
                        reuse_penalty = profile.reuse_penalty_s * 3.0 if coarse_cell in used_cells else 0.0
                        progress = (next_xy[0] - current_xy[0]) * corridor_unit[0] + (next_xy[1] - current_xy[1]) * corridor_unit[1]
                        reverse_penalty = abs(min(0.0, progress)) * 0.8
                        deviation_penalty = line_offset(next_xy) * profile.line_deviation_factor * 0.20
                        side_penalty = abs(signed_offset(next_xy) - preferred_side) * 0.05
                        clearance_m = min(node_building_clearance(*current), node_building_clearance(*nxt))
                        clearance_pressure = max(0.0, 1.0 - clearance_m / max(cell_m * 4.0, 1.0))
                        clearance_penalty = {
                            "fastest": 0.06,
                            "safest": 0.95,
                            "energy_saving": 0.18,
                            "balanced_stable": 0.45,
                            "most_accessible": 0.72,
                        }.get(profile.strategy, 0.2) * step * clearance_pressure
                        weather_penalty = combined_weather_penalty(current_xy, next_xy, step)
                        turn_penalty = 0.0
                        prev = came_from.get(current)
                        if prev is not None:
                            turn_penalty = step * self._xy_turn_penalty((x_values[prev[0]], y_values[prev[1]]), current_xy, next_xy) * profile.turn_penalty_factor
                        new_cost = current_cost + step + reuse_penalty + reverse_penalty + deviation_penalty + side_penalty + clearance_penalty + weather_penalty + turn_penalty
                        if new_cost >= best_cost.get(nxt, float("inf")):
                            continue
                        best_cost[nxt] = new_cost
                        came_from[nxt] = current
                        heapq.heappush(open_set, (new_cost + heuristic(nxt), new_cost, nxt))
                if found is None:
                    return None
                node_path = [found]
                while node_path[-1] in came_from:
                    node_path.append(came_from[node_path[-1]])
                node_path.reverse()
                return node_path

            def projected_component_route() -> tuple[tuple[float, float], tuple[float, float], list[tuple[int, int]]] | None:
                missing = object()
                cached_projection = self._building_detour_projection_cache.get(projection_cache_key, missing)
                if cached_projection is not missing:
                    if cached_projection is None:
                        return None
                    route_start_xy, route_end_xy, start_node, end_node = cached_projection
                    cached_path = search_path(route_start_xy, route_end_xy, [start_node], [end_node])
                    if cached_path is None:
                        return None
                    return route_start_xy, route_end_xy, cached_path

                assigned: set[tuple[int, int]] = set()
                best_choice: tuple[float, tuple[float, float], tuple[float, float], tuple[int, int], tuple[int, int]] | None = None
                for ix in range(len(x_values)):
                    for iy in range(len(y_values)):
                        seed = (ix, iy)
                        if seed in assigned or not node_is_clear(ix, iy):
                            continue
                        component: list[tuple[int, int]] = []
                        queue = [seed]
                        assigned.add(seed)
                        while queue:
                            current = queue.pop()
                            component.append(current)
                            for dx, dy in moves:
                                nxt = (current[0] + dx, current[1] + dy)
                                if nxt[0] < 0 or nxt[0] >= len(x_values) or nxt[1] < 0 or nxt[1] >= len(y_values):
                                    continue
                                if nxt in assigned or not node_is_clear(*nxt):
                                    continue
                                if not edge_is_clear(current[0], current[1], nxt[0], nxt[1]):
                                    continue
                                assigned.add(nxt)
                                queue.append(nxt)
                        if len(component) < 8:
                            continue
                        start_node = min(
                            component,
                            key=lambda node: (x_values[node[0]] - start_xy[0]) ** 2 + (y_values[node[1]] - start_xy[1]) ** 2,
                        )
                        end_node = min(
                            component,
                            key=lambda node: (x_values[node[0]] - end_xy[0]) ** 2 + (y_values[node[1]] - end_xy[1]) ** 2,
                        )
                        start_node_xy = (x_values[start_node[0]], y_values[start_node[1]])
                        end_node_xy = (x_values[end_node[0]], y_values[end_node[1]])
                        start_gap_m = self._xy_distance(start_xy, start_node_xy)
                        end_gap_m = self._xy_distance(end_xy, end_node_xy)
                        if start_gap_m + end_gap_m > route_distance_m * 1.85 + 900.0:
                            continue
                        component_bonus = min(len(component), 5000) * 0.02
                        score = start_gap_m + end_gap_m + max(start_gap_m, end_gap_m) * 0.35 - component_bonus
                        if best_choice is None or score < best_choice[0]:
                            route_start_xy = start_xy if segment_is_clear(start_xy, start_node_xy) else start_node_xy
                            route_end_xy = end_xy if segment_is_clear(end_node_xy, end_xy) else end_node_xy
                            best_choice = (score, route_start_xy, route_end_xy, start_node, end_node)
                if best_choice is None:
                    self._building_detour_projection_cache[projection_cache_key] = None
                    return None
                _score, route_start_xy, route_end_xy, start_node, end_node = best_choice
                self._building_detour_projection_cache[projection_cache_key] = (route_start_xy, route_end_xy, start_node, end_node)
                node_path = search_path(route_start_xy, route_end_xy, [start_node], [end_node])
                if node_path is None:
                    return None
                return route_start_xy, route_end_xy, node_path

            node_path = search_path(effective_start_xy, effective_end_xy, start_nodes, end_nodes)
            if node_path is None:
                projected = projected_component_route()
                if projected is None:
                    continue
                effective_start_xy, effective_end_xy, node_path = projected
            path_xy = [effective_start_xy]
            for ix, iy in node_path:
                point_xy = (x_values[ix], y_values[iy])
                if self._xy_distance(path_xy[-1], point_xy) > 1e-6:
                    path_xy.append(point_xy)
            if self._xy_distance(path_xy[-1], effective_end_xy) > 1e-6:
                path_xy.append(effective_end_xy)
            if not all(segment_is_clear(path_xy[idx - 1], path_xy[idx]) for idx in range(1, len(path_xy))):
                continue
            simplified = self._simplify_xy_path(
                path_xy,
                building_index=local_building_index,
                strict_building_avoidance=True,
                xy_segment_clear=lambda a, b, _altitude_m: segment_is_clear(a, b),
                altitude_m=request.min_altitude_m,
                request=request,
                consider_buildings=True,
            )
            if all(segment_is_clear(simplified[idx - 1], simplified[idx]) for idx in range(1, len(simplified))):
                return simplified
            return path_xy
        return None

    def _nearest_visible_road_node_indices(
        self,
        *,
        point_xy: tuple[float, float],
        altitude_m: float,
        xy_segment_clear: Any,
        limit: int,
    ) -> list[int]:
        if self.road_graph is None or not self.road_graph.nodes_xy:
            return []
        scored = sorted(
            (self._xy_distance(point_xy, road_point_xy), idx)
            for idx, road_point_xy in enumerate(self.road_graph.nodes_xy)
        )
        visible: list[int] = []
        for _distance, idx in scored:
            if xy_segment_clear(point_xy, self.road_graph.nodes_xy[idx], altitude_m):
                visible.append(idx)
                if len(visible) >= limit:
                    break
        return visible

    def _trusted_road_corridor_path(
        self,
        *,
        start_xy: tuple[float, float],
        end_xy: tuple[float, float],
        profile: CostProfile,
        altitude_m: float,
        xy_segment_clear: Any,
        request: PlannerRequest,
        used_edge_sets: list[set[tuple[int, int]]],
    ) -> list[tuple[float, float]] | None:
        if self.road_graph is None or not self.road_graph.nodes_xy:
            return None

        def nearest_road_indices(point_xy: tuple[float, float], limit: int) -> list[int]:
            scored = sorted(
                (self._xy_distance(point_xy, road_point_xy), idx)
                for idx, road_point_xy in enumerate(self.road_graph.nodes_xy)
            )
            return [idx for _distance, idx in scored[:limit]]

        start_candidates = nearest_road_indices(start_xy, 16)
        end_candidates = nearest_road_indices(end_xy, 16)
        if not start_candidates or not end_candidates:
            return None
        end_set = set(end_candidates)

        def heuristic_to_end(node_idx: int) -> float:
            node_xy = self.road_graph.nodes_xy[node_idx]
            return min(self._xy_distance(node_xy, self.road_graph.nodes_xy[end_idx]) for end_idx in end_candidates)

        open_set: list[tuple[float, float, int]] = []
        came_from: dict[int, int] = {}
        best_cost: dict[int, float] = {}
        for start_idx in start_candidates:
            access_cost = self._xy_distance(start_xy, self.road_graph.nodes_xy[start_idx])
            best_cost[start_idx] = min(best_cost.get(start_idx, float("inf")), access_cost)
            heapq.heappush(open_set, (access_cost + heuristic_to_end(start_idx), access_cost, start_idx))

        visited: set[int] = set()
        found: int | None = None
        while open_set:
            _priority, current_cost, current = heapq.heappop(open_set)
            if current in visited:
                continue
            visited.add(current)
            if current in end_set:
                found = current
                break
            for nxt, weight in self.road_graph.edges[current]:
                edge_key = tuple(sorted((current, nxt)))
                if not xy_segment_clear(self.road_graph.nodes_xy[current], self.road_graph.nodes_xy[nxt], altitude_m):
                    continue
                edge_cost = weight
                for used_edges in used_edge_sets:
                    if edge_key in used_edges:
                        edge_cost += max(profile.reuse_penalty_s * 6.0, 80.0)
                        break
                new_cost = current_cost + edge_cost
                if new_cost >= best_cost.get(nxt, float("inf")):
                    continue
                best_cost[nxt] = new_cost
                came_from[nxt] = current
                heapq.heappush(open_set, (new_cost + heuristic_to_end(nxt), new_cost, nxt))

        if found is None:
            return None
        node_path = [found]
        while node_path[-1] in came_from:
            node_path.append(came_from[node_path[-1]])
        node_path.reverse()
        if not node_path:
            return None

        first_xy = self.road_graph.nodes_xy[node_path[0]]
        last_xy = self.road_graph.nodes_xy[node_path[-1]]
        path_xy: list[tuple[float, float]] = []
        if xy_segment_clear(start_xy, first_xy, altitude_m):
            path_xy.append(start_xy)
        path_xy.extend(self.road_graph.nodes_xy[idx] for idx in node_path)
        if xy_segment_clear(last_xy, end_xy, altitude_m):
            path_xy.append(end_xy)
        deduped: list[tuple[float, float]] = []
        for point_xy in path_xy:
            if not deduped or self._xy_distance(deduped[-1], point_xy) > 1e-6:
                deduped.append(point_xy)
        if len(deduped) < 2:
            return None
        return deduped

    @staticmethod
    def _fallback_profile_altitude_m(*, profile: CostProfile, request: PlannerRequest) -> float:
        if request.planning_mode == CityRoutePlanner.PLANNING_MODE_BUILDING_ONLY:
            return CityRoutePlanner._building_low_cruise_altitude_m(request)
        preferred_altitude_m = min(profile.preferred_altitude_m, request.max_altitude_m)
        return max(
            request.min_altitude_m,
            min(
                request.max_altitude_m,
                max(request.start_altitude_m, request.end_altitude_m, preferred_altitude_m),
            ),
        )

    def _with_request_endpoint_anchors(self, *, route: RouteCandidate, request: PlannerRequest) -> RouteCandidate:
        if request.planning_mode != self.PLANNING_MODE_COMBINED or not route.waypoints:
            return route

        def anchor(lat: float, lon: float, altitude_m: float, label: str) -> dict[str, float | str]:
            return {
                "lat": round(lat, 9),
                "lon": round(lon, 9),
                "altitude_m": round(altitude_m, 1),
                "label": label,
            }

        def horizontal_gap_m(point: dict[str, float | str], lat: float, lon: float) -> float:
            point_xy = latlon_to_meters(self.origin, float(point["lat"]), float(point["lon"]))
            target_xy = latlon_to_meters(self.origin, lat, lon)
            return self._xy_distance(point_xy, target_xy)

        def connector_distance_m(a: dict[str, float | str], b: dict[str, float | str]) -> float:
            a_xy = latlon_to_meters(self.origin, float(a["lat"]), float(a["lon"]))
            b_xy = latlon_to_meters(self.origin, float(b["lat"]), float(b["lon"]))
            horizontal_m = self._xy_distance(a_xy, b_xy)
            vertical_m = abs(float(a["altitude_m"]) - float(b["altitude_m"]))
            return math.hypot(horizontal_m, vertical_m)

        start_anchor = anchor(request.start_lat, request.start_lon, request.start_altitude_m, "起点")
        end_anchor = anchor(request.end_lat, request.end_lon, request.end_altitude_m, "终点")
        extra_distance_m = 0.0
        anchored = [dict(point) for point in route.waypoints]
        if horizontal_gap_m(anchored[0], request.start_lat, request.start_lon) <= 1.0:
            anchored[0] = start_anchor
        else:
            extra_distance_m += connector_distance_m(start_anchor, anchored[0])
            anchored.insert(0, start_anchor)
        if horizontal_gap_m(anchored[-1], request.end_lat, request.end_lon) <= 1.0:
            anchored[-1] = end_anchor
        else:
            extra_distance_m += connector_distance_m(anchored[-1], end_anchor)
            anchored.append(end_anchor)
        if extra_distance_m > 0.0:
            route.distance_m = round(route.distance_m + extra_distance_m, 2)
            extra_duration_s = extra_distance_m / max(request.cruise_speed_mps, 0.1)
            route.estimated_duration_s = round(route.estimated_duration_s + extra_duration_s, 2)
            route.base_cost = round(route.base_cost + extra_duration_s, 2)
        route.waypoints = anchored
        route.waypoint_count = len(anchored)
        return route

    @staticmethod
    def _waypoint_matches_request_anchor(
        point: dict[str, float | str],
        *,
        lat: float,
        lon: float,
        altitude_m: float,
    ) -> bool:
        return (
            abs(float(point["lat"]) - lat) <= 1e-8
            and abs(float(point["lon"]) - lon) <= 1e-8
            and abs(float(point["altitude_m"]) - altitude_m) <= 0.11
        )

    def _route_segments_clear_buildings(
        self,
        *,
        route: RouteCandidate,
        request: PlannerRequest,
        building_index: BuildingIndex,
    ) -> bool:
        if len(route.waypoints) < 2:
            return False
        for idx in range(1, len(route.waypoints)):
            start = route.waypoints[idx - 1]
            end = route.waypoints[idx]
            if request.planning_mode == self.PLANNING_MODE_COMBINED:
                if idx == 1 and self._waypoint_matches_request_anchor(
                    start,
                    lat=request.start_lat,
                    lon=request.start_lon,
                    altitude_m=request.start_altitude_m,
                ):
                    continue
                if idx == len(route.waypoints) - 1 and self._waypoint_matches_request_anchor(
                    end,
                    lat=request.end_lat,
                    lon=request.end_lon,
                    altitude_m=request.end_altitude_m,
                ):
                    continue
            start_xy = latlon_to_meters(self.origin, float(start["lat"]), float(start["lon"]))
            end_xy = latlon_to_meters(self.origin, float(end["lat"]), float(end["lon"]))
            altitude_m = min(float(start["altitude_m"]), float(end["altitude_m"]))
            if not self._xy_segment_clear_at_altitude(
                start_xy=start_xy,
                end_xy=end_xy,
                altitude_m=altitude_m,
                building_index=building_index,
                request=request,
                consider_buildings=True,
            ):
                return False
        return True

    def _xy_point_required_altitude_m(
        self,
        *,
        point_xy: tuple[float, float],
        building_index: BuildingIndex,
        request: PlannerRequest,
        consider_buildings: bool,
    ) -> float:
        if not consider_buildings:
            return request.min_altitude_m
        if self._strict_building_avoidance(request.planning_mode):
            for building in building_index.query_bbox(point_xy[0], point_xy[1], point_xy[0], point_xy[1]):
                if point_in_poly(point_xy, building.points_xy):
                    return float("inf")
            return request.min_altitude_m
        required_altitude_m = request.min_altitude_m
        for building in building_index.query_bbox(point_xy[0], point_xy[1], point_xy[0], point_xy[1]):
            if point_in_poly(point_xy, building.points_xy):
                required_altitude_m = max(required_altitude_m, building.height_m + 1.0)
        return required_altitude_m

    def _xy_segment_required_altitude_m(
        self,
        *,
        start_xy: tuple[float, float],
        end_xy: tuple[float, float],
        building_index: BuildingIndex,
        request: PlannerRequest,
        consider_buildings: bool,
    ) -> float:
        if not consider_buildings:
            return request.min_altitude_m
        left = min(start_xy[0], end_xy[0])
        right = max(start_xy[0], end_xy[0])
        bottom = min(start_xy[1], end_xy[1])
        top = max(start_xy[1], end_xy[1])
        required_altitude_m = max(
            request.min_altitude_m,
            self._xy_point_required_altitude_m(
                point_xy=start_xy,
                building_index=building_index,
                request=request,
                consider_buildings=True,
            ),
            self._xy_point_required_altitude_m(
                point_xy=end_xy,
                building_index=building_index,
                request=request,
                consider_buildings=True,
            ),
        )
        for building in building_index.query_bbox(left, bottom, right, top):
            if not segment_hits_poly(start_xy, end_xy, building.points_xy):
                continue
            if self._strict_building_avoidance(request.planning_mode):
                return float("inf")
            if self._xy_segment_enters_building_interior(start_xy, end_xy, building):
                required_altitude_m = max(required_altitude_m, building.height_m + 1.0)
        return required_altitude_m

    def _building_segment_overflight_stats_for_xy(
        self,
        *,
        start_xy: tuple[float, float],
        end_xy: tuple[float, float],
        altitude_m: float,
        building_index: BuildingIndex,
        request: PlannerRequest,
    ) -> tuple[int, float]:
        left = min(start_xy[0], end_xy[0])
        right = max(start_xy[0], end_xy[0])
        bottom = min(start_xy[1], end_xy[1])
        top = max(start_xy[1], end_xy[1])
        building_count = 0
        exposure = 0.0
        for building in building_index.query_bbox(left, bottom, right, top):
            if not segment_hits_poly(start_xy, end_xy, building.points_xy):
                continue
            if not self._xy_segment_enters_building_interior(start_xy, end_xy, building):
                continue
            if altitude_m <= building.height_m + 1e-6:
                continue
            building_count += 1
            clearance_m = altitude_m - building.height_m
            exposure += (1.0 + min(building.height_m, 240.0) / 120.0) / (1.0 + clearance_m / max(request.safety_clearance_m + 10.0, 1.0))
        return building_count, exposure

    def _xy_path_altitude_profile(
        self,
        *,
        path_xy: list[tuple[float, float]],
        profile: CostProfile,
        fallback_altitude_m: float,
        building_index: BuildingIndex,
        request: PlannerRequest,
        consider_buildings: bool,
    ) -> list[float] | None:
        if not path_xy:
            return []
        base_altitude_m = max(request.min_altitude_m, min(request.max_altitude_m, fallback_altitude_m))
        required = [base_altitude_m for _point in path_xy]
        required[0] = max(request.min_altitude_m, min(request.max_altitude_m, request.start_altitude_m))
        required[-1] = max(request.min_altitude_m, min(request.max_altitude_m, request.end_altitude_m))
        for idx, point_xy in enumerate(path_xy):
            point_required_m = self._xy_point_required_altitude_m(
                point_xy=point_xy,
                building_index=building_index,
                request=request,
                consider_buildings=consider_buildings,
            )
            if point_required_m > request.max_altitude_m + 1e-6:
                return None
            required[idx] = max(required[idx], point_required_m)
        for idx in range(1, len(path_xy)):
            segment_required_m = self._xy_segment_required_altitude_m(
                start_xy=path_xy[idx - 1],
                end_xy=path_xy[idx],
                building_index=building_index,
                request=request,
                consider_buildings=consider_buildings,
            )
            if segment_required_m > request.max_altitude_m + 1e-6:
                return None
            required[idx - 1] = max(required[idx - 1], segment_required_m)
            required[idx] = max(required[idx], segment_required_m)

        ceiling_span = max(0.0, request.max_altitude_m - request.min_altitude_m)
        strategy_bias = {
            "fastest": 0.68,
            "safest": 1.00,
            "energy_saving": 0.00,
            "balanced_stable": 0.56,
            "most_accessible": 0.64,
        }.get(profile.strategy, 0.35)
        if strategy_bias > 0.0:
            preferred_altitude_m = min(request.max_altitude_m, request.min_altitude_m + ceiling_span * strategy_bias)
            for idx in range(1, len(required) - 1):
                required[idx] = max(required[idx], preferred_altitude_m)
        if profile.strategy == "safest":
            for idx in range(1, len(required) - 1):
                required[idx] = request.max_altitude_m

        if profile.strategy in {"safest", "most_accessible", "balanced_stable"}:
            clearance_bonus = min(
                max(2.0, request.safety_clearance_m * {"safest": 0.70, "most_accessible": 0.10, "balanced_stable": 0.12}[profile.strategy]),
                max(0.0, request.max_altitude_m - request.min_altitude_m),
            )
            for idx in range(1, len(path_xy) - 1):
                if required[idx] > base_altitude_m + 1e-6:
                    required[idx] = min(request.max_altitude_m, required[idx] + clearance_bonus)

        if profile.strategy in {"fastest", "safest", "most_accessible", "balanced_stable"} and len(required) > 3:
            smoothed = list(required)
            passes = 2 if profile.strategy in {"safest", "most_accessible"} else 1
            for _pass_idx in range(passes):
                next_values = list(smoothed)
                for idx in range(1, len(smoothed) - 1):
                    blended = (smoothed[idx - 1] + smoothed[idx] * 2.0 + smoothed[idx + 1]) / 4.0
                    next_values[idx] = max(required[idx], min(request.max_altitude_m, blended))
                smoothed = next_values
            required = smoothed

        if profile.strategy == "energy_saving":
            for idx, altitude_m in enumerate(required):
                required[idx] = min(request.max_altitude_m, max(request.min_altitude_m, altitude_m))
        else:
            for idx, altitude_m in enumerate(required):
                required[idx] = min(request.max_altitude_m, max(request.min_altitude_m, altitude_m))

        required[0] = max(
            required[0],
            min(request.max_altitude_m, max(request.min_altitude_m, request.start_altitude_m)),
        )
        required[-1] = max(
            required[-1],
            min(request.max_altitude_m, max(request.min_altitude_m, request.end_altitude_m)),
        )
        return [round(altitude_m, 2) for altitude_m in required]

    def _expand_xy_altitude_waypoints(
        self,
        *,
        path_xy: list[tuple[float, float]],
        altitude_profile_m: list[float],
        profile: CostProfile,
    ) -> tuple[list[tuple[float, float]], list[float]]:
        expanded_xy: list[tuple[float, float]] = []
        expanded_altitudes: list[float] = []
        for idx, (point_xy, altitude_m) in enumerate(zip(path_xy, altitude_profile_m)):
            if idx > 0 and profile.strategy in {"fastest", "safest", "most_accessible", "balanced_stable"}:
                prev_altitude_m = expanded_altitudes[-1]
                altitude_gap_m = abs(altitude_m - prev_altitude_m)
                if altitude_gap_m >= 8.0:
                    expanded_xy.append(point_xy)
                    expanded_altitudes.append(altitude_m)
                    continue
            if expanded_xy and self._xy_distance(expanded_xy[-1], point_xy) <= 1e-6 and abs(expanded_altitudes[-1] - altitude_m) <= 1e-6:
                continue
            expanded_xy.append(point_xy)
            expanded_altitudes.append(altitude_m)
        return expanded_xy, expanded_altitudes

    def _build_candidate_from_xy_path(
        self,
        *,
        route_id: str,
        profile: CostProfile,
        path_xy: list[tuple[float, float]],
        altitude_m: float,
        x_values: list[float],
        y_values: list[float],
        altitude_layers_m: list[float],
        node_weather: Any,
        xy_urban_density: Any,
        node_connectivity: Any,
        node_reachability: Any,
        building_index: BuildingIndex,
        request: PlannerRequest,
        consider_weather: bool,
    ) -> RouteCandidate:
        altitude_profile_m = self._xy_path_altitude_profile(
            path_xy=path_xy,
            profile=profile,
            fallback_altitude_m=altitude_m,
            building_index=building_index,
            request=request,
            consider_buildings=self._consider_buildings(request.planning_mode),
        )
        if altitude_profile_m is None:
            altitude_profile_m = [altitude_m for _point in path_xy]
        path_xy, altitude_profile_m = self._expand_xy_altitude_waypoints(
            path_xy=path_xy,
            altitude_profile_m=altitude_profile_m,
            profile=profile,
        )
        total_distance_m = 0.0
        estimated_duration_s = 0.0
        max_wind = 0.0
        max_headwind = 0.0
        max_crosswind = 0.0
        max_turbulence = 0.0
        max_precipitation = 0.0
        max_weather_risk = 0.0
        high_risk_segment_count = 0
        segment_count = 0
        density_sum = 0.0
        connectivity_sum = 0.0
        reachability_sum = 0.0
        min_connectivity = 1.0
        overflight_building_count = 0
        overflight_exposure = 0.0
        waypoints: list[dict[str, float | str]] = []
        prev_indices = None
        prev_point_xy = None
        prev_altitude_m = None
        for idx, point_xy in enumerate(path_xy):
            waypoint_altitude_m = max(request.min_altitude_m, min(request.max_altitude_m, altitude_profile_m[idx]))
            lat, lon = meters_to_latlon(self.origin, point_xy[0], point_xy[1])
            ix = self._nearest_axis_index(x_values, point_xy[0])
            iy = self._nearest_axis_index(y_values, point_xy[1])
            iz = self._nearest_axis_index(altitude_layers_m, waypoint_altitude_m)
            weather = (
                node_weather(ix, iy, iz)
                if consider_weather
                else WeatherState(
                    wind_east_mps=0.0,
                    wind_north_mps=0.0,
                    wind_speed_mps=0.0,
                    turbulence_index=0.0,
                    precipitation_mm=0.0,
                    pressure_hpa=1013.25,
                    temperature_c=0.0,
                    cloud_cover_pct=0.0,
                )
            )
            density = xy_urban_density(ix, iy)
            connectivity = node_connectivity(ix, iy, iz)
            reachability = node_reachability(ix, iy, iz)
            density_sum += density
            connectivity_sum += connectivity
            reachability_sum += reachability
            min_connectivity = min(min_connectivity, connectivity)
            max_wind = max(max_wind, weather.wind_speed_mps)
            max_turbulence = max(max_turbulence, weather.turbulence_index)
            max_precipitation = max(max_precipitation, weather.precipitation_mm)
            if consider_weather:
                max_weather_risk = max(max_weather_risk, self._visual_weather_risk_score(weather=weather, altitude_m=waypoint_altitude_m))
            waypoints.append(
                {
                    "lat": round(lat, 9),
                    "lon": round(lon, 9),
                    "altitude_m": round(waypoint_altitude_m, 1),
                    "label": f"航点{idx + 1}",
                }
            )
            if prev_indices is None:
                prev_indices = (ix, iy, iz)
                prev_point_xy = point_xy
                prev_altitude_m = waypoint_altitude_m
                continue
            segment = self._segment_stats(
                current=prev_indices,
                nxt=(ix, iy, iz),
                x_values=x_values,
                y_values=y_values,
                altitude_layers_m=altitude_layers_m,
                node_weather=node_weather,
                xy_urban_density=xy_urban_density,
                node_connectivity=node_connectivity,
                node_reachability=node_reachability,
                consider_weather=consider_weather,
            )
            horizontal_m = self._xy_distance(prev_point_xy, point_xy) if prev_point_xy is not None else segment.horizontal_m
            vertical_m = abs(waypoint_altitude_m - prev_altitude_m) if prev_altitude_m is not None else segment.vertical_m
            segment = SegmentStats(
                horizontal_m=horizontal_m,
                vertical_m=vertical_m,
                wind_speed_mps=segment.wind_speed_mps,
                headwind_mps=segment.headwind_mps,
                tailwind_mps=segment.tailwind_mps,
                crosswind_mps=segment.crosswind_mps,
                turbulence_index=segment.turbulence_index,
                precipitation_mm=segment.precipitation_mm,
                mean_density=segment.mean_density,
                mean_connectivity=segment.mean_connectivity,
                mean_reachability=segment.mean_reachability,
            )
            total_distance_m += math.hypot(horizontal_m, vertical_m)
            max_wind = max(max_wind, segment.wind_speed_mps)
            max_headwind = max(max_headwind, segment.headwind_mps)
            max_crosswind = max(max_crosswind, segment.crosswind_mps)
            max_turbulence = max(max_turbulence, segment.turbulence_index)
            max_precipitation = max(max_precipitation, segment.precipitation_mm)
            if consider_weather:
                max_weather_risk = max(
                    max_weather_risk,
                    self._edge_visual_weather_risk_score(
                        current=prev_indices,
                        nxt=(ix, iy, iz),
                        x_values=x_values,
                        y_values=y_values,
                        altitude_layers_m=altitude_layers_m,
                        node_weather=node_weather,
                    ),
                )
            segment_count += 1
            if consider_weather and self._weather_segment_high_risk(segment):
                high_risk_segment_count += 1
            if prev_point_xy is not None:
                segment_altitude_m = min(prev_altitude_m if prev_altitude_m is not None else waypoint_altitude_m, waypoint_altitude_m)
                segment_overflight_count, segment_overflight_exposure = self._building_segment_overflight_stats_for_xy(
                    start_xy=prev_point_xy,
                    end_xy=point_xy,
                    altitude_m=segment_altitude_m,
                    building_index=building_index,
                    request=request,
                )
                overflight_building_count += segment_overflight_count
                overflight_exposure += segment_overflight_exposure
            estimated_duration_s += self._evaluate_segment_duration(
                segment=segment,
                current_altitude_m=prev_altitude_m if prev_altitude_m is not None else waypoint_altitude_m,
                next_altitude_m=waypoint_altitude_m,
                request=request,
                consider_weather=consider_weather,
            )
            prev_indices = (ix, iy, iz)
            prev_point_xy = point_xy
            prev_altitude_m = waypoint_altitude_m
        average_density = density_sum / max(len(path_xy), 1)
        average_connectivity = connectivity_sum / max(len(path_xy), 1)
        average_reachability = reachability_sum / max(len(path_xy), 1)
        base_cost = round(
            estimated_duration_s
            + max_headwind * 7.5
            + max_crosswind * 4.5
            + max_turbulence * 110.0
            + max_precipitation * 38.0
            + max_weather_risk * 420.0
            + (high_risk_segment_count / max(segment_count, 1)) * 980.0
            + average_density * 70.0
            + overflight_exposure * 16.0
            + (1.0 - average_reachability) * 80.0,
            2,
        )
        candidate = RouteCandidate(
            route_id=route_id,
            label=profile.label,
            strategy=profile.strategy,
            score=0.0,
            base_cost=base_cost,
            topsis_score=0.0,
            robustness_score=0.0,
            reliability_ratio=0.0,
            duration_p95_s=0.0,
            expected_delay_ratio=0.0,
            distance_m=round(total_distance_m, 2),
            estimated_duration_s=round(estimated_duration_s, 2),
            max_wind_speed_mps=round(max_wind, 2),
            max_headwind_mps=round(max_headwind, 2),
            max_crosswind_mps=round(max_crosswind, 2),
            max_turbulence_index=round(max_turbulence, 3),
            max_precipitation_mm=round(max_precipitation, 3),
            max_weather_risk_score=round(max_weather_risk, 3),
            high_risk_exposure_ratio=round(high_risk_segment_count / max(segment_count, 1), 3),
            average_urban_density=round(average_density, 3),
            average_connectivity_index=round(average_connectivity, 3),
            minimum_connectivity_index=round(min_connectivity if path_xy else 0.0, 3),
            average_reachability_index=round(average_reachability, 3),
            corridor_diversity_index=0.0,
            overflight_building_count=overflight_building_count,
            overflight_exposure_index=round(overflight_exposure, 3),
            waypoint_count=len(waypoints),
            recommended_rank=0,
            waypoints=waypoints,
        )
        return self._with_request_endpoint_anchors(route=candidate, request=request)

    def _nearest_road_node_index(self, point_xy: tuple[float, float]) -> int | None:
        if self.road_graph is None or not self.road_graph.nodes_xy:
            return None
        best_idx = None
        best_distance = float("inf")
        for idx, road_point_xy in enumerate(self.road_graph.nodes_xy):
            distance = self._xy_distance(point_xy, road_point_xy)
            if distance < best_distance:
                best_distance = distance
                best_idx = idx
        return best_idx

    @staticmethod
    def _nearest_axis_index(values: list[float], target: float) -> int:
        best_idx = 0
        best_gap = float("inf")
        for idx, value in enumerate(values):
            gap = abs(value - target)
            if gap < best_gap:
                best_idx = idx
                best_gap = gap
        return best_idx

    @staticmethod
    def _xy_segment_hits_building_footprint(
        start_xy: tuple[float, float],
        end_xy: tuple[float, float],
        building_index: BuildingIndex,
    ) -> bool:
        left = min(start_xy[0], end_xy[0])
        right = max(start_xy[0], end_xy[0])
        bottom = min(start_xy[1], end_xy[1])
        top = max(start_xy[1], end_xy[1])
        for building in building_index.query_bbox(left, bottom, right, top):
            if segment_hits_poly(start_xy, end_xy, building.points_xy):
                return True
        return False

    def _xy_segment_clear_at_altitude(
        self,
        *,
        start_xy: tuple[float, float],
        end_xy: tuple[float, float],
        altitude_m: float,
        building_index: BuildingIndex,
        request: PlannerRequest,
        consider_buildings: bool,
    ) -> bool:
        if not consider_buildings:
            return True
        left = min(start_xy[0], end_xy[0])
        right = max(start_xy[0], end_xy[0])
        bottom = min(start_xy[1], end_xy[1])
        top = max(start_xy[1], end_xy[1])
        allow_overflight = self._segment_allows_overflight(min_altitude_m=altitude_m, request=request)
        for building in building_index.query_bbox(left, bottom, right, top):
            if not segment_hits_poly(start_xy, end_xy, building.points_xy):
                continue
            if request.planning_mode == self.PLANNING_MODE_BUILDING_ONLY or self._strict_building_avoidance(request.planning_mode):
                return False
            required_altitude = building.height_m + request.safety_clearance_m
            if altitude_m <= required_altitude + 1e-6 or not allow_overflight:
                if not self._xy_segment_enters_building_interior(start_xy, end_xy, building):
                    continue
                return False
        return True

    @staticmethod
    def _xy_segment_enters_building_interior(
        start_xy: tuple[float, float],
        end_xy: tuple[float, float],
        building: Building,
    ) -> bool:
        if point_in_poly(start_xy, building.points_xy) or point_in_poly(end_xy, building.points_xy):
            return True
        distance_m = math.hypot(end_xy[0] - start_xy[0], end_xy[1] - start_xy[1])
        steps = max(2, int(math.ceil(distance_m / 2.0)))
        for idx in range(1, steps):
            ratio = idx / steps
            sample_xy = (
                start_xy[0] + (end_xy[0] - start_xy[0]) * ratio,
                start_xy[1] + (end_xy[1] - start_xy[1]) * ratio,
            )
            if point_in_poly(sample_xy, building.points_xy):
                return True
        return False

    def _simplify_xy_path(
        self,
        path_xy: list[tuple[float, float]],
        *,
        building_index: BuildingIndex | None = None,
        strict_building_avoidance: bool = False,
        xy_segment_clear: Any | None = None,
        altitude_m: float | None = None,
        request: PlannerRequest | None = None,
        consider_buildings: bool = False,
    ) -> list[tuple[float, float]]:
        if len(path_xy) <= 2:
            return path_xy
        simplified = [path_xy[0]]
        for idx in range(1, len(path_xy) - 1):
            turn_penalty = CityRoutePlanner._xy_turn_penalty(simplified[-1], path_xy[idx], path_xy[idx + 1])
            if turn_penalty < 0.03:
                if (
                    building_index is not None
                    and altitude_m is not None
                    and request is not None
                    and not (
                        xy_segment_clear(simplified[-1], path_xy[idx + 1], altitude_m)
                        if xy_segment_clear is not None
                        else self._xy_segment_clear_at_altitude(
                            start_xy=simplified[-1],
                            end_xy=path_xy[idx + 1],
                            altitude_m=altitude_m,
                            building_index=building_index,
                            request=request,
                            consider_buildings=consider_buildings,
                        )
                    )
                ):
                    simplified.append(path_xy[idx])
                    continue
                if (
                    strict_building_avoidance
                    and building_index is not None
                    and self._xy_segment_hits_building_footprint(simplified[-1], path_xy[idx + 1], building_index)
                ):
                    simplified.append(path_xy[idx])
                    continue
            simplified.append(path_xy[idx])
        simplified.append(path_xy[-1])
        return simplified

    @staticmethod
    def _xy_turn_penalty(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
        vx1 = b[0] - a[0]
        vy1 = b[1] - a[1]
        vx2 = c[0] - b[0]
        vy2 = c[1] - b[1]
        norm1 = math.hypot(vx1, vy1)
        norm2 = math.hypot(vx2, vy2)
        if norm1 <= 1e-6 or norm2 <= 1e-6:
            return 0.0
        cosine = max(-1.0, min(1.0, (vx1 * vx2 + vy1 * vy2) / (norm1 * norm2)))
        return math.acos(cosine) / math.pi

    @staticmethod
    def _xy_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    def _entropy_weight_topsis(self, routes: list[RouteCandidate]) -> tuple[dict[str, float], list[float]]:
        if len(routes) == 1:
            weight = 1.0 / len(self.RANKING_METRICS)
            return ({metric.field: weight for metric in self.RANKING_METRICS}, [1.0])
        oriented: dict[str, list[float]] = {}
        for metric in self.RANKING_METRICS:
            raw_values = [float(getattr(route, metric.field)) for route in routes]
            min_value = min(raw_values)
            max_value = max(raw_values)
            if math.isclose(min_value, max_value, rel_tol=1e-9, abs_tol=1e-9):
                oriented[metric.field] = [1.0 for _route in routes]
                continue
            values: list[float] = []
            for value in raw_values:
                if metric.benefit:
                    normalized = (value - min_value) / (max_value - min_value)
                else:
                    normalized = (max_value - value) / (max_value - min_value)
                values.append(max(normalized, 1e-6))
            oriented[metric.field] = values
        divergence: dict[str, float] = {}
        route_count = len(routes)
        entropy_scale = 1.0 / math.log(route_count)
        for metric in self.RANKING_METRICS:
            values = oriented[metric.field]
            total = sum(values)
            if total <= 1e-12:
                divergence[metric.field] = 0.0
                continue
            entropy = 0.0
            for value in values:
                probability = value / total
                if probability > 1e-12:
                    entropy -= entropy_scale * probability * math.log(probability)
            divergence[metric.field] = max(0.0, 1.0 - entropy)
        divergence_sum = sum(divergence.values())
        if divergence_sum <= 1e-12:
            weights = {metric.field: 1.0 / len(self.RANKING_METRICS) for metric in self.RANKING_METRICS}
        else:
            weights = {metric.field: divergence[metric.field] / divergence_sum for metric in self.RANKING_METRICS}
        weighted_vectors: list[list[float]] = [[0.0 for _metric in self.RANKING_METRICS] for _route in routes]
        for metric_index, metric in enumerate(self.RANKING_METRICS):
            values = oriented[metric.field]
            vector_norm = math.sqrt(sum(value * value for value in values))
            for route_index, value in enumerate(values):
                normalized = value / vector_norm if vector_norm > 1e-12 else 1.0 / math.sqrt(route_count)
                weighted_vectors[route_index][metric_index] = normalized * weights[metric.field]
        ideal_best = [max(vector[idx] for vector in weighted_vectors) for idx in range(len(self.RANKING_METRICS))]
        ideal_worst = [min(vector[idx] for vector in weighted_vectors) for idx in range(len(self.RANKING_METRICS))]
        closeness_values: list[float] = []
        for vector in weighted_vectors:
            distance_best = math.sqrt(sum((vector[idx] - ideal_best[idx]) ** 2 for idx in range(len(vector))))
            distance_worst = math.sqrt(sum((vector[idx] - ideal_worst[idx]) ** 2 for idx in range(len(vector))))
            denom = distance_best + distance_worst
            closeness_values.append(distance_worst / denom if denom > 1e-12 else 1.0)
        return weights, closeness_values

    @staticmethod
    def _percentile(values: list[float], ratio: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        position = min(max(ratio, 0.0), 1.0) * (len(ordered) - 1)
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[lower]
        weight = position - lower
        return ordered[lower] * (1.0 - weight) + ordered[upper] * weight

    @staticmethod
    def _is_near_used_corridor(ix: int, iy: int, corridor: set[tuple[int, int]]) -> bool:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if (ix + dx, iy + dy) in corridor:
                    return True
        return False

    @staticmethod
    def _corridor_overlap_ratio(a: set[tuple[int, int]], b: set[tuple[int, int]]) -> float:
        if not a or not b:
            return 0.0
        return len(a & b) / max(1, min(len(a), len(b)))

    @staticmethod
    def _pairwise_diversity_index(*, overlap_ratio: float, altitude_gap_m: float, request: PlannerRequest) -> float:
        altitude_term = min(1.0, altitude_gap_m / max(80.0, request.max_altitude_m * 0.25))
        planar_term = 1.0 - overlap_ratio
        return max(0.0, min(1.0, planar_term * 0.70 + altitude_term * 0.30))
