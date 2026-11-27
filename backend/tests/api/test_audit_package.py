import hashlib
import io
import json
import zipfile

from sqlalchemy import select

from app.core.db import SessionFactory
from app.models import AuditPackage
from tests.api.review_helpers import access_rows, approve, keep_i10_with_reason
from tests.builders import invite_member, reviewed_note, sign_in

EXPECTED_FILES = {
    "defense-packet.pdf",
    "documents/document.pdf",
    "texts/r1-document.txt",
    "analyses/run-1.json",
    "analyses/run-1-replies.json",
    "suggestions.json",
    "decisions.json",
    "code-sets.json",
    "snapshots.json",
    "provider-requests.json",
    "provider-statements.json",
    "exports.json",
    "comments.json",
    "access-log.json",
    "manifest.json",
}


async def _exported_note(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await keep_i10_with_reason(harness, practice, note_id)
    assert (await approve(harness, practice, note_id)).status_code == 200
    await harness.client.post(f"/api/notes/{note_id}/comments", headers=practice.admin, json={"body": "Checked."})
    assert (await harness.client.post("/api/billing/export", headers=practice.admin, json={})).status_code == 200
    return practice, note_id


async def test_the_package_holds_every_record_with_a_manifest_of_hashes(harness, icd_catalog):
    practice, note_id = await _exported_note(harness, icd_catalog)

    response = await harness.client.post(f"/api/notes/{note_id}/audit-package", headers=practice.admin)

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/zip"
    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = set(archive.namelist())
    assert names >= EXPECTED_FILES
    manifest = json.loads(archive.read("manifest.json"))
    assert {item["path"] for item in manifest["files"]} == names - {"manifest.json"}
    for item in manifest["files"]:
        assert hashlib.sha256(archive.read(item["path"])).hexdigest() == item["sha256"]
    decisions = json.loads(archive.read("decisions.json"))
    assert [(row["suggestion_key"], row["override_reason"]) for row in decisions] == [("dx:I10", "documentation")]
    exports = json.loads(archive.read("exports.json"))
    assert archive.read(exports[0]["file"]).startswith(b"note_id,patient")
    assert "token_hash" not in archive.read("provider-requests.json").decode()


async def test_each_package_is_stored_with_its_hash_and_its_download_is_logged(harness, icd_catalog):
    practice, note_id = await _exported_note(harness, icd_catalog)

    response = await harness.client.post(f"/api/notes/{note_id}/audit-package", headers=practice.admin)

    async with SessionFactory() as db:
        [package] = (await db.scalars(select(AuditPackage))).all()
    assert package.file_sha256 == hashlib.sha256(response.content).hexdigest()
    assert harness.store.objects[package.file_key] == response.content
    assert package.file_key == f"practices/{practice.id}/notes/{note_id}/audit-packages/{package.id}.zip"
    assert (package.actor_role, package.ip) == ("admin", "127.0.0.1")
    logged = [row for row in await access_rows(harness, practice) if row["action"] == "downloaded audit package"]
    assert len(logged) == 1 and package.id[:8] in logged[0]["detail"]


async def test_only_admins_and_compliance_download_the_package(harness, icd_catalog):
    practice, note_id = await reviewed_note(harness, icd_catalog)
    await invite_member(harness, practice, name="Cora Coder", email="cora@lakeside.example.com", role="coder")
    coder = await sign_in(harness.client, "cora@lakeside.example.com")

    assert (await harness.client.post(f"/api/notes/{note_id}/audit-package", headers=coder)).status_code == 403
