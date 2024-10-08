from typing import Annotated
from uuid import UUID
from fastapi import Depends, HTTPException, Query
from fastapi.routing import APIRouter
from sqlalchemy.ext.asyncio import async_sessionmaker

from zappai.auth_tokens.di import get_current_user
from zappai.database.di import get_session_maker
from zappai.users.repositories.dtos import UserDTO
from zappai.users.repositories.exceptions import (
    EmailExistsError,
    UsernameExistsError,
)
from zappai.users.schemas import UserCreateBody, UserDetailsResponse
from zappai.users.repositories import UserRepository
from zappai.users.di import get_user_repository
from zappai.users.schemas import UsersCountResponse

user_router = APIRouter(prefix="/users")


@user_router.post(
    "/",
    response_model=UserDetailsResponse,
    responses={
        400: {
            "description": "Invalid data",
            "content": {"application/json": {"example": {"detail": "username_exists"}}},
        }
    },
)
async def create_user(
    session_maker: Annotated[async_sessionmaker, Depends(get_session_maker)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    data: UserCreateBody,
):
    try:
        async with session_maker() as session:
            user = await user_repository.create_user(
                session=session,
                username=data.username,
                password=data.password,
                name=data.name,
                email=data.email,
            )
            await session.commit()
        return UserDetailsResponse.model_construct(
            id=user.id,
            username=user.username,
            name=user.name,
            email=user.email,
            created_at=user.created_at,
            modified_at=user.modified_at,
            is_active=user.is_active,
        )
    except UsernameExistsError:
        raise HTTPException(status_code=400, detail="username_exists")
    except EmailExistsError:
        raise HTTPException(status_code=400, detail="email_exists")


@user_router.get(
    "/{user_id}",
    response_model=UserDetailsResponse,
    responses={
        404: {
            "description": "User not found",
            "content": {"application/json": {"example": {"detail": "user_not_found"}}},
        }
    },
)
async def get_user_details(
    session_maker: Annotated[async_sessionmaker, Depends(get_session_maker)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    user_id: UUID,
):
    async with session_maker() as session:
        user = await user_repository.get_user_by_id(session=session, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="not_found")
    return UserDetailsResponse.model_construct(
        id=user.id,
        username=user.username,
        name=user.name,
        email=user.email,
        created_at=user.created_at,
        modified_at=user.modified_at,
        is_active=user.is_active,
    )


@user_router.get("", response_model=list[UserDetailsResponse])
async def get_users(
    session_maker: Annotated[async_sessionmaker, Depends(get_session_maker)],
    _: Annotated[UserDTO | None, Depends(get_current_user)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
):
    async with session_maker() as session:
        users = await user_repository.get_users(
            session=session
        )
    return [
        UserDetailsResponse.model_construct(
            id=user.id,
            username=user.username,
            name=user.name,
            email=user.email,
            created_at=user.created_at,
            modified_at=user.modified_at,
            is_active=user.is_active,
        )
        for user in users
    ]


@user_router.get("/count", response_model=UsersCountResponse)
async def get_users_count(
    session_maker: Annotated[async_sessionmaker, Depends(get_session_maker)],
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
):
    async with session_maker() as session:
        count = await user_repository.get_users_count(session=session)
    return UsersCountResponse.model_construct(count=count)
