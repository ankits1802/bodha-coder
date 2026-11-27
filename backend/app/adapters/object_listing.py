from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.adapters.object_store import ObjectStore, S3ObjectStore

__all__ = ["ListingStore", "S3ListingStore", "StoredObject"]


@dataclass(frozen=True)
class StoredObject:
    key: str
    modified: datetime


class ListingStore(ObjectStore, Protocol):
    async def list_keys(self, prefix: str) -> list[str]: ...

    def object_pages(self, prefix: str) -> AsyncIterator[list[StoredObject]]: ...

    async def list_folders(self, prefix: str) -> list[str]: ...


class S3ListingStore(S3ObjectStore):
    async def list_keys(self, prefix: str) -> list[str]:
        _require_folder(prefix)
        return sorted(await asyncio.to_thread(self._keys_under, prefix))

    async def object_pages(self, prefix: str) -> AsyncIterator[list[StoredObject]]:
        _require_folder(prefix)
        pages = iter(self._client.get_paginator("list_objects_v2").paginate(Bucket=self._bucket, Prefix=prefix))
        while (page := await asyncio.to_thread(next, pages, None)) is not None:
            yield [StoredObject(item["Key"], item["LastModified"]) for item in page.get("Contents", [])]

    async def list_folders(self, prefix: str) -> list[str]:
        _require_folder(prefix)
        return sorted(await asyncio.to_thread(self._folders_under, prefix))

    def _folders_under(self, prefix: str) -> list[str]:
        paginator = self._client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=self._bucket, Prefix=prefix, Delimiter="/")
        return [item["Prefix"] for page in pages for item in page.get("CommonPrefixes", [])]


def _require_folder(prefix: str) -> None:
    if not prefix.endswith("/") or prefix == "/":
        raise ValueError(f"refusing to list under {prefix!r}: a prefix must name a folder")
