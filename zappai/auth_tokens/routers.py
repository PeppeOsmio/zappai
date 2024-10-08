import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Header, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from zappai.auth_tokens.di import get_auth_token_repository, get_current_user, oauth2_scheme
from zappai.auth_tokens.repositories import AuthTokenRepository
from zappai.auth_tokens.repositories.exceptions import WrongCredentialsError
from zappai.auth_tokens.schemas import (
    AuthTokenDetailsResponse,
    GetOwnInfoResponse,
)
from zappai.database.di import get_session_maker
from zappai.users.repositories.dtos import UserDTO
from zappai.users.models import User

auth_token_router = APIRouter(prefix="/auth")


@auth_token_router.post("/", response_model=AuthTokenDetailsResponse)
async def create_auth_token(
    session_maker: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_maker)],
    auth_token_repository: Annotated[
        AuthTokenRepository, Depends(get_auth_token_repository)
    ],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    token: Annotated[str | None, Depends(oauth2_scheme)],
    user: Annotated[User | None, Depends(get_current_user)],
    user_agent: Annotated[str | None, Header()] = None,
):
    try:
        async with session_maker() as session:
            if token is not None and user is not None:
                await auth_token_repository.revoke_token(session=session, token=token, executor_id=user.id)
            auth_token = await auth_token_repository.create_auth_token(
                session=session,
                username=form_data.username,
                password=form_data.password,
                user_agent=user_agent,
            )
            await session.commit()
        return AuthTokenDetailsResponse(
            access_token=auth_token.token, token_type="bearer"
        )
    except WrongCredentialsError:
        raise HTTPException(status_code=401, detail="wrong_credentials")


@auth_token_router.get("/me", response_model=GetOwnInfoResponse)
async def get_own_info(user: Annotated[UserDTO | None, Depends(get_current_user)]):
    if user is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return GetOwnInfoResponse(
        id=user.id,
        username=user.username,
        name=user.name,
        email=user.email,
        created_at=user.created_at,
    )
