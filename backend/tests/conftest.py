from __future__ import annotations

import pytest

from app.codes.icd import load_catalog


@pytest.fixture(scope="session")
def icd_catalog():
    return load_catalog()
