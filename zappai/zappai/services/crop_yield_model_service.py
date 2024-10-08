from typing import cast
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from zappai.zappai.exceptions import LocationNotFoundError
from zappai.zappai.repositories.climate_generative_model_repository import (
    FEATURES as CLIMATE_GENERATIVE_MODEL_FEATURES,
)
from zappai.zappai.repositories.crop_repository import CropRepository
from zappai.zappai.repositories.crop_yield_data_repository import CropYieldDataRepository
from zappai.zappai.dtos import ClimateDataDTO, CropYieldDataDTO, PastClimateDataDTO
from zappai.zappai.repositories.location_repository import LocationRepository
from zappai.zappai.repositories.past_climate_data_repository import (
    PastClimateDataRepository,
)
from uuid import UUID
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from zappai.zappai.utils.common import create_stats_dataframe

FEATURES = [
    "sowing_year",
    "sowing_month",
    "harvest_year",
    "harvest_month",
    "duration_months",
    "surface_solar_radiation_downwards_mean",
    "surface_solar_radiation_downwards_std",
    "surface_solar_radiation_downwards_min",
    "surface_solar_radiation_downwards_max",
    "surface_thermal_radiation_downwards_mean",
    "surface_thermal_radiation_downwards_std",
    "surface_thermal_radiation_downwards_min",
    "surface_thermal_radiation_downwards_max",
    "surface_net_solar_radiation_mean",
    "surface_net_solar_radiation_std",
    "surface_net_solar_radiation_min",
    "surface_net_solar_radiation_max",
    "surface_net_thermal_radiation_mean",
    "surface_net_thermal_radiation_std",
    "surface_net_thermal_radiation_min",
    "surface_net_thermal_radiation_max",
    "total_cloud_cover_mean",
    "total_cloud_cover_std",
    "total_cloud_cover_min",
    "total_cloud_cover_max",
    "2m_dewpoint_temperature_mean",
    "2m_dewpoint_temperature_std",
    "2m_dewpoint_temperature_min",
    "2m_dewpoint_temperature_max",
    "soil_temperature_level_3_mean",
    "soil_temperature_level_3_std",
    "soil_temperature_level_3_min",
    "soil_temperature_level_3_max",
    "volumetric_soil_water_layer_3_mean",
    "volumetric_soil_water_layer_3_std",
    "volumetric_soil_water_layer_3_min",
    "volumetric_soil_water_layer_3_max",
    "2m_temperature_mean",
    "2m_temperature_std",
    "2m_temperature_min",
    "2m_temperature_max",
    "total_precipitation_mean",
    "total_precipitation_std",
    "total_precipitation_min",
    "total_precipitation_max",
]
TARGET = ["yield_per_hectar"]


class CropYieldModelService:
    def __init__(
        self,
        past_climate_data_repository: PastClimateDataRepository,
        location_repository: LocationRepository,
        crop_yield_data_repository: CropYieldDataRepository,
        crop_repository: CropRepository,
    ) -> None:
        self.past_climate_data_repository = past_climate_data_repository
        self.location_repository = location_repository
        self.crop_yield_data_repository = crop_yield_data_repository
        self.crop_repository = crop_repository

    async def train_crop_yield_model(
        self, session: AsyncSession, crop_name: str
    ) -> tuple[
        RandomForestRegressor,
        float,
        float,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
    ]:
        crop_yield_data = await self.crop_yield_data_repository.get_crop_yield_data(
            session=session, crop_name=crop_name
        )
        crop_yield_data_df = CropYieldDataDTO.from_list_to_dataframe(crop_yield_data)

        enriched_crop_yield_data_df = pd.DataFrame()

        for _, row in crop_yield_data_df.iterrows():
            location = await self.location_repository.get_location_by_id(
                session=session,
                location_id=row["location_id"]
            )
            if location is None:
                raise LocationNotFoundError(str(row["location_id"]))
            past_climate_data_df = PastClimateDataDTO.from_list_to_dataframe(
                await self.past_climate_data_repository.get_past_climate_data(
                    session=session,
                    location_id=location.id,
                    year_from=row["sowing_year"],
                    month_from=row["sowing_month"],
                    year_to=row["harvest_year"],
                    month_to=row["harvest_month"],
                )
            )
            past_climate_data_df = past_climate_data_df[
                CLIMATE_GENERATIVE_MODEL_FEATURES
            ]
            result_climate_data_stats_df = create_stats_dataframe(
                df=past_climate_data_df, ignore=["sin_year", "cos_year"]
            )
            # convert the row to a DataFrame
            crop_yield_data_row_df = pd.DataFrame([row])
            # since the row was a Series, remove the useless index column that the DataFrame inherited
            crop_yield_data_row_df = crop_yield_data_row_df.drop(columns=["index"])
            crop_yield_data_row_df = crop_yield_data_row_df.reset_index(drop=True)
            enriched_crop_yield_data_row = pd.concat(
                [crop_yield_data_row_df, result_climate_data_stats_df], axis=1
            )
            enriched_crop_yield_data_df = pd.concat(
                [enriched_crop_yield_data_df, enriched_crop_yield_data_row],
                axis=0,
            )

        enriched_crop_yield_data_df = enriched_crop_yield_data_df[[*FEATURES, *TARGET]]
        enriched_crop_yield_data_df = enriched_crop_yield_data_df.reset_index(drop=True)

        x = enriched_crop_yield_data_df[FEATURES]
        y = enriched_crop_yield_data_df[TARGET]
        x_train, x_test, y_train, y_test = cast(
            tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame],
            train_test_split(x, y, test_size=0.2, train_size=0.8, random_state=42),
        )

        model = RandomForestRegressor(
            n_estimators=100,
            criterion="squared_error",
            min_samples_split=50,
            random_state=42,
        )
        model.fit(x_train.to_numpy(), y_train.to_numpy().flatten())

        y_pred = model.predict(x_test.to_numpy())
        mse = cast(float, mean_squared_error(y_true=y_test, y_pred=y_pred))
        r2 = cast(float, r2_score(y_true=y_test, y_pred=y_pred))

        return model, mse, r2, x_train, x_test, y_train, y_test

    async def train_and_save_crop_yield_model_for_all_crops(
        self, session: AsyncSession
    ):
        crops = await self.crop_repository.get_all_crops(session)

        processed = 0

        def print_processed():
            print(f"\rCrop yield models saved: {processed}/{len(crops)}", end="")

        print_processed()
        for crop in crops:
            model, mse, r2, _, _, _, _ = await self.train_crop_yield_model(
                crop_name=crop.name, session=session
            )
            await self.crop_repository.save_crop_yield_model(
                session=session, crop_name=crop.name, crop_yield_model=model, mse=mse, r2=r2
            )
            processed += 1
            print_processed()
