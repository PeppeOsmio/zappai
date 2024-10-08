from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import async_sessionmaker

from zappai.auth_tokens.di import get_current_user, get_current_user_with_error
from zappai.database.di import get_session_maker
from zappai.users.models import User
from zappai.zappai.di import get_crop_repository
from zappai.zappai.repositories.crop_repository import CropRepository
from zappai.zappai.schemas import CropDetailsResponse

crops_router = APIRouter(prefix="/crops")


@crops_router.get(path="")
async def get_crops(
    user: Annotated[User, Depends(get_current_user_with_error)],
    session_maker: Annotated[async_sessionmaker, Depends(get_session_maker)],
    crop_repository: Annotated[CropRepository, Depends(get_crop_repository)],
) -> list[CropDetailsResponse]:
    async with session_maker() as session:
        crops = await crop_repository.get_all_crops(session=session)
    return [CropDetailsResponse(name=crop.name) for crop in crops]
