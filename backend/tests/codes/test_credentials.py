import pytest

from app.codes.credentials import LICENSE_STATES, is_taxonomy_code, is_valid_dea


@pytest.mark.parametrize("number", ["AB1234563", "BJ6125341", "M91234563"])
def test_a_dea_number_passes_its_check_digit(number):
    assert is_valid_dea(number)


@pytest.mark.parametrize("number", ["AB1234562", "BJ6125342", "A11234563", "AB123456", "ab1234563", "AB12345630"])
def test_a_dea_number_with_a_wrong_digit_or_shape_is_refused(number):
    assert not is_valid_dea(number)


def test_a_taxonomy_code_is_ten_characters_ending_in_x():
    assert is_taxonomy_code("207Q00000X")
    assert is_taxonomy_code("363LF0000X")
    assert not is_taxonomy_code("207Q0000X")
    assert not is_taxonomy_code("207Q000000")
    assert not is_taxonomy_code("207q00000x")


def test_license_states_are_the_fifty_states_dc_and_five_territories():
    assert len(LICENSE_STATES) == 56
    assert {"TX", "DC", "PR", "GU"} <= LICENSE_STATES
    assert "ZZ" not in LICENSE_STATES
