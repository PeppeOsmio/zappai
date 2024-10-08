from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field
from zappai.schemas import CamelCaseBaseModel, CustomBaseModel


class AuthTokenDetailsResponse(CustomBaseModel):
    access_token: str
    token_type: Literal["bearer"]


class GetOwnInfoResponse(CamelCaseBaseModel):
    id: UUID
    username: str
    name: str
    email: str | None
    created_at: datetime
