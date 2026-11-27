import base64
import hashlib
import hmac

import pytest

from app.core.role_password import SCRAM_ITERATIONS, scram_verifier


def test_the_verifier_is_a_postgres_scram_sha_256_secret_for_the_password():
    verifier = scram_verifier("Runtime123")
    method, rest = verifier.split("$", 1)
    iterations, salt, keys = rest.split(":", 1)[0], rest.split(":", 1)[1].split("$")[0], rest.split("$")[1]
    stored_text, server_text = keys.split(":")
    salted = hashlib.pbkdf2_hmac("sha256", b"Runtime123", base64.b64decode(salt), SCRAM_ITERATIONS)
    assert (method, int(iterations)) == ("SCRAM-SHA-256", SCRAM_ITERATIONS)
    assert (
        base64.b64decode(stored_text)
        == hashlib.sha256(hmac.new(salted, b"Client Key", hashlib.sha256).digest()).digest()
    )
    assert base64.b64decode(server_text) == hmac.new(salted, b"Server Key", hashlib.sha256).digest()


def test_each_verifier_has_its_own_salt():
    assert scram_verifier("Runtime123") != scram_verifier("Runtime123")


def test_a_password_that_could_break_the_statement_is_refused():
    with pytest.raises(ValueError, match="letters and digits"):
        scram_verifier("bad'; DROP ROLE x; --")
