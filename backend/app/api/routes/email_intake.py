from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import Field

from app.api.bodies import Body
from app.api.responses.base import ExactRoute
from app.api.responses.email_intake import EmailIntakeView, IntakeMessagePage, IntakeTestView
from app.api.wiring import Mail
from app.core.deps import Actor, Db, require
from app.core.roles import ADMINS
from app.models import SENDER_LENGTH
from app.services import email_intake_settings

router = APIRouter(tags=["email intake"], route_class=ExactRoute)
Admin = Annotated[Actor, Depends(require(*ADMINS))]
EMAIL_INTAKE = "/practice/email-intake"


class SenderBody(Body):
    sender: str = Field(min_length=3, max_length=SENDER_LENGTH)


@router.get(EMAIL_INTAKE, response_model=EmailIntakeView)
async def email_intake(db: Db, actor: Admin) -> dict[str, Any]:
    return await email_intake_settings.email_intake_view(db, actor)


@router.post(f"{EMAIL_INTAKE}/address", response_model=EmailIntakeView)
async def issue_address(db: Db, actor: Admin) -> dict[str, Any]:
    return await email_intake_settings.issue_address(db, actor)


@router.delete(f"{EMAIL_INTAKE}/address", response_model=EmailIntakeView)
async def retire_address(db: Db, actor: Admin) -> dict[str, Any]:
    return await email_intake_settings.retire_address(db, actor)


@router.post(f"{EMAIL_INTAKE}/senders", response_model=EmailIntakeView)
async def add_sender(body: SenderBody, db: Db, actor: Admin) -> dict[str, Any]:
    return await email_intake_settings.add_sender(db, actor, body.sender)


@router.delete(f"{EMAIL_INTAKE}/senders/{{sender_id}}", response_model=EmailIntakeView)
async def remove_sender(sender_id: str, db: Db, actor: Admin) -> dict[str, Any]:
    return await email_intake_settings.remove_sender(db, actor, sender_id)


@router.post(f"{EMAIL_INTAKE}/tests", response_model=IntakeTestView)
async def send_test(db: Db, mail: Mail, actor: Admin) -> dict[str, Any]:
    return await email_intake_settings.send_test(db, mail, actor)


@router.get(f"{EMAIL_INTAKE}/tests/{{test_id}}", response_model=IntakeTestView)
async def intake_test(test_id: str, db: Db, actor: Admin) -> dict[str, Any]:
    return await email_intake_settings.intake_test_view(db, actor, test_id)


@router.get(f"{EMAIL_INTAKE}/messages", response_model=IntakeMessagePage)
async def messages(db: Db, actor: Admin, offset: Annotated[int, Query(ge=0)] = 0) -> dict[str, Any]:
    return await email_intake_settings.message_page(db, actor, offset=offset)
