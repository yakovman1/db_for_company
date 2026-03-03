from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")

    # MinIO
    minio_endpoint: str = Field(..., alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(..., alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(..., alias="MINIO_SECRET_KEY")
    minio_public_endpoint: str | None = Field(
        default=None, validation_alias=AliasChoices("MINIO_PUBLIC_ENDPOINT", "MINIO_PRESIGN_ENDPOINT")
    )
    minio_bucket: str = Field(..., validation_alias=AliasChoices("MINIO_BUCKET_FAMILIES", "MINIO_BUCKET"))
    minio_region: str = Field("us-east-1", alias="MINIO_REGION")
    minio_use_ssl: bool = Field(default=False, alias="MINIO_USE_SSL")

    # Security
    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")

    # Presigned URL TTLs
    presigned_put_expires: int = Field(900, alias="PRESIGNED_PUT_EXPIRES")
    presigned_get_expires: int = Field(300, alias="PRESIGNED_GET_EXPIRES")

    # Logging
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    @computed_field  # type: ignore[misc]
    @property
    def endpoint(self) -> str:
        return self.minio_endpoint

    @computed_field  # type: ignore[misc]
    @property
    def public_endpoint(self) -> str:
        return self.minio_public_endpoint or self.minio_endpoint

    @computed_field  # type: ignore[misc]
    @property
    def region(self) -> str:
        return self.minio_region

    @computed_field  # type: ignore[misc]
    @property
    def use_ssl(self) -> bool:
        return bool(self.minio_use_ssl)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]

