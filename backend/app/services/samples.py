from __future__ import annotations

from app.models import AuditSample

__all__ = ["SAMPLE_ID_PATH", "sample_id_of"]

SAMPLE_ID_PATH = ("sample", "id")


def sample_id_of(item: AuditSample) -> str:
    return str(item.result["sample"]["id"])
