from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import requests


class WeatherConfigError(Exception):
    """Raised when the weather adapter config is invalid."""


def _parse_path(path: str):
    tokens = []
    buf = ""
    idx = 0
    while idx < len(path):
        ch = path[idx]
        if ch == ".":
            if buf:
                tokens.append(buf)
                buf = ""
            idx += 1
            continue
        if ch == "[":
            if buf:
                tokens.append(buf)
                buf = ""
            end = path.find("]", idx)
            if end == -1:
                raise WeatherConfigError(f"Invalid path token: {path}")
            tokens.append(int(path[idx + 1 : end]))
            idx = end + 1
            continue
        buf += ch
        idx += 1
    if buf:
        tokens.append(buf)
    return tokens


def extract_path(data: Any, path: str):
    cur = data
    for token in _parse_path(path):
        if isinstance(token, int):
            if not isinstance(cur, list):
                raise WeatherConfigError(f"Expected list at {token} in path {path}")
            if token >= len(cur):
                raise WeatherConfigError(f"Index {token} out of range for path {path}")
            cur = cur[token]
        else:
            if not isinstance(cur, dict):
                raise WeatherConfigError(f"Expected dict at {token} in path {path}")
            if token not in cur:
                raise WeatherConfigError(f"Missing key '{token}' for path {path}")
            cur = cur[token]
    return cur


def apply_template(value: Any, mapping: dict[str, str]):
    if not isinstance(value, str):
        return value
    out = value
    for key, item in mapping.items():
        out = out.replace("{" + key + "}", item)
    return out


def normalize_field(values, scale: float, offset: float):
    if isinstance(values, list):
        series = pd.to_numeric(pd.Series(values), errors="coerce")
        return (series * scale + offset).tolist()
    numeric = pd.to_numeric(pd.Series([values]), errors="coerce").iloc[0]
    return [float(numeric) * scale + offset]


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise WeatherConfigError(f"Config not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


class GenericWeatherClient:
    def __init__(self, config_path: str | Path, api_key: str | None = None) -> None:
        self.config = load_config(config_path)
        self.api_key = api_key or os.environ.get("CMA_API_KEY")

    def fetch_hourly(
        self,
        latitude: float,
        longitude: float,
        extra_params: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        base_url = self.config.get("base_url")
        if not base_url:
            raise WeatherConfigError("base_url missing in weather config.")

        template = {
            "lat": str(latitude),
            "lon": str(longitude),
            "API_KEY": self.api_key or "",
        }

        params = {
            key: apply_template(value, template)
            for key, value in (self.config.get("params") or {}).items()
        }
        if extra_params:
            for key, value in extra_params.items():
                if value is None:
                    params.pop(key, None)
                else:
                    params[key] = apply_template(value, template)

        headers = {
            key: apply_template(value, template)
            for key, value in (self.config.get("headers") or {}).items()
        }

        method = str(self.config.get("method", "GET")).upper()
        if method == "GET":
            response = requests.get(base_url, params=params, headers=headers, timeout=30)
        else:
            response = requests.post(base_url, json=params, headers=headers, timeout=30)

        response.raise_for_status()
        payload = response.json()

        time_spec = self.config.get("time")
        if time_spec:
            time_path = time_spec.get("path")
            if not time_path:
                raise WeatherConfigError("time.path missing in weather config.")
            time_values = extract_path(payload, time_path)
            time_values = time_values if isinstance(time_values, list) else [time_values]
            if time_spec.get("epoch_unit"):
                times = pd.to_datetime(time_values, unit=time_spec["epoch_unit"], utc=True)
            elif time_spec.get("format"):
                times = pd.to_datetime(time_values, format=time_spec["format"], errors="coerce")
            else:
                times = pd.to_datetime(time_values, errors="coerce")
        else:
            times = pd.to_datetime([pd.Timestamp.now()])

        fields = self.config.get("fields")
        if not fields:
            raise WeatherConfigError("fields missing in weather config.")

        data: dict[str, list] = {}
        for name, spec in fields.items():
            if isinstance(spec, str):
                path = spec
                scale = 1.0
                offset = 0.0
            else:
                path = spec.get("path")
                if not path:
                    raise WeatherConfigError(f"Missing path for field {name}")
                scale = float(spec.get("scale", 1.0))
                offset = float(spec.get("offset", 0.0))
            values = extract_path(payload, path)
            data[name] = normalize_field(values, scale, offset)

        df = pd.DataFrame(data)
        if len(df) == 1 and len(times) > 1:
            df = pd.concat([df] * len(times), ignore_index=True)
        if len(times) == 1 and len(df) > 1:
            times = pd.to_datetime([times[0]] * len(df))

        df.index = pd.DatetimeIndex(times)
        df.index.name = "time"

        timezone = self.config.get("timezone")
        if timezone:
            if df.index.tz is None:
                df.index = df.index.tz_localize(timezone)
            else:
                df.index = df.index.tz_convert(timezone)
        return df
