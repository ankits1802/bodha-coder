from urllib.parse import parse_qs, urlsplit

from app.core.config import get_settings
from tests.api.membership_helpers import access_log, auth_events, membership_of
from tests.api.sso_helpers import (
    ANNA,
    SAML_COOKIE,
    assertion_for,
    person,
    post_back,
    refreshed_email,
    refused_location,
    save_settings,
    sessions_of,
    settings_body,
    sign_in_location,
    sso_ready,
    sso_round_trip,
    start,
)
from tests.builders import ADMIN_SITE, PASSWORD, back_from, invite_member, practice_with_provider, sign_in_page
from tests.saml_idp import MFA_CONTEXT, PASSWORD_CONTEXT, encoded, signed_response

ADMIN = "admin@lakeside.example.com"


async def _practice_with_anna(harness):
    practice = await practice_with_provider(harness)
    await invite_member(harness, practice, name="Anna Reyes", email=ANNA, role="coder")
    return practice


async def _admin_id(harness, practice) -> str:
    return (await harness.client.get("/api/auth/me", headers=practice.admin)).json()["id"]


async def test_a_sign_in_started_here_lands_the_person_with_a_session_and_a_record(harness, idp):
    practice = await _practice_with_anna(harness)
    setup = await sso_ready(harness, practice, idp)

    back = await sso_round_trip(harness, setup.connection_id, idp)

    assert (back.status_code, back.headers["location"]) == (303, sign_in_location("signed_in"))
    assert (
        harness.client.cookies.get(SAML_COOKIE, domain="app.test", path=f"/api/auth/saml/{setup.connection_id}") is None
    )
    assert await refreshed_email(harness) == ANNA
    [event] = [event for event in await auth_events("signed_in") if event.detail == "with single sign-on"]
    assert event.user_id == (await person(ANNA)).id
    entries = [(entry["action"], entry["detail"]) for entry in await access_log(harness, practice.admin)]
    assert ("signed in", "with single sign-on") in entries


async def test_the_start_cookie_is_scoped_secure_and_sent_cross_site(harness, idp):
    practice = await _practice_with_anna(harness)
    setup = await sso_ready(harness, practice, idp)
    started = await harness.client.get(f"/api/auth/saml/{setup.connection_id}/start")
    cookie = [value.lower() for value in started.headers.get_list("set-cookie") if value.startswith(SAML_COOKIE)][0]
    expected = ("httponly", "secure", "samesite=none", f"path=/api/auth/saml/{setup.connection_id}", "max-age=600")
    assert all(part in cookie for part in expected)
    location = urlsplit(started.headers["location"])
    assert (location.scheme, location.netloc, location.path) == ("https", "idp.lakeside.example.com", "/sso")
    assert len(parse_qs(location.query)["RelayState"][0]) <= 80


async def test_a_response_used_once_is_refused_the_second_time(harness, idp):
    practice = await _practice_with_anna(harness)
    setup = await sso_ready(harness, practice, idp)
    started = await start(harness, setup.connection_id)
    facts = assertion_for(setup.connection_id, in_response_to=started.request_id)
    value = encoded(signed_response(facts, idp))
    first = await post_back(harness, setup.connection_id, value, started.relay)
    harness.client.cookies.set(
        SAML_COOKIE, started.cookie, domain="app.test", path=f"/api/auth/saml/{setup.connection_id}"
    )

    again = await post_back(harness, setup.connection_id, value, started.relay)

    assert first.headers["location"] == sign_in_location("signed_in")
    assert again.headers["location"] == refused_location("sso_failed")
    assert [event.detail for event in await auth_events("sign_in_failed")] == ["single sign-on: replayed"]


