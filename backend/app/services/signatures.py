from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.object_store import ObjectStore, person_signature_key, provider_signature_key
from app.adapters.pdf_writer import UnreadableImage, image_size
from app.ai.errors import ModelError
from app.ai.signature_check import ImageModel, SignatureVerdict, check_signature_image
from app.core.deps import Actor, ProviderActor
from app.core.errors import Invalid, NotFound, SignatureRequired, Unavailable
from app.models import Signature, SignatureAdoption, new_id
from app.services.rate_limits import SIGNATURE_DRAFTS_PER_OWNER, hit
from app.services.signature_images import SignatureImage, data_url, read_signature_image

__all__ = [
    "CHECKED_SOURCES",
    "SignatureChoice",
    "SignatureDraft",
    "SignatureOwner",
    "SignatureTools",
    "adopt",
    "adopted_signature",
    "capture",
    "owned_signature",
    "person_signature",
    "provider_signature",
    "signature_card",
]

logger = logging.getLogger("bodha.signatures")
PNG = "image/png"
CHECKED_SOURCES = ("drawn", "uploaded")
AGENT_LENGTH = 300
CHECK_UNAVAILABLE = "the signature check is not available right now; type your name instead or try again"
ADD_YOURS = "add your signature before approving"
SIGN_FIRST = "sign before sending"


@dataclass(frozen=True)
class SignatureOwner:
    user_id: str | None = None
    provider_id: str | None = None
    practice_id: str | None = None

    @classmethod
    def person(cls, user_id: str) -> SignatureOwner:
        return cls(user_id=user_id)

    @classmethod
    def provider(cls, provider_id: str, practice_id: str) -> SignatureOwner:
        return cls(provider_id=provider_id, practice_id=practice_id)

    def columns(self) -> dict[str, str | None]:
        return {"user_id": self.user_id, "provider_id": self.provider_id, "practice_id": self.practice_id}

    def file_key(self, signature_id: str) -> str:
        if self.user_id is not None:
            return person_signature_key(self.user_id, signature_id)
        return provider_signature_key(self.practice_id or "", signature_id)

    @property
    def rate_key(self) -> str:
        return f"user:{self.user_id}" if self.user_id is not None else f"provider:{self.provider_id}"

    def owns(self, model: type[Signature] | type[SignatureAdoption]) -> list[Any]:
        if self.user_id is not None:
            return [model.user_id == self.user_id]
        return [model.provider_id == self.provider_id, model.practice_id == self.practice_id]


@dataclass(frozen=True)
class SignatureDraft:
    source: str
    typed_name: str
    image: str
    ip: str | None
    user_agent: str | None


@dataclass(frozen=True)
class SignatureTools:
    store: ObjectStore
    model: ImageModel


@dataclass(frozen=True)
class SignatureChoice:
    signature_id: str | None
    remember: bool


async def capture(db: AsyncSession, tools: SignatureTools, owner: SignatureOwner, draft: SignatureDraft) -> Signature:
    await hit(db, SIGNATURE_DRAFTS_PER_OWNER, owner.rate_key)
    image = read_signature_image(draft.image)
    await _readable(image)
    verdict = await _checked(tools.model, image) if draft.source in CHECKED_SOURCES else None
    signature_id = new_id()
    key = owner.file_key(signature_id)
    await tools.store.put(key, image.png, content_type=PNG)
    row = Signature(
        id=signature_id,
        **owner.columns(),
        source=draft.source,
        typed_name=draft.typed_name,
        file_key=key,
        sha256=image.sha256,
        width=image.width,
        height=image.height,
        file_bytes=len(image.png),
        checked=verdict is not None,
        check=verdict.record() if verdict is not None else None,
        ip=draft.ip,
        user_agent=(draft.user_agent or "")[:AGENT_LENGTH] or None,
    )
    db.add(row)
    await db.commit()
    return row


async def owned_signature(db: AsyncSession, owner: SignatureOwner, signature_id: str) -> Signature:
    row = await db.scalar(select(Signature).where(Signature.id == signature_id, *owner.owns(Signature)))
    if row is None:
        raise NotFound("signature not found")
    return row


async def adopt(db: AsyncSession, owner: SignatureOwner, signature_id: str) -> Signature:
    row = await owned_signature(db, owner, signature_id)
    db.add(SignatureAdoption(signature_id=row.id, **owner.columns()))
    await db.commit()
    return row


async def adopted_signature(db: AsyncSession, owner: SignatureOwner) -> Signature | None:
    adoption = await db.scalar(
        select(SignatureAdoption)
        .where(*owner.owns(SignatureAdoption))
        .order_by(SignatureAdoption.created_at.desc())
        .limit(1)
    )
    return None if adoption is None else await db.get_one(Signature, adoption.signature_id)


async def person_signature(db: AsyncSession, actor: Actor) -> Signature:
    found = await adopted_signature(db, SignatureOwner.person(actor.user.id))
    if found is None:
        raise SignatureRequired(ADD_YOURS)
    return found


async def provider_signature(db: AsyncSession, actor: ProviderActor, choice: SignatureChoice) -> Signature:
    owner = SignatureOwner.provider(actor.provider_id, actor.practice_id)
    if choice.signature_id is None:
        remembered = await adopted_signature(db, owner)
        if remembered is None:
            raise SignatureRequired(SIGN_FIRST)
        return remembered
    chosen = await owned_signature(db, owner, choice.signature_id)
    if choice.remember:
        db.add(SignatureAdoption(signature_id=chosen.id, **owner.columns()))
    return chosen


async def signature_card(store: ObjectStore, row: Signature) -> dict[str, Any]:
    return {
        "id": row.id,
        "source": row.source,
        "typed_name": row.typed_name,
        "image": data_url(await store.get(row.file_key)),
        "created_at": row.created_at.isoformat(),
    }


async def _readable(image: SignatureImage) -> None:
    try:
        await asyncio.to_thread(image_size, image.png)
    except UnreadableImage as error:
        raise Invalid("the signature image could not be read") from error


async def _checked(model: ImageModel, image: SignatureImage) -> SignatureVerdict:
    try:
        verdict = await check_signature_image(model, image.png)
    except ModelError as error:
        logger.warning("the signature check did not run (%s)", type(error).__name__)
        raise Unavailable(CHECK_UNAVAILABLE) from error
    if verdict.refusal is not None:
        raise Invalid(verdict.refusal)
    return verdict
