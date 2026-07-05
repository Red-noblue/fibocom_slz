"""历史存储层，使用 SQLite 保存实时采样结果并控制长期运行占用。"""

from __future__ import annotations

import json
import math
import sqlite3
import threading
from pathlib import Path


class HistoryStore:
    """负责读写传感器历史数据。"""

    def __init__(self, database_path: Path, retention_days: int = 3, max_rows: int = 50000) -> None:
        self.database_path = database_path
        self.retention_days = retention_days
        self.max_rows = max_rows
        self._lock = threading.Lock()
        self._write_count = 0
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    def append_readings(self, sampled_at: float, readings: list[dict]) -> None:
        """写入一次采样周期内的全部设备结果。"""

        if not readings:
            return
        with self._lock, sqlite3.connect(self.database_path) as connection:
            connection.executemany(
                """
                INSERT INTO readings (
                    sampled_at,
                    device_id,
                    name,
                    type,
                    port,
                    address,
                    status,
                    primary_value,
                    primary_label,
                    primary_unit,
                    secondary_value,
                    secondary_label,
                    secondary_unit,
                    raw_registers,
                    request_hex,
                    response_hex,
                    error,
                    extra_values
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        sampled_at,
                        item["device_id"],
                        item["name"],
                        item["type"],
                        item["port"],
                        item["address"],
                        item["status"],
                        item["primary_value"],
                        item["primary_label"],
                        item["primary_unit"],
                        item["secondary_value"],
                        item["secondary_label"],
                        item["secondary_unit"],
                        json.dumps(item["raw_registers"], ensure_ascii=False),
                        item["request_hex"],
                        item["response_hex"],
                        item["error"],
                        json.dumps(item.get("extra_values") or [], ensure_ascii=False),
                    )
                    for item in readings
                ],
            )
            connection.commit()
            self._write_count += 1
            if self._write_count % 120 == 0:
                self._purge_expired(connection, sampled_at)
                self._purge_over_limit(connection)
                connection.execute("VACUUM")

    def get_history(self, device_id: str, since_ts: float, max_points: int = 720) -> dict:
        """查询指定设备在给定时间范围内的历史曲线数据。"""

        with self._lock, sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT sampled_at, primary_value, status, error
                FROM readings
                WHERE device_id = ? AND sampled_at >= ?
                ORDER BY sampled_at ASC
                """,
                (device_id, since_ts),
            ).fetchall()

        points = [
            {"sampled_at": row[0], "value": row[1]}
            for row in rows
            if row[1] is not None and row[2] == "ok"
        ]
        error_points = sum(1 for row in rows if row[2] != "ok")
        sampled_points = self._downsample(points, max_points)
        return {
            "total_points": len(rows),
            "ok_points": len(points),
            "error_points": error_points,
            "points": sampled_points,
        }

    def get_metric_histories(self, item: dict, since_ts: float, max_points: int = 720) -> list[dict]:
        """查询单个设备的全部指标曲线。"""

        with self._lock, sqlite3.connect(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT sampled_at, primary_value, secondary_value, extra_values, status, error
                FROM readings
                WHERE device_id = ? AND sampled_at >= ?
                ORDER BY sampled_at ASC
                """,
                (item["device_id"], since_ts),
            ).fetchall()

        series_defs = [
            {
                "metric_key": "primary",
                "name": item["name"],
                "type": item["type"],
                "label": item["primary_label"],
                "unit": item["primary_unit"],
                "precision": self._metric_precision(item["primary_unit"]),
                "value_getter": lambda row: row[1],
            },
        ]
        if item["type"] == "temperature_humidity_pressure":
            series_defs.append(
                {
                    "metric_key": "secondary",
                    "name": item["name"],
                    "type": item["type"],
                    "label": item["secondary_label"],
                    "unit": item["secondary_unit"],
                    "precision": self._metric_precision(item["secondary_unit"]),
                    "value_getter": lambda row: row[2],
                }
            )
            for index, extra in enumerate(item.get("extra_values") or []):
                if extra.get("unit") != "kPa":
                    continue
                series_defs.append(
                    {
                        "metric_key": f"extra-{index}",
                        "name": item["name"],
                        "type": item["type"],
                        "label": extra.get("label", "附加指标"),
                        "unit": extra.get("unit", ""),
                        "precision": extra.get("precision", self._metric_precision(extra.get("unit", ""))),
                        "value_getter": lambda row, extra_index=index: self._extra_value(row[3], extra_index),
                    }
                )

        histories: list[dict] = []
        for definition in series_defs:
            points = []
            for row in rows:
                if row[4] != "ok":
                    continue
                value = definition["value_getter"](row)
                if value is not None:
                    points.append({"sampled_at": row[0], "value": value})
            if not points:
                continue
            histories.append(
                {
                    "device_id": item["device_id"],
                    "metric_key": definition["metric_key"],
                    "series_id": f"{item['device_id']}:{definition['metric_key']}",
                    "name": definition["name"],
                    "type": definition["type"],
                    "primary_label": definition["label"],
                    "primary_unit": definition["unit"],
                    "precision": definition["precision"],
                    "points": self._downsample(points, max_points),
                    "total_points": len(rows),
                    "ok_points": len(points),
                    "error_points": sum(1 for row in rows if row[4] != "ok"),
                }
            )
        return histories

    def _initialize_database(self) -> None:
        """初始化数据表与索引。"""

        with self._lock, sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sampled_at REAL NOT NULL,
                    device_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    port TEXT NOT NULL,
                    address INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    primary_value REAL,
                    primary_label TEXT NOT NULL,
                    primary_unit TEXT NOT NULL,
                    secondary_value REAL,
                    secondary_label TEXT NOT NULL,
                    secondary_unit TEXT NOT NULL,
                    raw_registers TEXT NOT NULL,
                    request_hex TEXT NOT NULL,
                    response_hex TEXT NOT NULL,
                    error TEXT,
                    extra_values TEXT NOT NULL DEFAULT '[]'
                )
                """
            )
            self._ensure_column(connection, "extra_values", "TEXT NOT NULL DEFAULT '[]'")
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_readings_device_time
                ON readings (device_id, sampled_at)
                """
            )
            connection.commit()

    @staticmethod
    def _ensure_column(connection: sqlite3.Connection, column_name: str, definition: str) -> None:
        """为已有数据库补齐新增列。"""

        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(readings)").fetchall()
        }
        if column_name not in columns:
            connection.execute(f"ALTER TABLE readings ADD COLUMN {column_name} {definition}")

    def _purge_expired(self, connection: sqlite3.Connection, sampled_at: float) -> None:
        """删除保留窗口之外的历史数据。"""

        keep_since = sampled_at - self.retention_days * 24 * 3600
        connection.execute("DELETE FROM readings WHERE sampled_at < ?", (keep_since,))
        connection.commit()

    def _purge_over_limit(self, connection: sqlite3.Connection) -> None:
        """按全局行数上限删除最老数据，防止长期运行后数据库膨胀。"""

        total_rows = connection.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
        overflow = total_rows - self.max_rows
        if overflow <= 0:
            return
        connection.execute(
            """
            DELETE FROM readings
            WHERE id IN (
                SELECT id FROM readings
                ORDER BY sampled_at ASC, id ASC
                LIMIT ?
            )
            """,
            (overflow,),
        )
        connection.commit()

    def enforce_limits(self) -> dict:
        """立即执行清理并返回清理后的数据库规模。"""

        with self._lock, sqlite3.connect(self.database_path) as connection:
            row_before = connection.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
            now = connection.execute("SELECT MAX(sampled_at) FROM readings").fetchone()[0]
            if now is not None:
                self._purge_expired(connection, float(now))
            self._purge_over_limit(connection)
            connection.execute("VACUUM")
            row_after = connection.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
        return {
            "row_before": row_before,
            "row_after": row_after,
            "retention_days": self.retention_days,
            "max_rows": self.max_rows,
        }

    @staticmethod
    def _downsample(points: list[dict], max_points: int) -> list[dict]:
        """控制返回点数，避免长时间范围下前端过载。"""

        if len(points) <= max_points:
            return points
        step = math.ceil(len(points) / max_points)
        sampled = points[::step]
        if sampled[-1] != points[-1]:
            sampled.append(points[-1])
        return sampled

    @staticmethod
    def _extra_value(raw_extra_values: str, index: int) -> float | None:
        """从历史行中的附加指标 JSON 取值。"""

        try:
            values = json.loads(raw_extra_values or "[]")
            value = values[index].get("value")
        except (IndexError, TypeError, json.JSONDecodeError, AttributeError):
            return None
        return float(value) if value is not None else None

    @staticmethod
    def _metric_precision(unit: str) -> int:
        """根据单位给出前端曲线的默认显示精度。"""

        if unit == "kPa":
            return 2
        if unit in {"℃", "%RH", "m/s", "°", "hPa"}:
            return 1
        return 0
