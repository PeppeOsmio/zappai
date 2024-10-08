import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
import os
import uuid
from geoalchemy2 import Geography
import pandas as pd
from sqlalchemy import BooleanClauseList, asc, delete, func, insert, select
from zappai.zappai.dtos import FutureClimateDataDTO
from zappai.zappai.models import FutureClimateData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from geoalchemy2.functions import ST_Distance
from typing import Any, cast
import sqlalchemy
from zappai.zappai.utils.common import coordinates_to_well_known_text
from zappai.zappai.repositories.copernicus_data_store_api import CopernicusDataStoreAPI


class FutureClimateDataRepository:
    def __init__(self, copernicus_data_store_api: CopernicusDataStoreAPI) -> None:
        self.copernicus_data_store_api = copernicus_data_store_api

    async def download_future_climate_data(self, session: AsyncSession):
        loop = asyncio.get_running_loop()

        def download_func():
            def on_save_chunk(chunk: pd.DataFrame):
                return asyncio.run_coroutine_threadsafe(
                    coro=self.__save_future_climate_data(session=session, future_climate_data_df=chunk),
                    loop=loop,
                ).result()

            self.copernicus_data_store_api.get_future_climate_data(
                on_save_chunk=on_save_chunk,
            )

        with ThreadPoolExecutor() as pool:
            await loop.run_in_executor(executor=pool, func=download_func)

        logging.info(f"Done")

    async def __save_future_climate_data(
        self, session: AsyncSession, future_climate_data_df: pd.DataFrame
    ):
        # delete the data of the same period as this dataframe
        max_year, max_month = future_climate_data_df.index[-1]
        min_year, min_month = future_climate_data_df.index[0]
        stmt = delete(FutureClimateData).where(
            (
                (FutureClimateData.year < max_year)
                | (
                    (FutureClimateData.year == max_year)
                    & (FutureClimateData.month <= max_month)
                )
            )
            & (
                (FutureClimateData.year > min_year)
                | (
                    (FutureClimateData.year == min_year)
                    & (FutureClimateData.month >= min_month)
                )
            )
        )
        await session.execute(stmt)
        processed = 0
        STEP = 1000
        logging.info(f"Saving future climate data...")
        while processed < len(future_climate_data_df):
            rows = future_climate_data_df[processed : processed + STEP]
            values_dicts: list[dict[str, Any]] = []
            for index, row in rows.iterrows():
                values_dicts.append(
                    {
                        "id": uuid.uuid4(),
                        "longitude": row["longitude"],
                        "latitude": row["latitude"],
                        "year": cast(pd.MultiIndex, index)[0],
                        "month": cast(pd.MultiIndex, index)[1],
                        "coordinates": coordinates_to_well_known_text(
                            longitude=row["longitude"], latitude=row["latitude"]
                        ),
                        "u_component_of_wind_10m": row["10m_u_component_of_wind"],
                        "v_component_of_wind_10m": row["10m_v_component_of_wind"],
                        "temperature_2m": row["2m_temperature"],
                        "evaporation": row["evaporation"],
                        "total_precipitation": row["total_precipitation"],
                        "surface_pressure": row["surface_pressure"],
                        "surface_solar_radiation_downwards": row[
                            "surface_solar_radiation_downwards"
                        ],
                        "surface_thermal_radiation_downwards": row[
                            "surface_thermal_radiation_downwards"
                        ],
                    }
                )
            await session.execute(insert(FutureClimateData).values(values_dicts))
            processed += len(rows)
        logging.info(f"Done.")

    async def get_future_climate_data_for_nearest_coordinates(
        self,
        session: AsyncSession,
        longitude: float,
        latitude: float,
        year_from: int,
        month_from: int,
        year_to: int,
        month_to: int,
    ) -> list[FutureClimateDataDTO]:
        """Get the future climate data starting from the provided start and end.

        Args:
            longitude (float):
            latitude (float):
            start_year (int):
            start_month (int):
            end_year (int):
            end_month: (int):

        Raises:
            ValueError:

        Returns:
            list[FutureClimateDataDTO]:
        """
        coordinates_stmt = (
            select(FutureClimateData.longitude, FutureClimateData.latitude).order_by(
                asc(
                    ST_Distance(
                        FutureClimateData.coordinates,
                        sqlalchemy.cast(
                            coordinates_to_well_known_text(
                                longitude=longitude, latitude=latitude
                            ),
                            Geography,
                        ),
                    )
                )
            )
        ).limit(1)
        results = list(await session.execute(coordinates_stmt))
        if len(results) == 0:
            raise ValueError(f"No future climate data downloaded")
        nearest_longitude, nearest_latitude = results[0].tuple()
        stmt = (
            select(FutureClimateData)
            .where(
                (FutureClimateData.longitude == nearest_longitude)
                & (FutureClimateData.latitude == nearest_latitude)
                & (
                    (FutureClimateData.year > year_from)
                    | (
                        (FutureClimateData.year == year_from)
                        & (FutureClimateData.month >= month_from)
                    )
                )
                & (
                    (FutureClimateData.year < year_to)
                    | (
                        (FutureClimateData.year == year_to)
                        & (FutureClimateData.month <= month_to)
                    )
                )
            )
            .order_by(asc(FutureClimateData.year), asc(FutureClimateData.month))
        )
        results = list(await session.scalars(stmt))
        if len(results) == 0:
            raise ValueError(
                f"No future climate data to download, nearest coordinates don't exist anymore?"
            )
        return [self.__future_climate_data_model_to_dto(result) for result in results]

    def __future_climate_data_model_to_dto(
        self, future_climate_data: FutureClimateData
    ) -> FutureClimateDataDTO:
        return FutureClimateDataDTO(
            year=future_climate_data.year,
            month=future_climate_data.month,
            longitude=future_climate_data.longitude,
            latitude=future_climate_data.latitude,
            u_component_of_wind_10m=future_climate_data.u_component_of_wind_10m,
            v_component_of_wind_10m=future_climate_data.v_component_of_wind_10m,
            temperature_2m=future_climate_data.temperature_2m,
            evaporation=future_climate_data.evaporation,
            total_precipitation=future_climate_data.total_precipitation,
            surface_pressure=future_climate_data.surface_pressure,
            surface_solar_radiation_downwards=future_climate_data.surface_solar_radiation_downwards,
            surface_thermal_radiation_downwards=future_climate_data.surface_thermal_radiation_downwards,
        )
