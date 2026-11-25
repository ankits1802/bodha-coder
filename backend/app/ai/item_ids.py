from __future__ import annotations

import hashlib
import re
from collections.abc import Callable, Sequence

from pydantic import BaseModel

__all__ = ["stamp_ids"]

_ID_NOISE = re.compile(r"[^a-z0-9]+")
_DIGEST_CHARACTERS = 16


def stamp_ids[M: BaseModel](
    entries: Sequence[M],
    *,
    identity: Callable[[M], str],
    prefix: str = "",
    default_section: str = "",
) -> list[M]:
    kept: list[M] = []
    seen: dict[str, int] = {}
    for entry in entries:
        name = identity(entry)
        if not name.strip() and not str(getattr(entry, "suggestedText", "")).strip():
            continue
        section = str(getattr(entry, "targetSection", ""))
        section = section if section.strip() else default_section
        basis = f"{_id_basis(section)}|{_id_basis(name)}"
        digest = hashlib.sha256(basis.encode("utf-8")).hexdigest()[:_DIGEST_CHARACTERS]
        count = seen.get(digest, 0)
        seen[digest] = count + 1
        suffixed = digest if count == 0 else f"{digest}-{count}"
        kept.append(entry.model_copy(update={"id": f"{prefix}{suffixed}", "targetSection": section}))
    return kept


def _id_basis(value: str) -> str:
    return _ID_NOISE.sub(" ", value.lower()).strip()
