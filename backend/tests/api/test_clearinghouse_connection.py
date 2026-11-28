import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from sqlalchemy import select

from app.adapters.sftp import SftpTarget
from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models import ClearinghouseConnection
from tests.api.claim_helpers import PORTAL, SFTP, access_entries, ok
from tests.builders import practice_with_provider
from tests.fakes import FAKE_HOST_KEY

pytestmark = pytest.mark.usefixtures("clearinghouse_key")
BASE = "/api/practice/clearinghouse"
SHOWN = {
    "name": "Office Ally",
    "transport": "sftp",
    "usage": "test",
    "sender_qualifier": "ZZ",
    "sender_id": "SUB123",
    "receiver_qualifier": "ZZ",
    "receiver_id": "OFFALLY",
    "receiver_name": "Office Ally",
    "host": "sftp.clearinghouse.example.com",
    "port": 22,
    "username": "lakeside",
    "auth_kind": "password",
    "secret_saved": True,
    "host_key_sha256": FAKE_HOST_KEY,
    "outbound_folder": "/outbound",
    "inbound_folder": "/inbound",
}


async def _rows() -> list[ClearinghouseConnection]:
    async with SessionFactory() as db:
        return list(await db.scalars(select(ClearinghouseConnection).order_by(ClearinghouseConnection.created_at)))


async def test_a_saved_connection_keeps_its_password_sealed_and_never_returns_it(harness, clearinghouse_key):
    practice = await practice_with_provider(harness)

    response = await harness.client.put(BASE, headers=practice.admin, json=SFTP)

    assert response.status_code == 200, response.text
    assert SFTP["password"] not in response.text
    connection = response.json()["connection"]
    assert {key: connection[key] for key in SHOWN} == SHOWN
    assert set(connection) == {*SHOWN, "id", "saved_at"}
    (row,) = await _rows()
    assert row.secret.startswith("v1:") and SFTP["password"] not in row.secret
    assert Fernet(clearinghouse_key).decrypt(row.secret.removeprefix("v1:").encode()).decode() == SFTP["password"]
    shown = await harness.client.get(BASE, headers=practice.admin)
    assert SFTP["password"] not in shown.text and shown.json()["encryption_ready"] is True


async def test_saving_again_keeps_the_sealed_secret_until_the_login_changes(harness):
    practice = await practice_with_provider(harness)
    ok(await harness.client.put(BASE, headers=practice.admin, json=SFTP))

    ok(
        await harness.client.put(
            BASE, headers=practice.admin, json={**SFTP, "password": None, "outbound_folder": "/claims"}
        )
    )

    first, second = await _rows()
    assert (first.retired_at is not None, second.retired_at, second.secret) == (True, None, first.secret)
    assert second.outbound_folder == "/claims"
    changed = await harness.client.put(
        BASE, headers=practice.admin, json={**SFTP, "password": None, "username": "other"}
    )
    assert (changed.status_code, changed.json()["message"]) == (422, "enter the password")


async def test_the_host_key_is_read_for_the_admin_then_checked_on_every_test(harness):
    practice = await practice_with_provider(harness)
    host = {"host": "sftp.clearinghouse.example.com", "port": 22}

    assert ok(await harness.client.post(f"{BASE}/host-key", headers=practice.admin, json=host)) == {
        "host_key_sha256": FAKE_HOST_KEY
    }
    assert (await harness.client.post(f"{BASE}/test", headers=practice.admin)).status_code == 404
    ok(await harness.client.put(BASE, headers=practice.admin, json=SFTP))
    assert ok(await harness.client.post(f"{BASE}/test", headers=practice.admin)) == {"ok": True}
    assert harness.link.checked == [("/outbound", "/inbound")]
    assert harness.link.targets[-1] == SftpTarget(
        "sftp.clearinghouse.example.com", 22, "lakeside", SFTP["password"], None, FAKE_HOST_KEY
    )
    harness.link.refusal = "the clearinghouse refused the user name, password or key"
    refused = await harness.client.post(f"{BASE}/test", headers=practice.admin)
    assert (refused.status_code, refused.json()["message"]) == (503, harness.link.refusal)
    tested = [
        entry.detail for entry in await access_entries(practice) if entry.action == "tested clearinghouse connection"
    ]
    assert tested == ["ok", "failed: the clearinghouse refused the user name, password or key"]


async def test_a_private_key_must_be_readable_and_is_handed_to_the_link(harness):
    practice = await practice_with_provider(harness)
    keyed = {**SFTP, "auth_kind": "key", "password": None}
    garbage = "-----BEGIN OPENSSH PRIVATE KEY-----\nAAAA\n-----END OPENSSH PRIVATE KEY-----"
    pem = (
        ed25519.Ed25519PrivateKey.generate()
        .private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.OpenSSH, serialization.NoEncryption())
        .decode()
    )

    refused = await harness.client.put(BASE, headers=practice.admin, json={**keyed, "private_key": garbage})

    assert refused.status_code == 422
    assert (
        refused.json()["message"]
        == "the private key could not be read; paste an unencrypted OpenSSH or PEM private key"
    )
    saved = ok(await harness.client.put(BASE, headers=practice.admin, json={**keyed, "private_key": pem}))
    assert saved["connection"]["auth_kind"] == "key" and "PRIVATE KEY" not in str(saved)
    ok(await harness.client.post(f"{BASE}/test", headers=practice.admin))
    assert (harness.link.targets[-1].private_key, harness.link.targets[-1].password) == (pem.strip(), None)


async def test_removing_a_connection_retires_it_and_keeps_its_record(harness):
    practice = await practice_with_provider(harness)
    ok(await harness.client.put(BASE, headers=practice.admin, json=PORTAL))

    removed = ok(await harness.client.delete(BASE, headers=practice.admin))

    assert removed == {"connection": None, "encryption_ready": True}
    assert (await harness.client.delete(BASE, headers=practice.admin)).status_code == 404
    (row,) = await _rows()
    assert row.retired_at is not None and row.retired_by is not None and row.transport == "portal"


async def test_sftp_needs_the_server_key_but_a_portal_connection_does_not(harness, monkeypatch):
    practice = await practice_with_provider(harness)
    monkeypatch.setattr(get_settings(), "clearinghouse_encryption_key", None)

    refused = await harness.client.put(BASE, headers=practice.admin, json=SFTP)

    assert (refused.status_code, refused.json()["message"]) == (
        503,
        "clearinghouse connections are not set up on this server yet",
    )
    assert ok(await harness.client.get(BASE, headers=practice.admin)) == {"connection": None, "encryption_ready": False}
    portal = ok(await harness.client.put(BASE, headers=practice.admin, json=PORTAL))
    assert (portal["connection"]["transport"], portal["connection"]["secret_saved"]) == ("portal", False)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"outbound_folder": "../etc"}, "the folder for claims must be a folder path such as /outbound"),
        ({"inbound_folder": ""}, "the folder for responses must be a folder path such as /outbound"),
        ({"host": "sftp_host!"}, "sftp_host! is not a host name"),
        (
            {"host_key_sha256": None},
            "an SFTP connection needs a user name, a password or key and the host key fingerprint",
        ),
    ],
)
async def test_an_sftp_connection_needs_plain_folders_a_host_name_and_a_pinned_key(harness, changes, message):
    practice = await practice_with_provider(harness)

    refused = await harness.client.put(BASE, headers=practice.admin, json={**SFTP, **changes})

    assert (refused.status_code, refused.json()["message"]) == (422, message)
    assert await _rows() == []
