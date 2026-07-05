"""环境测量硬件模块的公共数据模型。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class DeviceConfig:
    """描述一个串口设备的基础连接参数。"""

    id: str
    name: str
    type: str
    port: str
    address: int
    baudrate: int
    data_bits: int = 8
    parity: str = "N"
    stop_bits: int = 1
    detected: bool = False


@dataclass(frozen=True)
class SensorReading:
    """描述一次传感器读取结果。"""

    device_id: str
    name: str
    type: str
    port: str
    address: int
    status: str
    primary_value: float | None
    primary_label: str
    primary_unit: str
    secondary_value: float | None
    secondary_label: str
    secondary_unit: str
    raw_registers: list[int]
    request_hex: str
    response_hex: str
    error: str | None = None
    extra_values: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为可直接返回给接口的字典。"""

        return asdict(self)
