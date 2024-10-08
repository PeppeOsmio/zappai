from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, cast
from uuid import UUID
import uuid
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from zappai.zappai.exceptions import LocationNotFoundError, SoilTypeNotFoundError
from zappai.zappai.dtos import LocationDTO, SoilTypeDTO
from zappai.zappai.models import Location
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
import pandas as pd
import asyncio
from csv import DictWriter


class LocationRepository:
    def __init__(
        self,
    ) -> None:
        pass

    async def delete_location(self, session: AsyncSession, location_id: UUID):
        stmt = delete(Location).where(Location.id == location_id)
        await session.execute(stmt)

    async def create_location(
        self,
        session: AsyncSession,
        country: str,
        name: str,
        longitude: float,
        latitude: float,
        is_visible: bool,
    ) -> LocationDTO:
        location_id = uuid.uuid4()
        now = datetime.now(tz=timezone.utc).replace(tzinfo=None)
        stmt = insert(Location).values(
            id=location_id,
            country=country,
            name=name,
            longitude=longitude,
            latitude=latitude,
            created_at=now,
            is_downloading_past_climate_data=False,
            is_visible=is_visible,
        )
        await session.execute(stmt)
        return LocationDTO(
            id=location_id,
            country=country,
            name=name,
            longitude=longitude,
            latitude=latitude,
            created_at=now,
            is_downloading_past_climate_data=False,
            is_visible=is_visible,
        )

    async def set_locations_to_not_downloading(self, session: AsyncSession):
        stmt = update(Location).values(is_downloading_past_climate_data=False)
        await session.execute(stmt)

    async def set_location_to_downloading(
        self, session: AsyncSession, location_id: UUID
    ):
        stmt = (
            update(Location)
            .where(Location.id == location_id)
            .values(is_downloading_past_climate_data=True)
        )
        await session.execute(stmt)

    async def set_location_to_not_downloading(
        self, session: AsyncSession, location_id: UUID
    ):
        stmt = (
            update(Location)
            .where(Location.id == location_id)
            .values(is_downloading_past_climate_data=False)
        )
        await session.execute(stmt)

    async def get_locations(
        self, session: AsyncSession, is_visible: bool
    ) -> list[LocationDTO]:
        stmt = (
            select(Location)
            .where(Location.is_visible == is_visible)
            .order_by(Location.created_at)
        )
        locations = await session.scalars(stmt)
        return [self.__location_model_to_dto(location) for location in locations]

    async def get_location_by_country_and_name(
        self, session: AsyncSession, country: str, name: str
    ) -> LocationDTO | None:
        stmt = select(Location).where(
            (Location.country == country) & (Location.name == name)
        )
        location = await session.scalar(stmt)
        if location is None:
            return None
        return self.__location_model_to_dto(location)
    
    async def get_location_by_country_name_coordinates(self, session: AsyncSession, country: str, name: str, latitude: float, longitude: float) -> LocationDTO | None:
        stmt = select(Location).where(
            (Location.country == country) & (Location.name == name) & (Location.latitude == latitude) & (Location.longitude == longitude))
        location = await session.scalar(stmt)
        if location is None:
            return None
        return self.__location_model_to_dto(location)
    
    async def get_location_by_id(
        self, session: AsyncSession, location_id: UUID
    ) -> LocationDTO | None:
        stmt = select(Location).where(Location.id == location_id)
        location = await session.scalar(stmt)
        if location is None:
            return None
        return self.__location_model_to_dto(location)

    async def get_location_by_coordinates(
        self, session: AsyncSession, longitude: float, latitude: float
    ) -> LocationDTO | None:
        stmt = select(Location).where(
            (Location.longitude == longitude) & (Location.latitude == latitude)
        )
        location = await session.scalar(stmt)
        if location is None:
            return None
        return self.__location_model_to_dto(location)

    async def export_to_csv(
        self,
        session: AsyncSession,
        csv_path: str,
    ):

        def open_csv_file():
            return open(csv_path, "w")

        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as pool:
            csv_file = await loop.run_in_executor(executor=pool, func=open_csv_file)
            with csv_file:
                locations = await self.get_locations(session=session, is_visible=False)
                if len(locations) == 0:
                    raise LocationNotFoundError(f"No locations found")
                dicts: list[dict[str, Any]] = []
                for location in locations:
                    dct = location.to_dict()
                    dct.pop("id")
                    dicts.append(dct)

                def write_to_csv():
                    csv_writer = DictWriter(f=csv_file, fieldnames=dicts[0].keys())
                    csv_writer.writeheader()
                    csv_writer.writerows(dicts)

                await loop.run_in_executor(executor=pool, func=write_to_csv)

    async def import_from_csv(self, session: AsyncSession, csv_path: str):
        def read_csv() -> pd.DataFrame:
            return pd.read_csv(csv_path, parse_dates=["created_at"])

        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as pool:
            data = await loop.run_in_executor(executor=pool, func=read_csv)

        dicts = cast(list[dict[str, Any]], data.to_dict(orient="records"))
        for dct in dicts:
            await session.execute(
                delete(Location).where(
                    (Location.name == dct["name"])
                    & (Location.country == dct["country"])
                )
            )
            await self.create_location(
                session=session,
                country=dct["country"],
                name=dct["name"],
                longitude=dct["longitude"],
                latitude=dct["latitude"],
                is_visible=False,
            )

    def __location_model_to_dto(self, location: Location) -> LocationDTO:
        return LocationDTO(
            id=location.id,
            country=location.country,
            name=location.name,
            longitude=location.longitude,
            latitude=location.latitude,
            created_at=location.created_at,
            is_downloading_past_climate_data=location.is_downloading_past_climate_data,
            is_visible=location.is_visible,
        )
