from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.messenger import Messenger
from app.core.calendar import today_in, zone_named
from app.core.deps import ACTIVE_PRACTICE_STATUSES, Actor
from app.core.errors import Conflict, Invalid, NotFound
from app.core.roles import ADMIN_ROLE
from app.models import (
    CLOSED_STATUSES,
    PRACTICE_REALM,
    Activity,
    Analysis,
    Note,
    Organization,
    Practice,
    PracticeMembership,
    Provider,
    Subscription,
    User,
    utcnow,
)
from app.services.account_lookup import account_by_email, email_in_use
from app.services.audit_log import record_activity
from app.services.expenditure import SPEND_TIME_ZONE, month_to_date, spend_since
from app.services.hq_organizations import organization_count
from app.services.memberships import ACTIVE_MEMBER, BLOCKED, LIVE, SEAT_HOLDING
from app.services.password_reset import send_reset_email
from app.services.plan_limits import subscription_for
from app.services.plans import PLAN_KEYS
from app.services.practice_accounts import (
    AdminDraft,
    NewPractice,
    PracticeDraft,
    add_practice_for_person,
    add_practice_with_admin,
    signup_source,
)
from app.services.retention import purge_after
from app.services.subscriptions import refuse_combined_change, refuse_manual_change
from app.services.team import EMAIL_TAKEN, send_added, send_invite
from app.services.user_sessions import end_practice_sessions
from app.services.worklists import count_of

STATUSES = ("trial", "active", "ended", "blocked")
ACTIVITY_PAGE = 100
ADMIN_ORDER = (
    (PracticeMembership.status == BLOCKED).asc(),
    PracticeMembership.created_at,
    PracticeMembership.id,
)
HQ_SOURCE = "hq"
TRACKED_FIELDS = ("name", "time_zone", "status", "plan", "seats", "renews_on")
CLOSED_PRACTICE = "a closed practice cannot be changed"
RENEWAL_IN_PAST = "choose a renewal date after today"
NO_END_DATE = "no end date"
UNKNOWN_PLAN = "choose a plan"
PRACTICE_CLOSED = "practice closed by HQ"


async def overview(db: AsyncSession) -> dict[str, Any]:
    since = utcnow() - timedelta(hours=24)
    by_status = dict((await db.execute(select(Analysis.status, func.count()).group_by(Analysis.status))).all())
    read = await db.scalar(
        select(func.count())
        .select_from(Analysis)
        .where(Analysis.finished_at >= since, Analysis.status.in_(("succeeded", "superseded")))
    )
    spent = await spend_since(db, since)
    failed = await db.scalar(
        select(func.count()).select_from(Analysis).where(Analysis.finished_at >= since, Analysis.status == "failed")
    )
    practices = await db.scalar(
        select(func.count()).select_from(Practice).where(Practice.status.in_(ACTIVE_PRACTICE_STATUSES))
    )
    people = await db.scalar(
        select(func.count(func.distinct(PracticeMembership.user_id)))
        .join(User, User.id == PracticeMembership.user_id)
        .where(*ACTIVE_MEMBER, User.status == "active")
    )
    return {
        "organizations": await organization_count(db),
        "practices": practices or 0,
        "people": people or 0,
        "read_last_24h": read or 0,
        "tokens_last_24h": spent["input_tokens"] + spent["output_tokens"],
        "cost_last_24h_usd": spent["cost_usd"],
        "unpriced_last_24h": spent["unpriced_analyses"],
        "failed_last_24h": failed or 0,
        "waiting": by_status.get("queued", 0),
        "running": by_status.get("running", 0),
        "month": await month_to_date(db, today_in(zone_named(SPEND_TIME_ZONE))),
    }


async def practice_row(db: AsyncSession, practice_id: str) -> dict[str, Any]:
    found = await practices(db, practice_id=practice_id)
    if not found:
        raise NotFound("practice not found")
    return found[0]


