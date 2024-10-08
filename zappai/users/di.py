from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from zappai.database.di import get_session_maker
from zappai.users.repositories import UserRepository


def get_user_repository() -> UserRepository:
    return UserRepository()
