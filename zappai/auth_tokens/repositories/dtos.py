from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class AuthTokenDTO:
    token: str
    user_id: UUID
    created_at: datetime
    expires_at: datetime
    user_agent: str | None
    is_valid: bool
