from __future__ import annotations

import asyncio
from typing import Protocol

from app.adapters.object_store import ObjectStore, S3ObjectStore

__all__ = ["ListingStore", "S3ListingStore"]


class ListingStore(ObjectStore, Protocol):
    async def list_keys(self, prefix: str) -> list[str]: ...


class S3ListingStore(S3ObjectStore):
    async def list_keys(self, prefix: str) -> list[str]:
        if not prefix.endswith("/") or prefix == "/":
            raise ValueError(f"refusing to list under {prefix!r}: a prefix must name a folder")
        return sorted(await asyncio.to_thread(self._keys_under, prefix))
