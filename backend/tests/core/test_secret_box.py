import pytest
from cryptography.fernet import Fernet

from app.core.errors import Unavailable
from app.core.secret_box import SecretBox

OLD, NEW = Fernet.generate_key().decode(), Fernet.generate_key().decode()


class KeyMissing(Unavailable):
    pass


def _box(keys: str | None) -> SecretBox:
    return SecretBox("v1:", keys, KeyMissing, "no key here", "cannot read it")


def test_a_sealed_secret_opens_only_with_its_key_and_never_shows_the_plain_text():
    sealed = _box(OLD).seal("correct horse")

    assert sealed.startswith("v1:") and "correct horse" not in sealed
    assert Fernet(OLD).decrypt(sealed.removeprefix("v1:").encode()) == b"correct horse"
    assert _box(OLD).open(sealed) == "correct horse"
    with pytest.raises(KeyMissing, match="cannot read it"):
        _box(NEW).open(sealed)


def test_rotation_keeps_old_secrets_readable_and_marks_them_stale():
    sealed = _box(OLD).seal("pw")

    rotated = _box(f"{NEW}, {OLD}")
    assert rotated.open(sealed) == "pw"
    assert rotated.is_current(sealed) is False
    assert rotated.is_current(rotated.seal("pw")) is True


def test_no_key_or_a_bad_key_refuses_and_plain_values_are_never_opened():
    with pytest.raises(KeyMissing, match="no key here"):
        _box(None).seal("pw")
    with pytest.raises(KeyMissing, match="no key here"):
        _box("not-a-fernet-key").seal("pw")
    with pytest.raises(KeyMissing, match="cannot read it"):
        _box(OLD).open("pw")
    assert _box(OLD).is_current("pw") is False
