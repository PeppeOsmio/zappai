import asyncio
import logging
import os
from typing import cast
from uuid import UUID
import pandas as pd

from zappai import logging_conf
from zappai.zappai.di import (
    get_cds_api,
    get_location_repository,
    get_past_climate_data_repository,
)
from zappai.zappai.dtos import ClimateDataDTO
from zappai.database.di import get_session_maker
from zappai.zappai.utils import common

import traceback


async def main():
    logging.basicConfig(level=logging.INFO)

    session_maker = get_session_maker()
    location_repository = get_location_repository()
    cds_api = get_cds_api()
    past_climate_data_repository = get_past_climate_data_repository(
        cds_api=cds_api,
        location_repository=location_repository,
    )

    async with session_maker() as session:
        location = await location_repository.get_location_by_country_and_name(
            session=session,
            country=common.EXAMPLE_LOCATION_COUNTRY,
            name=common.EXAMPLE_LOCATION_NAME,
        )

        if location is None:
            raise Exception()

        retries = 0
        while retries < 10:
            try:
                logging.info(f"Starting download")
                await past_climate_data_repository.download_new_past_climate_data(
                    session=session,
                    location_id=location.id
                )
                break
            except Exception as e:
                logging.error(traceback.format_exc())
                logging.info("Failed to fetch past climate data, retrying...")
                retries += 1
    

if __name__ == "__main__":
    logging_conf.create_logger(config=logging_conf.get_default_conf())
    asyncio.run(main())
