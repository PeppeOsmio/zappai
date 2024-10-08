import logging
from typing import Annotated
from fastapi import Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from zappai.auth_tokens.repositories import AuthTokenRepository
from zappai.database.di import get_session_maker
from zappai.users.di import get_user_repository
from zappai.users.repositories.dtos import UserDTO
from zappai.users.models import User
from zappai.users.repositories.user_repository import UserRepository


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth", auto_error=False)


def get_auth_token_repository(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
) -> AuthTokenRepository:
    return AuthTokenRepository(user_repository=user_repository)


async def get_current_user(
    session_maker: Annotated[async_sessionmaker, Depends(get_session_maker)],
    auth_token_repository: Annotated[
        AuthTokenRepository, Depends(get_auth_token_repository)
    ],
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> UserDTO | None:
    if token is None:
        return None
    async with session_maker() as session:
        user = await auth_token_repository.get_user_from_auth_token(
            session=session, token=token
        )
    return user


async def get_current_user_with_error(
    user: Annotated[UserDTO | None, Depends(get_current_user)]
) -> UserDTO:
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return user
