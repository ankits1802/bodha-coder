import pytest

from app.core.errors import Invalid
from app.services.email_domains import claimable_domain, domain_of, is_public_domain, normal_domain


def test_a_domain_is_written_in_lower_case_without_a_leading_at_or_trailing_dot():
    assert normal_domain("  @Lakeside-Clinic.Example.COM. ") == "lakeside-clinic.example.com"
    assert normal_domain("xn--bcher-kva.example") == "xn--bcher-kva.example"


@pytest.mark.parametrize("text", ["localhost", "example", "-bad.example.com", "bad_name.example.com", "1.2.3.4", "a.b"])
def test_text_that_is_not_a_domain_is_refused(text):
    with pytest.raises(Invalid):
        normal_domain(text)


@pytest.mark.parametrize(
    "domain", ["gmail.com", "googlemail.com", "outlook.com", "yahoo.com", "icloud.com", "proton.me"]
)
def test_public_email_services_cannot_be_claimed(domain):
    assert is_public_domain(domain)
    with pytest.raises(Invalid, match="public email services"):
        claimable_domain(domain.upper())


def test_a_subdomain_of_a_public_service_is_public_but_a_look_alike_is_not():
    assert is_public_domain("mail.yahoo.com")
    assert not is_public_domain("notgmail.com")
    assert claimable_domain("notgmail.com") == "notgmail.com"


def test_the_domain_of_an_email_is_the_part_after_the_last_at():
    assert domain_of("Dana.Fox@Lakeside.Example.com") == "lakeside.example.com"
    assert domain_of("odd@name@lakeside.example.com") == "lakeside.example.com"
    assert domain_of("no-at-sign") is None
