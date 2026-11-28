import pytest
from cryptography.fernet import Fernet

from app.core.errors import Unavailable
from app.core.sealed_text import TextSeal

OLD_KEY = Fernet.generate_key().decode()
NEW_KEY = Fernet.generate_key().decode()
NOT_SET_UP = "sealing is not set up"
UNREADABLE = "this cannot be read"


def _seal(keys: str | None) -> TextSeal:
    return TextSeal(keys, not_set_up=NOT_SET_UP, unreadable=UNREADABLE)


def test_sealed_text_opens_with_the_same_key_and_never_shows_the_value():
    sealed = _seal(OLD_KEY).seal("-----BEGIN PRIVATE KEY-----")
    assert sealed.startswith("v1:") and "PRIVATE KEY" not in sealed
    assert _seal(OLD_KEY).open(sealed) == "-----BEGIN PRIVATE KEY-----"


def test_a_rotated_key_list_opens_old_text_and_marks_it_as_not_current():
    sealed = _seal(OLD_KEY).seal("secret")
    rotated = _seal(f"{NEW_KEY}, {OLD_KEY}")
    assert rotated.open(sealed) == "secret"
    assert rotated.is_current(sealed) is False
    assert rotated.is_current(rotated.seal("secret")) is True


def test_without_keys_or_with_the_wrong_key_nothing_opens():
    sealed = _seal(OLD_KEY).seal("secret")
    assert _seal(None).ready is False
    with pytest.raises(Unavailable, match=NOT_SET_UP):
        _seal(None).seal("secret")
    with pytest.raises(Unavailable, match=NOT_SET_UP):
        _seal("not-a-fernet-key").open(sealed)
    with pytest.raises(Unavailable, match=UNREADABLE):
        _seal(NEW_KEY).open(sealed)
    with pytest.raises(Unavailable, match=UNREADABLE):
        _seal(NEW_KEY).open("plain text")
