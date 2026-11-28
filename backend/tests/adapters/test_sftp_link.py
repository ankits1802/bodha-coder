import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa

from app.adapters.sftp import LinkRefused, ParamikoLink, SftpTarget, check_private_key, host_key_fingerprint
from app.core.errors import Invalid

ABC_SHA256_BASE64 = "ungWv48Bz+pBQUDeXa4iI7ADYaOWF3qctBD/YfIAFa0"


def test_the_fingerprint_is_openssh_style_unpadded_base64_of_sha256():
    assert host_key_fingerprint(b"abc") == f"SHA256:{ABC_SHA256_BASE64}"


def test_openssh_and_pem_private_keys_are_read_and_anything_else_is_refused():
    modern = ed25519.Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.OpenSSH, serialization.NoEncryption()
    )
    legacy = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()
    )
    check_private_key(modern.decode())
    check_private_key(legacy.decode())
    with pytest.raises(Invalid):
        check_private_key("-----BEGIN OPENSSH PRIVATE KEY-----\nnot a key\n-----END OPENSSH PRIVATE KEY-----")


@pytest.mark.parametrize("host", ["127.0.0.1", "10.1.2.3", "192.168.0.10", "169.254.169.254", "::1", "100.64.0.1"])
async def test_private_and_internal_addresses_are_never_dialled(host):
    link = ParamikoLink(timeout_seconds=5)
    with pytest.raises(Invalid, match="public internet addresses only"):
        await link.host_key(host, 22)
    target = SftpTarget(host, 22, "user", "pw", None, f"SHA256:{ABC_SHA256_BASE64}")
    with pytest.raises(Invalid):
        await link.upload(target, "/outbound", "claims.txt", b"ISA")


def test_a_link_refusal_is_a_service_unavailable_error():
    assert LinkRefused("the clearinghouse did not answer in time").status_code == 503
