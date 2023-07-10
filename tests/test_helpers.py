# type: ignore
"""Tests for helper utilities."""

import pytest

from valentina.utils.helpers import (
    all_traits_from_constants,
    get_max_trait_value,
    normalize_to_db_row,
    num_to_circles,
)


def test_all_traits_from_constants_one():
    """Test all_traits_from_constants().

    GIVEN a list of constants
    WHEN all_traits_from_constants() is called
    THEN a dictionary of all traits is returned
    """
    returned = all_traits_from_constants()
    assert "Disciplines" in returned
    assert "Knowledges" in returned
    assert "Skills" in returned
    assert returned["Spheres"] == [
        "Correspondence",
        "Entropy",
        "Forces",
        "Life",
        "Matter",
        "Mind",
        "Prime",
        "Spirit",
        "Time",
    ]


def test_all_traits_from_constants_two():
    """Test all_traits_from_constants().

    GIVEN a list of constants
    WHEN all_traits_from_constants() is called with flat_list=True
    THEN a list of all traits is returned
    """
    returned = all_traits_from_constants(flat_list=True)
    assert "Primal-Urge" in returned
    assert "Entropy" in returned
    assert "Strength" in returned
    assert "Drive" in returned
    assert "Willpower" in returned
    assert "Thaumaturgy" in returned


@pytest.mark.parametrize(
    ("trait", "expected"),
    [
        ("Willpower", 10),
        ("Humanity", 10),
        ("Rage", 10),
        ("Gnosis", 10),
        ("Arete", 10),
        ("blood_pool", 20),
        ("Quintessence", 20),
        ("random", 5),
        ("strength", 5),
    ],
)
def test_get_max_trait_value(trait, expected):
    """Test get_max_trait_value().

    GIVEN a trait name
    WHEN get_max_trait_value() is called
    THEN the correct value is returned
    """
    assert get_max_trait_value(trait) == expected


@pytest.mark.parametrize(("row", "expected"), [("Test-Row", "test_row"), ("Test Row", "test_row")])
def test_normalize_to_db_row(row, expected) -> None:
    """Test normalize_to_db_row().

    GIVEN a string
    WHEN normaliznormalize_to_db_rowe_row() is called
    THEN the correct string is returned
    """
    assert normalize_to_db_row(row) == expected


@pytest.mark.parametrize(
    ("num", "maximum", "expected"),
    [(0, 5, "○○○○○"), (3, 5, "●●●○○"), (5, None, "●●●●●"), (6, 5, "●●●●●●"), (0, 10, "○○○○○○○○○○")],
)
def test_num_to_circles(num, maximum, expected) -> None:
    """Test num_to_circles().

    GIVEN a number and a max
    WHEN num_to_circles() is called
    THEN the correct number of circles is returned
    """
    assert num_to_circles(num, maximum) == expected
