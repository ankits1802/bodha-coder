import re
import time

import pyotp
from cryptography.fernet import Fernet
from sqlalchemy import select, update

from app.core.config import get_settings
from app.core.db import SessionFactory
from app.models import RecoveryCode, User
from tests.builders import PASSWORD, accept_invite, create_hq_user, forget_last_code, practice_with_provider

HQ = "hq@bodha.example.com"
RECOVERY_CODE = re.compile(r"^[abcdefghjkmnpqrstuvwxyz23456789]{4}(-[abcdefghjkmnpqrstuvwxyz23456789]{4}){3}$")


async def login(harness, email: str = HQ) -> dict:
    response = await harness.client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return response.json()


async def set_up_two_step(harness, email: str = HQ) -> tuple[str, str, list[str]]:
    challenge = await login(harness, email)
    assert challenge["mfa"] == "setup"
    secret = (await harness.client.post("/api/auth/mfa/setup", json={"mfa_token": challenge["mfa_token"]})).json()[
        "secret"
    ]
    code = pyotp.TOTP(secret).now()
    verified = await harness.client.post(
        "/api/auth/mfa/verify", json={"mfa_token": challenge["mfa_token"], "code": code}
    )
    assert verified.status_code == 200, verified.text
    return secret, code, verified.json()["recovery_codes"]


async def recover(harness, recovery_code: str, email: str = HQ):
    challenge = await login(harness, email)
    assert challenge["mfa"] == "verify"
    return await harness.client.post(
        "/api/auth/mfa/recover", json={"mfa_token": challenge["mfa_token"], "recovery_code": recovery_code}
    )


async def stored_user(email: str) -> User:
    async with SessionFactory() as db:
        return await db.scalar(select(User).where(User.email == email))


async def stored_code_hashes(email: str) -> list[str]:
    user = await stored_user(email)
    async with SessionFactory() as db:
        return list(await db.scalars(select(RecoveryCode.code_hash).where(RecoveryCode.user_id == user.id)))


async def unused_code_count(email: str) -> int:
    user = await stored_user(email)
    async with SessionFactory() as db:
        unused = select(RecoveryCode.id).where(RecoveryCode.user_id == user.id, RecoveryCode.used_at.is_(None))
        return len((await db.scalars(unused)).all())


def bearer(body: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {body['access_token']}"}


async def test_setting_up_two_step_returns_ten_codes_stored_only_as_hashes(harness):
    await create_hq_user()
    _, _, codes = await set_up_two_step(harness)
    assert len(codes) == len(set(codes)) == 10
    assert all(RECOVERY_CODE.match(code) for code in codes)
    hashes = await stored_code_hashes(HQ)
    assert len(hashes) == 10
    assert not set(hashes) & {code.replace("-", "") for code in codes} and not set(hashes) & set(codes)


async def test_a_recovery_code_works_once_in_place_of_the_six_digits(harness):
    await create_hq_user()
    _, _, codes = await set_up_two_step(harness)
    first = await recover(harness, codes[0])
    assert first.status_code == 200 and "access_token" in first.json()
    assert (await recover(harness, codes[0])).status_code == 401
    typed = await recover(harness, codes[1].replace("-", "").upper())
    assert typed.status_code == 200
    status = await harness.client.get("/api/auth/recovery-codes", headers=bearer(typed.json()))
    assert status.json() == {"enabled": True, "remaining": 8}


async def test_new_recovery_codes_need_a_valid_current_code(harness):
    await create_hq_user()
    secret, _, old_codes = await set_up_two_step(harness)
    headers = bearer((await recover(harness, old_codes[0])).json())
    wrong = pyotp.TOTP(secret).at(time.time() + 600)
    refused = await harness.client.post("/api/auth/recovery-codes", headers=headers, json={"code": wrong})
    assert refused.status_code == 422
    await forget_last_code(HQ)
    valid = pyotp.TOTP(secret).now()
    made = await harness.client.post("/api/auth/recovery-codes", headers=headers, json={"code": valid})
    assert made.status_code == 200
    new_codes = made.json()["codes"]
    assert len(new_codes) == 10 and not set(new_codes) & set(old_codes)
    replayed = await harness.client.post("/api/auth/recovery-codes", headers=headers, json={"code": valid})
    assert replayed.status_code == 422
    assert (await recover(harness, old_codes[1])).status_code == 401
    assert (await recover(harness, new_codes[0])).status_code == 200


async def test_a_six_digit_code_is_accepted_only_once(harness):
    await create_hq_user()
    secret, used_code, _ = await set_up_two_step(harness)
    challenge = await login(harness)
    replay = {"mfa_token": challenge["mfa_token"], "code": used_code}
    assert (await harness.client.post("/api/auth/mfa/verify", json=replay)).status_code == 401
    newer = {"mfa_token": challenge["mfa_token"], "code": pyotp.TOTP(secret).at(time.time() + 30)}
    assert (await harness.client.post("/api/auth/mfa/verify", json=newer)).status_code == 200


async def test_two_step_secrets_are_encrypted_at_rest(harness):
    await create_hq_user()
    secret, _, _ = await set_up_two_step(harness)
    stored = (await stored_user(HQ)).mfa_secret
    assert stored.startswith("v1:") and secret not in stored
    assert Fernet(get_settings().mfa_encryption_key).decrypt(stored.removeprefix("v1:").encode()).decode() == secret


async def test_a_legacy_plain_secret_is_accepted_and_then_encrypted(harness):
    await create_hq_user()
    secret = pyotp.random_base32()
    async with SessionFactory() as db:
        await db.execute(update(User).where(User.email == HQ).values(mfa_secret=secret, mfa_enabled=True))
        await db.commit()
    challenge = await login(harness)
    assert challenge["mfa"] == "verify"
    code = pyotp.TOTP(secret).now()
    verified = await harness.client.post(
        "/api/auth/mfa/verify", json={"mfa_token": challenge["mfa_token"], "code": code}
    )
    assert verified.status_code == 200
    assert (await stored_user(HQ)).mfa_secret.startswith("v1:")


async def test_an_admin_two_step_reset_also_clears_recovery_codes(harness):
    practice = await practice_with_provider(harness)
    email = "rita@lakeside.example.com"
    invited = await harness.client.post(
        "/api/team", headers=practice.admin, json={"name": "Rita Moss", "email": email, "role": "compliance"}
    )
    await accept_invite(harness)
    await set_up_two_step(harness, email)
    assert len(await stored_code_hashes(email)) == 10
    reset = await harness.client.post(f"/api/team/{invited.json()['id']}/reset-mfa", headers=practice.admin)
    assert reset.status_code == 204
    assert len(await stored_code_hashes(email)) == 10
    assert await unused_code_count(email) == 0
    assert (await login(harness, email))["mfa"] == "setup"
