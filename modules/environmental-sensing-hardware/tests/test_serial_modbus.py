"""串口 Modbus 公共逻辑测试，覆盖 CRC 和寄存器解析。"""

from __future__ import annotations

import unittest

from environmental_sensing_hardware.transports.serial_modbus import (
    build_read_holding_registers_request,
    crc16_modbus,
    parse_holding_registers_response,
)


class SerialModbusTestCase(unittest.TestCase):
    """验证公共 Modbus 帧构造与解析结果。"""

    def test_crc16_matches_document_example(self) -> None:
        payload = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x02])
        self.assertEqual(crc16_modbus(payload), bytes([0xC4, 0x0B]))

    def test_build_read_request_matches_document_example(self) -> None:
        request = build_read_holding_registers_request(address=1, start=0, count=2)
        self.assertEqual(request.hex(), "010300000002c40b")

    def test_parse_holding_registers_response(self) -> None:
        response = bytes.fromhex("0103040c45013a6935")
        registers = parse_holding_registers_response(response, address=1, count=2)
        self.assertEqual(registers, [3141, 314])


if __name__ == "__main__":
    unittest.main()
