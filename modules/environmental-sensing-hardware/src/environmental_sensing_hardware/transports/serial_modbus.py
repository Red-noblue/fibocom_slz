"""基于标准库实现的 Modbus RTU 串口访问层。"""

from __future__ import annotations

import os
import select
import termios
import threading
import time
from pathlib import Path

from environmental_sensing_hardware.common.models import DeviceConfig

_PORT_LOCKS: dict[str, threading.Lock] = {}
_PORT_LOCKS_GUARD = threading.Lock()


def crc16_modbus(payload: bytes) -> bytes:
    """计算 Modbus RTU 所需的 CRC16 校验。"""

    crc = 0xFFFF
    for byte in payload:
        crc ^= byte
        for _ in range(8):
            if crc & 0x01:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return bytes((crc & 0xFF, (crc >> 8) & 0xFF))


def build_read_holding_registers_request(address: int, start: int, count: int) -> bytes:
    """构造功能码 03 的读保持寄存器请求帧。"""

    payload = bytes(
        [
            address,
            0x03,
            (start >> 8) & 0xFF,
            start & 0xFF,
            (count >> 8) & 0xFF,
            count & 0xFF,
        ]
    )
    return payload + crc16_modbus(payload)


def parse_holding_registers_response(response: bytes, address: int, count: int) -> list[int]:
    """校验并解析功能码 03 的应答帧。"""

    expected_length = 5 + count * 2
    if len(response) < expected_length:
        raise ValueError(f"应答长度不足，期望至少 {expected_length} 字节，实际 {len(response)} 字节")
    if response[0] != address:
        raise ValueError(f"应答地址不匹配，期望 {address}，实际 {response[0]}")
    if response[1] & 0x80:
        raise ValueError(f"设备返回异常码 0x{response[2]:02X}")
    if response[1] != 0x03:
        raise ValueError(f"应答功能码不匹配，期望 0x03，实际 0x{response[1]:02X}")
    if response[2] != count * 2:
        raise ValueError(f"应答字节数不匹配，期望 {count * 2}，实际 {response[2]}")
    expected_crc = crc16_modbus(response[:-2])
    if response[-2:] != expected_crc:
        raise ValueError(
            f"CRC 校验失败，期望 {expected_crc.hex()}，实际 {response[-2:].hex()}"
        )

    registers: list[int] = []
    data = response[3 : 3 + count * 2]
    for index in range(0, len(data), 2):
        registers.append((data[index] << 8) | data[index + 1])
    return registers


def _get_port_lock(port: str) -> threading.Lock:
    """为每个串口返回一个独立锁，避免并发访问互相干扰。"""

    with _PORT_LOCKS_GUARD:
        return _PORT_LOCKS.setdefault(port, threading.Lock())


class ModbusSerialClient:
    """针对单个串口设备的最小 Modbus RTU 客户端。"""

    def __init__(self, device: DeviceConfig, timeout_seconds: float = 0.45) -> None:
        self.device = device
        self.timeout_seconds = timeout_seconds

    def read_holding_registers(self, start: int, count: int) -> tuple[list[int], bytes, bytes]:
        """读取保持寄存器并返回寄存器值、请求帧和应答帧。"""

        port_path = Path(self.device.port)
        if not port_path.exists():
            raise FileNotFoundError(f"串口不存在: {self.device.port}")

        request = build_read_holding_registers_request(self.device.address, start, count)
        with _get_port_lock(self.device.port):
            fd = os.open(self.device.port, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
            try:
                self._configure_serial(fd)
                os.write(fd, request)
                time.sleep(0.05)
                response = self._receive_response(fd)
            finally:
                os.close(fd)

        registers = parse_holding_registers_response(response, self.device.address, count)
        return registers, request, response

    def _configure_serial(self, fd: int) -> None:
        """使用 termios 配置波特率、校验和停止位。"""

        attrs = termios.tcgetattr(fd)
        attrs[0] = 0
        attrs[1] = 0
        attrs[2] = termios.CLOCAL | termios.CREAD
        attrs[2] |= self._data_bits_mask()
        attrs[2] |= self._parity_mask()
        if self.device.stop_bits == 2:
            attrs[2] |= termios.CSTOPB
        attrs[3] = 0
        speed = self._baudrate_constant()
        attrs[4] = speed
        attrs[5] = speed
        attrs[6][termios.VMIN] = 0
        attrs[6][termios.VTIME] = 1
        termios.tcflush(fd, termios.TCIOFLUSH)
        termios.tcsetattr(fd, termios.TCSANOW, attrs)

    def _receive_response(self, fd: int) -> bytes:
        """接收直到超时，适合短帧 Modbus RTU 应答。"""

        response = bytearray()
        deadline = time.time() + self.timeout_seconds
        while time.time() < deadline:
            readable, _, _ = select.select([fd], [], [], 0.05)
            if fd not in readable:
                continue
            chunk = os.read(fd, 256)
            if not chunk:
                continue
            response.extend(chunk)
            deadline = time.time() + 0.08
        if not response:
            raise TimeoutError(f"{self.device.port} 未收到 Modbus 应答")
        return bytes(response)

    def _baudrate_constant(self) -> int:
        """将整数波特率映射为 termios 常量。"""

        baudrate_map = {
            2400: termios.B2400,
            4800: termios.B4800,
            9600: termios.B9600,
            19200: termios.B19200,
        }
        try:
            return baudrate_map[self.device.baudrate]
        except KeyError as exc:
            raise ValueError(f"暂不支持的波特率: {self.device.baudrate}") from exc

    def _data_bits_mask(self) -> int:
        """返回数据位掩码。"""

        if self.device.data_bits != 8:
            raise ValueError(f"暂不支持的数据位长度: {self.device.data_bits}")
        return termios.CS8

    def _parity_mask(self) -> int:
        """返回校验位掩码。"""

        parity = self.device.parity.upper()
        if parity == "N":
            return 0
        if parity == "E":
            return termios.PARENB
        if parity == "O":
            return termios.PARENB | termios.PARODD
        raise ValueError(f"暂不支持的校验方式: {self.device.parity}")
