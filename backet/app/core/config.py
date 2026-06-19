from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")

    # S3-compatible object storage. MINIO_* names are kept for existing deployments.
    minio_endpoint: str = Field(..., validation_alias=AliasChoices("S3_ENDPOINT", "MINIO_ENDPOINT"))
    minio_access_key: str = Field(..., validation_alias=AliasChoices("S3_ACCESS_KEY", "MINIO_ACCESS_KEY"))
    minio_secret_key: str = Field(..., validation_alias=AliasChoices("S3_SECRET_KEY", "MINIO_SECRET_KEY"))
    minio_public_endpoint: str | None = Field(
        default=None,
        validation_alias=AliasChoices("S3_PUBLIC_ENDPOINT", "S3_PRESIGN_ENDPOINT", "MINIO_PUBLIC_ENDPOINT", "MINIO_PRESIGN_ENDPOINT"),
    )
    minio_bucket: str = Field(..., validation_alias=AliasChoices("S3_BUCKET_FAMILIES", "S3_BUCKET", "MINIO_BUCKET_FAMILIES", "MINIO_BUCKET"))
    minio_region: str = Field("us-east-1", validation_alias=AliasChoices("S3_REGION", "MINIO_REGION"))
    minio_use_ssl: bool = Field(default=False, validation_alias=AliasChoices("S3_USE_SSL", "MINIO_USE_SSL"))

    # Security
    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    jwt_expires_seconds: int = Field(28800, alias="JWT_EXPIRES_SECONDS")

    # Presigned URL TTLs
    presigned_put_expires: int = Field(900, alias="PRESIGNED_PUT_EXPIRES")
    presigned_get_expires: int = Field(300, alias="PRESIGNED_GET_EXPIRES")

    # Shared catalog
    shared_catalog_company_id: str = Field("CATALOG", alias="SHARED_CATALOG_COMPANY_ID")

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

