from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, LargeBinary, String
from zappai.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship

from zappai.users.models import User


class AuthToken(Base):
    __tablename__ = "auth_token"
    token: Mapped[bytes] = mapped_column(LargeBinary(length=32), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey(column="user.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    user_agent: Mapped[str | None] = mapped_column(String(length=255), nullable=True)
    is_valid: Mapped[bool] = mapped_column(Boolean)

    user: Mapped[User] = relationship()