async def practices(db: AsyncSession, *, practice_id: str | None = None) -> list[dict[str, Any]]:
    counts = {
        "users": await _count_by_practice(db, PracticeMembership.practice_id, *SEAT_HOLDING),
        "providers": await _count_by_practice(db, Provider.practice_id),
        "waiting": await _count_by_practice(db, Note.practice_id, Note.status.in_(("queued", "reading", "ready"))),
    }
    admins = await _first_admins(db)
    failures = await _recent_failures(db, utcnow() - timedelta(hours=24))
    billing = {row.practice_id: row for row in await db.scalars(select(Subscription))}
    groups = dict((await db.execute(select(Organization.id, Organization.name))).tuples().all())
    query = select(Practice).order_by(Practice.name)
    rows = await db.scalars(query if practice_id is None else query.where(Practice.id == practice_id))
    return [
        {
            **_practice_row(p, counts, admins.get(p.id), failures.get(p.id, (0, None))),
            **_billing_view(billing.get(p.id)),
            "organization_id": p.organization_id,
            "organization_name": groups.get(p.organization_id) if p.organization_id else None,
            "combined_billing": p.combined_billing,
        }
        for p in rows
    ]


def _billing_view(subscription: Subscription | None) -> dict[str, Any]:
    if subscription is None:
        return {"billing_provider": None, "billing_status": None, "billing_interval": None}
    return {
        "billing_provider": subscription.provider,
        "billing_status": subscription.status,
        "billing_interval": subscription.interval,
    }


def _practice_row(
    practice: Practice, counts: dict[str, dict[str, int]], admin: Any, failure: tuple[int, str | None]
) -> dict[str, Any]:
    return {
        "id": practice.id,
        "name": practice.name,
        "status": practice.status,
        "plan": practice.plan,
        "seats": practice.seats,
        **{key: found.get(practice.id, 0) for key, found in counts.items()},
        "renews_on": practice.renews_on.isoformat() if practice.renews_on else None,
        "closed_at": practice.closed_at.isoformat() if practice.closed_at else None,
        "purge_after": purge_after(practice.closed_at).isoformat() if practice.closed_at else None,
        "purged_at": practice.purged_at.isoformat() if practice.purged_at else None,
        "time_zone": practice.time_zone,
        "source": signup_source(practice),
        "signed_up_on": practice.created_at.astimezone(zone_named(practice.time_zone)).date().isoformat(),
        "failed_24h": failure[0],
        "last_failure": failure[1],
        "admin_name": admin.name if admin else None,
        "admin_email": admin.email if admin else None,
        "admin_status": admin.status if admin else None,
    }


async def _count_by_practice(db: AsyncSession, column: Any, *conditions: Any) -> dict[str, int]:
    rows = await db.execute(select(column, func.count()).where(*conditions).group_by(column))
    return dict(rows.all())


async def _first_admins(db: AsyncSession) -> dict[str, Any]:
    rows = await db.execute(
        select(PracticeMembership.practice_id, User.name, User.email, PracticeMembership.status)
        .join(User, User.id == PracticeMembership.user_id)
        .where(PracticeMembership.role == ADMIN_ROLE, LIVE)
        .order_by(PracticeMembership.practice_id, *ADMIN_ORDER)
        .ext(distinct_on(PracticeMembership.practice_id))
    )
    return {row.practice_id: row for row in rows}


async def _recent_failures(db: AsyncSession, since: Any) -> dict[str, tuple[int, str | None]]:
    failed = (Analysis.status == "failed", Analysis.finished_at >= since)
    counts = await db.execute(
        select(Note.practice_id, func.count())
        .select_from(Analysis)
        .join(Note, Note.id == Analysis.note_id)
        .where(*failed)
        .group_by(Note.practice_id)
    )
    latest = await db.execute(
        select(Note.practice_id, Analysis.error)
        .select_from(Analysis)
        .join(Note, Note.id == Analysis.note_id)
        .where(*failed)
        .order_by(Note.practice_id, Analysis.finished_at.desc())
        .ext(distinct_on(Note.practice_id))
    )
    reasons: dict[str, str | None] = {practice_id: error for practice_id, error in latest.all()}
    return {practice_id: (count, reasons.get(practice_id)) for practice_id, count in counts.all()}


