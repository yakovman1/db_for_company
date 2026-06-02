from __future__ import annotations

from typing import Any, Dict, Optional

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class S3Service:
    def __init__(self) -> None:
        session = boto3.session.Session()
        common_config = Config(
            s3={"addressing_style": "path"},
            signature_version="s3v4",
            retries={"max_attempts": 3},
        )
        self.client = session.client(
            "s3",
            endpoint_url=str(settings.endpoint),
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            region_name=settings.region,
            config=common_config,
            use_ssl=settings.use_ssl,
        )
        self.presign_client = session.client(
            "s3",
            endpoint_url=str(settings.public_endpoint),
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            region_name=settings.region,
            config=common_config,
            use_ssl=settings.use_ssl,
        )
        self.bucket = settings.minio_bucket

    def generate_put_url(self, object_key: str, *, expires_in: int, content_type: str = "application/octet-stream") -> str:
        params = {
            "Bucket": self.bucket,
            "Key": object_key,
            "ContentType": content_type,
        }
        return self.presign_client.generate_presigned_url(
            "put_object", Params=params, ExpiresIn=expires_in
        )

    def generate_get_url(self, object_key: str, *, expires_in: int) -> str:
        params = {
            "Bucket": self.bucket,
            "Key": object_key,
        }
        return self.presign_client.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=expires_in
        )

    def head_object(self, object_key: str) -> Dict[str, Any] | None:
        try:
            response = self.client.head_object(Bucket=self.bucket, Key=object_key)
            return response
        except ClientError as exc:
            if exc.response["Error"]["Code"] in {"404", "NoSuchKey"}:
                return None
            logger.warning("s3_head_object_error", error=str(exc))
            return None

    def delete_object(self, object_key: str) -> bool:
        """Удаляет объект из S3. Возвращает True если успешно, False при ошибке."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=object_key)
            return True
        except ClientError as exc:
            logger.warning("s3_delete_object_error", object_key=object_key, error=str(exc))
            return False


s3_service = S3Service()
