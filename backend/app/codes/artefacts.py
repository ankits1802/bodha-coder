from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

__all__ = ["read_manifest", "verified_bytes"]


def read_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def verified_bytes(path: Path, sha256: str, corrupt: type[Exception], message: str) -> bytes:
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha256:
        raise corrupt(message)
    return raw
