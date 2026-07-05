"""温湿度气压计读取逻辑，负责把寄存器数据转换为湿度、温度和气压。"""

from __future__ import annotations

from environmental_sensing_hardware.common.models import DeviceConfig, SensorReading
from environmental_sensing_hardware.transports.serial_modbus import ModbusSerialClient


def _signed_16bit(value: int) -> int:
    """把 16 位寄存器值转换为有符号整数。"""

    return value - 0x10000 if value & 0x8000 else value


class TemperatureHumidityPressureSensor:
    """读取温湿度气压计的实时数据。"""

    def __init__(self, device: DeviceConfig) -> None:
        self.device = device
        self.client = ModbusSerialClient(device)

    def read(self) -> SensorReading:
        """读取湿度、温度和气压寄存器。"""

        registers, request, response = self.client.read_holding_registers(start=0, count=2)
        pressure_registers, pressure_request, pressure_response = self.client.read_holding_registers(
            start=0x0010,
            count=1,
        )
        humidity = registers[0] / 10.0
        temperature = _signed_16bit(registers[1]) / 10.0
        pressure_kpa = pressure_registers[0] / 100.0

        return SensorReading(
            device_id=self.device.id,
            name=self.device.name,
            type=self.device.type,
            port=self.device.port,
            address=self.device.address,
            status="ok",
            primary_value=temperature,
            primary_label="温度",
            primary_unit="℃",
            secondary_value=humidity,
            secondary_label="湿度",
            secondary_unit="%RH",
            raw_registers=registers + pressure_registers,
            request_hex=f"{request.hex()} / {pressure_request.hex()}",
            response_hex=f"{response.hex()} / {pressure_response.hex()}",
            extra_values=[
                {
                    "label": "气压",
                    "value": pressure_kpa,
                    "unit": "kPa",
                    "precision": 2,
                },
            ],
        )
