"""Open-Meteo 历史天气数据接入。"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def fetch_historical_weather(city: dict[str, Any]) -> dict[str, Any]:
    center = city["center"]
    weather = city["weather"]
    params = {
        "latitude": center["lat"],
        "longitude": center["lon"],
        "start_date": weather["history_date"],
        "end_date": weather["history_date"],
        "hourly": ",".join(weather["hourly"]),
        "timezone": weather.get("timezone", "UTC"),
    }
    url = ARCHIVE_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "uav-virtual-validation/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def write_weather_artifacts(payload: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    raw_path = out / "historical_weather_open_meteo.json"
    with raw_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    return {"raw": str(raw_path)}
