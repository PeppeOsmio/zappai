from typing import Annotated
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from fastapi import Depends

from zappai.zappai.repositories.climate_generative_model_repository import (
    ClimateGenerativeModelRepository,
)
from zappai.zappai.repositories.crop_repository import CropRepository
from zappai.zappai.repositories.crop_yield_data_repository import CropYieldDataRepository
from zappai.zappai.services.crop_optimizer_service import CropOptimizerService
from zappai.zappai.services.crop_yield_model_service import (
    CropYieldModelService,
)
from zappai.zappai.repositories.future_climate_data_repository import (
    FutureClimateDataRepository,
)
from zappai.zappai.repositories.location_repository import LocationRepository
from zappai.zappai.repositories.past_climate_data_repository import (
    PastClimateDataRepository,
)
from zappai.zappai.repositories.copernicus_data_store_api import CopernicusDataStoreAPI
from zappai.config import settings


def get_location_repository() -> LocationRepository:
    return LocationRepository()


def get_crop_repository() -> CropRepository:
    return CropRepository()


def get_cds_api() -> CopernicusDataStoreAPI:
    return CopernicusDataStoreAPI( 
        api_token=settings.cds_api_key,
    )


def get_past_climate_data_repository(
    cds_api: Annotated[CopernicusDataStoreAPI, Depends(get_cds_api)],
    location_repository: Annotated[
        LocationRepository, Depends(get_location_repository)
    ],
) -> PastClimateDataRepository:
    return PastClimateDataRepository(
        copernicus_data_store_api=cds_api,
        location_repository=location_repository,
    )


def get_crop_yield_data_repository(
    crop_repository: Annotated[CropRepository, Depends(get_crop_repository)],
    location_repository: Annotated[
        LocationRepository, Depends(get_location_repository)
    ],
    past_climate_data_repository: Annotated[
        PastClimateDataRepository, Depends(get_past_climate_data_repository)
    ],
) -> CropYieldDataRepository:
    return CropYieldDataRepository(
        crop_repository=crop_repository,
        location_repository=location_repository,
        past_climate_data_repository=past_climate_data_repository,
    )


def get_future_climate_data_repository(
    cds_api: Annotated[CopernicusDataStoreAPI, Depends(get_cds_api)],
) -> FutureClimateDataRepository:
    return FutureClimateDataRepository(copernicus_data_store_api=cds_api)


def get_climate_generative_model_repository(
    location_repository: Annotated[
        LocationRepository, Depends(get_location_repository)
    ],
    past_climate_data_repository: Annotated[
        PastClimateDataRepository, Depends(get_past_climate_data_repository)
    ],
    future_climate_data_repository: Annotated[
        FutureClimateDataRepository, Depends(get_future_climate_data_repository)
    ],
) -> ClimateGenerativeModelRepository:
    return ClimateGenerativeModelRepository(
        location_repository=location_repository,
        past_climate_data_repository=past_climate_data_repository,
        future_climate_data_repository=future_climate_data_repository,
    )


def get_crop_yield_model_service(
    past_climate_data_repository: Annotated[
        PastClimateDataRepository, Depends(get_past_climate_data_repository)
    ],
    location_repository: Annotated[
        LocationRepository, Depends(get_location_repository)
    ],
    crop_yield_data_repository: Annotated[
        CropYieldDataRepository, Depends(get_crop_yield_data_repository)
    ],
    crop_repository: Annotated[CropRepository, Depends(get_crop_repository)],
) -> CropYieldModelService:
    return CropYieldModelService(
        past_climate_data_repository=past_climate_data_repository,
        location_repository=location_repository,
        crop_yield_data_repository=crop_yield_data_repository,
        crop_repository=crop_repository,
    )


def get_crop_optimizer_service(
    past_climate_data_repository: Annotated[
        PastClimateDataRepository, Depends(get_past_climate_data_repository)
    ],
    location_repository: Annotated[
        LocationRepository, Depends(get_location_repository)
    ],
    climate_generative_model_repository: Annotated[
        ClimateGenerativeModelRepository,
        Depends(get_climate_generative_model_repository),
    ],
    crop_repository: Annotated[CropRepository, Depends(get_crop_repository)],
    future_climate_data_repository: Annotated[
        FutureClimateDataRepository, Depends(get_future_climate_data_repository)
    ],
) -> CropOptimizerService:
    return CropOptimizerService(
        crop_repository=crop_repository,
        past_climate_data_repository=past_climate_data_repository,
        future_climate_data_repository=future_climate_data_repository,
        location_repository=location_repository,
        climate_generative_model_repository=climate_generative_model_repository,
    )
