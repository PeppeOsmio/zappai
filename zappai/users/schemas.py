from datetime import datetime
from uuid import UUID
from pydantic import EmailStr, Field
from zappai.schemas import CamelCaseBaseModel, CustomBaseModel


class UserDetailsResponse(CamelCaseBaseModel):
    id: UUID
    username: str
    name: str
    created_at: datetime
    modified_at: datetime
    email: EmailStr | None
    is_active: bool


class UserCreateBody(CamelCaseBaseModel):
    username: str = Field(max_length=255)
    name: str = Field(max_length=255)
    password: str = Field(max_length=255)
    email: EmailStr | None = Field(max_length=255)


class UsersCountResponse(CamelCaseBaseModel):
    count: int
