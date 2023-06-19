# type: ignore
"""Tests for helper utilities."""

import pytest

from valentina.utils.helpers import (
    format_traits,
    get_max_trait_value,
    get_trait_multiplier,
    get_trait_new_value,
    normalize_row,
    num_to_circles,
)


class MockCharacter:
    """Mock character class."""

    def __init__(self) -> None:
        self.first_name = "Test"
        self.last_name = "Character"
        self.nickname = "Testy"
        self.char_class = "Vampire"
        self.willpower = 5
        self.strength = 2
        self.blood_pool = 10
        self.wits = 0
        self.dexterity = None


@pytest.mark.parametrize(("row", "expected"), [("Test-Row", "test_row"), ("Test Row", "test_row")])
def test_normalize_row(row, expected) -> None:
    """Test normalize_row().

    GIVEN a string
    WHEN normalize_row() is called
    THEN the correct string is returned
    """
    assert normalize_row(row) == expected


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


@pytest.mark.parametrize(
    ("trait", "expected"),
    [
        ("Willpower", 1),
        ("Humanity", 2),
        ("Rage", 1),
        ("Gnosis", 2),
        ("Arete", 10),
        ("Quintessence", 1),
        ("random", 2),
        ("strength", 4),
        ("drive", 2),
        ("Conscience", 2),
    ],
)
def test_get_trait_multiplier(trait, expected):
    """Test get_trait_multiplier().

    GIVEN a trait name
    WHEN get_trait_multiplier() is called
    THEN the correct value is returned
    """
    assert get_trait_multiplier(trait) == expected


@pytest.mark.parametrize(
    ("trait", "expected"),
    [
        ("Willpower", 1),
        ("Humanity", 1),
        ("RANDOM", 1),
        ("drive", 3),
        ("Conscience", 1),
        ("potence", 10),
        ("Spirit", 10),
    ],
)
def test_get_trait_new_value(trait, expected):
    """Test get_trait_new_value().

    GIVEN a trait name
    WHEN get_trait_new_value() is called
    THEN the correct value is returned
    """
    assert get_trait_new_value(trait) == expected


def test_format_traits():
    """Test format_traits().

    GIVEN a character and a list of traits
    WHEN format_traits() is called
    THEN the correct string is returned
    """
    assert (
        format_traits(MockCharacter(), ["Blood Pool", "Strength", "wits", "Dexterity", "Nothing"])
        == "`blood_pool   : ●●●●●●●●●●○○○○○○○○○○`\n`strength     : ●●○○○`\n`wits         : ○○○○○`\n`dexterity    : ○○○○○`"
    )
    assert (
        format_traits(
            MockCharacter(), ["Blood Pool", "Strength", "wits", "Dexterity", "Nothing"], False
        )
        == "`blood_pool   : ●●●●●●●●●●○○○○○○○○○○`\n`strength     : ●●○○○`"
    )
