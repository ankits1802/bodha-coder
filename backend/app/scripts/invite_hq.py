from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from email.utils import parseaddr

from pydantic import EmailStr, TypeAdapter, ValidationError

from app.adapters.messenger import Messenger, build_messenger
from app.core.config import get_settings
from app.core.db import SessionFactory
from app.core.errors import AppError
from app.services.hq_team import HqEnrolment, enrol_hq_person

USAGE = 'usage: python -m app.scripts.invite_hq "Full Name <email>" ["Full Name <email>" ...]\n'
NOT_A_PERSON = 'not in the form "Full Name <email>"; skipped'
EMAIL = TypeAdapter(EmailStr)


@dataclass(frozen=True)
class Person:
    name: str
    email: str


def person_from(argument: str) -> Person | None:
    name, email = parseaddr(argument)
    if not name.strip():
        return None
    try:
        return Person(name.strip(), EMAIL.validate_python(email))
    except ValidationError:
        return None


async def invite_people(arguments: list[str], messenger: Messenger) -> list[str]:
    return [await _invite_one(place, argument, messenger) for place, argument in enumerate(arguments, start=1)]


def enrolment_line(enrolment: HqEnrolment) -> str:
    renamed = f", renamed from {enrolment.renamed_from}" if enrolment.renamed_from else ""
    return f"{enrolment.user.name}: {enrolment.outcome}{renamed} (user {enrolment.user.id})"


async def _invite_one(place: int, argument: str, messenger: Messenger) -> str:
    person = person_from(argument)
    if person is None:
        return f"{place}. {NOT_A_PERSON}"
    async with SessionFactory() as db:
        try:
            enrolment = await enrol_hq_person(db, messenger, name=person.name, email=person.email)
        except AppError as error:
            return f"{place}. {person.name}: {error.message}; skipped"
    return f"{place}. {enrolment_line(enrolment)}"


def main(arguments: list[str]) -> int:
    if not arguments:
        sys.stderr.write(USAGE)
        return 2
    lines = asyncio.run(invite_people(arguments, build_messenger(get_settings())))
    sys.stdout.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
