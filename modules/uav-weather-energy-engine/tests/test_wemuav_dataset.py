"""验证 WEMUAV 数据集适配器能输出统一飞行日志。"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd

from uav_energy_engine.dataset import build_training_dataset
from uav_energy_engine.wemuav_dataset import prepare_wemuav_dataset


def test_prepare_wemuav_dataset_from_zip(tmp_path: Path):
    """WEMUAV 适配器应裁剪任务时间窗并完成单位转换。"""

    dataset_root = tmp_path / "wemuav"
    dataset_root.mkdir()

    overview = pd.DataFrame(
        [
            {
                "DataStartTimeString": "19-Apr-2021 09:31:07",
                "DataEndTimeString": "19-Apr-2021 09:31:20",
                "ID": 1,
                "FOLDER": "EPFL20210419",
                "FLIGHT": "FLY134.csv",
                "FLIGHTDATATYPE": "datconv4",
                "REF": "2021-04-19_Mesures_MoTUS",
                "REFDATATYPE": "motus",
                "REFMETEO": "18-Apr-2021.txt",
                "REFMETEODATATYPE": "topoaws",
                "FlightType": "Hover",
                "Mean windHMag [m/s]": 2.5,
            },
            {
                "DataStartTimeString": "27-Apr-2020 10:00:00",
                "DataEndTimeString": "27-Apr-2020 10:00:13",
                "ID": 2,
                "FOLDER": "Svalbard20200427",
                "FLIGHT": "FLY059.csv",
                "FLIGHTDATATYPE": "datconv3",
                "REF": "",
                "REFDATATYPE": "",
                "REFMETEO": "-",
                "REFMETEODATATYPE": "",
                "FlightType": "Vertical2ms",
                "Mean windHMag [m/s]": 1.8,
            }
        ]
    )
    overview.to_csv(dataset_root / "01_DATA_OVERVIEW.csv", index=False)

    flight_csv = (
        "Clock:offsetTime,GPS:dateTimeStamp,IMU_ATTI(0):Longitude,IMU_ATTI(0):Latitude,"
        "IMU_ATTI(0):relativeHeight:C,IMU_ATTI(0):velH:C,BatteryInfo:BatVol:D,"
        "BatteryInfo:BatCurrent:D,AirSpeed:windSpeed,AirSpeed:windDirection\n"
        "100.0,2021-04-19T09:31:07Z,116.0000,39.0000,10.0,2.0,16000,-1500,3.0,90\n"
        "113.0,2021-04-19T09:31:20Z,116.0003,39.0003,10.2,2.2,15900,-1600,3.2,100\n"
        "200.0,2021-04-19T09:40:00Z,116.0100,39.0100,10.0,2.0,15800,-1500,3.0,90\n"
    )
    weather_txt = (
        '"TOA5","demo","CR1000"\n'
        '"TIMESTAMP","WindSpeed","WindDir","AirTemp1","AirHumidity","AtmPressure"\n'
        '"TS","","","","",""\n'
        '"","","","","",""\n'
        '"2021-04-19 09:31:07",4.0,90,10.0,50,1000\n'
        '"2021-04-19 09:31:20",6.0,100,12.0,60,1002\n'
    )

    zip_path = dataset_root / "02_EPFL_FLIGHTS.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("EPFL20210419/FLIGHT/FLY134.csv", flight_csv)
        zf.writestr("EPFL20210419/WEATHER/18-Apr-2021.txt", weather_txt)

    svalbard_flight_csv = (
        "Clock:offsetTime,GPS:dateTimeStamp,GPS:Long,GPS:Lat,GPS:heightMSL,GPS:velH,"
        "BattInfo:vol_t,BattInfo:Pack_ve,BattInfo:Ad_v,BattInfo:Current\n"
        "0.0,2020-04-27T10:00:00Z,15.0000,78.0000,20.0,1.0,12800,15.006,15.020,1.522\n"
        "13.0,2020-04-27T10:00:13Z,15.0002,78.0002,22.0,1.1,12800,14.990,15.000,1.500\n"
    )
    svalbard_zip_path = dataset_root / "03_SVALBARD_FLIGHTS.zip"
    with zipfile.ZipFile(svalbard_zip_path, "w") as zf:
        zf.writestr("Svalbard20200427/FLIGHT/FLY059.csv", svalbard_flight_csv)

    output_csv = dataset_root / "wemuav_flights.csv"
    out = prepare_wemuav_dataset(
        dataset_root=dataset_root,
        output_csv=output_csv,
        flight_id_offset=1000,
    )

    assert output_csv.exists()
    assert len(out) == 4
    assert list(out["flight"].unique()) == [1001, 1002]

    epfl = out[out["flight"] == 1001].reset_index(drop=True)
    assert epfl["time"].tolist() == [0.0, 13.0]
    assert round(float(epfl["battery_voltage"].iloc[0]), 6) == 16.0
    assert round(float(epfl["battery_current"].iloc[0]), 6) == -1.5
    assert round(float(epfl["hist_wind_speed_mps"].iloc[0]), 6) == 5.0
    assert round(float(epfl["hist_temperature_c"].iloc[0]), 6) == 11.0
    assert epfl["battery_voltage_source_column"].iloc[0] == "BatteryInfo:BatVol:D"
    assert epfl["wind_speed_source"].iloc[0] == "flight_log:AirSpeed:windSpeed"

    svalbard = out[out["flight"] == 1002].reset_index(drop=True)
    assert round(float(svalbard["battery_voltage"].iloc[0]), 6) == 15.006
    assert round(float(svalbard["battery_current"].iloc[0]), 6) == 1.522
    assert round(float(svalbard["hist_wind_speed_mps"].iloc[0]), 6) == 1.8
    assert svalbard["battery_voltage_source_column"].iloc[0] == "BattInfo:Pack_ve"
    assert svalbard["wind_speed_source"].iloc[0] == "external_weather"

    features_csv = dataset_root / "features.csv"
    features = build_training_dataset(output_csv, features_csv)
    assert features_csv.exists()
    assert len(features) == 2
    assert round(float(features.loc[features["flight"] == 1001, "hist_wind_speed_mps"].iloc[0]), 6) == 5.0
    assert float(features.loc[features["flight"] == 1001, "energy_wh"].iloc[0]) > 0
    assert float(features.loc[features["flight"] == 1002, "energy_wh"].iloc[0]) < 0.1
