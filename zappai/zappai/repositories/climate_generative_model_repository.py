import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import cast
from uuid import UUID
import uuid
import numpy as np
import pandas as pd
from keras.src.models import Sequential
from keras.src.layers import Dropout, InputLayer, LSTM, Dense
from sklearn.preprocessing import StandardScaler
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from zappai.zappai.exceptions import (
    ClimateGenerativeModelNotFoundError,
    LocationNotFoundError,
)
from zappai.zappai.models import ClimateGenerativeModel
from zappai.zappai.dtos import (
    ClimateGenerativeModelDTO,
    FutureClimateDataDTO,
    ClimateDataDTO,
    PastClimateDataDTO,
)
from zappai.zappai.repositories.future_climate_data_repository import (
    FutureClimateDataRepository,
)
from zappai.zappai.repositories.location_repository import LocationRepository
from zappai.zappai.repositories.past_climate_data_repository import (
    PastClimateDataRepository,
)

from zappai.zappai.utils.common import bytes_to_object, get_next_n_months, object_to_bytes

TARGET = [
    "surface_solar_radiation_downwards",
    "surface_thermal_radiation_downwards",
    "surface_net_solar_radiation",
    "surface_net_thermal_radiation",
    "total_cloud_cover",
    "2m_dewpoint_temperature",
    "soil_temperature_level_3",
    "volumetric_soil_water_layer_3",
]

MODEL_CMIP5_VARIABLES = [
    "2m_temperature",
    "total_precipitation",
]

# These are the variables of future climate data
MODEL_CMIP5_VARIABLES_WITH_SIN_COS = ["sin_year", "cos_year", *MODEL_CMIP5_VARIABLES]

FEATURES = [*TARGET, *MODEL_CMIP5_VARIABLES]

FEATURES_WITH_SIN_COS = [*TARGET, *MODEL_CMIP5_VARIABLES_WITH_SIN_COS]

SEQ_LENGTH = 12


def add_sin_cos_year(df: pd.DataFrame):
    # Reset the index to access the multi-index columns
    df_reset = df.reset_index()
    # Convert year and month to a single time representation (fractional year)
    df_reset.drop(columns=["sin_year"], errors="ignore")
    df_reset.drop(columns=["cos_year"], errors="ignore")
    # Create sin and cos features
    df_reset["sin_year"] = np.sin(2 * np.pi * (df_reset["month"]) / 12)
    df_reset["cos_year"] = np.cos(2 * np.pi * (df_reset["month"]) / 12)
    # Optionally, set the index back to the original if needed
    df_reset = df_reset.set_index(["year", "month"])
    return df_reset