async def test_a_response_from_another_browser_or_with_a_changed_relay_state_is_refused(harness, idp):
    practice = await _practice_with_anna(harness)
    setup = await sso_ready(harness, practice, idp)
    started = await start(harness, setup.connection_id)
    facts = assertion_for(setup.connection_id, in_response_to=started.request_id)
    changed = await post_back(harness, setup.connection_id, encoded(signed_response(facts, idp)), "another-relay")
    assert changed.headers["location"] == refused_location("sso_expired")
    stray = await post_back(harness, setup.connection_id, encoded(signed_response(facts, idp)), started.relay)
    assert stray.headers["location"] == refused_location("sso_expired")
    assert [event.detail for event in await auth_events("sign_in_failed")] == [
        "single sign-on: relay",
        "single sign-on: request",
    ]


async def test_a_sign_in_the_identity_provider_starts_is_asked_again_from_here(harness, idp):
    practice = await _practice_with_anna(harness)
    setup = await sso_ready(harness, practice, idp)
    unsolicited = encoded(signed_response(assertion_for(setup.connection_id), idp))
    base = f"{get_settings().app_url}/api/auth/saml/{setup.connection_id}/start"

    bounced = await post_back(harness, setup.connection_id, unsolicited, "/notes/n-1")
    replayed = await post_back(harness, setup.connection_id, unsolicited, "/notes/n-1")
    foreign = encoded(signed_response(assertion_for(setup.connection_id), idp))
    elsewhere = await post_back(harness, setup.connection_id, foreign, "https://evil.example.com/")

    assert (bounced.status_code, bounced.headers["location"]) == (303, f"{base}?next=%2Fnotes%2Fn-1")
    assert replayed.headers["location"] == refused_location("sso_failed")
    assert elsewhere.headers["location"] == base
    started = await start(harness, setup.connection_id, next_path="/notes/n-1")
    facts = assertion_for(setup.connection_id, in_response_to=started.request_id)
    landed = await post_back(harness, setup.connection_id, encoded(signed_response(facts, idp)), started.relay)
    assert landed.headers["location"] == sign_in_location("signed_in", next_path="/notes/n-1")


async def test_an_email_outside_the_configured_domains_is_refused_and_logged(harness, idp):
    practice = await _practice_with_anna(harness)
    setup = await sso_ready(harness, practice, idp)

    back = await sso_round_trip(harness, setup.connection_id, idp, email="eve@elsewhere.example.com")

    assert back.headers["location"] == refused_location("sso_domain")
    entries = [(entry["action"], entry["detail"]) for entry in await access_log(harness, practice.admin)]
    assert ("single sign-on refused", "domain") in entries
    assert all("eve@" not in str(entry) for entry in entries)


async def test_a_response_signed_by_another_key_is_refused(harness, idp, stranger_idp):
    practice = await _practice_with_anna(harness)
    setup = await sso_ready(harness, practice, idp)
    back = await sso_round_trip(harness, setup.connection_id, stranger_idp)
    assert back.headers["location"] == refused_location("sso_failed")
    assert [event.detail for event in await auth_events("sign_in_failed")] == ["single sign-on: signature"]


async def test_new_people_are_created_on_first_sign_in_only_when_allowed(harness, idp):
    practice = await _practice_with_anna(harness)
    setup = await sso_ready(harness, practice, idp)
    ben = {"email": "ben@lakeside.example.com", "name": "Ben Ortiz"}
    assert (await sso_round_trip(harness, setup.connection_id, idp, **ben)).headers["location"] == refused_location(
        "no_account"
    )
    body = settings_body((idp,), claim_ids=[setup.claim_id], create_people=True, new_person_role="coder")
    assert (await save_settings(harness, practice.admin, body)).status_code == 200
    admin_body = {**body, "new_person_role": "admin"}
    assert (await save_settings(harness, practice.admin, admin_body)).status_code == 422

    back = await sso_round_trip(harness, setup.connection_id, idp, **ben)

    assert back.headers["location"] == sign_in_location("signed_in")
    created = await person("ben@lakeside.example.com")
    assert (created.name, created.status) == ("Ben Ortiz", "active")
    membership = await membership_of(created.id, practice.id)
    assert (membership.role, membership.status) == ("coder", "active")
    entries = [(entry["action"], entry["detail"]) for entry in await access_log(harness, practice.admin)]
    assert ("joined by single sign-on", "Ben Ortiz as coder") in entries


