import logging
from typing import Literal
from uuid import UUID
from pydantic_settings import BaseSettings, SettingsConfigDict
import dotenv

dotenv.load_dotenv(dotenv_path=".env", override=True)


class Settings(BaseSettings):
    db_host: str
    db_port: str
    db_name: str
    db_user: str
    db_password: str
    cds_api_key: UUID

    model_config = SettingsConfigDict(env_prefix="ZAPPAI_")


settings = Settings()  # type: ignore
