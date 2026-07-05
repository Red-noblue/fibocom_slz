"""设备自动识别器，通过 Modbus 寄存器特征判断当前串口连接的传感器类型。"""

from __future__ import annotations

from dataclasses import dataclass
from glob import glob

from environmental_sensing_hardware.common.models import DeviceConfig
from environmental_sensing_hardware.transports.serial_modbus import ModbusSerialClient


@dataclass(frozen=True)
class ProbeResult:
    """记录一次设备探测的匹配结果。"""

    config: DeviceConfig
    score: int
    reason: str


def discover_modbus_devices(
    ports: list[str] | None = None,
    addresses: list[int] | None = None,
) -> list[DeviceConfig]:
    """扫描本机串口，并返回识别出的环境测量设备配置。"""

    scan_ports = ports or sorted(glob("/dev/ttyUSB*") + glob("/dev/ttyACM*"))
    scan_addresses = addresses or [1, 16]
    results: list[ProbeResult] = []
    for port in scan_ports:
        best = _probe_port(port, scan_addresses)
        if best is not None:
            results.append(best)
    return [result.config for result in sorted(results, key=lambda item: item.config.id)]


def _probe_port(port: str, addresses: list[int]) -> ProbeResult | None:
    """返回单个串口最可信的设备识别结果。"""

    probes: list[ProbeResult] = []
    for baudrate in (9600, 4800):
        for address in addresses:
            config = DeviceConfig(
                id="probe",
                name="探测设备",
                type="probe",
                port=port,
                address=address,
                baudrate=baudrate,
                detected=True,
            )
            client = ModbusSerialClient(config, timeout_seconds=0.35)
            registers = _read_registers(client, start=0, count=2)
            if registers is None:
                continue
            pressure = _read_registers(client, start=0x0010, count=1)
            if pressure is not None:
                matched = _match_temperature_humidity_pressure(port, address, baudrate, registers, pressure[0])
                if matched:
                    probes.append(matched)
            wind_speed = _match_wind_speed(port, address, baudrate, registers)
            if wind_speed:
                probes.append(wind_speed)
            wind_direction = _match_wind_direction(port, address, baudrate, registers)
            if wind_direction:
                probes.append(wind_direction)
    if not probes:
        return None
    return sorted(probes, key=lambda item: item.score, reverse=True)[0]


def _read_registers(client: ModbusSerialClient, start: int, count: int) -> list[int] | None:
    """读取寄存器；探测阶段失败视为不匹配。"""

    try:
        registers, _, _ = client.read_holding_registers(start=start, count=count)
    except Exception:  # noqa: BLE001
        return None
    return registers


def _match_temperature_humidity_pressure(
    port: str,
    address: int,
    baudrate: int,
    registers: list[int],
    pressure_raw: int,
) -> ProbeResult | None:
    """根据温湿度气压寄存器范围判断三合一传感器。"""

    humidity = registers[0] / 10.0
    temperature = _signed_16bit(registers[1]) / 10.0
    pressure_kpa = pressure_raw / 100.0
    if 0 <= humidity <= 100 and -40 <= temperature <= 80 and 30 <= pressure_kpa <= 120:
        return ProbeResult(
            config=DeviceConfig(
                id=_device_id("temperature-humidity-pressure", port),
                name="温湿度气压计",
                type="temperature_humidity_pressure",
                port=port,
                address=address,
                baudrate=baudrate,
                detected=True,
            ),
            score=100,
            reason=f"湿度={humidity:.1f}%RH 温度={temperature:.1f}℃ 气压={pressure_kpa:.2f}kPa",
        )
    return None


def _match_wind_direction(
    port: str,
    address: int,
    baudrate: int,
    registers: list[int],
) -> ProbeResult | None:
    """根据风向寄存器特征判断风向计。"""

    decimal_degrees = registers[0] / 10.0
    integer_degrees = registers[1]
    if 0 <= decimal_degrees <= 360 and 0 <= integer_degrees <= 360:
        if registers == [0, 0]:
            return None
        return ProbeResult(
            config=DeviceConfig(
                id=_device_id("wind-direction", port),
                name="风向计",
                type="wind_direction",
                port=port,
                address=address,
                baudrate=baudrate,
                detected=True,
            ),
            score=60 if baudrate == 4800 else 40,
            reason=f"风向={decimal_degrees:.1f}° 整数风向={integer_degrees}°",
        )
    return None


def _match_wind_speed(
    port: str,
    address: int,
    baudrate: int,
    registers: list[int],
) -> ProbeResult | None:
    """根据风速寄存器特征判断风速计。"""

    wind_speed = registers[0] / 10.0
    wind_level = registers[1]
    if 0 <= wind_speed <= 75 and 0 <= wind_level <= 17:
        return ProbeResult(
            config=DeviceConfig(
                id=_device_id("wind-speed", port),
                name="风速计",
                type="wind_speed",
                port=port,
                address=address,
                baudrate=baudrate,
                detected=True,
            ),
            score=65 if registers == [0, 0] else 55 if baudrate == 4800 else 35,
            reason=f"风速={wind_speed:.1f}m/s 风级={wind_level}",
        )
    return None


def _signed_16bit(value: int) -> int:
    """把 16 位寄存器值转换为有符号整数。"""

    return value - 0x10000 if value & 0x8000 else value


def _device_id(prefix: str, port: str) -> str:
    """用设备类型和串口名生成稳定设备编号。"""

    return f"{prefix}-{port.rsplit('/', 1)[-1].lower()}"