async def test_an_invited_person_who_signs_in_through_the_identity_provider_joins(harness, idp):
    practice = await practice_with_provider(harness)
    invited = await harness.client.post(
        "/api/team",
        headers=practice.admin,
        json={"name": "Dan Cole", "email": "dan@lakeside.example.com", "role": "cdi"},
    )
    assert invited.status_code == 200, invited.text
    setup = await sso_ready(harness, practice, idp)

    back = await sso_round_trip(harness, setup.connection_id, idp, email="dan@lakeside.example.com", name="Dan Cole")

    assert back.headers["location"] == sign_in_location("signed_in")
    dan = await person("dan@lakeside.example.com")
    assert dan.status == "active"
    assert (await membership_of(dan.id, practice.id)).status == "active"


async def test_identity_provider_two_step_counts_only_with_the_configured_context(harness, idp):
    practice = await practice_with_provider(harness)
    await invite_member(harness, practice, name="Carla Diaz", email="carla@lakeside.example.com", role="compliance")
    setup = await sso_ready(harness, practice, idp)
    carla = {"email": "carla@lakeside.example.com", "name": "Carla Diaz"}

    without = await sso_round_trip(harness, setup.connection_id, idp, context_class=MFA_CONTEXT, **carla)
    body = settings_body((idp,), claim_ids=[setup.claim_id], mfa_context=MFA_CONTEXT)
    assert (await save_settings(harness, practice.admin, body)).status_code == 200
    weaker = await sso_round_trip(harness, setup.connection_id, idp, context_class=PASSWORD_CONTEXT, **carla)
    stronger = await sso_round_trip(harness, setup.connection_id, idp, context_class=MFA_CONTEXT, **carla)

    for challenged in (without, weaker):
        fragment = parse_qs(urlsplit(challenged.headers["location"]).fragment)
        assert (fragment["setup"], bool(fragment["mfa"][0])) == (["1"], True)
    assert stronger.headers["location"] == sign_in_location("signed_in")
    assert await refreshed_email(harness) == "carla@lakeside.example.com"
    sessions = await sessions_of((await person("carla@lakeside.example.com")).id)
    assert [session.idp_two_step for session in sessions] == [True]


async def test_an_admin_with_two_step_still_verifies_after_single_sign_on(harness, idp):
    practice = await practice_with_provider(harness)
    setup = await sso_ready(harness, practice, idp)
    back = await sso_round_trip(harness, setup.connection_id, idp, email=ADMIN, name="Practice Admin")
    fragment = parse_qs(urlsplit(back.headers["location"]).fragment)
    assert fragment["setup"] == ["0"]


async def test_required_single_sign_on_blocks_password_and_social_sign_in_but_keeps_break_glass(harness, idp):
    practice = await _practice_with_anna(harness)
    setup = await sso_ready(harness, practice, idp)
    body = settings_body(
        (idp,), claim_ids=[setup.claim_id], required=True, break_glass=[await _admin_id(harness, practice)]
    )
    assert (await save_settings(harness, practice.admin, body)).status_code == 200

    anna = await harness.client.post("/api/auth/login", json={"email": ANNA, "password": PASSWORD})
    stranger = await harness.client.post("/api/auth/login", json={"email": "zoe@lakeside.example.com", "password": "x"})
    keeper = await harness.client.post("/api/auth/login", json={"email": ADMIN, "password": PASSWORD})
    harness.providers["google"].returns("code-9", subject="g-anna", email=ANNA, name="Anna Reyes")
    social = await back_from(harness, "google", "code-9")

    assert (anna.status_code, anna.json()) == (
        403,
        {"error": "sso_required", "message": "your organization signs in with single sign-on"},
    )
    assert stranger.status_code == 403
    assert (keeper.status_code, keeper.json()["mfa"]) == (200, "verify")
    assert social.headers["location"] == sign_in_page("error=sso_required&provider=google")
    details = [event.detail for event in await auth_events("sign_in_failed")]
    assert details.count("password: single sign-on required") == 2


