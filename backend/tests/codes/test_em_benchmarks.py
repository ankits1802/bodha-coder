from __future__ import annotations

import json
import shutil

import pytest

from app.codes.em_benchmarks import (
    DATA_DIR,
    EmBenchmarkCorrupt,
    artefact_name,
    default_em_benchmarks,
    load_em_benchmarks,
    manifest_name,
)

INTERNAL_MEDICINE_ESTABLISHED = {
    "99211": 238334,
    "99212": 484731,
    "99213": 6427984.5,
    "99214": 15027208,
    "99215": 1802410,
}


def test_the_vendored_cms_2025_file_gives_internal_medicine_office_shares():
    benchmarks = default_em_benchmarks()
    total = sum(INTERNAL_MEDICINE_ESTABLISHED.values())

    shares = benchmarks.shares("INTERNAL MEDICINE", "office_established")

    assert benchmarks.year == "2025"
    assert shares is not None
    for code, services in INTERNAL_MEDICINE_ESTABLISHED.items():
        assert shares[code] == pytest.approx(services / total)
    assert shares["99214"] == pytest.approx(0.6266, abs=1e-4)


@pytest.mark.parametrize(
    ("text", "specialty"),
    [
        ("Internal medicine", "INTERNAL MEDICINE"),
        ("  family   medicine ", "FAMILY PRACTICE"),
        ("Allergy & Immunology", "ALLERGY/IMMUNOLOGY"),
        ("Nurse practitioner", "NURSE PRACTITIONER"),
        ("Aerospace medicine", None),
        (None, None),
    ],
)
def test_provider_specialties_map_to_the_cms_list_or_to_nothing(text, specialty):
    assert default_em_benchmarks().specialty_for(text) == specialty


def test_a_family_outside_the_benchmark_has_no_shares():
    with pytest.raises(KeyError, match="emergency"):
        default_em_benchmarks().shares("INTERNAL MEDICINE", "emergency")


def test_a_file_that_does_not_match_its_manifest_is_refused(tmp_path):
    shutil.copy(DATA_DIR / artefact_name("2025"), tmp_path / artefact_name("2025"))
    manifest = json.loads((DATA_DIR / manifest_name("2025")).read_text(encoding="utf-8"))
    (tmp_path / manifest_name("2025")).write_text(
        json.dumps({**manifest, "rows": manifest["rows"] + 1}), encoding="utf-8"
    )
    with pytest.raises(EmBenchmarkCorrupt, match="rows"):
        load_em_benchmarks("2025", data_dir=tmp_path)
    tampered = {**manifest, "artefactSha256": "0" * 64}
    (tmp_path / manifest_name("2025")).write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(EmBenchmarkCorrupt, match="checksum"):
        load_em_benchmarks("2025", data_dir=tmp_path)
