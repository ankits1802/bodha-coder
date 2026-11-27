import pytest

from app.services.queue_views import MAX_SAVED_VIEWS
from tests.builders import invite_member, practice_with_provider, sign_in

PATH = "/api/queue-views"
DEFAULT_FILTERS = {"lane": None, "reason": None, "assigned": None, "provider_id": None, "overdue": False, "sort": "due"}


@pytest.mark.parametrize(
    ("role", "keys"),
    [
        ("coder", ["my_work"]),
        ("cdi", ["questions_to_send"]),
        ("compliance", ["flagged"]),
        ("biller", []),
    ],
)
async def test_each_role_starts_with_its_own_built_in_views(harness, role, keys):
    practice = await practice_with_provider(harness)
    email = f"{role}@lakeside.example.com"
    await invite_member(harness, practice, name=f"{role.title()} Person", email=email, role=role)
    person = await sign_in(harness.client, email, secret_box=practice.secrets)

    views = (await harness.client.get(PATH, headers=person)).json()

    assert ([view["key"] for view in views["builtin"]], views["saved"]) == (keys, [])


async def test_admins_get_unassigned_and_overdue_with_the_filters_they_apply(harness):
    practice = await practice_with_provider(harness)

    builtin = (await harness.client.get(PATH, headers=practice.admin)).json()["builtin"]

    assert builtin == [
        {"key": "unassigned", "filters": {**DEFAULT_FILTERS, "assigned": "none"}},
        {"key": "overdue", "filters": {**DEFAULT_FILTERS, "overdue": True}},
    ]


async def test_a_saved_view_belongs_to_its_author_and_can_be_deleted(harness):
    practice = await practice_with_provider(harness)
    await invite_member(harness, practice, name="Cora Coder", email="cora@lakeside.example.com", role="coder")
    coder = await sign_in(harness.client, "cora@lakeside.example.com")
    body = {"name": "Varga by impact", "filters": {"provider_id": practice.provider_id, "sort": "impact"}}

    saved = await harness.client.post(PATH, headers=practice.admin, json=body)
    again = await harness.client.post(PATH, headers=practice.admin, json={**body, "name": "VARGA BY IMPACT"})

    assert saved.status_code == 200, saved.text
    view = saved.json()
    assert (view["name"], view["filters"]) == (
        "Varga by impact",
        {**DEFAULT_FILTERS, "provider_id": practice.provider_id, "sort": "impact"},
    )
    assert again.status_code == 409
    assert (await harness.client.get(PATH, headers=practice.admin)).json()["saved"] == [view]
    assert (await harness.client.get(PATH, headers=coder)).json()["saved"] == []
    assert (await harness.client.delete(f"{PATH}/{view['id']}", headers=coder)).status_code == 404
    assert (await harness.client.delete(f"{PATH}/{view['id']}", headers=practice.admin)).status_code == 204
    assert (await harness.client.get(PATH, headers=practice.admin)).json()["saved"] == []


async def test_a_view_names_only_this_practices_providers_and_known_filters(harness):
    lakeside = await practice_with_provider(harness)
    hillside = await practice_with_provider(harness, name="Hillside", admin_email="admin@hillside.example.com")

    foreign = await harness.client.post(
        PATH, headers=lakeside.admin, json={"name": "Theirs", "filters": {"provider_id": hillside.provider_id}}
    )
    unknown = await harness.client.post(PATH, headers=lakeside.admin, json={"name": "Odd", "filters": {"lane": "x"}})
    nameless = await harness.client.post(PATH, headers=lakeside.admin, json={"name": "", "filters": {}})

    assert (foreign.status_code, unknown.status_code, nameless.status_code) == (422, 422, 422)


async def test_a_person_keeps_at_most_the_saved_view_limit(harness):
    practice = await practice_with_provider(harness)
    for number in range(MAX_SAVED_VIEWS):
        made = await harness.client.post(PATH, headers=practice.admin, json={"name": f"View {number}", "filters": {}})
        assert made.status_code == 200, made.text

    over = await harness.client.post(PATH, headers=practice.admin, json={"name": "One more", "filters": {}})

    assert (over.status_code, over.json()["message"]) == (409, f"keep at most {MAX_SAVED_VIEWS} saved views")
