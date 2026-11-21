from pathlib import Path
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Core Application Settings
    APP_NAME: str = "Smart Document Processing and Management System"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Server Settings
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # CORS Settings
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://127.0.0.1:5500,http://localhost:5500"

    # Database Settings
    DATABASE_URL: str = "sqlite:///./smart_document_manager.db"

    # Storage Settings
    STORAGE_TYPE: str = "local"  # "local" for Phase 1, "s3" for Phase 2
    LOCAL_STORAGE_DIR: str = "./local_storage/documents"
    MAX_UPLOAD_SIZE_BYTES: int = 20971520  # 20 MB (Part 4 requirement)

    # Authentication & JWT Security Settings
    JWT_SECRET_KEY: str = "smartdoc-super-secure-production-ready-jwt-key-32-chars-minimum"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def resolved_storage_path(self) -> Path:
        path = Path(self.LOCAL_STORAGE_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
