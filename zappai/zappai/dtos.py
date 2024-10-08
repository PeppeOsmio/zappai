from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from keras.src.models import Sequential
import pandas as pd

from typing import Any, Sequence, cast

from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

from zappai.schemas import CustomBaseModel


@dataclass
class SoilTypeDTO:
    id: UUID
    name: str


@dataclass
class LocationClimateYearsDTO:
    location_id: UUID
    years: set[int]


@dataclass
class CropDTO:
    name: str
    created_at: datetime
    min_farming_months: int
    max_farming_months: int
    crop_yield_model: RandomForestRegressor | None
    mse: float | None
    r2: float | None


@dataclass
class CropYieldDataDTO:
    id: UUID
    location_id: UUID
    crop_name: str
    sowing_year: int
    sowing_month: int
    harvest_year: int
    harvest_month: int
    duration_months: int
    yield_per_hectar: float

    @staticmethod
    def from_list_to_dataframe(lst: list[CropYieldDataDTO]) -> pd.DataFrame:
        df = pd.DataFrame([obj.__dict__ for obj in lst])
        df = df.sort_values(by=["sowing_year", "sowing_month"])
        df = df.reset_index()
        return df


@dataclass
class LocationDTO:
    id: UUID
    country: str
    name: str
    longitude: float
    latitude: float
    created_at: datetime
    is_downloading_past_climate_data: bool
    is_visible: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "country": self.country,
            "name": self.name,
            "longitude": self.longitude,
            "latitude": self.latitude,
            "created_at": self.created_at.isoformat(),
            "is_downloading_past_climate_data": self.is_downloading_past_climate_data,
        }


@dataclass
class ClimateGenerativeModelDTO:
    id: UUID
    location_id: UUID
    model: Sequential
    x_scaler: StandardScaler
    y_scaler: StandardScaler
    rmse: float

    train_start_year: int
    train_start_month: int
    train_end_year: int
    train_end_month: int

    validation_start_year: int
    validation_start_month: int
    validation_end_year: int
    validation_end_month: int

    test_start_year: int
    test_start_month: int
    test_end_year: int
    test_end_month: int


@dataclass
class FutureClimateDataDTO:
    year: int
    month: int
    longitude: float
    latitude: float

    u_component_of_wind_10m: float
    v_component_of_wind_10m: float
    temperature_2m: float
    evaporation: float
    total_precipitation: float
    surface_pressure: float
    surface_solar_radiation_downwards: float
    surface_thermal_radiation_downwards: float

    @staticmethod
    def from_list_to_dataframe(lst: Sequence[FutureClimateDataDTO]) -> pd.DataFrame:
        df = pd.DataFrame([obj.__dict__ for obj in lst])
        df = df.rename(
            columns={
                "u_component_of_wind_10m": "10m_u_component_of_wind",
                "v_component_of_wind_10m": "10m_v_component_of_wind",
                "temperature_2m": "2m_temperature",
            },
        )
        df = df.set_index(keys=["year", "month"], drop=True)
        df = df.sort_index(ascending=[True, True])
        return df

    @staticmethod
    def from_dataframe_to_list(df: pd.DataFrame) -> list[FutureClimateDataDTO]:
        tmp_df = df.rename(
            columns={
                "10m_u_component_of_wind": "u_component_of_wind_10m",
                "10m_v_component_of_wind": "v_component_of_wind_10m",
                "2m_temperature": "temperature_2m",
            },
        )
        result: list[FutureClimateDataDTO] = []
        for index, row in tmp_df.iterrows():
            year, month = cast(pd.MultiIndex, index)
            result.append(FutureClimateDataDTO(year=year, month=month, **row.to_dict()))
        return result


