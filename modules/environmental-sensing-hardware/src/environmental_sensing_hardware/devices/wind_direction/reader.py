"""风向计读取逻辑，负责把寄存器数据转换为风向角。"""

from __future__ import annotations

from environmental_sensing_hardware.common.models import DeviceConfig, SensorReading
from environmental_sensing_hardware.transports.serial_modbus import ModbusSerialClient


class WindDirectionSensor:
    """读取风向计的实时数据。"""

    def __init__(self, device: DeviceConfig) -> None:
        self.device = device
        self.client = ModbusSerialClient(device)

    def read(self) -> SensorReading:
        """读取风向计寄存器 0 和 1。"""

        registers, request, response = self.client.read_holding_registers(start=0, count=2)
        decimal_degrees = registers[0] / 10.0
        integer_degrees = registers[1]
        return SensorReading(
            device_id=self.device.id,
            name=self.device.name,
            type=self.device.type,
            port=self.device.port,
            address=self.device.address,
            status="ok",
            primary_value=decimal_degrees,
            primary_label="风向",
            primary_unit="°",
            secondary_value=float(integer_degrees),
            secondary_label="整数风向",
            secondary_unit="°",
            raw_registers=registers,
            request_hex=request.hex(),
            response_hex=response.hex(),
        )
