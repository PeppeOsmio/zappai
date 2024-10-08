import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging
from typing import Any, cast
import uuid
import numpy as np
import pandas as pd
from sqlalchemy import delete, insert, select
from zappai.zappai.exceptions import (
    CropNotFoundError,
    CropYieldDataNotFoundError,
)
from zappai.zappai.dtos import (
    CropYieldDataDTO,
    LocationClimateYearsDTO,
)
from zappai.zappai.models import CropYieldData
from sqlalchemy.ext.asyncio import AsyncSession

from zappai.zappai.repositories.crop_repository import CropRepository
from zappai.zappai.repositories.location_repository import LocationRepository
from zappai.zappai.repositories.past_climate_data_repository import (
    PastClimateDataRepository,
)
from zappai.zappai.utils.common import calc_months_delta

all_columns = [
    "Author",
    "Journal",
    "Year",
    "Site country",
    "Location",
    "Latitude",
    "Longitude",
    "Soil information recorded in the paper",
    "pH (surface layer)",
    "Replications in experiment",
    "Crop",
    "Initial year of NT practice ( or first year of experiment if missing)",
    "Sowing year",
    "Harvest year",
    "Years since NT started (yrs)",
    "Crop growing season recorded in the paper",
    "Crop rotation with at least 3 crops involved in CT",
    "Crop rotation with at least 3 crops involved in NT",
    "Crop sequence (details)",
    "Cover crop before sowing",
    "Soil cover in CT",
    "Soil cover in NT",
    "Residue management of previous crop in CT  (details)",
    "Residue management of previous crop in NT (details)",
    "Weed and pest control CT",
    "Weed and pest control NT ",
    "Weed and pest control CT (details)",
    "Weed and pest control NT  (details)",
    "Fertilization CT ",
    "Fertilization NT",
    "N input",
    "N input rates with the unit kg N ha-1 (details)",
    "Field fertilization (details)",
    "Irrigation CT",
    "Irrigation NT",
    "Water applied in CT",
    "Water applied in NT",
    "Other information",
    "Yield of CT",
    "Yield of NT",
    "Relative yield change",
    "Yield increase with NT",
    "Outlier of CT",
    "Outlier of NT",
    "Sowing month",
    "Harvesting month",
    "P",
    "E",
    "PB",
    "Tave",
    "Tmax",
    "Tmin",
    "ST",
]


columns_to_include: dict[str, str] = {
    "Site country": "country",
    "Location": "location",
    "Latitude": "latitude",
    "Longitude": "longitude",
    "Crop": "crop",
    "Sowing year": "sowing_year",
    "Sowing month": "sowing_month",
    "Harvest year": "harvest_year",
    "Harvesting month": "harvest_month",
    "Yield of CT": "yield_per_hectar",
}


