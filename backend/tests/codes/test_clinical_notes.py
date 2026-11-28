from app.codes.clinical_notes import NOTE_TYPES, loinc_codes_for


def test_each_note_type_pulls_its_loinc_document_types():
    assert loinc_codes_for(["progress"]) == {"11506-3"}
    assert loinc_codes_for(["consult", "history_physical"]) == {"11488-4", "34117-2"}
    assert {"34113-1", "34119-8", "34096-8"} <= loinc_codes_for(["nursing_facility"])


def test_no_loinc_code_belongs_to_two_note_types():
    codes = [code for note_type in NOTE_TYPES for code in loinc_codes_for([note_type])]
    assert len(codes) == len(set(codes))
