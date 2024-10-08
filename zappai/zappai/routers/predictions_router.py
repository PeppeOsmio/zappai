from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import async_sessionmaker

from zappai.auth_tokens.di import get_current_user, get_current_user_with_error
from zappai.database.di import get_session_maker
from zappai.users.models import User
from zappai.zappai.di import get_crop_optimizer_service
from zappai.zappai.exceptions import (
    ClimateGenerativeModelNotFoundError,
    CropYieldModelNotFoundError,
)
from zappai.zappai.schemas import (
    ClimateDataDetails,
    PredictionsResponse,
    SowingAndHarvestingDetails,
)
from zappai.zappai.services.crop_optimizer_service import CropOptimizerService

predictions_router = APIRouter(prefix="/predictions")


@predictions_router.get(path="", response_model=PredictionsResponse)
async def get_best_crop_sowing_and_harvesting_prediction(
    user: Annotated[User, Depends(get_current_user_with_error)],
    session_maker: Annotated[async_sessionmaker, Depends(get_session_maker)],
    crop_optimizer_service: Annotated[
        CropOptimizerService, Depends(get_crop_optimizer_service)
    ],
    crop_name: str,
    location_id: UUID,
):
    try:
        async with session_maker() as session:
            result = await crop_optimizer_service.get_best_crop_sowing_and_harvesting(
                session=session, crop_name=crop_name, location_id=location_id
            )
        return PredictionsResponse(
            best_combinations=[
                SowingAndHarvestingDetails(
                    sowing_year=item.sowing_year,
                    sowing_month=item.sowing_month,
                    harvest_year=item.harvest_year,
                    harvest_month=item.harvest_month,
                    estimated_yield_per_hectar=item.estimated_yield_per_hectar,
                    duration=item.duration,
                )
                for item in result.best_combinations
            ],
            forecast=[
                ClimateDataDetails(
                    location_id=item.location_id,
                    year=item.year,
                    month=item.month,
                    temperature_2m=item.temperature_2m,
                    total_precipitation=item.total_precipitation,
                    surface_solar_radiation_downwards=item.surface_solar_radiation_downwards,
                    surface_thermal_radiation_downwards=item.surface_thermal_radiation_downwards,
                    surface_net_solar_radiation=item.surface_net_solar_radiation,
                    surface_net_thermal_radiation=item.surface_net_thermal_radiation,
                    total_cloud_cover=item.total_cloud_cover,
                    dewpoint_temperature_2m=item.dewpoint_temperature_2m,
                    soil_temperature_level_3=item.soil_temperature_level_3,
                    volumetric_soil_water_layer_3=item.volumetric_soil_water_layer_3,
                )
                for item in result.forecast
            ],
        )
    except CropYieldModelNotFoundError:
        return JSONResponse(
            status_code=404, content={"error": "Crop yield model not found"}
        )
    except ClimateGenerativeModelNotFoundError:
        return JSONResponse(
            status_code=404, content={"error": "Climate generative model not found"}
        )
