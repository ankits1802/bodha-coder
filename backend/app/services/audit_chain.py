from __future__ import annotations

from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import Actor
from app.models import Practice, utcnow
from app.services.audit_log import record_activity

__all__ = ["ACCESS_LOG_CHAIN", "ACTIVITY_CHAIN", "AUDIT_LOG_VERIFIED", "chain_view", "verify_audit_log"]

ACCESS_LOG_CHAIN, ACTIVITY_CHAIN = "access_log:", "activity"
AUDIT_LOG_VERIFIED = "audit log verified"
VERIFY = text("SELECT * FROM bodha_verify_audit_log()")


async def verify_audit_log(db: AsyncSession, actor: Actor) -> dict[str, Any]:
    results = (await db.execute(VERIFY)).mappings().all()
    names = await _practice_names(db, [_practice_of(row["chain_name"]) for row in results])
    chains = [chain_view(row, names) for row in results]
    broken = [chain for chain in chains if not chain["intact"]]
    record_activity(db, actor, AUDIT_LOG_VERIFIED, practice_id=None, detail=_summary(chains, broken))
    await db.commit()
    return {"checked_at": utcnow().isoformat(), "intact": not broken, "chains": chains}


def chain_view(row: Any, names: dict[str, str]) -> dict[str, Any]:
    practice_id = _practice_of(row["chain_name"])
    return {
        "chain": ACTIVITY_CHAIN if practice_id is None else "access_log",
        "practice_id": practice_id,
        "practice_name": names.get(practice_id or ""),
        "checked": row["checked"],
        "head_seq": row["head_seq"],
        "head_hash": row["head_hash"],
        "intact": row["problem"] is None,
        "broken_seq": row["broken_seq"],
        "broken_id": row["broken_id"],
        "problem": row["problem"],
    }


def _practice_of(chain_name: str) -> str | None:
    return chain_name.removeprefix(ACCESS_LOG_CHAIN) if chain_name.startswith(ACCESS_LOG_CHAIN) else None


async def _practice_names(db: AsyncSession, practice_ids: list[str | None]) -> dict[str, str]:
    wanted = {practice_id for practice_id in practice_ids if practice_id}
    if not wanted:
        return {}
    rows = await db.execute(select(Practice.id, Practice.name).where(Practice.id.in_(wanted)))
    return dict(rows.tuples().all())


def _summary(chains: list[dict[str, Any]], broken: list[dict[str, Any]]) -> str:
    rows = sum(chain["checked"] for chain in chains)
    if not broken:
        return f"{len(chains)} chains, {rows} entries, intact"
    first = broken[0]
    where = f"{first['practice_id'] or ACTIVITY_CHAIN} at entry {first['broken_seq']} ({first['problem']})"
    return f"{len(broken)} of {len(chains)} chains broken; first: {where}"