class CropYieldDataRepository:
    def __init__(
        self,
        crop_repository: CropRepository,
        location_repository: LocationRepository,
        past_climate_data_repository: PastClimateDataRepository,
    ) -> None:
        self.crop_repository = crop_repository
        self.location_repository = location_repository
        self.past_climate_data_repository = past_climate_data_repository

    def __import_crops_yield_data(self) -> pd.DataFrame:

        # got from "https://figshare.com/ndownloader/files/26690678"
        file_path = "./training_data/crops_yield_data.csv"

        df = pd.read_csv(
            file_path,
            usecols=[
                *list(columns_to_include.keys()),
                "Outlier of CT",
                "Outlier of NT",
            ],
        )

        # rename
        df = df.filter(items=list(columns_to_include.keys())).rename(
            columns=columns_to_include
        )

        df["crop"] = df["crop"].str.replace(r"\.autumn$", "", regex=True)
        df["crop"] = df["crop"].str.replace(r"\.winter$", "", regex=True)
        df["crop"] = df["crop"].str.replace(r"\.spring$", "", regex=True)
        df["crop"] = df["crop"].str.replace(r"\.summer$", "", regex=True)

        def calc_duration(row: pd.Series):
            return calc_months_delta(
                start_year=row["sowing_year"],
                start_month=row["sowing_month"],
                end_year=row["harvest_year"],
                end_month=row["harvest_month"],
            )

        df["duration_months"] = df.apply(calc_duration, axis=1)

        def remove_outliers(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
            # Calculate Z-scores
            for column in columns:
                df[f"z_score_{column}"] = (df[column] - df[column].mean()) / df[
                    column
                ].std()
                df = df[np.abs(df[f"z_score_{column}"]) < 3]
                df = df.drop(columns=[f"z_score_{column}"])
            return df

        df_no_outliers = pd.DataFrame(columns=df.columns)

        for crop in df["crop"].unique():
            tmp_df = remove_outliers(
                df=df[df["crop"] == crop],
                columns=["duration_months", "yield_per_hectar"],
            )
            df_no_outliers = pd.concat([df_no_outliers, tmp_df], axis=0)

        df = df.sort_values(
            by=["crop", "country", "location"], ascending=[True, True, True]
        )
        df = df.reset_index(drop=True)

        # include only the rows where the sowing is before the harvest
        df = df[
            (df["sowing_year"] < df["harvest_year"])
            | (
                (df["sowing_year"] == df["harvest_year"])
                & (df["sowing_month"] < df["harvest_month"])
            )
        ]

        df = df.dropna(
            subset=[
                "longitude",
                "latitude",
                "crop",
                "yield_per_hectar",
                "sowing_month",
                "harvest_month",
                "sowing_year",
                "harvest_year",
            ],
        )

        df = df.reset_index(drop=True)

        # in the downloaded CSV there is data referring to the same crop, same location, same sowing month and same harvest month
        # that has different yield values. We now take all the rows with the same "unique_cols" that you can view below and take the mean
        # value of the yield, aggregating them into a single row

        agg_df = pd.DataFrame(columns=df.columns)
        unique_cols = [
            "country",
            "location",
            "crop",
            "sowing_year",
            "sowing_month",
            "harvest_year",
            "harvest_month",
        ]
        unique_tuples = cast(
            list[tuple], list(df[unique_cols].groupby(unique_cols).groups.keys())
        )
        processed = 0

        def print_processed():
            print(
                f"\rProcessed unique tuples: {processed}/{len(unique_tuples)}", end=""
            )

        print_processed()
        for unique_tuple in unique_tuples:
            condition = None
            for i, col_name in enumerate(unique_cols):
                cond = df[col_name] == unique_tuple[i]
                if condition is None:
                    condition = cond
                condition &= cond
            tmp_df = df[condition].reset_index(drop=True)
            mean_yield_per_unit_surface = tmp_df["yield_per_hectar"].mean()
            tmp_df.loc[0, "yield_per_hectar"] = mean_yield_per_unit_surface
            first_row = pd.DataFrame([tmp_df.iloc[0]])
            agg_df = pd.concat([agg_df, first_row], axis=0)
            processed += 1
            print_processed()

        return agg_df

    async def import_crop_yield_data(self, session: AsyncSession):
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as pool:
            crop_yield_data_df = await loop.run_in_executor(
                executor=pool, func=self.__import_crops_yield_data
            )

        await session.execute(delete(CropYieldData))

        logging.info("Checking crops to create")

        crop_names = set(cast(list[str], list(crop_yield_data_df["crop"])))
        for crop_name in crop_names:
            sub_df = crop_yield_data_df[crop_yield_data_df["crop"] == crop_name]
            min_farming_months = cast(int, sub_df["duration_months"].min())
            max_farming_months = cast(int, sub_df["duration_months"].max())

            await self.crop_repository.delete_crop_by_name(
                session=session, name=crop_name
            )
            logging.info(f"Creating crop {crop_name}")
            crop = await self.crop_repository.create_crop(
                session=session,
                name=crop_name,
                min_farming_months=min_farming_months,
                max_farming_months=max_farming_months,
            )

        logging.info("Checking locations to create")
        location_coordinates_to_ids: dict[str, uuid.UUID] = {}

        locations_df = crop_yield_data_df[
            ["country", "location", "latitude", "longitude"]
        ].drop_duplicates()
        locations_tuples = cast(
            list[tuple[str, str, float, float]],
            list(locations_df.itertuples(index=False, name=None)),
        )
        for country, location_name, latitude, longitude in locations_tuples:
            location = await self.location_repository.get_location_by_coordinates(
                session=session, longitude=longitude, latitude=latitude
            )
            if location is not None:
                await self.location_repository.delete_location(
                    session=session, location_id=location.id
                )

            logging.info(f"Creating location {location_name} at {longitude} {latitude}")
            location = await self.location_repository.create_location(
                session=session,
                country=country,
                name=location_name,
                longitude=longitude,
                latitude=latitude,
                is_visible=False
            )
            location_coordinates_to_ids.update(
                {str((longitude, latitude)): location.id}
            )

        logging.info("Starting creating crop yield data")
        values_dicts: list[dict[str, Any]] = []
        for index, row in crop_yield_data_df.iterrows():
            values_dicts.append(
                {
                    "id": uuid.uuid4(),
                    "location_id": location_coordinates_to_ids[
                        str((row["longitude"], row["latitude"]))
                    ],
                    "crop_name": row["crop"],
                    "sowing_year": row["sowing_year"],
                    "sowing_month": row["sowing_month"],
                    "harvest_year": row["harvest_year"],
                    "harvest_month": row["harvest_month"],
                    "duration_months": row["duration_months"],
                    "yield_per_hectar": row["yield_per_hectar"],
                }
            )
        await session.execute(insert(CropYieldData), values_dicts)

    async def get_unique_location_climate_years(
        self, session: AsyncSession
    ) -> list[LocationClimateYearsDTO]:
        stmt = (
            select(
                CropYieldData.location_id,
                CropYieldData.sowing_year,
                CropYieldData.harvest_year,
            )
            .order_by(
                CropYieldData.location_id,
                CropYieldData.sowing_year,
                CropYieldData.harvest_year,
            )
            .distinct()
        )
        results = list(await session.execute(stmt))

        location_id_to_years_dict: dict[uuid.UUID, set[int]] = {}
        for result in results:
            location_id, sowing_year, harvest_year = result.tuple()
            if location_id_to_years_dict.get(location_id) is None:
                location_id_to_years_dict.update({location_id: set()})
            location_id_to_years_dict[location_id].add(sowing_year)
            location_id_to_years_dict[location_id].add(harvest_year)

        return [
            LocationClimateYearsDTO(location_id=location_id, years=years)
            for location_id, years in location_id_to_years_dict.items()
        ]

    async def get_crop_yield_data(
        self, session: AsyncSession, crop_name: str
    ) -> list[CropYieldDataDTO]:
        crop = await self.crop_repository.get_crop_by_id(
            session=session, crop_name=crop_name
        )
        if crop is None:
            raise CropNotFoundError()
        stmt = select(CropYieldData).where(CropYieldData.crop_name == crop_name)
        results = list(await session.scalars(stmt))
        return [
            self.__crop_yield_data_model_to_dto(crop_yield_data)
            for crop_yield_data in results
        ]

    async def get_unique_location_and_period_tuples(
        self, session: AsyncSession
    ) -> list[tuple[uuid.UUID, int, int, int, int]]:
        stmt = select(
            CropYieldData.location_id,
            CropYieldData.sowing_year,
            CropYieldData.sowing_month,
            CropYieldData.harvest_year,
            CropYieldData.harvest_month,
        )
        results = list(row.tuple() for row in await session.execute(stmt))
        logging.info(len(set([tpl[0] for tpl in results])))
        if len(results) == 0:
            raise CropYieldDataNotFoundError()
        return results

    async def get_crop_yield_data_for_locations(
        self, session: AsyncSession, location_ids: list[uuid.UUID]
    ) -> list[CropYieldDataDTO]:
        stmt = select(CropYieldData).where(CropYieldData.location_id.in_(location_ids))
        results = list(await session.scalars(stmt))
        return [self.__crop_yield_data_model_to_dto(item) for item in results]

    def __crop_yield_data_model_to_dto(
        self, crop_yield_data: CropYieldData
    ) -> CropYieldDataDTO:
        return CropYieldDataDTO(
            id=crop_yield_data.id,
            location_id=crop_yield_data.location_id,
            crop_name=crop_yield_data.crop_name,
            sowing_year=crop_yield_data.sowing_year,
            sowing_month=crop_yield_data.sowing_month,
            harvest_year=crop_yield_data.harvest_year,
            harvest_month=crop_yield_data.harvest_month,
            duration_months=crop_yield_data.duration_months,
            yield_per_hectar=crop_yield_data.yield_per_hectar,
        )
