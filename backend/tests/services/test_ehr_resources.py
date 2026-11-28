from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

from app.codes.clinical_notes import loinc_codes_for
from app.services.ehr_resources import (
    DocumentReference,
    Encounter,
    Practitioner,
    chosen_attachment,
    documents_in,
    is_final,
    is_wanted,
    npi_of,
    place_for,
    practitioner_references,
    reference_id,
    service_day,
)
from tests.ehr_fakes import attachment, document, encounter, practitioner

CHICAGO = ZoneInfo("America/Chicago")
POS = "https://www.cms.gov/Medicare/Coding/place-of-service-codes/Place_of_Service_Code_Set"
OFFICE_AND_MORE = frozenset({"11", "12", "21", "22", "23", "31", "32"})


def _document(**changes) -> DocumentReference:
    return DocumentReference.model_validate(document("d1", **changes))


def _encounter(start: str = "2026-11-20T09:30:00-06:00", **changes) -> Encounter:
    return Encounter.model_validate(encounter("e1", start, **changes))


def test_the_date_of_service_is_the_encounter_start_in_the_practice_time_zone():
    late_evening = _encounter("2026-11-20T02:30:00Z")
    assert service_day(late_evening, _document(), CHICAGO) == date(2026, 11, 19)
    assert service_day(_encounter("2026-11-20"), _document(), CHICAGO) == date(2026, 11, 20)


def test_without_an_encounter_the_documented_period_gives_the_date():
    found = document("d1", encounter=None)
    found["context"] = {"period": {"start": "2026-11-18T14:00:00-05:00"}}
    assert service_day(None, DocumentReference.model_validate(found), CHICAGO) == date(2026, 11, 18)
    assert service_day(None, _document(encounter=None), CHICAGO) is None
    assert service_day(_encounter("2026-11"), _document(), CHICAGO) is None


def test_an_r3_style_single_encounter_reference_is_read():
    found = document("d1", encounter=None)
    found["context"] = {"encounter": {"reference": "Encounter/e9"}}
    parsed = DocumentReference.model_validate(found)
    assert parsed.context is not None
    assert reference_id(parsed.context.encounter[0], "Encounter") == "e9"


def test_the_place_comes_from_a_coded_place_then_the_class_then_the_provider():
    coded = _encounter(type=[{"coding": [{"system": POS, "code": "31"}]}], class_code="IMP")
    assert place_for(coded, "11", OFFICE_AND_MORE) == "31"
    assert place_for(_encounter(class_code="EMER"), "11", OFFICE_AND_MORE) == "23"
    assert place_for(_encounter(class_code="AMB"), "22", OFFICE_AND_MORE) == "22"
    assert place_for(_encounter(class_code="AMB"), None, OFFICE_AND_MORE) == "11"
    assert place_for(None, None, OFFICE_AND_MORE) is None
    assert place_for(_encounter(class_code="EMER"), None, frozenset({"11"})) is None


def test_the_note_author_comes_before_the_encounter_performers():
    performers = _encounter(
        participant=[
            {"type": [{"coding": [{"code": "ATND"}]}], "individual": {"reference": "Practitioner/attending"}},
            {"type": [{"coding": [{"code": "PPRF"}]}], "individual": {"reference": "Practitioner/primary"}},
        ]
    )
    found = practitioner_references(_document(author="Practitioner/author"), performers)
    assert found == ["Practitioner/author", "Practitioner/primary", "Practitioner/attending"]
    assert practitioner_references(_document(author="PractitionerRole/r1"), None) == []


def test_only_a_valid_npi_under_the_npi_system_counts():
    assert npi_of(Practitioner.model_validate(practitioner("p1", "1234567893"))) == "1234567893"
    assert npi_of(Practitioner.model_validate(practitioner("p1", "1234567890"))) is None
    other_system = practitioner("p1", "1234567893")
    other_system["identifier"][0]["system"] = "urn:oid:1.2.3"
    assert npi_of(Practitioner.model_validate(other_system)) is None


def test_only_current_notes_of_the_chosen_types_are_wanted_and_only_final_ones_are_taken():
    progress = loinc_codes_for(["progress"])
    assert is_wanted(_document(), progress)
    assert not is_wanted(_document(code="11488-4"), progress)
    superseded = document("d1")
    superseded["status"] = "superseded"
    assert not is_wanted(DocumentReference.model_validate(superseded), progress)
    assert is_final(_document()) and not is_final(_document(doc_status="preliminary"))
    assert not is_final(_document(doc_status=None))


def test_a_pdf_is_chosen_over_html_and_unreadable_formats_are_not_chosen():
    both = _document(content=[attachment("Binary/h", "text/html"), attachment("Binary/p", "application/pdf")])
    assert chosen_attachment(both).url == "Binary/p"
    assert chosen_attachment(_document(content=[attachment("Binary/r", "text/rtf")])) is None
    html = _document(content=[attachment("Binary/h", "text/html; charset=utf-8")])
    assert chosen_attachment(html).media_type == "text/html"


def test_a_bundle_yields_only_document_references_and_marks_unreadable_ones():
    bundle = {
        "entry": [
            {"resource": document("d1")},
            {"resource": {"resourceType": "OperationOutcome"}},
            {"resource": {"resourceType": "DocumentReference"}},
        ]
    }
    found = list(documents_in(bundle))
    assert [item.id if item else None for item in found] == ["d1", None]