class ClimateGenerativeModelRepository:
    def __init__(
        self,
        location_repository: LocationRepository,
        past_climate_data_repository: PastClimateDataRepository,
        future_climate_data_repository: FutureClimateDataRepository,
    ) -> None:
        self.location_repository = location_repository
        self.past_climate_data_repository = past_climate_data_repository
        self.future_climate_data_repository = future_climate_data_repository

    @staticmethod
    def format_data(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        x_train_scaled_with_sequences = []
        y_train_scaled_for_model = []
        for i in range(len(x) - SEQ_LENGTH):
            x_train_scaled_with_sequences.append(x[i : i + SEQ_LENGTH])
            y_train_scaled_for_model.append(y[i + SEQ_LENGTH])

        x_train_scaled_with_sequences = np.array(x_train_scaled_with_sequences)
        y_train_scaled_for_model = np.array(y_train_scaled_for_model)
        return x_train_scaled_with_sequences, y_train_scaled_for_model

    def __train_model(
        self, location_id: UUID, past_climate_data_df: pd.DataFrame
    ) -> ClimateGenerativeModelDTO:
        """_summary_

        Args:
            past_climate_data_df (pd.DataFrame): _description_

        Returns:
            model, x_scaler, y_scaler, rmse, x_train_from
        """
        past_climate_data_df = add_sin_cos_year(past_climate_data_df)
        past_climate_data_df = past_climate_data_df[FEATURES_WITH_SIN_COS]

        x_df = past_climate_data_df[FEATURES_WITH_SIN_COS]
        y_df = past_climate_data_df[TARGET]

        perc_70 = int(len(x_df) * 0.7)
        perc_85 = int(len(x_df) * 0.85)

        x_df_train, x_df_val, x_df_test = (
            x_df[:perc_70],
            x_df[perc_70:perc_85],
            x_df[perc_85:],
        )
        y_df_train, y_df_val, y_df_test = (
            y_df[:perc_70],
            y_df[perc_70:perc_85],
            y_df[perc_85:],
        )

        x_scaler = StandardScaler()
        y_scaler = StandardScaler()

        x_scaler = StandardScaler()
        x_scaler = x_scaler.fit(x_df_train.to_numpy())

        # descending order
        train_start_year, train_start_month = x_df_train.index[0]
        train_end_year, train_end_month = x_df_train.index[-1]

        validation_start_year, validation_start_month = x_df_val.index[0]
        validation_end_year, validation_end_month = x_df_val.index[-1]

        test_start_year, test_start_month = x_df_test.index[0]
        test_end_year, test_end_month = x_df_test.index[-1]

        if len(TARGET) == 0:
            return ClimateGenerativeModelDTO(
                id=uuid.uuid4(),
                location_id=location_id,
                model=Sequential(),
                x_scaler=StandardScaler(),
                y_scaler=StandardScaler(),
                rmse=0.0,
                train_start_year=train_start_year,
                train_start_month=train_start_month,
                train_end_year=train_end_year,
                train_end_month=train_end_month,
                validation_start_year=validation_start_year,
                validation_start_month=validation_start_month,
                validation_end_year=validation_end_year,
                validation_end_month=validation_end_month,
                test_start_year=test_start_year,
                test_start_month=test_start_month,
                test_end_year=test_end_year,
                test_end_month=test_end_month,
            )

        y_scaler = StandardScaler()
        y_scaler = y_scaler.fit(y_df_train.to_numpy())

        x_train_scaled, x_val_scaled, x_test_scaled = (
            cast(np.ndarray, x_scaler.transform(x_df_train.to_numpy())),
            cast(np.ndarray, x_scaler.transform(x_df_val.to_numpy())),
            cast(np.ndarray, x_scaler.transform(x_df_test.to_numpy())),
        )
        y_train_scaled, y_val_scaled, y_test_scaled = (
            cast(np.ndarray, y_scaler.transform(y_df_train.to_numpy())),
            cast(np.ndarray, y_scaler.transform(y_df_val.to_numpy())),
            cast(np.ndarray, y_scaler.transform(y_df_test.to_numpy())),
        )

        x_train_formatted, y_train_formatted = (
            ClimateGenerativeModelRepository.format_data(
                x=x_train_scaled, y=y_train_scaled
            )
        )
        x_val_formatted, y_val_formatted = ClimateGenerativeModelRepository.format_data(
            x=x_val_scaled, y=y_val_scaled
        )
        x_test_formatted, y_test_formatted = (
            ClimateGenerativeModelRepository.format_data(
                x=x_test_scaled, y=y_test_scaled
            )
        )

        model = Sequential(
            layers=[
                InputLayer(
                    shape=(
                        SEQ_LENGTH,
                        len(FEATURES_WITH_SIN_COS),
                    )
                ),
                LSTM(units=50, return_sequences=True),
                Dropout(rate=0.2),
                LSTM(units=50, return_sequences=True),
                Dropout(rate=0.2),
                LSTM(units=50),
                Dropout(rate=0.2),
                Dense(units=len(TARGET)),
            ]
        )

        model.compile(loss="mean_squared_error", optimizer="adam", metrics=["root_mean_squared_error"])  # type: ignore

        model.fit(
            x=x_train_formatted,
            y=y_train_formatted,
            validation_data=(x_val_formatted, y_val_formatted),
            epochs=50,
        )

        rmse = model.evaluate(x=x_test_formatted, y=y_test_formatted)[1]

        return ClimateGenerativeModelDTO(
            id=uuid.uuid4(),
            location_id=location_id,
            model=model,
            x_scaler=x_scaler,
            y_scaler=y_scaler,
            rmse=rmse,
            train_start_year=train_start_year,
            train_start_month=train_start_month,
            train_end_year=train_end_year,
            train_end_month=train_end_month,
            validation_start_year=validation_start_year,
            validation_start_month=validation_start_month,
            validation_end_year=validation_end_year,
            validation_end_month=validation_end_month,
            test_start_year=test_start_year,
            test_start_month=test_start_month,
            test_end_year=test_end_year,
            test_end_month=test_end_month,
        )

    async def create_model_for_location(
        self,
        session: AsyncSession,
        location_id: UUID,
    ) -> ClimateGenerativeModelDTO:
        """Creates as Sequential model

        Args:
            location_repository (LocationRepository):
            past_climate_data_repository (PastClimateDataRepository):
            location_id (UUID):

        Raises:
            LocationNotFoundError:
        """
        location = await self.location_repository.get_location_by_id(
            session=session, location_id=location_id
        )
        if location is None:
            raise LocationNotFoundError()

        past_climate_data_df = PastClimateDataDTO.from_list_to_dataframe(
            await self.past_climate_data_repository.get_all_past_climate_data(
                session=session, location_id=location.id
            )
        )

        # train in thread
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as pool:
            climate_generative_model = await loop.run_in_executor(
                executor=pool,
                func=lambda: self.__train_model(
                    location_id=location_id,
                    past_climate_data_df=past_climate_data_df,
                ),
            )

        await self.__save_climate_generative_model(
            session=session, climate_generative_model=climate_generative_model
        )

        return climate_generative_model

    def generate_data_from_seed(
        self,
        model: Sequential,
        x_scaler: StandardScaler,
        y_scaler: StandardScaler,
        seed_data_df: pd.DataFrame,
        future_climate_data_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Generates climate data for year, month > seed_data.

        Args:
            model (Sequential):
            x_scaler (StandardScaler):
            y_scaler (StandardScaler):
            seed_data (np.ndarray):
            future_climate_data_df (pd.DataFrame): future data that has to start from the month after seed_data

        Returns:
            pd.DataFrame:
        """
        if len(seed_data_df) != SEQ_LENGTH:
            raise ValueError(f"Seed data must have length of {SEQ_LENGTH}")

        if len(future_climate_data_df) == 0:
            raise ValueError(f"Future climate data can't be empty!")

        # check if seed_data and future_climate_data_df are sequential (e.g. seed data terminates in 2022-09 and future data starts ad 2022-10)
        last_seed_year, last_seed_month = cast(pd.MultiIndex, seed_data_df.index[-1])
        first_future_year, first_future_month = cast(
            pd.MultiIndex, future_climate_data_df.index[0]
        )

        is_future_data_sequential = False
        # Check if the next month is within the same year
        if (
            first_future_year == last_seed_year
            and first_future_month == last_seed_month + 1
        ):
            is_future_data_sequential = True
        # Check if the next month is January of the next year
        elif (
            last_seed_year + 1 == first_future_year
            and last_seed_month == 12
            and first_future_month == 1
        ):
            is_future_data_sequential = True

        if not is_future_data_sequential:
            raise IndexError(
                f"Future climate data must start from the month after seed data. Seed data: {last_seed_year}-{last_seed_month}. Future data: {first_future_year}-{first_future_month}"
            )

        seed_data_df = add_sin_cos_year(seed_data_df)
        seed_data_df = seed_data_df[FEATURES_WITH_SIN_COS]
        future_climate_data_df = add_sin_cos_year(future_climate_data_df)
        future_climate_data_df = future_climate_data_df[
            MODEL_CMIP5_VARIABLES_WITH_SIN_COS
        ]
        generated_data = []
        # shape (SEQ_LENGHT, len(FEATURES))
        current_step = seed_data_df.to_numpy()
        year_col: list[int] = []
        month_col: list[int] = []
        for index, row in future_climate_data_df.iterrows():
            year, month = cast(pd.MultiIndex, index)
            year_col.append(year)
            month_col.append(month)
            if len(TARGET) == 0:
                generated_data.append(row.to_numpy())
                continue
            # shape (SEQ_LENGHT, len(FEATURES))
            scaled_current_step = cast(
                np.ndarray,
                x_scaler.transform(current_step),
            )

            # shape (len(TARGET),)
            scaled_prediction = cast(
                np.ndarray, model(np.array([scaled_current_step]))
            )[0]

            # shape (len(TARGET),)
            prediction = cast(
                np.ndarray, y_scaler.inverse_transform(np.array([scaled_prediction]))
            )[0]

            # shape (len(FEATURES),)
            enriched_prediction = np.concatenate([prediction, row.to_numpy()], axis=0)
            generated_data.append(enriched_prediction)

            current_step = np.concatenate(
                [current_step[1:], np.array([enriched_prediction])]
            )
        result = pd.DataFrame(data=generated_data, columns=FEATURES_WITH_SIN_COS)
        result["year"] = year_col
        result["month"] = month_col

        result = result.set_index(keys=["year", "month"], drop=True)

        return result

    async def generate_climate_data_from_last_past_climate_data(
        self, session: AsyncSession, location_id: UUID, months: int
    ) -> list[ClimateDataDTO]:
        location = await self.location_repository.get_location_by_id(
            session=session, location_id=location_id
        )
        if location is None:
            raise LocationNotFoundError()

        climate_generative_model = (
            await self.get_climate_generative_model_by_location_id(
                session=session, location_id=location_id
            )
        )
        if climate_generative_model is None:
            raise ClimateGenerativeModelNotFoundError()

        last_n_months_seed_data = PastClimateDataDTO.from_list_to_dataframe(
            await self.past_climate_data_repository.get_past_climate_data_of_previous_n_months(
                session=session,
                location_id=location_id,
                n=SEQ_LENGTH,
            )
        )

        index = last_n_months_seed_data.index[-1]
        start_year, start_month = index
        start_year = cast(int, start_year)
        start_month = cast(int, start_month)

        start_year, start_month = get_next_n_months(
            n=1, year=start_year, month=start_month
        )

        year_to, month_to = get_next_n_months(
            n=months, month=start_month, year=start_year
        )

        future_climate_data_df = FutureClimateDataDTO.from_list_to_dataframe(
            await self.future_climate_data_repository.get_future_climate_data_for_nearest_coordinates(
                session=session,
                longitude=location.longitude,
                latitude=location.latitude,
                year_from=start_year,
                month_from=start_month,
                year_to=year_to,
                month_to=month_to,
            )
        )

        data = self.generate_data_from_seed(
            model=climate_generative_model.model,
            x_scaler=climate_generative_model.x_scaler,
            y_scaler=climate_generative_model.y_scaler,
            seed_data_df=last_n_months_seed_data,
            future_climate_data_df=future_climate_data_df,
        )

        result = pd.DataFrame(data=data, columns=[*FEATURES, *TARGET])
        result.index = future_climate_data_df.index
        result["location_id"] = location_id
        return ClimateDataDTO.from_dataframe_to_list(result)

    async def get_climate_generative_model_by_location_id(
        self, session: AsyncSession, location_id: UUID
    ) -> ClimateGenerativeModelDTO | None:
        stmt = select(ClimateGenerativeModel).where(
            ClimateGenerativeModel.location_id == location_id
        )
        climate_generative_model = await session.scalar(stmt)
        if climate_generative_model is None:
            return None

        return ClimateGenerativeModelDTO(
            id=climate_generative_model.id,
            location_id=location_id,
            model=bytes_to_object(climate_generative_model.model),
            x_scaler=bytes_to_object(climate_generative_model.x_scaler),
            y_scaler=bytes_to_object(climate_generative_model.y_scaler),
            rmse=climate_generative_model.rmse,
            train_start_year=climate_generative_model.test_start_year,
            train_start_month=climate_generative_model.train_start_month,
            validation_start_year=climate_generative_model.validation_start_year,
            validation_start_month=climate_generative_model.validation_start_month,
            test_start_year=climate_generative_model.test_start_year,
            test_start_month=climate_generative_model.test_start_month,
            train_end_year=climate_generative_model.train_end_year,
            train_end_month=climate_generative_model.train_end_month,
            validation_end_year=climate_generative_model.validation_end_year,
            validation_end_month=climate_generative_model.validation_end_month,
            test_end_year=climate_generative_model.test_end_year,
            test_end_month=climate_generative_model.test_end_month,
        )

    async def delete_climate_generative_model(
        self, session: AsyncSession, location_id: UUID
    ):
        stmt = delete(ClimateGenerativeModel).where(
            ClimateGenerativeModel.location_id == location_id
        )
        await session.execute(stmt)

    async def __save_climate_generative_model(
        self, session: AsyncSession, climate_generative_model: ClimateGenerativeModelDTO
    ) -> UUID:
        model_id = uuid.uuid4()
        await session.execute(
            delete(ClimateGenerativeModel).where(
                ClimateGenerativeModel.location_id
                == climate_generative_model.location_id
            )
        )
        stmt = insert(ClimateGenerativeModel).values(
            id=climate_generative_model.id,
            location_id=climate_generative_model.location_id,
            model=object_to_bytes(climate_generative_model.model),
            x_scaler=object_to_bytes(climate_generative_model.x_scaler),
            y_scaler=object_to_bytes(climate_generative_model.y_scaler),
            rmse=climate_generative_model.rmse,
            train_start_year=climate_generative_model.test_start_year,
            train_start_month=climate_generative_model.train_start_month,
            validation_start_year=climate_generative_model.validation_start_year,
            validation_start_month=climate_generative_model.validation_start_month,
            test_start_year=climate_generative_model.test_start_year,
            test_start_month=climate_generative_model.test_start_month,
            train_end_year=climate_generative_model.train_end_year,
            train_end_month=climate_generative_model.train_end_month,
            validation_end_year=climate_generative_model.validation_end_year,
            validation_end_month=climate_generative_model.validation_end_month,
            test_end_year=climate_generative_model.test_end_year,
            test_end_month=climate_generative_model.test_end_month,
        )
        await session.execute(stmt)
        return model_id
