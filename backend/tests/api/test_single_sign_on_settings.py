import pytest
from lxml import etree
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models import SsoVersion
from tests.api.membership_helpers import access_log, auth_events, membership_of
from tests.api.organization_helpers import organization_of_two, organization_path, verified_domain
from tests.api.sso_helpers import (
    PRACTICE_SSO,
    assertion_for,
    connection_for,
    person,
    post_back,
    saml_base,
    save_settings,
    settings_body,
    sign_in_location,
    sso_ready,
    sso_round_trip,
    start,
)
from tests.builders import accept_invite, invite_member, practice_with_provider, sign_in
from tests.saml_idp import IDP_ENTITY, IDP_SSO_URL, MD, PASSWORD_CONTEXT, encoded, idp_metadata, signed_response

METADATA_URL = "https://idp.lakeside.example.com/federationmetadata.xml"
ACME = "acme.example.com"


async def _versions(connection_id: str) -> list[SsoVersion]:
    async with SessionFactory() as db:
        rows = await db.scalars(
            select(SsoVersion).where(SsoVersion.connection_id == connection_id).order_by(SsoVersion.version)
        )
        return list(rows.all())


async def test_only_practice_admins_reach_single_sign_on(harness):
    practice = await practice_with_provider(harness)
    await invite_member(harness, practice, name="Sam Patel", email="sam@lakeside.example.com", role="coder")
    coder = await sign_in(harness.client, "sam@lakeside.example.com")
    for method, path in (("get", PRACTICE_SSO), ("post", PRACTICE_SSO), ("delete", PRACTICE_SSO)):
        assert (await harness.client.request(method.upper(), path, headers=coder)).status_code == 403


async def test_setting_up_gives_the_service_provider_details_to_copy_and_download(harness):
    practice = await practice_with_provider(harness)
    empty = await harness.client.get(PRACTICE_SSO, headers=practice.admin)
    connection_id = await connection_for(harness, practice.admin)
    again = await harness.client.post(PRACTICE_SSO, headers=practice.admin)
    downloaded = await harness.client.get(f"/api/auth/saml/{connection_id}/metadata")

    assert empty.json()["connection"] is None
    view = again.json()["connection"]
    base = saml_base(connection_id)
    assert view["id"] == connection_id
    assert view["service_provider"] == {
        "entity_id": f"{base}/metadata",
        "acs_url": f"{base}/acs",
        "metadata_url": f"{base}/metadata",
    }
    assert (view["current"], view["history"]) == (None, [])
    assert downloaded.headers["content-type"].startswith("application/samlmetadata+xml")
    assert downloaded.headers["content-disposition"] == 'attachment; filename="bodha-assure-sp-metadata.xml"'
    root = etree.fromstring(downloaded.content)
    service = root.find(f"{{{MD}}}SPSSODescriptor/{{{MD}}}AssertionConsumerService")
    assert (root.get("entityID"), service.get("Location")) == (f"{base}/metadata", f"{base}/acs")


async def test_metadata_is_read_from_an_upload_or_an_https_address(harness, idp, next_idp):
    practice = await practice_with_provider(harness)
    harness.metadata.documents[METADATA_URL] = idp_metadata((idp, next_idp))
    uploaded = await harness.client.post(
        f"{PRACTICE_SSO}/metadata", headers=practice.admin, json={"xml": idp_metadata((idp,)).decode()}
    )
    fetched = await harness.client.post(f"{PRACTICE_SSO}/metadata", headers=practice.admin, json={"url": METADATA_URL})
    plain = await harness.client.post(
        f"{PRACTICE_SSO}/metadata", headers=practice.admin, json={"url": "http://idp.lakeside.example.com/m.xml"}
    )
    neither = await harness.client.post(f"{PRACTICE_SSO}/metadata", headers=practice.admin, json={})

    assert uploaded.status_code == 200, uploaded.text
    body = uploaded.json()
    assert (body["entity_id"], body["sso_url"], body["metadata_url"]) == (IDP_ENTITY, IDP_SSO_URL, None)
    [certificate] = body["certificates"]
    assert (certificate["value"], certificate["sha256"]) == (idp.compact, idp.sha256)
    assert certificate["expires_at"] == idp.certificate.not_valid_after_utc.isoformat()
    assert [item["sha256"] for item in fetched.json()["certificates"]] == [idp.sha256, next_idp.sha256]
    assert fetched.json()["metadata_url"] == METADATA_URL
    assert harness.metadata.fetched == [METADATA_URL]
    assert (plain.status_code, neither.status_code) == (422, 422)


