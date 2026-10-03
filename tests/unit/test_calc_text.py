from __future__ import annotations

import math

import pytest

from voltplan.calc.text import fixed, general


@pytest.mark.parametrize("value, precision, digits, expected", [
    (210.54, 4, 1, "210,5"),
    (123.456, 5, 3, "123,460"),
    (1.23456, 5, 3, "1,235"),
    (0.0004, 5, 3, "0,000"),
    (5.3249, 4, 2, "5,32"),
    (-0.00001, 4, 2, "0,00"),
    (66.05, 4, 1, "66,0"),
    (0.125, 5, 2, "0,13"),
    (230.0, 4, 1, "230,0"),
])
def test_fixed_matches_float_to_str_f(value, precision, digits, expected):
    assert fixed(value, precision, digits) == expected


@pytest.mark.parametrize("value, expected", [
    (230.04, "230"), (210.54, "210,5"), (99.95, "99,95"), (0.05, "0,05"), (229.96, "230"), (0.0, "0"),
])
def test_general_drops_trailing_zeros(value, expected):
    assert general(value, 4) == expected


@pytest.mark.parametrize("value, precision, digits, expected", [
    (212824000.6, 6, 2, "2,12824E8"),
    (677192000.0, 6, 2, "6,77192E8"),
    (3.43969e66, 6, 2, "3,43969E66"),
    (10400.0, 4, 1, "1,04E4"),
    (5.425e10, 4, 1, "5,425E10"),
    (9999.96, 4, 1, "1E4"),
    (9999.44, 4, 1, "9999,0"),
    (123456.0, 5, 2, "1,2346E5"),
    (99999.4, 5, 3, "99999,000"),
])
def test_fixed_switches_to_exponent_for_long_integer_part(value, precision, digits, expected):
    assert fixed(value, precision, digits) == expected


@pytest.mark.parametrize("value, expected", [
    (0.00001, "1E-5"), (0.0001, "0,0001"), (12345.6, "1,235E4"), (9999.4, "9999"), (-0.000012346, "-1,235E-5"),
])
def test_general_uses_exponent_outside_plain_range(value, expected):
    assert general(value, 4) == expected


@pytest.mark.parametrize("value, expected", [(math.inf, "INF"), (-math.inf, "-INF"), (math.nan, "NAN")])
def test_special_values_are_named(value, expected):
    assert fixed(value, 4, 1) == expected
    assert general(value, 4) == expected


def test_exact_half_rounds_away_from_zero():
    assert general(1.0625, 4) == "1,063"
    assert fixed(1.0625, 4, 3) == "1,063"
    assert fixed(-1.0625, 4, 3) == "-1,063"
