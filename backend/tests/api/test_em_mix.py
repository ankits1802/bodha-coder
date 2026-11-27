from __future__ import annotations

import gzip
import hashlib
import json
import math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.api.routes.defensibility import em_benchmark_data
from app.codes.em_benchmarks import load_em_benchmarks
from app.main import app
from tests.batches import NoteFile, add_provider, upload_batch
from tests.builders import practice_with_provider
from tests.fakes import NOTE_TEXT, text_pdf

FIXTURE_ROWS = (
    ("INTERNAL MEDICINE", "office_established", "99212", "50"),
    ("INTERNAL MEDICINE", "office_established", "99213", "300"),
    ("INTERNAL MEDICINE", "office_established", "99214", "550"),
    ("INTERNAL MEDICINE", "office_established", "99215", "100"),
)
BILLED_LEVELS = ["99213"] * 5 + ["99214"] * 20 + ["99215"] * 15


@pytest.fixture
def tiny_benchmark(tmp_path):
    text = "specialty\tfamily\tcode\tservices\n" + "".join("\t".join(row) + "\n" for row in FIXTURE_ROWS)
    artefact = gzip.compress(text.encode("utf-8"), mtime=0)
    (tmp_path / "em_specialty_2025.tsv.gz").write_bytes(artefact)
    manifest = {
        "calendarYear": "2025",
        "sourceUrl": "https://www.cms.gov/example.xlsx",
        "artefact": "em_specialty_2025.tsv.gz",
        "artefactSha256": hashlib.sha256(artefact).hexdigest(),
        "rows": 4,
        "specialties": 1,
    }
    (tmp_path / "em_specialty_2025.meta.json").write_text(json.dumps(manifest), encoding="utf-8")
    benchmarks = load_em_benchmarks("2025", data_dir=tmp_path)
    app.dependency_overrides[em_benchmark_data] = lambda: benchmarks
    yield benchmarks
    app.dependency_overrides.pop(em_benchmark_data, None)


def _files(prefix: str, codes: list[str]) -> list[NoteFile]:
    return [
        NoteFile(f"{prefix} {index}.pdf", text_pdf(f"{NOTE_TEXT} {prefix} {index}"), code)
        for index, code in enumerate(codes)
    ]


async def _practice_with_visits(harness):
    practice = await practice_with_provider(harness)
    seen = datetime.now(ZoneInfo("America/Chicago")).date() - timedelta(days=2)
    await upload_batch(harness, practice, practice.provider_id, seen, _files("recent", [*BILLED_LEVELS, "99285"]))
    await upload_batch(harness, practice, practice.provider_id, seen - timedelta(days=40), _files("old", ["99215"]))
    other = await add_provider(harness, practice, name="Omar Haddad", specialty="Aerospace medicine")
    await upload_batch(harness, practice, other, seen, _files("other", ["99213"]))
    return practice


async def test_a_provider_is_compared_with_the_cms_mix_for_their_specialty(harness, tiny_benchmark):
    practice = await _practice_with_visits(harness)

    response = await harness.client.get("/api/insights/em-mix?days=30", headers=practice.admin)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["benchmark"]["year"] == "2025"
    varga, haddad = body["providers"]
    assert (varga["name"], varga["cms_specialty"], varga["visits"]) == ("Elena Varga", "INTERNAL MEDICINE", 40)
    [family] = varga["families"]
    assert family["family"] == "office_established"
    assert [(row["code"], row["count"], row["benchmark"], row["direction"]) for row in family["levels"]] == [
        ("99211", 0, 0.0, None),
        ("99212", 0, 0.05, None),
        ("99213", 5, 0.3, "below"),
        ("99214", 20, 0.55, None),
        ("99215", 15, 0.1, "above"),
    ]
    assert family["p_value"] == pytest.approx(math.erfc(math.sqrt((81 / 14 + 81 / 26) / 2)))
    assert (family["outlier"], family["reasons"], family["lean"]) == (True, ["points", "chi_square"], "higher")
    assert (haddad["name"], haddad["cms_specialty"], haddad["visits"]) == ("Omar Haddad", None, 1)
    assert (haddad["families"][0]["has_benchmark"], haddad["families"][0]["outlier"]) == (False, False)


async def test_only_the_listed_periods_are_accepted(harness, tiny_benchmark):
    practice = await practice_with_provider(harness)

    assert (await harness.client.get("/api/insights/em-mix?days=5", headers=practice.admin)).status_code == 422
    assert (await harness.client.get("/api/insights/em-mix?days=90", headers=practice.admin)).status_code == 200