async def test_every_save_is_a_new_version_and_versions_never_change(harness, idp, next_idp):
    practice = await practice_with_provider(harness)
    setup = await sso_ready(harness, practice, idp)
    rolled = settings_body((idp, next_idp), claim_ids=[setup.claim_id], email_attribute="email")
    saved = await save_settings(harness, practice.admin, rolled)

    view = saved.json()["connection"]
    assert [row["version"] for row in view["history"]] == [2, 1]
    assert view["current"]["version"] == 2
    assert view["current"]["email_attribute"] == "email"
    assert [item["value"] for item in view["current"]["identity_provider"]["certificates"]] == [
        idp.compact,
        next_idp.compact,
    ]
    assert [row.version for row in await _versions(setup.connection_id)] == [1, 2]
    for statement in ("UPDATE sso_versions SET required = true", "DELETE FROM sso_versions"):
        async with SessionFactory() as db:
            with pytest.raises(DBAPIError):
                await db.execute(text(statement))
    assert len(await _versions(setup.connection_id)) == 2


async def test_changes_are_recorded_in_the_access_log_and_the_auth_events(harness, idp):
    practice = await practice_with_provider(harness)
    await sso_ready(harness, practice, idp)
    removed = await harness.client.delete(PRACTICE_SSO, headers=practice.admin)
    assert removed.status_code == 200

    entries = [
        entry["detail"]
        for entry in await access_log(harness, practice.admin)
        if entry["action"] == "single sign-on changed"
    ]
    assert entries == ["removed", "version 1: 1 domains, required off, new people off, 0 break-glass", "set up"]
    assert [event.detail for event in await auth_events("sso_changed")] == list(reversed(entries))


async def test_domains_must_be_verified_by_this_practice(harness, idp):
    lakeside = await practice_with_provider(harness)
    riverbend = await practice_with_provider(harness, name="Riverbend", admin_email="admin@riverbend.example.com")
    unverified = await harness.client.post(
        "/api/practice/domains", headers=lakeside.admin, json={"domain": "lake.example.org"}
    )
    theirs = await verified_domain(harness, riverbend.admin, mode="off")
    await connection_for(harness, lakeside.admin)

    for claim_ids in ([unverified.json()["id"]], [theirs]):
        refused = await save_settings(harness, lakeside.admin, settings_body((idp,), claim_ids=claim_ids))
        assert (refused.status_code, refused.json()["message"]) == (422, "choose domains this account has verified")
    empty = await save_settings(harness, lakeside.admin, settings_body((idp,), claim_ids=[], required=True))
    assert empty.json()["message"] == "choose a domain to require single sign-on for"


async def test_saving_before_setting_up_or_with_expired_certificates_is_refused(harness, idp, expired_idp):
    practice = await practice_with_provider(harness)
    claim_id = await verified_domain(harness, practice.admin, mode="off")
    early = await save_settings(harness, practice.admin, settings_body((idp,), claim_ids=[claim_id]))
    await connection_for(harness, practice.admin)
    stale = await save_settings(harness, practice.admin, settings_body((expired_idp,), claim_ids=[claim_id]))
    mixed = await save_settings(harness, practice.admin, settings_body((expired_idp, idp), claim_ids=[claim_id]))
    too_many = settings_body((idp,), claim_ids=[claim_id])
    too_many["identity_provider"]["certificates"] = [idp.compact] * 5

    assert (early.status_code, early.json()["message"]) == (404, "set up single sign-on first")
    assert (stale.status_code, stale.json()["message"]) == (422, "every signing certificate has expired")
    assert mixed.status_code == 200, mixed.text
    assert (await save_settings(harness, practice.admin, too_many)).status_code == 422


async def test_required_mode_keeps_a_break_glass_admin_who_can_sign_in_without_the_provider(harness, idp):
    practice = await practice_with_provider(harness)
    sam = await invite_member(harness, practice, name="Sam Patel", email="sam@lakeside.example.com", role="coder")
    invited = await harness.client.post(
        "/api/team",
        headers=practice.admin,
        json={"name": "Second Admin", "email": "second@lakeside.example.com", "role": "admin"},
    )
    await accept_invite(harness)
    admin_id = (await harness.client.get("/api/auth/me", headers=practice.admin)).json()["id"]
    setup = await sso_ready(harness, practice, idp)

    def required(break_glass: list[str]) -> dict:
        return settings_body((idp,), claim_ids=[setup.claim_id], required=True, break_glass=break_glass)

    nobody = await save_settings(harness, practice.admin, required([]))
    coder = await save_settings(harness, practice.admin, required([sam]))
    unready = await save_settings(harness, practice.admin, required([invited.json()["id"]]))
    ready = await save_settings(harness, practice.admin, required([admin_id]))

    assert nobody.json()["message"] == "keep at least one break-glass admin when single sign-on is required"
    assert coder.json()["message"] == "choose break-glass accounts among the admins"
    assert (
        unready.json()["message"]
        == "Second Admin needs a password and two-step verification to be a break-glass account"
    )
    assert ready.status_code == 200, ready.text
    admins = {row["email"]: row["ready"] for row in ready.json()["admins"]}
    assert admins == {"admin@lakeside.example.com": True, "second@lakeside.example.com": False}
    assert ready.json()["connection"]["current"]["break_glass"] == [admin_id]


