from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID
import uuid

import bcrypt
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count
from zappai.users.repositories.dtos import UserDTO
from zappai.users.models import User
from zappai.users.repositories.exceptions import (
    EmailExistsError,
    UserNotFoundError,
    UsernameExistsError,
)


class UserRepository:

    def __init__(self) -> None:
        pass

    async def get_user_by_id(
        self, session: AsyncSession, user_id: UUID
    ) -> UserDTO | None:
        """

        Args:
            user_id (UUID):

        Returns:
            User | None:
        """
        stmt = select(User).where(User.id == user_id)
        user = await session.scalar(stmt)
        if user is None:
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

    async def get_users(self, session: AsyncSession) -> list[UserDTO]:
        """Get users with pagination and page size.

        Args:
            cursor (str):
            page_size (int):

        Returns:
            list[User]:
        """
        stmt = select(User).order_by(User.created_at, User.id)
        results = await session.scalars(stmt)
        return [
            UserDTO(
                id=user.id,
                username=user.username,
                name=user.name,
                created_at=user.created_at,
                modified_at=user.modified_at,
                email=user.email,
                is_active=user.is_active,
            )
            for user in results
        ]

    async def get_users_count(self, session: AsyncSession) -> int:
        """

        Raises:
            Exception:

        Returns:
            int:
        """
        async with session:
            stmt = select(count(User.id))
            result = await session.scalar(stmt)
        if result is None:
            raise Exception("idk why count is none")
        return result

    async def create_user(
        self,
        session: AsyncSession,
        username: str,
        password: str,
        name: str,
        email: str | None,
    ) -> UserDTO:
        exists_username_stmt = select(User.id).where(User.username == username)
        user_id = await session.scalar(exists_username_stmt)
        if user_id is not None:
            raise UsernameExistsError()
        exists_email_stmt = select(User.email).where(User.email == email)
        email = await session.scalar(exists_email_stmt)
        if email is not None:
            raise EmailExistsError()
        now = datetime.now(tz=timezone.utc).replace(tzinfo=None)
        user = User(
            id=uuid.uuid4(),
            username=username,
            name=name,
            email=email,
            password=self.__hash_password(password),
            created_at=now,
            modified_at=now,
            is_active=True,
        )
        session.add(user)
        return UserDTO(
            id=user.id,
            username=user.username,
            name=user.name,
            created_at=user.created_at,
            modified_at=user.modified_at,
            email=user.email,
            is_active=user.is_active,
        )
    
    async def delete_user(self, session: AsyncSession, username: str):
        user_id = await self.get_user_id_from_username(session=session, username=username)
        if user_id is None:
            raise UserNotFoundError(username)
        await session.execute(delete(User).where(User.username == username))

    async def check_password(
        self, session: AsyncSession, username: str, password: str
    ) -> bool:
        stmt = select(User.password).where(User.username == username)
        hashed_pw = await session.scalar(stmt)
        if hashed_pw is None:
            raise UserNotFoundError()
        return bcrypt.checkpw(
            password=password.encode(), hashed_password=hashed_pw.encode()
        )

    async def get_user_id_from_username(
        self, session: AsyncSession, username: str
    ) -> UUID | None:
        stmt = select(User.id).where(User.username == username)
        result = (await session.execute(stmt)).first()
        if result is None:
            return None
        return result.tuple()[0]

    async def check_user_exists(self, session: AsyncSession, user_id: UUID) -> bool:
        stmt = select(User.id).where(User.id == user_id)
        result = await session.execute(stmt)
        return result.first() is None

    def __hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password=password.encode(), salt=bcrypt.gensalt()).decode()
