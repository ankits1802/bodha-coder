from datetime import date

import pytest

from app.codes.billing_codes import FilenameFacts
from app.services.upload_matching import (
    CHECK_BELOW,
    ProviderRef,
    match_file,
    patient_in,
    place_in,
    provider_in,
    service_date_in,
)

TODAY = date(2026, 11, 28)
VARGA = ProviderRef("p-varga", "Elena Varga", "1234567893", "11")
HADDAD = ProviderRef("p-haddad", "Omar Haddad", None, "31")
ELENA_RUIZ = ProviderRef("p-ruiz", "Elena Ruiz", None, None)
PROVIDERS = [VARGA, HADDAD]
PLACES = {
    "11": "Office",
    "31": "Skilled nursing facility",
    "32": "Nursing facility",
    "02": "Telehealth, other than home",
}
NO_FACTS = FilenameFacts(None, None, None)


def test_an_npi_on_the_page_names_the_provider_with_the_highest_confidence():
    found = provider_in("Signed by Dr. E. V. NPI: 1234567893", PROVIDERS)
    assert (found.value, found.confidence) == ("p-varga", 0.99)


def test_an_npi_with_a_wrong_check_digit_is_not_trusted():
    assert provider_in("NPI 1234567890", PROVIDERS).value is None


def test_a_full_name_matches_and_a_surname_alone_needs_a_check():
    full = provider_in("Rendering provider: Omar Haddad, DO", PROVIDERS)
    surname = provider_in("Seen by Dr. Haddad today", PROVIDERS)
    assert (full.value, full.confidence) == ("p-haddad", 0.9)
    assert (surname.value, surname.confidence) == ("p-haddad", 0.6)
    assert surname.confidence < CHECK_BELOW


def test_two_providers_whose_names_both_appear_are_not_trusted():
    found = provider_in("Elena Varga and Omar Haddad co-signed", PROVIDERS)
    assert found.confidence == 0.6


def test_a_shared_first_name_alone_names_nobody():
    assert provider_in("Elena called back", [VARGA, ELENA_RUIZ]).value is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Date of service: 11/24/2026", date(2026, 11, 24)),
        ("DOS 2026-11-23", date(2026, 11, 23)),
        ("Visit date: November 22, 2026", date(2026, 11, 22)),
        ("Encounter date: 21 Nov 2026", date(2026, 11, 21)),
        ("Service date: 11/20/26", date(2026, 11, 20)),
    ],
)
def test_a_labelled_date_of_service_is_read_in_the_usual_formats(text, expected):
    found = service_date_in(text, None, today=TODAY)
    assert (found.value, found.confidence) == (expected, 0.95)


def test_the_page_and_the_file_name_agreeing_raise_confidence_and_disagreeing_ask_for_a_check():
    agree = service_date_in("DOS: 11/24/2026", date(2026, 11, 24), today=TODAY)
    disagree = service_date_in("DOS: 11/24/2026", date(2026, 11, 21), today=TODAY)
    assert (agree.value, agree.confidence) == (date(2026, 11, 24), 0.99)
    assert (disagree.value, disagree.confidence) == (date(2026, 11, 24), 0.6)


def test_a_birth_date_and_a_future_date_are_never_the_date_of_service():
    text = "DOB: 03/14/1959 Next visit 12/30/2026 Seen 11/19/2026"
    found = service_date_in(text, None, today=TODAY)
    assert (found.value, found.confidence) == (date(2026, 11, 19), 0.5)


def test_without_any_date_the_file_name_date_is_used():
    found = service_date_in("Follow up visit", date(2026, 11, 18), today=TODAY)
    assert (found.value, found.confidence) == (date(2026, 11, 18), 0.85)


def test_a_labelled_place_wins_over_the_providers_usual_place():
    by_code = place_in("POS: 31", PLACES, VARGA)
    by_name = place_in("Place of service: Skilled nursing facility", PLACES, VARGA)
    usual = place_in("Office visit", PLACES, VARGA)
    assert (by_code.value, by_code.confidence) == ("31", 0.95)
    assert (by_name.value, by_name.confidence) == ("31", 0.95)
    assert (usual.value, usual.confidence) == ("11", 0.8)


def test_an_inactive_or_unknown_place_is_not_chosen():
    assert place_in("POS: 99", PLACES, ELENA_RUIZ).value is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Patient: REYES, MARISOL DOB: 03/14/1959", "Marisol Reyes"),
        ("Patient name: Jonah Pike Age: 41", "Jonah Pike"),
        ("Patient: anna gray MRN 5512", "Anna Gray"),
    ],
)
def test_the_patient_name_is_read_after_its_label_and_stops_at_the_next_label(text, expected):
    found = patient_in(text, None)
    assert (found.value, found.confidence) == (expected, 0.9)


def test_without_a_labelled_patient_the_file_name_patient_is_used():
    found = patient_in("Patient with diabetes", "Reyes Marisol")
    assert (found.value, found.confidence) == ("Reyes Marisol", 0.85)


def test_a_whole_page_is_matched_and_its_confidence_is_the_weakest_of_provider_date_and_place():
    text = "Patient: Jonah Pike\nDate of service: 11/24/2026\nSeen by Dr. Haddad"
    found = match_file(text, NO_FACTS, PROVIDERS, PLACES, today=TODAY)
    assert (found.provider.value, found.service_date.value, found.place.value, found.patient.value) == (
        "p-haddad",
        date(2026, 11, 24),
        "31",
        "Jonah Pike",
    )
    assert (found.confidence, found.needs_check) == (0.6, True)
