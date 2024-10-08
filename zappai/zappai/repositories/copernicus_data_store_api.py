from datetime import datetime, timezone
import logging
import os
import random
from typing import Callable
import cdsapi
import zipfile
import pandas as pd
from zappai.zappai.utils.common import (
    process_copernicus_climate_data,
    retry_on_error,
)
from uuid import UUID
import traceback
import subprocess


_ERA5_VARIABLES = {
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "2m_temperature",
    "evaporation",
    "total_precipitation",  # this can be derived by <mean_precipitation_flux> * <seconds in a day> / 1000 (to convert mm to m)
    "surface_pressure",
    "surface_solar_radiation_downwards",
    "surface_thermal_radiation_downwards",
    # exclusive to ERA5 below
    "surface_net_solar_radiation",
    "surface_net_thermal_radiation",
    "snowfall",
    "total_cloud_cover",
    "2m_dewpoint_temperature",
    "soil_temperature_level_3",
    "volumetric_soil_water_layer_3",
}

_CMIP5_VARIABLES = {
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "2m_temperature",
    "evaporation",
    "mean_precipitation_flux",
    "surface_pressure",
    "surface_solar_radiation_downwards",
    "surface_thermal_radiation_downwards",
}

_ERA5_VARIABLES_RESPONSE_TO_DATAFRAME_MAPPING = {
    "u10": "10m_u_component_of_wind",  # Eastward component of wind at 10 meters
    "v10": "10m_v_component_of_wind",  # Northward component of wind at 10 meters
    "t2m": "2m_temperature",  # Temperature at 2 meters above the surface
    "e": "evaporation",  # Evaporation
    "tp": "total_precipitation",  # Total precipitation
    "sp": "surface_pressure",  # Surface pressure
    "ssrd": "surface_solar_radiation_downwards",  # Surface solar radiation downwards
    "strd": "surface_thermal_radiation_downwards",  # Surface thermal radiation downwards
    # Exclusive to ERA5 below
    "tcc": "total_cloud_cover",  # Total cloud cover
    "sf": "snowfall",  # Snowfall
    "d2m": "2m_dewpoint_temperature",  # Dewpoint temperature at 2 meters
    "stl3": "soil_temperature_level_3",  # Soil temperature at level 1 (top layer)
    "ssr": "surface_net_solar_radiation",  # Surface net solar radiation
    "str": "surface_net_thermal_radiation",  # Surface net thermal radiation
    "swvl3": "volumetric_soil_water_layer_3",  # Volumetric soil water content at layer 1
}


_CMIP5_VARIABLES_RESPONSE_TO_DATAFRAME_MAPPING = {
    "uas": "10m_u_component_of_wind",  # Eastward component of wind at 10 meters
    "vas": "10m_v_component_of_wind",  # Northward component of wind at 10 meters
    "tas": "2m_temperature",  # Temperature at 2 meters above the surface
    "evspsbl": "evaporation",  # Evaporation
    "pr": "mean_precipitation_flux",  # Precipitation flux
    "ps": "surface_pressure",  # Surface pressure
    "rsds": "surface_solar_radiation_downwards",  # Surface solar radiation downwards
    "rlds": "surface_thermal_radiation_downwards",  # Surface thermal radiation downwards
}

ERA5_VARIABLES = [
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "2m_temperature",
    "evaporation",
    "total_precipitation",
    "surface_pressure",
    "surface_solar_radiation_downwards",
    "surface_thermal_radiation_downwards",
    # exclusive to ERA5 below
    "surface_net_solar_radiation",
    "surface_net_thermal_radiation",
    "snowfall",
    "total_cloud_cover",
    "2m_dewpoint_temperature",
    "soil_temperature_level_3",
    "volumetric_soil_water_layer_3",
]

CMIP5_VARIABLES = [
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "2m_temperature",
    "evaporation",
    "total_precipitation",
    "surface_pressure",
    "surface_solar_radiation_downwards",
    "surface_thermal_radiation_downwards",
]

ERA5_EXCLUSIVE_VARIABLES = list(set(ERA5_VARIABLES) - set(CMIP5_VARIABLES))


