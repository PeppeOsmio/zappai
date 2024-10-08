import asyncio
import logging
import traceback

from zappai import logging_conf
from zappai.zappai.di import (
    get_cds_api,
    get_crop_repository,
    get_crop_yield_data_repository,
    get_crop_yield_model_service,
    get_location_repository,
    get_past_climate_data_repository,
)
from zappai.database.di import get_session_maker


async def main():

    logging.basicConfig(level=logging.INFO)

    session_maker = get_session_maker()
    location_repository = get_location_repository()
    crop_repository = get_crop_repository()
    cds_api = get_cds_api()
    past_climate_data_repository = get_past_climate_data_repository(
        cds_api=cds_api,
        location_repository=location_repository,
    )
    crop_yield_data_repository = get_crop_yield_data_repository(
        crop_repository=crop_repository,
        location_repository=location_repository,
        past_climate_data_repository=past_climate_data_repository,
    )
    
    async with session_maker() as session:
        await crop_yield_data_repository.import_crop_yield_data(session=session)
        await session.commit()


if __name__ == "__main__":
    logging_conf.create_logger(config=logging_conf.get_default_conf())
    asyncio.run(main())
