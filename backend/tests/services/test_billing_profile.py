import pytest

from app.core.errors import Invalid
from app.services.billing_profile import (
    BillingProfile,
    billing_profile,
    missing_from_profile,
    validated_practice_details,
)
from app.services.charge_schedule import parsed_charges

DETAILS = {
    "legal_name": "Lakeside Family Medicine",
    "tax_id": "12-3456789",
    "group_npi": "1245319599",
    "taxonomy_code": "207q00000x",
    "address": "123 Main St",
    "address_line_2": "",
    "city": "Springfield",
    "state": "il",
    "zip": "62701-1234",
    "phone": "(555) 555-1234",
    "billing_contact": "Dana Biller",
}


def test_valid_details_are_kept_with_the_state_and_taxonomy_upper_case():
    clean = validated_practice_details(DETAILS)

    assert (clean["state"], clean["taxonomy_code"], clean["tax_id"]) == ("IL", "207Q00000X", "12-3456789")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("tax_id", "123-45-678", "the tax ID must be the nine-digit EIN, like 12-3456789"),
        ("group_npi", "1245319590", "1245319590 is not a valid group NPI"),
        ("taxonomy_code", "207Q0000", "207Q0000 is not a taxonomy code (10 characters ending in X)"),
        ("state", "ZZ", "ZZ is not a US state or territory"),
        ("zip", "6270", "the ZIP code must be five digits or ZIP+4"),
        ("phone", "555-1234", "the phone number must have ten digits"),
        ("address", "1 Main*St", "address cannot hold *, :, ^ or ~"),
        ("city", "S" * 31, "city is longer than 30 characters"),
    ],
)
def test_each_field_is_checked_when_it_is_filled(field, value, message):
    with pytest.raises(Invalid) as raised:
        validated_practice_details({**DETAILS, field: value})
    assert raised.value.message == message


def test_the_profile_holds_digits_only_and_needs_zip_plus_four():
    profile = billing_profile({"practice_details": validated_practice_details(DETAILS)})

    assert profile == BillingProfile(
        "Lakeside Family Medicine",
        "123456789",
        "1245319599",
        "207Q00000X",
        "123 Main St",
        None,
        "Springfield",
        "IL",
        "627011234",
        "5555551234",
        "Dana Biller",
    )
    assert missing_from_profile(profile) == []
    five_digits = billing_profile({"practice_details": {**DETAILS, "zip": "62701"}})
    assert missing_from_profile(five_digits) == ["practice.zip"]


def test_an_empty_or_older_free_text_profile_lists_what_is_missing():
    older = billing_profile({"practice_details": {"legal_name": "Lakeside", "tax_id": "TBD", "address": "1 Main St"}})

    assert missing_from_profile(older) == [
        "practice.tax_id",
        "practice.city",
        "practice.state",
        "practice.zip",
        "practice.phone",
        "practice.billing_contact",
    ]
    assert len(missing_from_profile(billing_profile({}))) == 8


def test_a_charge_schedule_imports_codes_and_dollars():
    found = parsed_charges('Code,Charge\n99214,$150.00\ng2211,16\n96127,"1,250.5"\n')

    assert found == {"99214": 15000, "G2211": 1600, "96127": 125050}


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("procedure,price\n9921,10\n", "row 2: 9921 is not a CPT or HCPCS code"),
        ("cpt,fee\n99214,ten\n", "row 2: ten is not an amount"),
        ("cpt,fee\n99214,0\n", "row 2: the charge for 99214 must be more than $0 and at most $99,999.99"),
        ("code\n99214\n", "the file needs a code column and a charge column"),
        ("code,charge\n", "the file holds no charges"),
    ],
)
def test_a_charge_file_names_its_first_problem(text, message):
    with pytest.raises(Invalid) as raised:
        parsed_charges(text)
    assert raised.value.message == message
