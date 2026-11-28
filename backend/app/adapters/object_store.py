from __future__ import annotations

import asyncio
from typing import Any, Protocol

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import Settings


class ObjectStore(Protocol):
    async def put(self, key: str, data: bytes, *, content_type: str) -> None: ...

    async def get(self, key: str) -> bytes: ...

    async def signed_url(self, key: str, *, seconds: int) -> str: ...

    async def delete(self, keys: list[str]) -> None: ...

    async def delete_prefix(self, prefix: str) -> int: ...

    async def exists(self, key: str) -> bool: ...


def practice_prefix(practice_id: str) -> str:
    if not practice_id or "/" in practice_id:
        raise ValueError(f"not a practice id: {practice_id!r}")
    return f"practices/{practice_id}/"


def note_prefix(practice_id: str, note_id: str) -> str:
    if not note_id or "/" in note_id:
        raise ValueError(f"not a note id: {note_id!r}")
    return f"{practice_prefix(practice_id)}notes/{note_id}/"


def note_document_key(practice_id: str, note_id: str) -> str:
    return f"practices/{practice_id}/notes/{note_id}/document.pdf"


def note_document_revision_key(practice_id: str, note_id: str, revision: int) -> str:
    return f"practices/{practice_id}/notes/{note_id}/document-r{revision}.pdf"


def analysis_response_key(practice_id: str, note_id: str, revision: int) -> str:
    return f"practices/{practice_id}/notes/{note_id}/analyses/{revision}.json"


def analysis_prompt_key(practice_id: str, note_id: str, revision: int) -> str:
    return f"practices/{practice_id}/notes/{note_id}/analyses/{revision}.prompt.json"


def access_log_archive_key(practice_id: str) -> str:
    if not practice_id or "/" in practice_id:
        raise ValueError(f"not a practice id: {practice_id!r}")
    return f"archives/practices/{practice_id}/access-log.csv"


def evaluation_response_key(practice_id: str, run_id: str, case_id: str, attempt: int) -> str:
    return f"practices/{practice_id}/evaluations/{run_id}/{case_id}-{attempt}.json"


def claim_export_key(practice_id: str, export_id: str, suffix: str) -> str:
    return f"{practice_prefix(practice_id)}exports/{export_id}.{suffix}"


def claim_file_key(practice_id: str, submission_id: str) -> str:
    return f"{practice_prefix(practice_id)}claim-files/{_object_id(submission_id)}.x12"


def claim_ack_key(practice_id: str, file_id: str) -> str:
    return f"{practice_prefix(practice_id)}claim-acks/{_object_id(file_id)}.x12"


def _object_id(value: str) -> str:
    if not value or "/" in value:
        raise ValueError(f"not an object id: {value!r}")
    return value


def audit_package_key(practice_id: str, note_id: str, package_id: str) -> str:
    return f"{note_prefix(practice_id, note_id)}audit-packages/{package_id}.zip"


def person_prefix(user_id: str) -> str:
    if not user_id or "/" in user_id:
        raise ValueError(f"not a user id: {user_id!r}")
    return f"people/{user_id}/"


def person_signature_key(user_id: str, signature_id: str) -> str:
    return f"{person_prefix(user_id)}signatures/{signature_id}.png"


def provider_signature_key(practice_id: str, signature_id: str) -> str:
    return f"{practice_prefix(practice_id)}signatures/{signature_id}.png"


DELETE_BATCH = 1000
MISSING_OBJECT_CODES = ("404", "NoSuchKey", "NotFound")


class S3ObjectStore:
    def __init__(self, settings: Settings, *, client: Any = None, bucket: str | None = None) -> None:
        self._bucket = bucket or settings.s3_bucket
        self._encryption = settings.s3_server_side_encryption
        self._client: Any = client or boto3.client(
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

    async def exists(self, key: str) -> bool:
        try:
            await asyncio.to_thread(self._client.head_object, Bucket=self._bucket, Key=key)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in MISSING_OBJECT_CODES:
                return False
            raise
        return True

    async def check_bucket(self) -> None:
        await asyncio.to_thread(self._client.head_bucket, Bucket=self._bucket)

    async def delete(self, keys: list[str]) -> None:
        for start in range(0, len(keys), DELETE_BATCH):
            objects = [{"Key": key} for key in keys[start : start + DELETE_BATCH]]
            await asyncio.to_thread(
                self._client.delete_objects, Bucket=self._bucket, Delete={"Objects": objects, "Quiet": True}
            )

    async def delete_prefix(self, prefix: str) -> int:
        if not prefix.endswith("/") or prefix == "/":
            raise ValueError(f"refusing to delete under {prefix!r}: a prefix must name a folder")
        keys = await asyncio.to_thread(self._keys_under, prefix)
        await self.delete(keys)
        return len(keys)

    def _keys_under(self, prefix: str) -> list[str]:
        pages = self._client.get_paginator("list_objects_v2").paginate(Bucket=self._bucket, Prefix=prefix)
        return [item["Key"] for page in pages for item in page.get("Contents", [])]
