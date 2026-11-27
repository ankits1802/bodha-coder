import pytest
from pydantic import ValidationError
from starlette.requests import Request

from app.core.config import Settings, get_settings
from app.core.realms import Site, account_space, public_host, realm_url, site_for

MAIN = "https://www.bodha.example.com"
ADMIN = "https://admin.bodha.example.com"


def settings(**values) -> Settings:
    base = {"secret_key": "test-only-secret-key-that-is-long-enough-000", "s3_bucket": "test-bucket", "app_url": MAIN}
    return Settings(_env_file=None, **{**base, **values})


def request(host: str, *, forwarded: str | None = None, peer: str = "127.0.0.1") -> Request:
    headers = [(b"host", host.encode())]
    if forwarded is not None:
        headers.append((b"x-forwarded-host", forwarded.encode()))
    return Request(
        {"type": "http", "method": "GET", "path": "/api/auth/me", "headers": headers, "client": (peer, 5000)}
    )


def test_without_an_admin_url_the_main_site_serves_both_realms_and_takes_sign_ups():
    for host in ("www.bodha.example.com", "admin.bodha.example.com"):
        assert site_for(host, settings()) == Site(MAIN, ("hq", "practice"))
    assert site_for("www.bodha.example.com", settings()).takes_signups is True


def test_with_an_admin_url_only_the_admin_host_serves_hq_and_every_other_host_serves_practices():
    chosen = settings(admin_url=ADMIN)
    assert site_for("admin.bodha.example.com", chosen) == Site(ADMIN, ("hq",))
    assert site_for("www.bodha.example.com", chosen) == Site(MAIN, ("practice",))
    assert site_for("admin.bodha.example.com:8443", chosen) == Site(MAIN, ("practice",))
    assert site_for("admin.bodha.example.com", chosen).takes_signups is False


@pytest.mark.parametrize(
    ("host", "forwarded", "peer", "allowed", "expected"),
    [
        ("admin.bodha.example.com", "www.bodha.example.com", "10.0.3.7", "10.0.0.0/16", "admin.bodha.example.com"),
        ("localhost:8000", "admin.localhost:3000", "127.0.0.1", "127.0.0.1", "admin.localhost:3000"),
        ("api:8000", "Admin.Bodha.example.com", "172.18.0.4", "*", "admin.bodha.example.com"),
        ("api:8000", "admin.bodha.example.com", "10.0.3.7", "10.0.0.0/16", "admin.bodha.example.com"),
        ("api:8000", "admin.bodha.example.com", "203.0.113.9", "10.0.0.0/16", "api:8000"),
        (
            "api:8000",
            "admin.bodha.example.com, www.bodha.example.com",
            "::1",
            "127.0.0.1, ::1",
            "admin.bodha.example.com",
        ),
        ("api:8000", None, "127.0.0.1", "127.0.0.1", "api:8000"),
    ],
)
def test_the_public_host_is_the_host_header_unless_a_trusted_proxy_forwarded_another(
    host, forwarded, peer, allowed, expected
):
    chosen = settings(admin_url=ADMIN, forwarded_allow_ips=allowed)
    assert public_host(request(host, forwarded=forwarded, peer=peer), chosen) == expected


@pytest.mark.parametrize(
    "value", ["admin.bodha.example.com", "https://admin.bodha.example.com/hq", "ftp://admin.bodha.example.com"]
)
def test_admin_url_must_be_a_bare_web_address(value):
    with pytest.raises(ValidationError, match="ADMIN_URL must be a web address"):
        settings(admin_url=value)


def test_admin_url_must_name_another_host_than_app_url():
    with pytest.raises(ValidationError, match="different host from APP_URL"):
        settings(admin_url="https://WWW.bodha.example.com/")


def test_a_blank_admin_url_keeps_one_host_and_a_trailing_slash_is_dropped():
    assert settings(admin_url="  ").admin_url == ""
    assert settings(admin_url=f"{ADMIN}/").admin_url == ADMIN


def test_links_and_account_spaces_follow_the_admin_url(monkeypatch):
    monkeypatch.setattr(get_settings(), "admin_url", ADMIN)
    assert (realm_url("hq"), realm_url("practice")) == (ADMIN, get_settings().app_url)
    assert (account_space("hq"), account_space("practice")) == (("hq",), ("practice",))
    monkeypatch.setattr(get_settings(), "admin_url", "")
    assert realm_url("hq") == get_settings().app_url
    assert account_space("hq") == account_space("practice") == ("hq", "practice")
