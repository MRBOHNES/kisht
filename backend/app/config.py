from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://kisht:kisht@localhost:5432/kisht"
    jwt_secret: str = "change-me"
    cors_origin: str = "http://localhost:3000"
    cookie_secure: bool = False
    session_hours: int = 12
    max_failed_logins: int = 5
    lock_minutes: int = 15
    max_upload_bytes: int = 2_000_000

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