async def _trial(harness, practice, connection_id: str, keys, facts: dict):
    link = await harness.client.post(f"{PRACTICE_SSO}/test", headers=practice.admin)
    started = await start(harness, connection_id, url=link.json()["url"])
    sent = signed_response(assertion_for(connection_id, in_response_to=started.request_id, **facts), keys)
    return await post_back(harness, connection_id, encoded(sent), started.relay)


async def test_a_test_sign_in_reports_to_the_admin_without_signing_anyone_in(harness, idp, stranger_idp):
    practice = await practice_with_provider(harness)
    setup = await sso_ready(harness, practice, idp)
    facts = {"email": "admin@lakeside.example.com", "name": "Practice Admin"}

    back = await _trial(harness, practice, setup.connection_id, idp, facts)
    failed = await _trial(harness, practice, setup.connection_id, stranger_idp, facts)

    page = f"{get_settings().app_url}/settings/security#sso_test="
    assert back.headers["location"].startswith(page) and failed.headers["location"].startswith(page)
    assert not [value for value in back.headers.get_list("set-cookie") if value.startswith("bodha_refresh=")]
    passed = await _result(harness, practice, back.headers["location"])
    assert passed == {
        "passed": True,
        "reason": None,
        "domain": "lakeside.example.com",
        "in_domains": True,
        "account": True,
        "mfa": False,
        "context_class": PASSWORD_CONTEXT,
        "name_found": True,
    }
    report = await _result(harness, practice, failed.headers["location"])
    assert (report["passed"], report["reason"]) == (False, "signature")
    assert [event.detail for event in await auth_events("sso_tested")] == ["passed", "failed: signature"]


async def _result(harness, practice, location: str) -> dict:
    token = location.split("#sso_test=", 1)[1]
    answer = await harness.client.post(f"{PRACTICE_SSO}/test-result", headers=practice.admin, json={"token": token})
    assert answer.status_code == 200, answer.text
    return answer.json()


async def test_testing_needs_saved_settings(harness):
    practice = await practice_with_provider(harness)
    await connection_for(harness, practice.admin)
    link = await harness.client.post(f"{PRACTICE_SSO}/test", headers=practice.admin)
    assert (link.status_code, link.json()["message"]) == (404, "save the single sign-on settings before testing them")


async def test_an_organization_admin_sets_up_single_sign_on_for_its_practices(harness, idp):
    group = await organization_of_two(harness)
    admin = group.lakeside.admin
    claimed = await harness.client.post(
        organization_path(group, "/domains"), headers=admin, json={"domain": ACME, "practice_id": group.riverbend.id}
    )
    claim_id = claimed.json()["id"]
    listed = (await harness.client.get(organization_path(group, "/domains"), headers=admin)).json()
    harness.dns.records[ACME] = [next(row["txt_record"] for row in listed if row["id"] == claim_id)]
    assert (
        await harness.client.post(organization_path(group, f"/domains/{claim_id}/check"), headers=admin)
    ).status_code == 204
    sso_path = organization_path(group, "/sso")
    connection_id = await connection_for(harness, admin, sso_path)
    body = settings_body((idp,), claim_ids=[claim_id], create_people=True, new_person_role="coder")

    saved = await save_settings(harness, admin, body, sso_path)
    outsider = await harness.client.get(sso_path, headers=group.riverbend.admin)
    practice_scope = await save_settings(harness, admin, body)
    back = await sso_round_trip(harness, connection_id, idp, email="rita@acme.example.com", name="Rita Moss")

    assert saved.status_code == 200, saved.text
    assert saved.json()["domains"] == [{"claim_id": claim_id, "domain": ACME, "practice_name": "Riverbend"}]
    assert {row["email"] for row in saved.json()["admins"]} == {
        "admin@lakeside.example.com",
        "admin@riverbend.example.com",
    }
    assert outsider.status_code == 404
    assert practice_scope.status_code == 404
    assert back.headers["location"] == sign_in_location("signed_in")
    rita = await person("rita@acme.example.com")
    assert (await membership_of(rita.id, group.riverbend.id)).role == "coder"
    events = await auth_events("sso_changed")
    assert {event.practice_id for event in events} == {group.lakeside.id, group.riverbend.id}


async def test_an_organization_admin_cannot_use_a_practice_claim(harness, idp):
    group = await organization_of_two(harness)
    claim_id = await verified_domain(harness, group.lakeside.admin, mode="off")
    sso_path = organization_path(group, "/sso")
    await connection_for(harness, group.lakeside.admin, sso_path)
    refused = await save_settings(harness, group.lakeside.admin, settings_body((idp,), claim_ids=[claim_id]), sso_path)
    assert refused.json()["message"] == "choose domains this account has verified"
