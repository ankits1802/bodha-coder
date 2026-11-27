from __future__ import annotations

import asyncio
import hashlib
import io
import zipfile
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore, audit_package_key
from app.core.deps import Actor
from app.models import AuditPackage, Note, new_id, utcnow
from app.services.audit_log import record_access
from app.services.audit_package_files import PackageFile, json_file, note_files
from app.services.certificates import certificate_files, note_certificates
from app.services.defense_packet import build_packet
from app.services.review_actions import note_for

__all__ = ["MANIFEST", "AuditPackageFile", "audit_package", "note_packages", "package_view", "zipped"]

MANIFEST = "manifest.json"
AGENT_LENGTH = 300
DOWNLOADED = "downloaded audit package"


@dataclass(frozen=True)
class AuditPackageFile:
    package: AuditPackage
    file_name: str
    content: bytes


async def audit_package(db: AsyncSession, store: ObjectStore, actor: Actor, note_id: str) -> AuditPackageFile:
    note = await note_for(db, actor, note_id)
    package_id, generated = new_id(), utcnow()
    packet = await build_packet(db, store, actor, note)
    certificates = await certificate_files(await note_certificates(db, store, note.id), actor.zone)
    files = [PackageFile("defense-packet.pdf", packet.content), *await note_files(db, store, note)]
    files += [PackageFile(path, content) for path, content in certificates]
    manifest = _manifest(note, actor, package_id, generated.isoformat(), files)
    content = await asyncio.to_thread(zipped, [*files, manifest])
    key = audit_package_key(note.practice_id, note.id, package_id)
    await store.put(key, content, content_type="application/zip")
    package = _package_row(note, actor, package_id, key=key, content=content, file_count=len(files) + 1)
    db.add(package)
    await db.flush()
    detail = f"package {package_id[:8]} · {package.file_count} files · sha256 {package.file_sha256[:12]}"
    record_access(db, actor, DOWNLOADED, note_id=note.id, detail=detail)
    await db.commit()
    name = f"bodha-audit-package-{note.service_date:%Y%m%d}-{note.id[:8]}.zip"
    return AuditPackageFile(package, name, content)


def zipped(files: list[PackageFile]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for item in files:
            archive.writestr(item.path, item.content)
    return buffer.getvalue()


async def note_packages(db: AsyncSession, note_id: str) -> list[AuditPackage]:
    rows = await db.scalars(
        select(AuditPackage).where(AuditPackage.note_id == note_id).order_by(AuditPackage.created_at)
    )
    return list(rows.all())


def package_view(row: AuditPackage) -> dict[str, Any]:
    return {
        "id": row.id,
        "at": row.created_at.isoformat(),
        "by": row.actor_name,
        "role": row.actor_role,
        "files": row.file_count,
        "sha256": row.file_sha256,
        "bytes": row.file_bytes,
    }


def _manifest(note: Note, actor: Actor, package_id: str, generated: str, files: list[PackageFile]) -> PackageFile:
    return json_file(
        MANIFEST,
        {
            "package_id": package_id,
            "note_id": note.id,
            "generated_at": generated,
            "generated_by": actor.user.name,
            "role": actor.user.role,
            "files": [
                {"path": item.path, "sha256": hashlib.sha256(item.content).hexdigest(), "bytes": len(item.content)}
                for item in files
            ],
        },
    )


def _package_row(
    note: Note, actor: Actor, package_id: str, *, key: str, content: bytes, file_count: int
) -> AuditPackage:
    return AuditPackage(
        id=package_id,
        practice_id=note.practice_id,
        note_id=note.id,
        file_key=key,
        file_sha256=hashlib.sha256(content).hexdigest(),
        file_bytes=len(content),
        file_count=file_count,
        actor_id=actor.user.id,
        actor_name=actor.user.name,
        actor_role=actor.user.role,
        ip=actor.ip,
        user_agent=(actor.user_agent or "")[:AGENT_LENGTH] or None,
    )
