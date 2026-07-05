"""导出 Cesium CZML 预览数据。"""

from __future__ import annotations

from typing import Any

from uav_virtual_validation.world.models import GeneratedWorld


def world_route_to_czml(world: GeneratedWorld, altitude_m: float) -> list[dict[str, Any]]:
    positions: list[float] = []
    for lat, lon in world.route_points:
        positions.extend([lon, lat, altitude_m])
    return [
        {
            "id": "document",
            "name": f"{world.name}_route",
            "version": "1.0",
        },
        {
            "id": "route_corridor",
            "name": "UAV 计划航线",
            "polyline": {
                "positions": {"cartographicDegrees": positions},
                "width": 4,
                "material": {
                    "solidColor": {
                        "color": {"rgba": [15, 123, 108, 255]}
                    }
                },
                "clampToGround": False,
            },
        },
    ]
