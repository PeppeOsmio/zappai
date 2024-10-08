import asyncio
import logging

from zappai import logging_conf
from zappai.database.di import get_session_maker
from zappai.zappai.di import (
    get_cds_api,
    get_location_repository,
    get_past_climate_data_repository,
)


async def main():
    session_maker = get_session_maker()
    location_repository = get_location_repository()
    cds_api = get_cds_api()
    past_climate_data_repository = get_past_climate_data_repository(
        cds_api=cds_api,
        location_repository=location_repository,
    )

    async with session_maker() as session:
        logging.info("Importing past climate data")
        await past_climate_data_repository.import_from_csv(
            session=session, csv_path="training_data/past_climate_data.csv"
        )
        await session.commit()


if __name__ == "__main__":
    logging_conf.create_logger(config=logging_conf.get_default_conf())
    asyncio.run(main())