class CopernicusDataStoreAPI:
    def __init__(self, api_token: UUID) -> None:
        self.cds_client = cdsapi.Client(
            url="https://cds.climate.copernicus.eu/api",
            key=str(api_token),
        )

    # this is needed because of a super weird bug that gives OSError -101 from NetCDF when opening a .nc file after
    # downloaded by cds_api, maybe because of a lock problem.
    def __run_conversion_script(
        self, source_file_path: str, limit: int | None
    ) -> pd.DataFrame:
        # Create the base command
        command = [
            "python",
            "./zappai/zappai/utils/nc_to_csv.py",
            "--path",
            source_file_path,
        ]

        # Add the limit argument if provided
        if limit is not None:
            command += ["--limit", str(limit)]

        # Run the script as a subprocess
        try:
            result = subprocess.run(command, check=True)
            print(result.stdout)
            print(result.stderr)
        except Exception as e:
            logging.error(traceback.format_exc())
            raise e
        print(result.stdout)
        print(result.stderr)
        print(f"Conversion completed for {source_file_path}")
        csv_path = f"{source_file_path}.csv"
        result_df = pd.read_csv(csv_path)
        os.remove(csv_path)
        return result_df

    @retry_on_error(max_retries=10, wait_time=10)
    def get_future_climate_data(self, on_save_chunk: Callable[[pd.DataFrame], None]):
        """https://cds.climate.copernicus.eu/cdsapp#!/dataset/sis-hydrology-meteorology-derived-projections?tab=form

        Response headers:
            time lat lon bnds average_DT average_T1 average_T2 <parameter abbreviation> time_bnds lat_bnds lon_bnds

        Returns:
            pd.DataFrame:
        """
        dest_dir = "tmp/future_climate_data"

        os.makedirs(dest_dir, exist_ok=True)

        zip_file = os.path.join(dest_dir, f"{random.randbytes(16).hex()}.zip")

        periods = ["202101-202512", "202601-203012"]

        for period in periods:
            logging.info(f"Downloading future climate data for period {period}")
            self.cds_client.retrieve(
                "projections-cmip5-monthly-single-levels",
                {
                    "ensemble_member": "r10i1p1",
                    "format": "zip",
                    "variable": list(_CMIP5_VARIABLES),
                    "experiment": "historical",
                    "model": "gfdl_cm2p1",
                    "period": [period],
                },
                zip_file,
            )

            with zipfile.ZipFile(zip_file, "r") as zip_ref:
                zip_ref.extractall(dest_dir)

            os.remove(zip_file)

            result_df = pd.DataFrame()

            for extracted_file in os.listdir(dest_dir):
                extracted_nc_file_path = os.path.join(dest_dir, extracted_file)
                if not extracted_file.endswith(".nc"):
                    continue
                logging.info(f"Converting {extracted_nc_file_path}")
                df = self.__run_conversion_script(
                    source_file_path=extracted_nc_file_path, limit=None
                )
                # take only the first segment of each measurement for each day and location
                df = df[df["bnds"] == 1.0]
                df = df.drop(
                    columns=[
                        "bnds",
                        "average_DT",
                        "average_T1",
                        "average_T2",
                        "time_bnds",
                        "lat_bnds",
                        "lon_bnds",
                    ],
                )
                df = df.dropna()
                if "time" not in result_df.columns:
                    result_df["time"] = df["time"]
                if "longitude" not in result_df.columns:
                    result_df["longitude"] = df["lon"]
                if "latitude" not in result_df.columns:
                    result_df["latitude"] = df["lat"]
                for (
                    key,
                    value,
                ) in _CMIP5_VARIABLES_RESPONSE_TO_DATAFRAME_MAPPING.items():
                    if key in df.columns:
                        result_df[value] = df[key]
                        result_df.reset_index()
                        break
                os.remove(extracted_nc_file_path)
            result_df = process_copernicus_climate_data(
                df=result_df, is_cmip5_data=True, columns_mappings={}
            )

            # convert from mm/s (aggregated over 24 hours) to m
            result_df["total_precipitation"] = (
                (result_df["mean_precipitation_flux"] / 1000) * 60 * 60 * 24
            )
            result_df = result_df.drop(columns=["mean_precipitation_flux"])
            on_save_chunk(result_df)

    @retry_on_error(max_retries=10, wait_time=10)
    def get_past_climate_data_for_years(
        self,
        longitude: float,
        latitude: float,
        years: list[int],
        on_save_chunk: Callable[[pd.DataFrame], None],
    ):

        tmp_dir = "./tmp/global_climate_data"
        os.makedirs(tmp_dir, exist_ok=True)

        _years = [*years]
        _years.sort()

        STEP = 20
        processed = 0

        while processed < len(_years):
            years_to_fetch = _years[processed : processed + STEP]

            logging.info(
                f"Getting data for years {years_to_fetch} and coordinates ({longitude} {latitude})"
            )
            tmp_nc_file_path = os.path.join(tmp_dir, f"{random.randbytes(32).hex()}.nc")
            self.cds_client.retrieve(
                name="reanalysis-era5-single-levels-monthly-means",
                request={
                    "product_type": "monthly_averaged_reanalysis",
                    "variable": list(_ERA5_VARIABLES),
                    "year": [str(year) for year in years_to_fetch],
                    "month": [str(month).zfill(2) for month in range(1, 13)],
                    "day": [str(day).zfill(2) for day in range(1, 32)],
                    # "time": [f"{hour:02d}:00" for hour in range(24)],
                    "time": ["00:00"],
                    "format": "netcdf",
                    "area": [
                        latitude + 0.01,
                        longitude - 0.01,
                        latitude - 0.01,
                        longitude + 0.01,
                    ],
                    "download_format": "unarchived",
                },
                target=tmp_nc_file_path,
            )

            tmp_df = self.__run_conversion_script(
                source_file_path=tmp_nc_file_path, limit=None
            )

            os.remove(tmp_nc_file_path)

            tmp_df = process_copernicus_climate_data(
                df=tmp_df,
                is_cmip5_data=False,
                columns_mappings=_ERA5_VARIABLES_RESPONSE_TO_DATAFRAME_MAPPING,
            )

            on_save_chunk(tmp_df)
            processed += len(years_to_fetch)

    def get_past_climate_data(
        self,
        year_from: int | None,
        month_from: int | None,
        longitude: float,
        latitude: float,
        on_save_chunk: Callable[[pd.DataFrame], None],
    ):

        _year_from = year_from if year_from is not None else 1940
        _month_from = month_from if month_from is not None else 1

        now = datetime.now(tz=timezone.utc)

        if _year_from > now.year:
            return
        # data is available for the previous previous month. e.g if it's June now, it's available until April for sure
        if _month_from >= now.month - 1:
            return

        years = list(range(_year_from, now.year + 1))

        return self.get_past_climate_data_for_years(
            longitude=longitude,
            latitude=latitude,
            years=years,
            on_save_chunk=on_save_chunk,
        )