async def create_practice(
    db: AsyncSession,
    messenger: Messenger,
    actor: Actor,
    *,
    name: str,
    admin_name: str,
    admin_email: str,
    plan: str,
    seats: int,
    time_zone: str,
) -> Practice:
    if plan not in PLAN_KEYS or seats < 1:
        raise Invalid("choose a plan and at least one seat")
    zone_named(time_zone)
    status = "trial" if plan == "trial" else "active"
    draft = PracticeDraft(name, plan, status, seats, time_zone, signup={"source": HQ_SOURCE})
    created = await _practice_with_admin(db, draft, AdminDraft(admin_name, admin_email, "invited"))
    practice = created.practice
    if created.admin.status == "invited":
        await send_invite(db, messenger, created.admin, team_name=practice.name)
    else:
        await send_added(messenger, created.admin, practice_name=practice.name)
    record_activity(
        db, actor, "practice added", practice_id=practice.id, detail=f"{practice.name}, {plan}, {seats} seats"
    )
    await db.commit()
    return practice


async def _practice_with_admin(db: AsyncSession, draft: PracticeDraft, admin: AdminDraft) -> NewPractice:
    person = await account_by_email(db, admin.email, (PRACTICE_REALM,))
    if person is not None:
        return await add_practice_for_person(db, draft, person)
    if await email_in_use(db, admin.email, PRACTICE_REALM):
        raise Conflict(EMAIL_TAKEN)
    return await add_practice_with_admin(db, draft, admin)


async def update_practice(db: AsyncSession, actor: Actor, practice_id: str, changes: dict[str, Any]) -> Practice:
    practice = await db.get(Practice, practice_id)
    if practice is None:
        raise NotFound("practice not found")
    if practice.status in CLOSED_STATUSES:
        raise Conflict(CLOSED_PRACTICE)
    before = _tracked(practice)
    status, plan, seats = changes.get("status"), changes.get("plan"), changes.get("seats")
    if (status and status not in STATUSES) or (plan and plan not in PLAN_KEYS) or (seats is not None and seats < 1):
        raise Invalid("status, plan or seats is not allowed")
    renewal_changed = "renews_on" in changes and changes["renews_on"] != practice.renews_on
    if renewal_changed or (plan and plan != practice.plan):
        refuse_combined_change(practice)
        refuse_manual_change(await subscription_for(db, practice.id))
    if changes.get("time_zone"):
        practice.time_zone = zone_named(changes["time_zone"]).key
    if changes.get("name"):
        practice.name = changes["name"].strip()
    if status and status != practice.status and status in ("ended", "blocked"):
        await _close_sessions(db, actor, practice.id)
    practice.status = status or status_for_plan(practice.status, plan or practice.plan)
    practice.plan = plan or practice.plan
    practice.seats = seats if seats is not None else practice.seats
    if "renews_on" in changes:
        practice.renews_on = changes["renews_on"]
    after = _tracked(practice)
    record_activity(
        db,
        actor,
        "practice updated",
        practice_id=practice.id,
        detail=f"{practice.status}, {practice.plan}, {practice.seats} seats",
        changes=[
            {"field": key, "before": before[key], "after": after[key]} for key in after if after[key] != before[key]
        ],
    )
    await db.commit()
    return practice


def status_for_plan(status: str, plan: str) -> str:
    if status not in ACTIVE_PRACTICE_STATUSES:
        return status
    return "trial" if plan == "trial" else "active"


def _tracked(practice: Practice) -> dict[str, Any]:
    values = {field: getattr(practice, field) for field in TRACKED_FIELDS}
    return {field: value.isoformat() if isinstance(value, date) else value for field, value in values.items()}


