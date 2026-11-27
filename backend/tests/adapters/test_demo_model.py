from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.adapters.demo_answers import DemoCodeBook
from app.adapters.demo_model import DEMO_MODEL, DemoModelClient, demo_outcome
from app.adapters.gemini import GeminiClient
from app.ai.contracts import BilledCode, ReviewInputs, ReviewReport
from app.ai.errors import ModelRequestRejected
from app.ai.prompts.context import ADDENDUM_HEADING_PATTERN, labelled_addendum
from app.ai.review import review_note
from app.codes.billing_codes import Code
from app.codes.em import em_ladder
from app.core.config import Settings
from app.services.findings import build_findings
from app.services.routing import place
from app.worker import model_client
from tests.fakes import NOTE_TEXT

SERVICE_DATE = date(2026, 11, 25)
BILLED = (Code("99214", "CPT"), Code("E11.65", "ICD-10"), Code("I10", "ICD-10"))
SECTIONS = frozenset({"em", "diagnoses", "code_review", "cdi", "audit"})
REYES = (
    "Patient: Marisol Reyes   DOB: 03/14/1959   Sex: Female   Date of service: 11/25/2026\n"
    "67-year-old woman with type 2 diabetes and hypertension.\n"
    "Assessment and plan:\n"
    "1. Type 2 diabetes with hyperglycemia. Increase metformin.\n"
    "2. Hypertension above goal. Add amlodipine.\n"
    "Electronically signed: Elena Varga, MD"
)


def variant(weeks: int) -> str:
    return f"{NOTE_TEXT} Return in {weeks} weeks."


def inputs(note_text: str | None, *, pdf: bytes | None = None) -> ReviewInputs:
    return ReviewInputs(
        sections=SECTIONS,
        setting="office",
        place_of_service="11",
        visit_type="Established patient",
        service_date=SERVICE_DATE,
        billed_codes=tuple(BilledCode(code.code, code.type) for code in BILLED),
        note_text=note_text,
        pdf=pdf,
    )


@pytest.fixture(scope="module")
def client(icd_catalog) -> DemoModelClient:
    return DemoModelClient(DemoCodeBook(em_ladder=em_ladder, icd_name=icd_catalog.describe))


async def reviewed(client: DemoModelClient, review: ReviewInputs) -> ReviewReport:
    outcome = await review_note(client, review)
    assert outcome.failed_sections == frozenset()
    assert [reply.model for reply in outcome.replies] == [DEMO_MODEL]
    return outcome.report


def test_the_outcome_is_the_first_sha256_byte_modulo_five():
    assert demo_outcome(b"") == "billed_too_low"
    assert demo_outcome(b"abc") == "billed_too_high"
    assert demo_outcome(b"The quick brown fox jumps over the lazy dog") == "matches"
    assert demo_outcome(b"The quick brown fox jumps over the lazy dog.") == "audit_risk"


@pytest.mark.parametrize(
    ("weeks", "expected"),
    [
        (1, ("approve", "matches", "Matches the note", "keep", "99214")),
        (3, ("coder", "code_changes", "Billed too high", "lower", "99213")),
        (2, ("coder", "code_changes", "Billed too low", "raise", "99215")),
        (14, ("provider", "questions", "1 question to send", "keep", "99214")),
        (8, ("compliance", "audit_risk", "High audit risk", "keep", "99214")),
    ],
)
async def test_each_outcome_reaches_its_lane(client, icd_catalog, weeks, expected):
    report = await reviewed(client, inputs(variant(weeks)))
    findings = build_findings(report, BILLED, icd_catalog.for_service_date(SERVICE_DATE))
    placement = place(findings, flagged=False, cleared=False, awaiting_provider=False, billed_diagnoses=True)
    em = next(item for item in findings if item.kind == "em")
    assert (placement.lane, placement.reason, placement.headline, em.action, em.code_after) == expected


async def test_diagnoses_are_named_from_the_release_for_the_date_of_service(client):
    report = await reviewed(client, inputs(variant(1)))
    assert [(item.icd10, item.name, item.status) for item in report.diagnoses or []] == [
        ("E11.65", "Type 2 diabetes mellitus with hyperglycemia", "supported"),
        ("I10", "Essential (primary) hypertension", "supported"),
    ]


async def test_a_signed_addendum_answers_the_query(client, icd_catalog):
    answered = f"{variant(14)}\n\n{labelled_addendum(2, 'Diabetes is uncontrolled.')}"
    assert ADDENDUM_HEADING_PATTERN.search(answered) is not None
    report = await reviewed(client, inputs(answered))
    findings = build_findings(report, BILLED, icd_catalog.for_service_date(SERVICE_DATE))
    placement = place(findings, flagged=False, cleared=False, awaiting_provider=False, billed_diagnoses=True)
    assert (placement.lane, placement.reason) == ("approve", "matches")


async def test_patient_facts_and_quotes_come_from_the_note(client, icd_catalog):
    report = await reviewed(client, inputs(REYES))
    assert report.patient.model_dump() == {
        "name": "Marisol Reyes",
        "age": 67,
        "sex": "Female",
        "birth_date": date(1959, 3, 14),
    }
    findings = build_findings(report, BILLED, icd_catalog.for_service_date(SERVICE_DATE))
    quotes = {finding.key: finding.evidence for finding in findings}
    assert quotes["dx:I10"] == ("2. Hypertension above goal. Add amlodipine.",)
    assert quotes["dx:E11.65"] == ("1. Type 2 diabetes with hyperglycemia. Increase metformin.",)


async def test_a_scan_is_read_from_the_pdf_checksum(client):
    report = await reviewed(client, inputs(None, pdf=b"abc"))
    assert report.extracted_text == "Scanned visit note."
    assert report.em is not None and report.em.code == "99213"


async def test_a_call_without_a_schema_is_refused(client):
    with pytest.raises(ModelRequestRejected):
        await client.generate("prompt", schema=None)


def test_settings_refuse_the_demo_model_in_production():
    required = {"secret_key": "s" * 32, "s3_bucket": "bucket", "_env_file": None}
    with pytest.raises(ValidationError, match="APP_ENVIRONMENT is production"):
        Settings(gemini_backend="demo", **required)
    with pytest.raises(ValidationError, match="APP_ENVIRONMENT is production"):
        Settings(gemini_backend="demo", app_environment="production", **required)
    assert Settings(gemini_backend="demo", app_environment="development", **required).gemini_backend == "demo"
    assert Settings(gemini_backend="demo", app_environment="staging", **required).gemini_backend == "demo"


def test_the_worker_builds_the_client_its_settings_name(icd_catalog):
    demo = Settings.model_construct(gemini_backend="demo", app_environment="development")
    developer = Settings.model_construct(
        gemini_backend="developer", gemini_api_key="test-key", gemini_model="gemini-test", gemini_timeout_seconds=5
    )
    assert isinstance(model_client(demo, icd_catalog), DemoModelClient)
    assert isinstance(model_client(developer, icd_catalog), GeminiClient)
