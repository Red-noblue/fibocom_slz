"""历史存储测试，验证 SQLite 写入与历史查询逻辑。"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from environmental_sensing_hardware.storage.history_store import HistoryStore


class HistoryStoreTestCase(unittest.TestCase):
    """验证历史存储的基础行为。"""

    def test_append_and_query_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "history.sqlite3"
            store = HistoryStore(database_path)
            store.append_readings(
                1000.0,
                [
                    {
                        "device_id": "wind-direction-1",
                        "name": "风向计",
                        "type": "wind_direction",
                        "port": "/dev/ttyUSB0",
                        "address": 1,
                        "status": "ok",
                        "primary_value": 306.7,
                        "primary_label": "风向",
                        "primary_unit": "°",
                        "secondary_value": 306.0,
                        "secondary_label": "整数风向",
                        "secondary_unit": "°",
                        "raw_registers": [3067, 306],
                        "request_hex": "010300000002c40b",
                        "response_hex": "0103040bfb013209a3",
                        "error": None,
                    },
                    {
                        "device_id": "wind-speed-1",
                        "name": "风速计",
                        "type": "wind_speed",
                        "port": "/dev/ttyUSB1",
                        "address": 1,
                        "status": "error",
                        "primary_value": None,
                        "primary_label": "风速",
                        "primary_unit": "m/s",
                        "secondary_value": None,
                        "secondary_label": "风级",
                        "secondary_unit": "级",
                        "raw_registers": [],
                        "request_hex": "",
                        "response_hex": "",
                        "error": "timeout",
                    },
                ],
            )

            history = store.get_history("wind-direction-1", since_ts=900.0, max_points=100)
            self.assertEqual(history["total_points"], 1)
            self.assertEqual(history["ok_points"], 1)
            self.assertEqual(history["error_points"], 0)
            self.assertEqual(history["points"][0]["value"], 306.7)

            error_history = store.get_history("wind-speed-1", since_ts=900.0, max_points=100)
            self.assertEqual(error_history["total_points"], 1)
            self.assertEqual(error_history["ok_points"], 0)
            self.assertEqual(error_history["error_points"], 1)
            self.assertEqual(error_history["points"], [])


if __name__ == "__main__":
    unittest.main()
