from cryptography.fernet import Fernet

from app.core.config import get_settings
from app.core.security import mfa_secret_is_current, open_mfa_secret, seal_mfa_secret

OLD_KEY = Fernet.generate_key().decode()
NEW_KEY = Fernet.generate_key().decode()


def test_a_secret_sealed_with_the_old_key_opens_after_rotation_and_reseals_with_the_new_one(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "mfa_encryption_key", OLD_KEY)
    sealed_with_old = seal_mfa_secret("JBSWY3DPEHPK3PXP")
    assert mfa_secret_is_current(sealed_with_old) is True

    monkeypatch.setattr(settings, "mfa_encryption_key", f"{NEW_KEY}, {OLD_KEY}")
    assert open_mfa_secret(sealed_with_old) == "JBSWY3DPEHPK3PXP"
    assert mfa_secret_is_current(sealed_with_old) is False
    resealed = seal_mfa_secret(open_mfa_secret(sealed_with_old))
    assert mfa_secret_is_current(resealed) is True

    monkeypatch.setattr(settings, "mfa_encryption_key", NEW_KEY)
    assert open_mfa_secret(resealed) == "JBSWY3DPEHPK3PXP"


def test_a_plain_legacy_secret_is_never_current():
    assert mfa_secret_is_current("JBSWY3DPEHPK3PXP") is False
