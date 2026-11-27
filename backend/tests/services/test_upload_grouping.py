from datetime import date

import pytest

from app.codes.billing_codes import parse_code_list
from app.core.errors import Invalid
from app.services.estimates import impact_cents
from app.services.uploads import FilePlacement, UploadFile, UploadPlan, grouped_files

VISIT = "Established patient"
DEFAULT = FilePlacement("p-varga", date(2026, 11, 25), "11")


def pdf(name: str) -> UploadFile:
    return UploadFile(name, b"%PDF-1.4", None, None)


def test_files_without_their_own_placement_share_the_default_batch():
    groups = grouped_files([(pdf("a.pdf"), FilePlacement()), (pdf("b.pdf"), FilePlacement())], DEFAULT, VISIT)
    assert [(plan, [file.name for file in files]) for plan, files in groups] == [
        (UploadPlan("p-varga", date(2026, 11, 25), "11", VISIT), ["a.pdf", "b.pdf"])
    ]


def test_files_are_grouped_by_provider_date_and_place_in_the_order_first_seen():
    files = [
        (pdf("a.pdf"), FilePlacement("p-haddad", date(2026, 11, 24), "31")),
        (pdf("b.pdf"), FilePlacement()),
        (pdf("c.pdf"), FilePlacement("p-haddad", date(2026, 11, 24), "31")),
        (pdf("d.pdf"), FilePlacement(service_date=date(2026, 11, 23))),
    ]
    groups = grouped_files(files, DEFAULT, VISIT)
    assert [
        (plan.provider_id, plan.service_date, plan.place_code, [f.name for f in group]) for plan, group in groups
    ] == [
        ("p-haddad", date(2026, 11, 24), "31", ["a.pdf", "c.pdf"]),
        ("p-varga", date(2026, 11, 25), "11", ["b.pdf"]),
        ("p-varga", date(2026, 11, 23), "11", ["d.pdf"]),
    ]


def test_a_file_with_no_provider_date_or_place_is_refused_by_name():
    with pytest.raises(Invalid, match="scan.pdf: choose the provider, date of service and place of service"):
        grouped_files([(pdf("scan.pdf"), FilePlacement(provider_id="p-varga"))], FilePlacement(), VISIT)


def codes(text: str):
    return parse_code_list(text).codes


def test_the_dollar_impact_is_the_suggested_claim_minus_the_billed_one_in_cents():
    assert impact_cents(codes("99214, I10"), codes("99215, I10"), "11", date(2026, 11, 25)) == 13_561 - 19_239


def test_no_impact_is_stored_when_nothing_can_be_priced():
    assert impact_cents(codes("99214"), codes("99215"), "98", date(2026, 11, 25)) is None
    assert impact_cents(codes("99214"), codes("99215"), "11", date(2031, 1, 2)) is None
    assert impact_cents(codes("E11.65"), codes("E11.9"), "11", date(2026, 11, 25)) is None
