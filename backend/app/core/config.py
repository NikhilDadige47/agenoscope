from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    PROJECT_NAME: str = "agenoscope"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    
    SECRET_KEY: str = "insecure-dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Default to local SQLite for simplicity in dev/testing, easily overridden by postgres in prod
    DATABASE_URL: str = "sqlite:///./agenoscope.db"

    # CORS origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    # Rate limiting
    LOGIN_RATE_LIMIT: str = "10/minute"


settings = Settings()
