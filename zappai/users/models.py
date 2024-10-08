from datetime import datetime
from uuid import UUID

from sqlalchemy import String

from zappai.database import Base
from sqlalchemy.orm import Mapped, mapped_column


class User(Base):
    __tablename__ = "user"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(length=255), unique=True)
    name: Mapped[str] = mapped_column(String(length=255))
    password: Mapped[str] = mapped_column(String(length=60))  # encrpyted with bcrypt
    created_at: Mapped[datetime] = mapped_column(index=True)
    modified_at: Mapped[datetime]
    email: Mapped[str | None] = mapped_column(String(length=255), unique=True)
    is_active: Mapped[bool]
