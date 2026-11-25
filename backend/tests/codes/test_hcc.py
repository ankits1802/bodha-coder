import shutil
from datetime import date

import pytest

from app.codes.hcc import (
    DATA_DIR,
    HccDataCorrupt,
    HccPatient,
    hcc_model_for,
    load_hcc_model,
    payment_year_for,
    segment_for,
    sex_code,
)

WOMAN_70 = HccPatient(70, "2")


@pytest.fixture(scope="module")
def model():
    return load_hcc_model("2027")


def test_icd_codes_map_to_the_cms_v28_categories(model):
    assert model.hccs_for("E11.9", WOMAN_70) == {"HCC38"}
    assert model.hccs_for("E1122", WOMAN_70) == {"HCC37"}
    assert model.hccs_for("I50.22", WOMAN_70) == {"HCC226"}
    assert model.hccs_for("I10", WOMAN_70) == frozenset()


def test_age_edits_from_the_cms_mapping_apply(model):
    assert model.hccs_for("J44.9", HccPatient(17, "1")) == frozenset()
    assert model.hccs_for("J44.9", HccPatient(70, "1")) == {"HCC280"}
    assert model.hccs_for("C50.011", HccPatient(40, "2")) == {"HCC22"}
    assert model.hccs_for("C50.011", HccPatient(60, "2")) == {"HCC23"}
    assert model.hccs_for("J44.9", HccPatient(None, None)) == frozenset()


def test_labels_and_relative_factors_come_from_the_cms_tables(model):
    assert model.label("HCC37") == "Diabetes with Chronic Complications"
    assert model.factor("HCC226", "aged") == 0.36
    assert model.factor("HCC226", "disabled") == 0.442


def test_hierarchies_keep_only_the_most_severe_category(model):
    assert model.payment_hccs({"HCC37", "HCC38"}) == {"HCC37"}
    assert model.payment_hccs({"HCC328", "HCC329"}) == {"HCC328"}


def test_a_heart_assist_device_counts_only_with_heart_failure(model):
    assert model.payment_hccs({"HCC223"}) == frozenset()
    assert model.payment_hccs({"HCC223", "HCC226"}) == {"HCC223"}


def test_the_score_adds_factors_interactions_and_the_count_variable(model):
    assert model.score({"HCC37", "HCC226"}, "aged") == 0.638
    assert model.score({"HCC226", "HCC328"}, "aged") == 0.663
    assert model.score({"HCC1", "HCC48", "HCC81", "HCC107", "HCC201"}, "aged") == 1.483
    assert model.score(set(), "aged") == 0


def test_service_dates_feed_the_next_payment_year():
    assert payment_year_for(date(2026, 11, 25)) == "2027"
    assert payment_year_for(date(2026, 1, 1)) == "2027"


def test_segments_and_sex_codes():
    assert segment_for(64) == "disabled"
    assert segment_for(65) == "aged"
    assert segment_for(None) is None
    assert (sex_code("Female"), sex_code("M"), sex_code("unknown")) == ("2", "1", None)


def test_a_payment_year_without_vendored_files_has_no_model():
    assert hcc_model_for("2028") is None
    assert hcc_model_for(None) is None


def test_a_changed_artefact_is_refused(tmp_path):
    for path in DATA_DIR.glob("hcc_v28_2027*"):
        shutil.copy(path, tmp_path / path.name)
    artefact = tmp_path / "hcc_v28_2027_icd.tsv.gz"
    artefact.write_bytes(artefact.read_bytes() + b"\0")

    with pytest.raises(HccDataCorrupt, match="checksum"):
        load_hcc_model("2027", data_dir=tmp_path)
