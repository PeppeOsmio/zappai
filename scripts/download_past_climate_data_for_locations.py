import asyncio
import logging
import traceback
from typing import Iterable
from uuid import UUID

from zappai import logging_conf
from zappai.zappai.di import (
    get_cds_api,
    get_crop_repository,
    get_crop_yield_data_repository,
    get_location_repository,
    get_past_climate_data_repository,
)
from zappai.zappai.dtos import LocationClimateYearsDTO
from zappai.database.di import get_session_maker
import os


import tracemalloc

# Start tracing memory allocations
tracemalloc.start()


async def main():
    
    session_maker = get_session_maker()
    location_repository = get_location_repository()
    cds_api = get_cds_api()
    past_climate_data_repository = get_past_climate_data_repository(
        cds_api=cds_api,
        location_repository=location_repository,
    )
    crop_repository = get_crop_repository()

    crop_yield_data_repository = get_crop_yield_data_repository(
        crop_repository=crop_repository,
        location_repository=location_repository,
        past_climate_data_repository=past_climate_data_repository,
    )

    logging.info("Getting location and climate data from Crop Yields table")
    async with session_maker() as session:
        location_climate_years_from_crop_yield_data = (
            await crop_yield_data_repository.get_unique_location_climate_years(
                session=session
            )
        )

        logging.info("Getting location and climate data from Past Climate Data table")
        location_climate_years_from_past_climate_data = (
            await past_climate_data_repository.get_unique_location_climate_years(session=session)
        )

        for location_climate_years in location_climate_years_from_crop_yield_data:
            for tmp in location_climate_years_from_past_climate_data:
                if location_climate_years.location_id == tmp.location_id:
                    location_climate_years.years = location_climate_years.years - tmp.years
                    break

        location_climate_years_to_fetch: list[LocationClimateYearsDTO] = [
            item
            for item in location_climate_years_from_crop_yield_data
            if len(item.years) > 0
        ]

        processed = len(location_climate_years_from_crop_yield_data) - len(location_climate_years_to_fetch)
        logging.info(f"COMPLETED: {processed}/{len(location_climate_years_from_crop_yield_data)}")

        for location_climate_years in location_climate_years_to_fetch:
            await past_climate_data_repository.download_past_climate_data_for_years(session=session,
                location_id=location_climate_years.location_id,
                years=list(location_climate_years.years),
            )
            await session.commit()
            processed += 1
            logging.info(
                f"COMPLETED: {processed}/{len(location_climate_years_from_crop_yield_data)}"
            )

if __name__ == "__main__":
    logging_conf.create_logger(config=logging_conf.get_default_conf())
    asyncio.run(main())
