from datetime import datetime, timedelta, timezone
import logging
from uuid import UUID
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from zappai.auth_tokens.repositories.dtos import AuthTokenDTO
from zappai.auth_tokens.models import AuthToken
import secrets

from zappai.auth_tokens.repositories.exceptions import (
    AuthTokenNotFoundError,
    WrongCredentialsError,
)
from zappai.users.repositories.dtos import UserDTO
from zappai.users.models import User
from zappai.users.repositories.exceptions import UserNotFoundError
from dataclasses import dataclass

from zappai.users.repositories import UserRepository


class AuthTokenRepository:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def create_auth_token(
        self,
        session: AsyncSession,
        username: str,
        password: str,
        user_agent: str | None,
    ) -> AuthTokenDTO:
        """_summary_

        Args:
            data (CreateAuthTokenDTO):

        Raises:
            UserNotFoundError:

        Returns:
            AuthToken:
        """
        user_id = await self.user_repository.get_user_id_from_username(
            session=session, username=username
        )
        if user_id is None:
            raise WrongCredentialsError()
        now = datetime.now(tz=timezone.utc).replace(tzinfo=None)
        if not await self.user_repository.check_password(
            session=session, username=username, password=password
        ):
            raise WrongCredentialsError()
        auth_token = AuthToken(
            token=secrets.token_bytes(32),
            user_id=user_id,
            user_agent=user_agent,
            created_at=now,
            expires_at=now + timedelta(hours=4),
            is_valid=True,
        )
        session.add(auth_token)
        return AuthTokenDTO(
            token=auth_token.token.hex(),
            user_id=auth_token.user_id,
            created_at=auth_token.created_at,
            expires_at=auth_token.expires_at,
            user_agent=auth_token.user_agent,
            is_valid=auth_token.is_valid,
        )

    async def get_auth_token(
        self, session: AsyncSession, token: str
    ) -> AuthTokenDTO | None:
        """

        Args:
            token (str):

        Returns:
            AuthToken | None:
        """
        stmt = select(AuthToken).where(AuthToken.token == token.encode())
        auth_token = await session.scalar(stmt)
        if auth_token is None:
            return None
        return AuthTokenDTO(
            token=auth_token.token.hex(),
            user_id=auth_token.user_id,
            created_at=auth_token.created_at,
            expires_at=auth_token.expires_at,
            user_agent=auth_token.user_agent,
            is_valid=auth_token.is_valid,
        )

    async def get_tokens(
        self, session: AsyncSession, user_id: UUID
    ) -> list[AuthTokenDTO]:
        """

        Args:
            user_id (UUID):

        Raises:
            UserNotFoundError:

        Returns:
            list[AuthToken]:
        """
        if not await self.user_repository.check_user_exists(
            session=session, user_id=user_id
        ):
            raise UserNotFoundError()
        stmt = select(AuthToken).where(AuthToken.user_id == user_id)
        auth_tokens = await session.scalars(stmt)
        return [
            AuthTokenDTO(
                token=auth_token.token.hex(),
                user_id=auth_token.user_id,
                created_at=auth_token.created_at,
                expires_at=auth_token.expires_at,
                user_agent=auth_token.user_agent,
                is_valid=auth_token.is_valid,
            )
            for auth_token in auth_tokens
        ]

    async def revoke_token(self, session: AsyncSession, token: str, executor_id: UUID):
        """

        Args:
            token (str):

        Raises:
            AuthTokenNotFoundError:
            PermissionError:

        Returns:
            AuthToken:
        """
        # is_admin = self.user_repository.check_is_admin(
        #     session=session, executor_id=executor_id
        # )
        exists_stmt = select(AuthToken.user_id).where(AuthToken.token == token.encode())
        user_id = (await session.execute(exists_stmt)).scalar()
        if user_id is None:
            raise AuthTokenNotFoundError()
        if user_id != executor_id: # and not is_admin:
            raise PermissionError()
        stmt = (
            delete(AuthToken)
            .where(AuthToken.token == token.encode())
        )
        await session.execute(stmt)

    async def revoke_all_tokens_by_username(self, session: AsyncSession, username: str):
        """

        Args:
            user_id (UUID):

        Raises:
            UserNotFoundError:
        """
        user_id = await self.user_repository.get_user_id_from_username(session=session, username=username)
        if user_id is None:
            raise UserNotFoundError(username)
        stmt = (
            delete(AuthToken)
            .where(AuthToken.user_id == user_id)
        )
        await session.execute(stmt)

    async def get_user_from_auth_token(
        self, session: AsyncSession, token: str
    ) -> UserDTO | None:
        now = datetime.now(tz=timezone.utc).replace(tzinfo=None)
        stmt = (
            select(User, AuthToken.expires_at)
            .join(
                AuthToken,
                onclause=AuthToken.user_id == User.id,
            )
            .where(AuthToken.token == bytes.fromhex(token))
        )
        result = (await session.execute(stmt)).first()
        if result is None:
            return None
        user, expires_at = result.tuple()
        if expires_at < now:
            return None
        return UserDTO(
            id=user.id,
            username=user.username,
            name=user.name,
            created_at=user.created_at,
            modified_at=user.modified_at,
            email=user.email,
            is_active=user.is_active,
        )
