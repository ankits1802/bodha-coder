from __future__ import annotations

from typing import Any

from sqlalchemy import ColumnElement, Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.codes.billing_codes import parse_code_list
from app.codes.icd import format_icd, is_icd_shaped
from app.core.deps import Actor
from app.core.errors import Invalid
from app.models import CodeSet, Note, Provider
from app.services.audit_log import record_access
from app.services.worklists import summary

MIN_SEARCH_LENGTH = 2
MAX_SEARCH_LENGTH = 100
SEARCH_LIMIT = 50
SEARCHED = "searched"
LIKE_ESCAPE = "\\"


async def search_notes(db: AsyncSession, actor: Actor, text: str) -> list[dict[str, Any]]:
    term = text.strip()
    if len(term) < MIN_SEARCH_LENGTH:
        raise Invalid(f"type at least {MIN_SEARCH_LENGTH} characters")
    if len(term) > MAX_SEARCH_LENGTH:
        raise Invalid(f"type at most {MAX_SEARCH_LENGTH} characters")
    query = (
        select(Note, Provider.name)
        .join(Provider, Provider.id == Note.provider_id)
        .where(Note.practice_id == actor.practice_id, or_(*_matches(actor.practice_id, term)))
        .order_by(Note.service_date.desc(), Note.created_at.desc())
        .limit(SEARCH_LIMIT)
    )
    rows = (await db.execute(query)).all()
    record_access(db, actor, SEARCHED, detail=f"{len(rows)} results")
    await db.commit()
    return [summary(note, provider_name) for note, provider_name in rows]


def code_forms(term: str) -> set[str]:
    forms = {code.code for code in parse_code_list(term).codes}
    if is_icd_shaped(term):
        forms.add(format_icd(term))
    return forms


def _matches(practice_id: str, term: str) -> list[ColumnElement[bool]]:
    pattern = f"%{_escaped(term)}%"
    found: list[ColumnElement[bool]] = [
        Note.patient_name.ilike(pattern, escape=LIKE_ESCAPE),
        Note.file_name.ilike(pattern, escape=LIKE_ESCAPE),
        Provider.name.ilike(pattern, escape=LIKE_ESCAPE),
    ]
    forms = code_forms(term)
    if forms:
        found.append(Note.id.in_(_coded(practice_id, forms)))
    return found


def _coded(practice_id: str, forms: set[str]) -> Select[Any]:
    latest = (
        select(CodeSet.note_id, CodeSet.kind, func.max(CodeSet.revision).label("revision"))
        .join(Note, Note.id == CodeSet.note_id)
        .where(Note.practice_id == practice_id)
        .group_by(CodeSet.note_id, CodeSet.kind)
        .subquery()
    )
    return (
        select(CodeSet.note_id)
        .join(
            latest,
            and_(
                CodeSet.note_id == latest.c.note_id,
                CodeSet.kind == latest.c.kind,
                CodeSet.revision == latest.c.revision,
            ),
        )
        .where(or_(*(CodeSet.codes.contains([{"code": form}]) for form in sorted(forms))))
    )


def _escaped(term: str) -> str:
    return term.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2).replace("%", f"{LIKE_ESCAPE}%").replace("_", f"{LIKE_ESCAPE}_")
