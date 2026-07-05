"""设备自动识别测试，验证寄存器特征能映射到正确硬件类型。"""

from __future__ import annotations

import unittest

from environmental_sensing_hardware.registry.device_discovery import (
    _match_temperature_humidity_pressure,
    _match_wind_direction,
    _match_wind_speed,
)


class DeviceDiscoveryTestCase(unittest.TestCase):
    """验证自动识别规则的基础行为。"""

    def test_match_temperature_humidity_pressure(self) -> None:
        result = _match_temperature_humidity_pressure("/dev/ttyUSB0", 1, 9600, [446, 245], 10001)
        self.assertIsNotNone(result)
        self.assertEqual(result.config.type, "temperature_humidity_pressure")
        self.assertEqual(result.config.baudrate, 9600)

    def test_match_wind_direction(self) -> None:
        result = _match_wind_direction("/dev/ttyUSB1", 1, 4800, [498, 49])
        self.assertIsNotNone(result)
        self.assertEqual(result.config.type, "wind_direction")

    def test_match_wind_speed(self) -> None:
        result = _match_wind_speed("/dev/ttyUSB2", 1, 4800, [0, 0])
        self.assertIsNotNone(result)
        self.assertEqual(result.config.type, "wind_speed")

    def test_zero_registers_do_not_match_wind_direction(self) -> None:
        result = _match_wind_direction("/dev/ttyUSB2", 1, 4800, [0, 0])
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
