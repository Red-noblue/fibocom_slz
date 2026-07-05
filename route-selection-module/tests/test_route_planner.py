"""最小测试：验证路径规划能绕开建筑障碍并产出多条候选路线。"""

from __future__ import annotations

import unittest
from unittest import mock

from route_selection.geo import GeoOrigin, latlon_to_meters, segment_hits_poly
from route_selection.planner import CityRoutePlanner, PlannerRequest


class RoutePlannerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.city_config = {
            "name": "test_city",
            "display_name": "测试城市",
            "center": {"lat": 30.0, "lon": 114.0},
            "bbox": {"south": 29.995, "west": 113.995, "north": 30.005, "east": 114.005},
        }
        self.city_summary = {
            "name": "test_city",
            "display_name": "测试城市",
            "center": {"lat": 30.0, "lon": 114.0},
            "bbox": {"south": 29.995, "west": 113.995, "north": 30.005, "east": 114.005},
        }
        self.buildings = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"height_m": 90.0},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [113.9993, 29.9982],
                            [114.0007, 29.9982],
                            [114.0007, 30.0018],
                            [113.9993, 30.0018],
                            [113.9993, 29.9982],
                        ]],
                    },
                }
            ],
        }
        features = []
        for lon in (113.995, 113.9975, 114.0, 114.0025, 114.005):
            for lat in (29.995, 29.9975, 30.0, 30.0025, 30.005):
                for altitude_m in (0.0, 20.0, 60.0, 120.0, 220.0):
                    features.append(
                        {
                            "type": "Feature",
                            "properties": {
                                "altitude_m": altitude_m,
                                "wind_speed_mps": 3.0 if lat < 30.0 else 5.0,
                                "wind_dir_deg": 90.0,
                                "turbulence_index": 0.1 if lon < 114.0 else 0.25,
                                "precipitation_mm": 0.0,
                                "pressure_hpa": 1013.25 - altitude_m * 0.11,
                                "temperature_c": 20.0,
                            },
                            "geometry": {"type": "Point", "coordinates": [lon, lat, altitude_m]},
                        }
                    )
        self.weather = {"type": "FeatureCollection", "features": features}
        self.ground = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"layer": "road"},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [113.9954, 30.0],
                            [113.9964, 30.0],
                        ],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {"layer": "road"},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [113.9964, 30.0],
                            [113.998, 30.0],
                            [114.002, 30.0],
                            [114.0036, 30.0],
                        ],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {"layer": "road"},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [113.9964, 30.0],
                            [113.9964, 30.0022],
                            [114.0036, 30.0022],
                            [114.0036, 30.0],
                        ],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {"layer": "road"},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [113.9964, 30.0],
                            [113.9964, 29.9978],
                            [114.0036, 29.9978],
                            [114.0036, 30.0],
                            [114.0046, 30.0],
                        ],
                    },
                }
            ],
        }

    def _assert_routes_respect_building_clearance(self, routes, *, clearance_m: float) -> None:
        origin = GeoOrigin(
            lat=float(self.city_config["center"]["lat"]),
            lon=float(self.city_config["center"]["lon"]),
        )
        building_polys = []
        for feature in self.buildings["features"]:
            geometry = feature.get("geometry") or {}
            if geometry.get("type") != "Polygon":
                continue
            ring = (geometry.get("coordinates") or [[]])[0]
            points_xy = [latlon_to_meters(origin, lat, lon) for lon, lat, *_ in ring]
            if len(points_xy) < 3:
                continue
            height_m = float((feature.get("properties") or {}).get("height_m") or 0.0)
            building_polys.append((points_xy, height_m))
        for route in routes:
            for idx in range(1, len(route.waypoints)):
                start = route.waypoints[idx - 1]
                end = route.waypoints[idx]
                start_xy = latlon_to_meters(origin, float(start["lat"]), float(start["lon"]))
                end_xy = latlon_to_meters(origin, float(end["lat"]), float(end["lon"]))
                min_altitude_m = min(float(start["altitude_m"]), float(end["altitude_m"]))
                for points_xy, height_m in building_polys:
                    if segment_hits_poly(start_xy, end_xy, points_xy):
                        if min_altitude_m <= height_m + clearance_m + 1e-6:
                            self.fail(
                                f"路线 {route.route_id} 第 {idx} 段未满足建筑净空："
                                f"segment=({start['lon']},{start['lat']},{start['altitude_m']})"
                                f"->({end['lon']},{end['lat']},{end['altitude_m']}) "
                                f"building_height={height_m} clearance={clearance_m}"
                            )

    def _assert_routes_avoid_building_footprints(self, routes) -> None:
        origin = GeoOrigin(
            lat=float(self.city_config["center"]["lat"]),
            lon=float(self.city_config["center"]["lon"]),
        )
        building_polys = []
        for feature in self.buildings["features"]:
            geometry = feature.get("geometry") or {}
            if geometry.get("type") != "Polygon":
                continue
            ring = (geometry.get("coordinates") or [[]])[0]
            points_xy = [latlon_to_meters(origin, lat, lon) for lon, lat, *_ in ring]
            if len(points_xy) >= 3:
                building_polys.append(points_xy)
        for route in routes:
            for idx in range(1, len(route.waypoints)):
                start = route.waypoints[idx - 1]
                end = route.waypoints[idx]
                start_xy = latlon_to_meters(origin, float(start["lat"]), float(start["lon"]))
                end_xy = latlon_to_meters(origin, float(end["lat"]), float(end["lon"]))
                for points_xy in building_polys:
                    if segment_hits_poly(start_xy, end_xy, points_xy):
                        self.fail(
                            f"路线 {route.route_id} 第 {idx} 段穿过建筑投影："
                            f"segment=({start['lon']},{start['lat']},{start['altitude_m']})"
                            f"->({end['lon']},{end['lat']},{end['altitude_m']})"
                        )

    @staticmethod
    def _empty_buildings() -> dict:
        return {"type": "FeatureCollection", "features": []}

    def _weather_with_hazard(
        self,
        *,
        severe_nodes: set[tuple[float, float, float]],
        severe_wind_speed_mps: float = 16.0,
        severe_turbulence_index: float = 0.78,
        severe_precipitation_mm: float = 6.0,
        severe_pressure_hpa: float | None = None,
    ) -> dict:
        features = []
        for lon in (113.995, 113.9975, 114.0, 114.0025, 114.005):
            for lat in (29.995, 29.9975, 30.0, 30.0025, 30.005):
                for altitude_m in (0.0, 20.0, 60.0, 120.0, 220.0):
                    key = (round(lon, 4), round(lat, 4), round(altitude_m, 1))
                    is_severe = key in severe_nodes
                    pressure_hpa = severe_pressure_hpa if is_severe and severe_pressure_hpa is not None else 1013.25 - altitude_m * 0.11
                    features.append(
                        {
                            "type": "Feature",
                            "properties": {
                                "altitude_m": altitude_m,
                                "wind_speed_mps": severe_wind_speed_mps if is_severe else 3.4,
                                "wind_dir_deg": 90.0,
                                "turbulence_index": severe_turbulence_index if is_severe else 0.12,
                                "precipitation_mm": severe_precipitation_mm if is_severe else 0.0,
                                "pressure_hpa": pressure_hpa,
                                "temperature_c": 20.0,
                            },
                            "geometry": {"type": "Point", "coordinates": [lon, lat, altitude_m]},
                        }
                    )
        return {"type": "FeatureCollection", "features": features}

    def test_plan_returns_multiple_routes(self) -> None:
        planner = CityRoutePlanner.from_payloads(
            city_config=self.city_config,
            city_summary=self.city_summary,
            buildings_geojson=self.buildings,
            weather_geojson=self.weather,
        )
        result = planner.plan(
            PlannerRequest(
                start_lat=30.0,
                start_lon=113.9955,
                end_lat=30.0,
                end_lon=114.0045,
                start_altitude_m=20.0,
                end_altitude_m=20.0,
                min_altitude_m=0.0,
                candidate_count=5,
                cell_m=80.0,
                safety_clearance_m=20.0,
                max_altitude_m=-1.0,
            )
        )
        self.assertEqual(len(result.routes), 5)
        self.assertEqual(result.planner["ranking_method"], "entropy_weight_topsis")
        self.assertGreater(result.planner["monte_carlo_runs"], 0)
        self.assertAlmostEqual(sum(result.planner["ranking_weights"].values()), 1.0, places=3)
        self.assertEqual(result.planner["min_altitude_m"], 0.0)
        self.assertGreater(result.planner["max_altitude_m"], 0.0)
        self.assertEqual(
            {route.strategy for route in result.routes},
            {"fastest", "safest", "energy_saving", "balanced_stable", "most_accessible"},
        )
        self.assertEqual(
            {route.label for route in result.routes},
            {"最快到达", "低风险", "能耗最少", "均衡稳定推荐", "最畅通路线"},
        )
        by_strategy = {route.strategy: route for route in result.routes}
        self.assertAlmostEqual(
            by_strategy["fastest"].estimated_duration_s,
            min(route.estimated_duration_s for route in result.routes),
            places=6,
        )
        self.assertAlmostEqual(
            by_strategy["safest"].overflight_exposure_index,
            min(route.overflight_exposure_index for route in result.routes),
            places=6,
        )
        self.assertFalse(
            by_strategy["energy_saving"].estimated_duration_s == max(route.estimated_duration_s for route in result.routes)
            and by_strategy["energy_saving"].distance_m == max(route.distance_m for route in result.routes)
        )
        previous_rank = 0
        has_local_detour = False
        for route in result.routes:
            self.assertGreater(route.distance_m, 0.0)
            self.assertGreater(route.waypoint_count, 1)
            self.assertGreaterEqual(route.score, 0.0)
            self.assertLessEqual(route.score, 100.0)
            self.assertGreaterEqual(route.robustness_score, 0.0)
            self.assertLessEqual(route.robustness_score, 100.0)
            self.assertGreaterEqual(route.reliability_ratio, 0.0)
            self.assertLessEqual(route.reliability_ratio, 1.0)
            self.assertGreaterEqual(route.average_connectivity_index, 0.0)
            self.assertLessEqual(route.average_connectivity_index, 1.0)
            self.assertGreaterEqual(route.average_reachability_index, 0.0)
            self.assertLessEqual(route.average_reachability_index, 1.0)
            self.assertGreaterEqual(route.corridor_diversity_index, 0.0)
            self.assertLessEqual(route.corridor_diversity_index, 1.0)
            self.assertGreaterEqual(route.overflight_building_count, 0)
            self.assertGreaterEqual(route.overflight_exposure_index, 0.0)
            self.assertGreaterEqual(route.recommended_rank, 1)
            self.assertGreater(route.recommended_rank, previous_rank)
            previous_rank = route.recommended_rank
            if route.waypoint_count > 2 and route.overflight_building_count == 0:
                has_local_detour = True
        self.assertTrue(has_local_detour)
        self.assertTrue(all(route.overflight_building_count == 0 for route in result.routes))
        self.assertTrue(all(route.overflight_exposure_index == 0.0 for route in result.routes))
        self._assert_routes_respect_building_clearance(result.routes, clearance_m=20.0)
        self._assert_routes_avoid_building_footprints(result.routes)

    def test_high_altitude_combined_request_still_avoids_building_footprints(self) -> None:
        planner = CityRoutePlanner.from_payloads(
            city_config=self.city_config,
            city_summary=self.city_summary,
            buildings_geojson=self.buildings,
            weather_geojson=self.weather,
        )
        result = planner.plan(
            PlannerRequest(
                start_lat=30.0,
                start_lon=113.9955,
                end_lat=30.0,
                end_lon=114.0045,
                start_altitude_m=140.0,
                end_altitude_m=140.0,
                min_altitude_m=120.0,
                candidate_count=3,
                cell_m=80.0,
                safety_clearance_m=20.0,
                max_altitude_m=220.0,
            )
        )
        self.assertEqual(len(result.routes), 3)
        self.assertTrue(all(route.overflight_building_count == 0 for route in result.routes))
        self.assertTrue(all(route.overflight_exposure_index == 0.0 for route in result.routes))
        self._assert_routes_respect_building_clearance(result.routes, clearance_m=20.0)
        self._assert_routes_avoid_building_footprints(result.routes)

    def test_plan_falls_back_to_road_graph_when_air_grid_fails(self) -> None:
        planner = CityRoutePlanner.from_payloads(
            city_config=self.city_config,
            city_summary=self.city_summary,
            buildings_geojson=self.buildings,
            weather_geojson=self.weather,
            ground_geojson=self.ground,
        )
        request = PlannerRequest(
            start_lat=30.0,
            start_lon=113.9955,
            end_lat=30.0,
            end_lon=114.0045,
            start_altitude_m=20.0,
            end_altitude_m=20.0,
            min_altitude_m=0.0,
            candidate_count=3,
            cell_m=220.0,
            safety_clearance_m=5.0,
            max_altitude_m=40.0,
        )
        with mock.patch.object(CityRoutePlanner, "_astar", side_effect=RuntimeError("mock air-grid failure")):
            result = planner.plan(request)
        self.assertGreaterEqual(len(result.routes), 1)
        self.assertEqual(result.planner["candidate_count"], len(result.routes))
        self.assertTrue(all(route.waypoint_count >= 2 for route in result.routes))
        self.assertTrue(all(route.overflight_building_count == 0 for route in result.routes))
        self._assert_routes_avoid_building_footprints(result.routes)

    def test_weather_hazard_triggers_horizontal_detour_when_ceiling_is_low(self) -> None:
        severe_nodes = {
            (round(lon, 4), 30.0, altitude_m)
            for lon in (113.9975, 114.0, 114.0025)
            for altitude_m in (0.0, 20.0)
        }
        planner = CityRoutePlanner.from_payloads(
            city_config=self.city_config,
            city_summary=self.city_summary,
            buildings_geojson=self._empty_buildings(),
            weather_geojson=self._weather_with_hazard(severe_nodes=severe_nodes),
        )
        result = planner.plan(
            PlannerRequest(
                start_lat=30.0,
                start_lon=113.9955,
                end_lat=30.0,
                end_lon=114.0045,
                start_altitude_m=0.0,
                end_altitude_m=0.0,
                min_altitude_m=0.0,
                candidate_count=2,
                cell_m=80.0,
                safety_clearance_m=5.0,
                max_altitude_m=20.0,
            )
        )
        self.assertGreaterEqual(len(result.routes), 1)
        self.assertTrue(all(route.max_wind_speed_mps < 12.0 for route in result.routes))
        self.assertTrue(
            any(
                any(abs(float(point["lat"]) - 30.0) > 1e-5 for point in route.waypoints)
                for route in result.routes
            )
        )

    def test_weather_hazard_triggers_altitude_change_when_upper_layer_is_clear(self) -> None:
        severe_nodes = {
            (round(lon, 4), round(lat, 4), altitude_m)
            for lon in (113.9975, 114.0, 114.0025)
            for lat in (29.995, 29.9975, 30.0, 30.0025, 30.005)
            for altitude_m in (0.0, 20.0, 60.0)
        }
        planner = CityRoutePlanner.from_payloads(
            city_config=self.city_config,
            city_summary=self.city_summary,
            buildings_geojson=self._empty_buildings(),
            weather_geojson=self._weather_with_hazard(severe_nodes=severe_nodes),
        )
        result = planner.plan(
            PlannerRequest(
                start_lat=30.0,
                start_lon=113.9955,
                end_lat=30.0,
                end_lon=114.0045,
                start_altitude_m=0.0,
                end_altitude_m=0.0,
                min_altitude_m=0.0,
                candidate_count=2,
                cell_m=80.0,
                safety_clearance_m=5.0,
                max_altitude_m=120.0,
            )
        )
        self.assertGreaterEqual(len(result.routes), 1)
        self.assertTrue(all(route.max_wind_speed_mps < 12.0 for route in result.routes))
        self.assertTrue(
            any(
                any(float(point["altitude_m"]) >= 100.0 for point in route.waypoints)
                for route in result.routes
            )
        )

    def test_pressure_anomaly_triggers_horizontal_detour_when_ceiling_is_low(self) -> None:
        severe_nodes = {
            (round(lon, 4), 30.0, altitude_m)
            for lon in (113.9975, 114.0, 114.0025)
            for altitude_m in (0.0, 20.0)
        }
        for severe_pressure_hpa in (996.0, 1029.0):
            with self.subTest(severe_pressure_hpa=severe_pressure_hpa):
                planner = CityRoutePlanner.from_payloads(
                    city_config=self.city_config,
                    city_summary=self.city_summary,
                    buildings_geojson=self._empty_buildings(),
                    weather_geojson=self._weather_with_hazard(
                        severe_nodes=severe_nodes,
                        severe_wind_speed_mps=3.4,
                        severe_turbulence_index=0.12,
                        severe_precipitation_mm=0.0,
                        severe_pressure_hpa=severe_pressure_hpa,
                    ),
                )
                result = planner.plan(
                    PlannerRequest(
                        start_lat=30.0,
                        start_lon=113.9955,
                        end_lat=30.0,
                        end_lon=114.0045,
                        start_altitude_m=0.0,
                        end_altitude_m=0.0,
                        min_altitude_m=0.0,
                        candidate_count=2,
                        cell_m=80.0,
                        safety_clearance_m=5.0,
                        max_altitude_m=20.0,
                    )
                )
                self.assertGreaterEqual(len(result.routes), 1)
                self.assertTrue(
                    any(
                        any(abs(float(point["lat"]) - 30.0) > 1e-5 for point in route.waypoints)
                        for route in result.routes
                    )
                )

    def test_pressure_anomaly_triggers_altitude_change_when_upper_layer_is_clear(self) -> None:
        severe_nodes = {
            (round(lon, 4), round(lat, 4), altitude_m)
            for lon in (113.9975, 114.0, 114.0025)
            for lat in (29.995, 29.9975, 30.0, 30.0025, 30.005)
            for altitude_m in (0.0, 20.0, 60.0)
        }
        planner = CityRoutePlanner.from_payloads(
            city_config=self.city_config,
            city_summary=self.city_summary,
            buildings_geojson=self._empty_buildings(),
            weather_geojson=self._weather_with_hazard(
                severe_nodes=severe_nodes,
                severe_wind_speed_mps=3.4,
                severe_turbulence_index=0.12,
                severe_precipitation_mm=0.0,
                severe_pressure_hpa=995.0,
            ),
        )
        result = planner.plan(
            PlannerRequest(
                start_lat=30.0,
                start_lon=113.9955,
                end_lat=30.0,
                end_lon=114.0045,
                start_altitude_m=0.0,
                end_altitude_m=0.0,
                min_altitude_m=0.0,
                candidate_count=2,
                cell_m=80.0,
                safety_clearance_m=5.0,
                max_altitude_m=120.0,
            )
        )
        self.assertGreaterEqual(len(result.routes), 1)
        self.assertTrue(
            any(
                any(float(point["altitude_m"]) >= 100.0 for point in route.waypoints)
                for route in result.routes
            )
        )

    def test_weather_only_mode_ignores_buildings(self) -> None:
        planner = CityRoutePlanner.from_payloads(
            city_config=self.city_config,
            city_summary=self.city_summary,
            buildings_geojson=self.buildings,
            weather_geojson=self.weather,
        )
        result = planner.plan(
            PlannerRequest(
                start_lat=30.0,
                start_lon=113.9955,
                end_lat=30.0,
                end_lon=114.0045,
                planning_mode="weather_only",
                start_altitude_m=20.0,
                end_altitude_m=20.0,
                min_altitude_m=0.0,
                candidate_count=1,
                cell_m=80.0,
                safety_clearance_m=20.0,
                max_altitude_m=60.0,
            )
        )
        self.assertEqual(result.planner["planning_mode"], "weather_only")
        self.assertEqual(result.request["planning_mode"], "weather_only")
        route = result.routes[0]
        self.assertEqual(route.average_urban_density, 0.0)
        self.assertEqual(route.overflight_building_count, 0)
        self.assertEqual(route.waypoint_count, 2)
        self.assertAlmostEqual(float(route.waypoints[0]["lat"]), float(route.waypoints[-1]["lat"]), places=6)

    def test_building_only_mode_ignores_weather(self) -> None:
        severe_nodes = {
            (round(lon, 4), 30.0, altitude_m)
            for lon in (113.9975, 114.0, 114.0025)
            for altitude_m in (0.0, 20.0, 60.0, 120.0, 220.0)
        }
        planner = CityRoutePlanner.from_payloads(
            city_config=self.city_config,
            city_summary=self.city_summary,
            buildings_geojson=self._empty_buildings(),
            weather_geojson=self._weather_with_hazard(severe_nodes=severe_nodes),
        )
        result = planner.plan(
            PlannerRequest(
                start_lat=30.0,
                start_lon=113.9955,
                end_lat=30.0,
                end_lon=114.0045,
                planning_mode="building_only",
                start_altitude_m=0.0,
                end_altitude_m=0.0,
                min_altitude_m=0.0,
                candidate_count=1,
                cell_m=80.0,
                safety_clearance_m=5.0,
                max_altitude_m=20.0,
            )
        )
        self.assertEqual(result.planner["planning_mode"], "building_only")
        route = result.routes[0]
        self.assertEqual(route.max_wind_speed_mps, 0.0)
        self.assertEqual(route.max_turbulence_index, 0.0)
        self.assertEqual(route.max_precipitation_mm, 0.0)
        self.assertEqual(route.max_weather_risk_score, 0.0)
        self.assertEqual(route.high_risk_exposure_ratio, 0.0)
        self.assertEqual(route.waypoint_count, 2)
        self.assertAlmostEqual(float(route.waypoints[0]["lat"]), float(route.waypoints[-1]["lat"]), places=6)

    def test_building_only_mode_avoids_building_footprints_with_variable_altitude(self) -> None:
        planner = CityRoutePlanner.from_payloads(
            city_config=self.city_config,
            city_summary=self.city_summary,
            buildings_geojson=self.buildings,
            weather_geojson=self.weather,
        )
        result = planner.plan(
            PlannerRequest(
                start_lat=30.0,
                start_lon=113.9955,
                end_lat=30.0,
                end_lon=114.0045,
                planning_mode="building_only",
                start_altitude_m=20.0,
                end_altitude_m=20.0,
                min_altitude_m=0.0,
                candidate_count=3,
                cell_m=80.0,
                safety_clearance_m=20.0,
                max_altitude_m=220.0,
            )
        )
        self.assertGreaterEqual(len(result.routes), 1)
        self.assertTrue(all(route.overflight_building_count == 0 for route in result.routes))
        self.assertTrue(all(route.overflight_exposure_index == 0.0 for route in result.routes))
        self._assert_routes_avoid_building_footprints(result.routes)

    def test_explicit_max_altitude_is_hard_ceiling(self) -> None:
        planner = CityRoutePlanner.from_payloads(
            city_config=self.city_config,
            city_summary=self.city_summary,
            buildings_geojson=self._empty_buildings(),
            weather_geojson=self.weather,
        )
        result = planner.plan(
            PlannerRequest(
                start_lat=30.0,
                start_lon=113.9955,
                end_lat=30.0,
                end_lon=114.0045,
                planning_mode="building_only",
                start_altitude_m=15.0,
                end_altitude_m=10.0,
                min_altitude_m=0.0,
                candidate_count=5,
                cell_m=80.0,
                safety_clearance_m=5.0,
                max_altitude_m=26.0,
            )
        )
        self.assertEqual(result.planner["max_altitude_m"], 26.0)
        for route in result.routes:
            self.assertLessEqual(max(float(point["altitude_m"]) for point in route.waypoints), 26.0)

    def test_building_only_low_ceiling_generates_distinct_strategy_routes(self) -> None:
        planner = CityRoutePlanner.from_payloads(
            city_config=self.city_config,
            city_summary=self.city_summary,
            buildings_geojson=self.buildings,
            weather_geojson=self.weather,
            ground_geojson=self.ground,
        )
        request = PlannerRequest(
            start_lat=30.0,
            start_lon=113.9955,
            end_lat=30.0,
            end_lon=114.0045,
            planning_mode="building_only",
            start_altitude_m=15.0,
            end_altitude_m=10.0,
            min_altitude_m=0.0,
            candidate_count=5,
            cell_m=220.0,
            safety_clearance_m=5.0,
            max_altitude_m=27.0,
        )
        result = planner.plan(request)
        self.assertEqual(len(result.routes), 5)
        self.assertEqual(
            {route.strategy for route in result.routes},
            {"fastest", "safest", "energy_saving", "balanced_stable", "most_accessible"},
        )
        xy_signatures = {
            tuple((round(float(point["lat"]), 6), round(float(point["lon"]), 6)) for point in route.waypoints)
            for route in result.routes
        }
        altitude_signatures = {
            tuple(round(float(point["altitude_m"]), 1) for point in route.waypoints)
            for route in result.routes
        }
        self.assertGreaterEqual(len(xy_signatures), 4)
        self.assertGreaterEqual(len(altitude_signatures), 3)
        for route in result.routes:
            altitudes = [float(point["altitude_m"]) for point in route.waypoints]
            self.assertLessEqual(max(altitudes), 27.0)
            self.assertGreaterEqual(min(altitudes), 0.0)
        by_strategy = {route.strategy: route for route in result.routes}
        self.assertLessEqual(
            by_strategy["fastest"].estimated_duration_s,
            min(route.estimated_duration_s for route in result.routes) + 1e-6,
        )
        energy_proxy = {
            route.strategy: planner._route_energy_proxy(route, request)
            for route in result.routes
        }
        self.assertLessEqual(
            energy_proxy["energy_saving"],
            min(energy_proxy.values()) + 1e-6,
        )

    def test_building_only_road_fallback_does_not_simplify_through_buildings(self) -> None:
        safe_ground = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"layer": "road"},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [113.9954, 30.0],
                            [113.9964, 30.0],
                        ],
                    },
                },
                {
                    "type": "Feature",
                    "properties": {"layer": "road"},
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [
                            [113.9964, 30.0],
                            [113.9964, 30.0022],
                            [114.0036, 30.0022],
                            [114.0036, 30.0],
                            [114.0046, 30.0],
                        ],
                    },
                },
            ],
        }
        planner = CityRoutePlanner.from_payloads(
            city_config=self.city_config,
            city_summary=self.city_summary,
            buildings_geojson=self.buildings,
            weather_geojson=self.weather,
            ground_geojson=safe_ground,
        )
        request = PlannerRequest(
            start_lat=30.0,
            start_lon=113.9955,
            end_lat=30.0,
            end_lon=114.0045,
            planning_mode="building_only",
            start_altitude_m=20.0,
            end_altitude_m=20.0,
            min_altitude_m=0.0,
            candidate_count=3,
            cell_m=220.0,
            safety_clearance_m=5.0,
            max_altitude_m=40.0,
        )
        with mock.patch.object(CityRoutePlanner, "_astar", side_effect=RuntimeError("mock air-grid failure")):
            result = planner.plan(request)
        self.assertGreaterEqual(len(result.routes), 1)
        self.assertTrue(all(route.overflight_building_count == 0 for route in result.routes))
        self.assertTrue(all(route.overflight_exposure_index == 0.0 for route in result.routes))
        self.assertTrue(
            all(max(float(point["altitude_m"]) for point in route.waypoints) <= request.max_altitude_m for route in result.routes)
        )
        self._assert_routes_avoid_building_footprints(result.routes)

    def test_building_only_projects_unreachable_endpoint_without_crossing_buildings(self) -> None:
        def building(left: float, bottom: float, right: float, top: float) -> dict:
            return {
                "type": "Feature",
                "properties": {"height_m": 80.0},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [left, bottom],
                        [right, bottom],
                        [right, top],
                        [left, top],
                        [left, bottom],
                    ]],
                },
            }

        caged_buildings = {
            "type": "FeatureCollection",
            "features": [
                building(113.9958, 29.9994, 113.9960, 30.0006),
                building(113.9964, 29.9994, 113.9966, 30.0006),
                building(113.9958, 29.9994, 113.9966, 29.9996),
                building(113.9958, 30.0004, 113.9966, 30.0006),
                building(113.9993, 29.9982, 114.0007, 30.0018),
            ],
        }
        planner = CityRoutePlanner.from_payloads(
            city_config=self.city_config,
            city_summary=self.city_summary,
            buildings_geojson=caged_buildings,
            weather_geojson=self.weather,
            ground_geojson=self.ground,
        )
        request = PlannerRequest(
            start_lat=30.0,
            start_lon=113.9962,
            end_lat=30.0,
            end_lon=114.0045,
            planning_mode="building_only",
            start_altitude_m=15.0,
            end_altitude_m=10.0,
            min_altitude_m=0.0,
            candidate_count=2,
            cell_m=220.0,
            safety_clearance_m=5.0,
            max_altitude_m=27.0,
        )
        result = planner.plan(request)
        self.assertGreaterEqual(len(result.routes), 1)
        origin = GeoOrigin(lat=30.0, lon=114.0)
        building_polys = []
        for feature in caged_buildings["features"]:
            ring = (feature.get("geometry") or {}).get("coordinates", [[]])[0]
            building_polys.append([latlon_to_meters(origin, lat, lon) for lon, lat, *_ in ring])
        for route in result.routes:
            for idx in range(1, len(route.waypoints)):
                start = route.waypoints[idx - 1]
                end = route.waypoints[idx]
                start_xy = latlon_to_meters(origin, float(start["lat"]), float(start["lon"]))
                end_xy = latlon_to_meters(origin, float(end["lat"]), float(end["lon"]))
                self.assertFalse(
                    any(segment_hits_poly(start_xy, end_xy, poly) for poly in building_polys),
                    f"路线 {route.route_id} 第 {idx} 段穿过建筑投影",
                )


if __name__ == "__main__":
    unittest.main()
