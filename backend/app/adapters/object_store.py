from __future__ import annotations

import asyncio
from typing import Any, Protocol

import boto3
from botocore.config import Config

from app.core.config import Settings


class ObjectStore(Protocol):
    async def put(self, key: str, data: bytes, *, content_type: str) -> None: ...

    async def get(self, key: str) -> bytes: ...

    async def signed_url(self, key: str, *, seconds: int) -> str: ...


def note_document_key(practice_id: str, note_id: str) -> str:
    return f"practices/{practice_id}/notes/{note_id}/document.pdf"


def analysis_response_key(practice_id: str, note_id: str, revision: int) -> str:
    return f"practices/{practice_id}/notes/{note_id}/analyses/{revision}.json"


class S3ObjectStore:
    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.s3_bucket
        self._encryption = settings.s3_server_side_encryption
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            config=Config(signature_version="s3v4", retries={"max_attempts": 5, "mode": "standard"}),
        )

    async def put(self, key: str, data: bytes, *, content_type: str) -> None:
        extra = {"ServerSideEncryption": self._encryption} if self._encryption else {}
        await asyncio.to_thread(
            self._client.put_object, Bucket=self._bucket, Key=key, Body=data, ContentType=content_type, **extra
        )

    async def get(self, key: str) -> bytes:
        response = await asyncio.to_thread(self._client.get_object, Bucket=self._bucket, Key=key)
        return await asyncio.to_thread(response["Body"].read)

    async def signed_url(self, key: str, *, seconds: int) -> str:
        return await asyncio.to_thread(
            self._client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self._bucket, "Key": key, "ResponseContentDisposition": "inline"},
            ExpiresIn=seconds,
        )