@dataclass
class ClimateDataDTO:
    location_id: UUID
    year: int
    month: int

    temperature_2m: float
    total_precipitation: float
    surface_solar_radiation_downwards: float
    surface_thermal_radiation_downwards: float

    surface_net_solar_radiation: float
    surface_net_thermal_radiation: float
    total_cloud_cover: float
    dewpoint_temperature_2m: float
    soil_temperature_level_3: float
    volumetric_soil_water_layer_3: float

    @staticmethod
    def from_list_to_dataframe(lst: Sequence[ClimateDataDTO]) -> pd.DataFrame:
        df = pd.DataFrame([item.__dict__ for item in lst])
        df = df.rename(
            columns={
                "temperature_2m": "2m_temperature",
                "dewpoint_temperature_2m": "2m_dewpoint_temperature",
            },
        )
        df = df.set_index(keys=["year", "month"], drop=True)
        df = df.sort_index(ascending=[True, True])
        return df

    @staticmethod
    def from_dataframe_to_list(df: pd.DataFrame) -> list[ClimateDataDTO]:
        tmp_df = df.rename(
            columns={
                "2m_temperature": "temperature_2m",
                "2m_dewpoint_temperature": "dewpoint_temperature_2m",
            },
        )
        result: list[ClimateDataDTO] = []
        for index, row in tmp_df.iterrows():
            year, month = cast(pd.MultiIndex, index)
            result.append(ClimateDataDTO(year=year, month=month, **row.to_dict()))
        return result


@dataclass
class PastClimateDataDTO(ClimateDataDTO):
    u_component_of_wind_10m: float
    v_component_of_wind_10m: float
    evaporation: float
    surface_pressure: float
    snowfall: float

    @staticmethod
    def from_list_to_dataframe(
        lst: list[PastClimateDataDTO], index_keys: list[str] | None = None, ascending: list[bool] | None = None
    ) -> pd.DataFrame:
        df = pd.DataFrame([item.__dict__ for item in lst])
        df = df.rename(
            columns={
                "u_component_of_wind_10m": "10m_u_component_of_wind",
                "v_component_of_wind_10m": "10m_v_component_of_wind",
                "temperature_2m": "2m_temperature",
                "dewpoint_temperature_2m": "2m_dewpoint_temperature",
            },
        )
        if index_keys is None:
            df = df.set_index(keys=["year", "month"], drop=True)
            df = df.sort_index(ascending=[True, True])
            return df
        if len(index_keys) == 0:
            return df
        df = df.set_index(keys=index_keys, drop=True)
        df = df.sort_index(ascending=cast(list[bool], ascending))
        return df

    @staticmethod
    def from_dataframe_to_list(df: pd.DataFrame) -> list[PastClimateDataDTO]:
        tmp_df = df.rename(
            columns={
                "10m_u_component_of_wind": "u_component_of_wind_10m",
                "10m_v_component_of_wind": "v_component_of_wind_10m",
                "2m_temperature": "temperature_2m",
                "2m_dewpoint_temperature": "dewpoint_temperature_2m",
            },
        )
        result: list[PastClimateDataDTO] = []
        for index, row in tmp_df.iterrows():
            year, month = cast(pd.MultiIndex, index)
            result.append(PastClimateDataDTO(year=year, month=month, **row.to_dict()))
        return result

    def to_climate_data_dto(self) -> ClimateDataDTO:
        return ClimateDataDTO(
            location_id=self.location_id,
            year=self.year,
            month=self.month,
            temperature_2m=self.temperature_2m,
            total_precipitation=self.total_precipitation,
            surface_solar_radiation_downwards=self.surface_solar_radiation_downwards,
            surface_thermal_radiation_downwards=self.surface_thermal_radiation_downwards,
            surface_net_solar_radiation=self.surface_net_solar_radiation,
            surface_net_thermal_radiation=self.surface_net_thermal_radiation,
            total_cloud_cover=self.total_cloud_cover,
            dewpoint_temperature_2m=self.dewpoint_temperature_2m,
            soil_temperature_level_3=self.soil_temperature_level_3,
            volumetric_soil_water_layer_3=self.volumetric_soil_water_layer_3,
        )
