from datetime import datetime, timezone
import uuid
from sklearn.ensemble import RandomForestRegressor
from sqlalchemy import delete, insert, select, update
from zappai.zappai.utils.common import bytes_to_object, object_to_bytes
from zappai.zappai.dtos import CropDTO
from zappai.zappai.models import Crop
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class CropRepository:
    def __init__(
        self,
    ) -> None:
        pass

    async def delete_crop_by_name(self, session: AsyncSession, name: str):
        await session.execute(delete(Crop).where(Crop.name == name))

    async def create_crop(
        self, session: AsyncSession, name: str, min_farming_months: int, max_farming_months: int
    ) -> CropDTO:
        now = datetime.now(tz=timezone.utc).replace(tzinfo=None)
        stmt = insert(Crop).values(
            [
                {
                    "name": name,
                    "min_farming_months": min_farming_months,
                    "max_farming_months": max_farming_months,
                    "created_at": now,
                }
            ]
        )
        await session.execute(stmt)
        await session.commit()
        return CropDTO(
            name=name,
            created_at=now,
            min_farming_months=min_farming_months,
            max_farming_months=max_farming_months,
            crop_yield_model=None,
            mse=None,
            r2=None,
        )

    async def get_crop_by_name(self, session: AsyncSession, name: str) -> CropDTO | None:
        stmt = select(Crop).where(Crop.name == name)
        crop = await session.scalar(stmt)
        if crop is None:
            return None
        return self.__crop_model_to_dto(crop)

    async def get_crop_by_id(self, session: AsyncSession, crop_name: str) -> CropDTO | None:
        stmt = select(Crop).where(Crop.name == crop_name)
        crop = await session.scalar(stmt)
        if crop is None:
            return None
        return self.__crop_model_to_dto(crop)

    async def save_crop_yield_model(
        self,
        session: AsyncSession,
        crop_name: str,
        crop_yield_model: RandomForestRegressor,
        mse: float,
        r2: float,
    ):
        stmt = (
            update(Crop)
            .where(Crop.name == crop_name)
            .values(
                crop_yield_model=object_to_bytes(crop_yield_model), mse=mse, r2=r2
            )
        )
        await session.execute(stmt)

    async def get_all_crops(self, session: AsyncSession) -> list[CropDTO]:
        stmt = select(Crop)
        results = list(await session.scalars(stmt))
        return [self.__crop_model_to_dto(crop) for crop in results]

    def __crop_model_to_dto(self, crop: Crop) -> CropDTO:
        return CropDTO(
            name=crop.name,
            created_at=crop.created_at,
            min_farming_months=crop.min_farming_months,
            max_farming_months=crop.max_farming_months,
            crop_yield_model=(
                bytes_to_object(crop.crop_yield_model)
                if crop.crop_yield_model is not None
                else None
            ),
            mse=crop.mse,
            r2=crop.r2,
        )
