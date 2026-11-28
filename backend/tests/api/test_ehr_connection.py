from __future__ import annotations

from datetime import timedelta
from urllib.parse import urlsplit

import jwt
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.core.db import SessionFactory
from app.main import app
from app.models import AccessLog, EhrConnection, EhrKey
from tests.api.ehr_helpers import API, SCOPES, TODAY, connected, settings_body
from tests.builders import invite_member, practice_with_provider, sign_in
from tests.ehr_fakes import BASE, TOKEN_URL, resolving_to, smart_configuration

PRIVATE_MEMBERS = {"d", "p", "q", "dp", "dq", "qi"}


async def _view(harness, practice) -> dict:
    response = await harness.client.get(API, headers=practice.admin)
    assert response.status_code == 200, response.text
    return response.json()


async def _jwks(harness, url: str):
    return await harness.client.get(urlsplit(url).path)


async def _actions(practice_id: str) -> list[tuple[str, str | None]]:
    async with SessionFactory() as db:
        rows = await db.execute(
            select(AccessLog.action, AccessLog.detail)
            .where(AccessLog.practice_id == practice_id, AccessLog.action.like("%EHR%"))
            .order_by(AccessLog.chain_seq)
        )
    return list(rows.tuples().all())


async def test_the_connection_waits_for_bodha_to_hold_a_key_encryption_key(harness):
    practice = await practice_with_provider(harness)
    view = await _view(harness, practice)
    assert (view["available"], view["status"], view["registration"], view["connection"]) == (
        False,
        "unavailable",
        None,
        None,
    )
    refused = await harness.client.post(f"{API}/key", headers=practice.admin, json={"algorithm": "RS384"})
    assert refused.status_code == 409
    assert refused.json()["message"] == "the EHR connection is not set up for Bodha yet"


async def test_a_new_key_is_published_at_a_jwks_address_with_only_its_public_half(harness, ehr):
    practice = await practice_with_provider(harness)
    made = await harness.client.post(f"{API}/key", headers=practice.admin, json={"algorithm": "ES384"})
    assert made.status_code == 200, made.text
    registration = made.json()["registration"]
    assert (registration["algorithm"], registration["grant_type"], registration["auth_method"]) == (
        "ES384",
        "client_credentials",
        "private_key_jwt",
    )
    assert registration["jwks_url"].startswith("https://")
    assert practice.id not in registration["jwks_url"]

    published = await _jwks(harness, registration["jwks_url"])
    assert published.status_code == 200, published.text
    [key] = published.json()["keys"]
    assert (key["kid"], key["kty"], key["crv"], key["alg"]) == (registration["key_id"], "EC", "P-384", "ES384")
    assert not PRIVATE_MEMBERS & set(key)
    async with SessionFactory() as db:
        stored = await db.scalar(select(EhrKey).where(EhrKey.practice_id == practice.id))
    assert stored.private_key.startswith("v1:") and "PRIVATE KEY" not in stored.private_key
    shown = str(made.json())
    assert "PRIVATE KEY" not in shown and stored.private_key not in shown


async def test_a_replaced_key_keeps_the_address_and_publishes_only_the_new_key(harness, ehr):
    practice = await practice_with_provider(harness)
    first = (await harness.client.post(f"{API}/key", headers=practice.admin, json={"algorithm": "RS384"})).json()
    second = (await harness.client.post(f"{API}/key", headers=practice.admin, json={})).json()

    assert second["registration"]["jwks_url"] == first["registration"]["jwks_url"]
    assert second["registration"]["key_id"] != first["registration"]["key_id"]
    [key] = (await _jwks(harness, second["registration"]["jwks_url"])).json()["keys"]
    assert (key["kid"], key["kty"]) == (second["registration"]["key_id"], "RSA")
    async with SessionFactory() as db:
        keys = (await db.scalars(select(EhrKey).order_by(EhrKey.created_at))).all()
    assert [key.retired_at is not None for key in keys] == [True, False]
    assert [action for action, _ in await _actions(practice.id)] == [
        "connection key created for the EHR",
        "connection key replaced for the EHR",
    ]
    assert (await harness.client.get("/api/ehr/jwks/unknown-key-set")).status_code == 404


async def test_saving_reads_the_token_endpoint_from_the_smart_configuration(harness, ehr):
    practice = await connected(harness)

    view = await _view(harness, practice)

    assert view["status"] == "pulling"
    assert view["connection"] == {
        "base_url": BASE,
        "token_endpoint": TOKEN_URL,
        "client_id": "bodha-lakeside",
        "scopes": SCOPES,
        "note_types": ["progress"],
        "start_date": settings_body()["start_date"],
        "paused": False,
        "saved_at": view["connection"]["saved_at"],
    }
    assert [request.url.path for request in ehr.requests] == ["/fhir/r4/.well-known/smart-configuration"]
    [(action, detail)] = [row for row in await _actions(practice.id) if row[0].startswith("connection saved")]
    assert detail == f"ehr.example.com, client bodha-lakeside, 1 note types from {settings_body()['start_date']}"


async def test_pause_and_resume_add_revisions_and_never_change_one(harness, ehr):
    practice = await connected(harness)
    paused = await harness.client.post(f"{API}/pause", headers=practice.admin)
    assert (paused.status_code, paused.json()["status"]) == (200, "paused")
    resumed = await harness.client.post(f"{API}/resume", headers=practice.admin)
    assert (resumed.status_code, resumed.json()["status"]) == (200, "pulling")

    async with SessionFactory() as db:
        rows = (await db.scalars(select(EhrConnection).order_by(EhrConnection.revision))).all()
    assert [(row.revision, row.change, row.paused) for row in rows] == [
        (1, "saved", False),
        (2, "paused", True),
        (3, "resumed", False),
    ]
    async with SessionFactory() as db:
        with pytest.raises(DBAPIError):
            await db.execute(text("UPDATE ehr_connections SET paused = true"))
    actions = [action for action, _ in await _actions(practice.id)]
    assert actions[-2:] == ["pulling from the EHR paused", "pulling from the EHR resumed"]


