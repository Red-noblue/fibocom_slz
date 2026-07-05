"""风速计读取逻辑，负责把寄存器数据转换为风速和风级，并对偶发超时做短重试。"""

from __future__ import annotations

import time

from environmental_sensing_hardware.common.models import DeviceConfig, SensorReading
from environmental_sensing_hardware.transports.serial_modbus import ModbusSerialClient


class WindSpeedSensor:
    """读取风速计的实时数据。"""

    def __init__(self, device: DeviceConfig) -> None:
        self.device = device
        self.client = ModbusSerialClient(device, timeout_seconds=0.8)

    def read(self) -> SensorReading:
        """读取风速计寄存器 0 和 1。"""

        last_error: Exception | None = None
        for attempt in range(2):
            try:
                registers, request, response = self.client.read_holding_registers(start=0, count=2)
                break
            except TimeoutError as exc:
                last_error = exc
                if attempt == 1:
                    raise
                time.sleep(0.12)
        else:
            raise last_error or TimeoutError(f"{self.device.port} 未收到 Modbus 应答")
        wind_speed = registers[0] / 10.0
        wind_level = registers[1]
        return SensorReading(
            device_id=self.device.id,
            name=self.device.name,
            type=self.device.type,
            port=self.device.port,
            address=self.device.address,
            status="ok",
            primary_value=wind_speed,
            primary_label="风速",
            primary_unit="m/s",
            secondary_value=float(wind_level),
            secondary_label="风级",
            secondary_unit="级",
            raw_registers=registers,
            request_hex=request.hex(),
            response_hex=response.hex(),
        )