async def test_people_who_must_use_single_sign_on_get_no_password_links(harness, idp):
    practice = await _practice_with_anna(harness)
    setup = await sso_ready(harness, practice, idp)
    body = settings_body(
        (idp,), claim_ids=[setup.claim_id], required=True, break_glass=[await _admin_id(harness, practice)]
    )
    assert (await save_settings(harness, practice.admin, body)).status_code == 200
    sent = len(harness.messenger.sent)

    await harness.client.post("/api/auth/forgot", json={"email": ANNA})
    invited = await harness.client.post(
        "/api/team",
        headers=practice.admin,
        json={"name": "Eli Fox", "email": "eli@lakeside.example.com", "role": "viewer"},
    )

    assert invited.status_code == 200, invited.text
    [(to, message)] = harness.messenger.sent[sent:]
    assert to == "eli@lakeside.example.com"
    assert "single sign-on" in message and "set-password" not in message


async def test_the_sign_in_page_learns_whether_a_domain_uses_single_sign_on(harness, idp):
    practice = await _practice_with_anna(harness)
    before = await harness.client.post("/api/auth/sso", json={"email": ANNA})
    setup = await sso_ready(harness, practice, idp)
    optional = await harness.client.post("/api/auth/sso", json={"email": ANNA})
    other = await harness.client.post("/api/auth/sso", json={"email": "someone@gmail.com"})
    body = settings_body(
        (idp,), claim_ids=[setup.claim_id], required=True, break_glass=[await _admin_id(harness, practice)]
    )
    assert (await save_settings(harness, practice.admin, body)).status_code == 200
    required = await harness.client.post("/api/auth/sso", json={"email": "New.Person@Lakeside.Example.com"})

    start_url = f"/api/auth/saml/{setup.connection_id}/start"
    assert before.json() == {"mode": "none", "start_url": None}
    assert optional.json() == {"mode": "optional", "start_url": start_url}
    assert other.json() == {"mode": "none", "start_url": None}
    assert required.json() == {"mode": "required", "start_url": start_url}


async def test_the_admin_host_never_offers_single_sign_on(harness, idp, monkeypatch):
    practice = await _practice_with_anna(harness)
    setup = await sso_ready(harness, practice, idp)
    monkeypatch.setattr(get_settings(), "admin_url", ADMIN_SITE)
    found = await harness.client.post(f"{ADMIN_SITE}/api/auth/sso", json={"email": ANNA})
    started = await harness.client.get(f"{ADMIN_SITE}/api/auth/saml/{setup.connection_id}/start")
    assert found.json() == {"mode": "none", "start_url": None}
    assert started.headers["location"].startswith(f"{ADMIN_SITE}/sign-in#error=sso_failed")


async def test_a_removed_connection_no_longer_signs_anyone_in(harness, idp):
    practice = await _practice_with_anna(harness)
    setup = await sso_ready(harness, practice, idp)
    started = await start(harness, setup.connection_id)
    removed = await harness.client.delete("/api/practice/sso", headers=practice.admin)
    facts = assertion_for(setup.connection_id, in_response_to=started.request_id)

    back = await post_back(harness, setup.connection_id, encoded(signed_response(facts, idp)), started.relay)

    assert (removed.status_code, removed.json()["connection"]) == (200, None)
    assert back.headers["location"] == refused_location("sso_failed")
    assert (await harness.client.post("/api/auth/sso", json={"email": ANNA})).json()["mode"] == "none"
    assert (await harness.client.get(f"/api/auth/saml/{setup.connection_id}/metadata")).status_code == 404
