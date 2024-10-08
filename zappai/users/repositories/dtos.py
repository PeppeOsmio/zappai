from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class UserDTO:
    id: UUID
    username: str
    name: str
    created_at: datetime
    modified_at: datetime
    email: str | None
    is_active: bool