async def test_the_base_url_must_be_public_https_with_a_smart_configuration(harness, ehr):
    practice = await practice_with_provider(harness)
    plain = await harness.client.put(API, headers=practice.admin, json=settings_body(base_url="http://ehr.example.com"))
    assert (plain.status_code, plain.json()["message"]) == (422, "the base URL must be an https address")

    app.state.outbound = ehr.outbound(resolver=resolving_to("10.0.0.7"))
    inside = await harness.client.put(API, headers=practice.admin, json=settings_body())
    assert (inside.status_code, inside.json()["message"]) == (422, "the base URL must be a public https address")
    assert ehr.requests == []

    app.state.outbound = ehr.outbound()
    ehr.configuration = smart_configuration(token_endpoint_auth_methods_supported=["client_secret_basic"])
    unsigned = await harness.client.put(API, headers=practice.admin, json=settings_body())
    assert unsigned.status_code == 422
    assert "private_key_jwt" in unsigned.json()["message"]
    async with SessionFactory() as db:
        assert await db.scalar(select(func.count()).select_from(EhrConnection)) == 0


async def test_the_settings_are_checked_before_anything_is_saved(harness, ehr):
    practice = await practice_with_provider(harness)
    cases = [
        (settings_body(scopes=["system/DocumentReference.read"]), "Encounter, Practitioner"),
        (settings_body(scopes=["patient/DocumentReference.read"]), "only system scopes"),
        (settings_body(start_date=(TODAY + timedelta(days=1)).isoformat()), "cannot be in the future"),
        (settings_body(start_date=(TODAY - timedelta(days=800)).isoformat()), "at most 730 days ago"),
        (settings_body(client_id="has a space"), "no spaces"),
        (settings_body(base_url=f"{BASE}?tenant=1"), "without a query"),
    ]
    for body, phrase in cases:
        response = await harness.client.put(API, headers=practice.admin, json=body)
        assert response.status_code == 422, body
        assert phrase in response.json()["message"], response.json()
    empty = await harness.client.put(API, headers=practice.admin, json=settings_body(note_types=[]))
    assert empty.status_code == 422


async def test_the_test_signs_in_with_the_published_key_and_reads_the_capability_statement(harness, ehr):
    practice = await connected(harness)
    jwks_url = (await _view(harness, practice))["registration"]["jwks_url"]

    tested = await harness.client.post(f"{API}/tests", headers=practice.admin)

    assert tested.status_code == 200, tested.text
    body = tested.json()
    assert body["passed"] is True
    assert [(step["step"], step["passed"], step["detail"]) for step in body["steps"]] == [
        ("configuration", True, f"token endpoint {TOKEN_URL}"),
        ("token", True, f"granted {' '.join(SCOPES)}"),
        ("capability", True, "the EHR serves FHIR 4.0.1"),
    ]
    [key] = (await _jwks(harness, jwks_url)).json()["keys"]
    claims = jwt.decode(ehr.assertions[-1], jwt.PyJWK(key).key, algorithms=["RS384"], audience=TOKEN_URL)
    assert (claims["iss"], claims["sub"]) == ("bodha-lakeside", "bodha-lakeside")
    assert ("connection to the EHR tested", "passed") in await _actions(practice.id)


async def test_a_refused_token_stops_the_test_at_that_step(harness, ehr):
    practice = await connected(harness)
    ehr.token_status = 401

    body = (await harness.client.post(f"{API}/tests", headers=practice.admin)).json()

    assert body["passed"] is False
    assert [(step["step"], step["passed"]) for step in body["steps"]] == [("configuration", True), ("token", False)]
    assert body["steps"][1]["detail"] == "the token endpoint answered 401 invalid_client"
    assert ("connection to the EHR tested", "failed at token") in await _actions(practice.id)


async def test_testing_needs_a_saved_connection_and_a_key(harness, ehr):
    practice = await practice_with_provider(harness)
    unsaved = await harness.client.post(f"{API}/tests", headers=practice.admin)
    assert (unsaved.status_code, unsaved.json()["message"]) == (409, "save the EHR connection first")
    saved = await harness.client.put(API, headers=practice.admin, json=settings_body())
    assert saved.json()["status"] == "incomplete"
    keyless = await harness.client.post(f"{API}/tests", headers=practice.admin)
    assert (keyless.status_code, keyless.json()["message"]) == (409, "create a key first")


async def test_only_admins_manage_the_connection_and_anyone_reads_the_public_keys(harness, ehr):
    practice = await connected(harness)
    jwks_url = (await _view(harness, practice))["registration"]["jwks_url"]
    await invite_member(harness, practice, name="Casey Coder", email="coder@lakeside.example.com", role="coder")
    coder = await sign_in(harness.client, "coder@lakeside.example.com")
    for method, path in (
        ("GET", API),
        ("PUT", API),
        ("POST", f"{API}/key"),
        ("POST", f"{API}/pause"),
        ("POST", f"{API}/resume"),
        ("POST", f"{API}/tests"),
        ("GET", f"{API}/runs"),
        ("GET", f"{API}/documents"),
    ):
        response = await harness.client.request(
            method, path, headers=coder, json=settings_body() if method == "PUT" else {}
        )
        assert response.status_code == 403, (method, path)
    assert (await _jwks(harness, jwks_url)).status_code == 200