def _day(value: date | None) -> str | None:
    return value.isoformat() if value else None


async def _close_sessions(db: AsyncSession, actor: Actor, practice_id: str) -> None:
    members = select(User).join(PracticeMembership, PracticeMembership.user_id == User.id)
    for user in (await db.scalars(members.where(PracticeMembership.practice_id == practice_id))).all():
        await end_practice_sessions(db, user, practice_id, reason=PRACTICE_CLOSED, client=actor.client)


@dataclass(frozen=True)
class ActivityPage:
    rows: list[Activity]
    total: int
    actions: list[str]


async def activity(db: AsyncSession, *, practice_id: str | None, action: str | None, offset: int) -> ActivityPage:
    query = select(Activity)
    if practice_id:
        query = query.where(Activity.practice_id == practice_id)
    if action:
        query = query.where(Activity.action == action)
    rows = await db.scalars(query.order_by(Activity.created_at.desc(), Activity.id).offset(offset).limit(ACTIVITY_PAGE))
    actions = await db.scalars(select(Activity.action).distinct().order_by(Activity.action))
    return ActivityPage(list(rows.all()), await count_of(db, query), list(actions.all()))


async def send_admin_link(db: AsyncSession, messenger: Messenger, actor: Actor, practice_id: str) -> str:
    practice = await _practice(db, practice_id)
    first = (
        select(User, PracticeMembership.status)
        .join(PracticeMembership, PracticeMembership.user_id == User.id)
        .where(PracticeMembership.practice_id == practice.id, PracticeMembership.role == ADMIN_ROLE, LIVE)
        .order_by(*ADMIN_ORDER)
        .limit(1)
    )
    found = (await db.execute(first)).tuples().first()
    if found is None:
        raise NotFound("this practice has no admin")
    admin, standing = found
    if standing == BLOCKED:
        raise Conflict("the practice admin is blocked")
    if admin.status == "invited":
        record_activity(db, actor, "admin invite resent", practice_id=practice.id, detail=admin.name)
        await send_invite(db, messenger, admin, team_name=practice.name)
        await db.commit()
        return "invite"
    if admin.status == "active":
        record_activity(db, actor, "admin password reset sent", practice_id=practice.id, detail=admin.name)
        await send_reset_email(db, messenger, admin)
        return "reset"
    raise Conflict("the practice admin is blocked")


async def renew_practice(
    db: AsyncSession, actor: Actor, practice_id: str, until: date | None, *, plan: str | None = None
) -> Practice:
    practice = await _practice(db, practice_id)
    refuse_combined_change(practice)
    refuse_manual_change(await subscription_for(db, practice.id))
    if until is not None and until <= today_in(zone_named(practice.time_zone)):
        raise Invalid(RENEWAL_IN_PAST)
    if plan is not None and plan not in PLAN_KEYS:
        raise Invalid(UNKNOWN_PLAN)
    previous, previous_plan = practice.renews_on, practice.plan
    practice.renews_on, practice.plan = until, plan or practice.plan
    practice.status = status_for_plan(practice.status, practice.plan)
    detail = f"{practice.plan}, renews {until.isoformat()}" if until else f"{practice.plan}, {NO_END_DATE}"
    changed = [{"field": "renews_on", "before": _day(previous), "after": _day(until)}]
    if practice.plan != previous_plan:
        changed.append({"field": "plan", "before": previous_plan, "after": practice.plan})
    record_activity(db, actor, "practice renewed", practice_id=practice.id, detail=detail, changes=changed)
    await db.commit()
    return practice


async def _practice(db: AsyncSession, practice_id: str) -> Practice:
    practice = await db.get(Practice, practice_id, with_for_update=True)
    if practice is None:
        raise NotFound("practice not found")
    if practice.status in CLOSED_STATUSES:
        raise Conflict(CLOSED_PRACTICE)
    return practice
