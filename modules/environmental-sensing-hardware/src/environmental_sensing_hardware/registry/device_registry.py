"""设备注册层，统一加载配置并分发到对应硬件读取器。"""

from __future__ import annotations

import json
import time
from pathlib import Path

from environmental_sensing_hardware.common.models import DeviceConfig, SensorReading
from environmental_sensing_hardware.devices.temperature_humidity_pressure.reader import (
    TemperatureHumidityPressureSensor,
)
from environmental_sensing_hardware.devices.wind_direction.reader import WindDirectionSensor
from environmental_sensing_hardware.devices.wind_speed.reader import WindSpeedSensor
from environmental_sensing_hardware.registry.device_discovery import discover_modbus_devices


class DeviceRegistry:
    """按配置创建设备实例，并统一返回当前采样结果。"""

    def __init__(
        self,
        config_path: Path,
        auto_discover: bool = True,
        discovery_interval_seconds: int = 30,
    ) -> None:
        self.config_path = config_path
        self.auto_discover = auto_discover
        self.discovery_interval_seconds = discovery_interval_seconds
        self.discovery_error: str | None = None
        self._last_discovery_at: float | None = None
        self.devices = self._load_devices()

    def _load_devices(self) -> list[DeviceConfig]:
        """从 JSON 配置中加载设备列表。"""

        if self.auto_discover:
            try:
                discovered = discover_modbus_devices()
            except Exception as exc:  # noqa: BLE001
                self.discovery_error = str(exc)
            else:
                self.discovery_error = None
                self._last_discovery_at = time.time()
                if discovered:
                    return discovered

        payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        devices: list[DeviceConfig] = []
        for item in payload.get("devices", []):
            devices.append(DeviceConfig(**item))
        return devices

    def read_all(self) -> list[dict]:
        """读取所有设备，单个失败不会影响其他设备。"""

        if self.auto_discover and self._should_refresh_discovery():
            self.refresh_discovered_devices()

        results: list[dict] = []
        for device in self.devices:
            try:
                reading = self._build_reader(device).read()
            except Exception as exc:  # noqa: BLE001
                reading = SensorReading(
                    device_id=device.id,
                    name=device.name,
                    type=device.type,
                    port=device.port,
                    address=device.address,
                    status="error",
                    primary_value=None,
                    primary_label="主值",
                    primary_unit="",
                    secondary_value=None,
                    secondary_label="副值",
                    secondary_unit="",
                    raw_registers=[],
                    request_hex="",
                    response_hex="",
                    error=str(exc),
                    extra_values=[],
                )
            results.append(reading.to_dict())
        return results

    def refresh_discovered_devices(self) -> None:
        """刷新自动识别到的设备；识别失败时保留上一轮设备列表。"""

        try:
            discovered = discover_modbus_devices()
        except Exception as exc:  # noqa: BLE001
            self.discovery_error = str(exc)
            return
        self.discovery_error = None
        self._last_discovery_at = time.time()
        if discovered:
            self.devices = discovered

    def _should_refresh_discovery(self) -> bool:
        """判断是否到达下一次自动识别窗口。"""

        if self._last_discovery_at is None:
            return True
        return time.time() - self._last_discovery_at >= self.discovery_interval_seconds

    def _build_reader(self, device: DeviceConfig):
        """按设备类型创建对应读取器。"""

        if device.type == "wind_direction":
            return WindDirectionSensor(device)
        if device.type == "wind_speed":
            return WindSpeedSensor(device)
        if device.type == "temperature_humidity_pressure":
            return TemperatureHumidityPressureSensor(device)
        raise ValueError(f"未知设备类型: {device.type}")
