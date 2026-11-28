from __future__ import annotations

import pytest

from app.codes.icd import load_catalog
from tests.saml_idp import IdpKeys, idp_keys


@pytest.fixture(scope="session")
def icd_catalog():
    return load_catalog()


@pytest.fixture(scope="session")
def idp() -> IdpKeys:
    return idp_keys()


@pytest.fixture(scope="session")
def next_idp() -> IdpKeys:
    return idp_keys(common_name="next.idp.lakeside.example.com")


@pytest.fixture(scope="session")
def stranger_idp() -> IdpKeys:
    return idp_keys(common_name="idp.elsewhere.example.com")


@pytest.fixture(scope="session")
def expired_idp() -> IdpKeys:
    return idp_keys(common_name="old.idp.lakeside.example.com", expired=True)
