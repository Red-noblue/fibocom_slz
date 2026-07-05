"""验证天气时间对齐与飞行时刻构造的基础行为。"""

from __future__ import annotations

import pandas as pd

from uav_energy_engine.weather import build_flight_time_index, circular_interp_deg, height_aware_wind, interpolate_weather


def test_build_flight_time_index_uses_local_start_time():
    """本地起飞时间加相对秒数应形成绝对时刻索引。"""

    frame = pd.DataFrame(
        {
            "date": ["2019-05-06", "2019-05-06"],
            "local_time": ["15:56", "15:56"],
            "time": [0.0, 30.0],
        }
    )
    index = build_flight_time_index(frame, timezone="America/New_York")
    assert str(index[0]) == "2019-05-06 15:56:00-04:00"
    assert str(index[1]) == "2019-05-06 15:56:30-04:00"


def test_interpolate_weather_aligns_hourly_to_subminute():
    """逐小时天气应可插值到飞行采样时刻。"""

    weather = pd.DataFrame(
        {"temperature_c": [10.0, 14.0]},
        index=pd.DatetimeIndex(
            ["2019-05-06 15:00:00-04:00", "2019-05-06 16:00:00-04:00"]
        ),
    )
    target = pd.DatetimeIndex(
        ["2019-05-06 15:30:00-04:00", "2019-05-06 15:45:00-04:00"]
    )
    out = interpolate_weather(weather, target)
    assert round(float(out.iloc[0]["temperature_c"]), 6) == 12.0
    assert round(float(out.iloc[1]["temperature_c"]), 6) == 13.0


def test_height_aware_wind_interpolates_between_10m_and_100m():
    """高度层风场应在 10m 和 100m 风之间插值。"""

    row = pd.Series(
        {
            "wind_speed_mps": 2.0,
            "wind_dir_deg": 350.0,
            "wind_speed_100m_mps": 6.0,
            "wind_dir_100m_deg": 10.0,
        }
    )
    speed, direction = height_aware_wind(row, altitude_m=55.0)

    assert round(speed, 6) == 4.0
    assert direction < 20.0 or direction > 340.0


def test_circular_interp_deg_crosses_zero_degrees():
    """角度插值应正确跨越 0 度。"""

    assert circular_interp_deg(350.0, 10.0, 0.5) < 1.0
