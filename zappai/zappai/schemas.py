from datetime import datetime
from uuid import UUID
from zappai.schemas import CamelCaseBaseModel, CustomBaseModel
from zappai.zappai.dtos import ClimateDataDTO, CropDTO
from zappai.zappai.services.crop_optimizer_service import (
    CropOptimizerResultDTO,
    SowingAndHarvestingDTO,
)


class GetPastClimateDataOfLocationResponse(CamelCaseBaseModel):
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
    soil_temperature_level_1: float
    volumetric_soil_water_layer_1: float


class CreateLocationBody(CamelCaseBaseModel):
    country: str
    name: str
    longitude: float
    latitude: float


class LocationDetailsResponse(CamelCaseBaseModel):
    id: UUID
    country: str
    name: str
    longitude: float
    latitude: float
    created_at: datetime
    is_model_ready: bool
    is_downloading_past_climate_data: bool
    last_past_climate_data_year: int | None
    last_past_climate_data_month: int | None


class ClimateDataDetails(CamelCaseBaseModel):
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


class SowingAndHarvestingDetails(CamelCaseBaseModel):
    sowing_year: int
    sowing_month: int
    harvest_year: int
    harvest_month: int
    estimated_yield_per_hectar: float
    duration: int


class PredictionsResponse(CamelCaseBaseModel):
    best_combinations: list[SowingAndHarvestingDetails]
    forecast: list[ClimateDataDetails]


class CropDetailsResponse(CamelCaseBaseModel):
    name: str
