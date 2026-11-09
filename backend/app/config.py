from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://kisht:kisht@localhost:5432/kisht"
    # required: no default, so a missing secret stops the app instead of signing with a known one
    jwt_secret: str = Field(min_length=32)
    cors_origin: str = "http://localhost:3000"
    # only set to false for local http development
    cookie_secure: bool = True
    session_hours: int = 12
    max_failed_logins: int = 5
    lock_minutes: int = 15
    max_upload_bytes: int = 2_000_000

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
