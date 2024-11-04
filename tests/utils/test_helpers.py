# type: ignore
"""Tests for helper utilities."""

import pytest

from valentina.utils import ValentinaConfig, errors
from valentina.utils.helpers import (
    convert_int_to_emoji,
    divide_total_randomly,
    get_max_trait_value,
    get_trait_multiplier,
    get_trait_new_value,
    num_to_circles,
    random_string,
    truncate_string,
)


@pytest.mark.no_db
def test_random_string(debug) -> None:
    """Test random_string()."""
    returned = random_string(10)
    assert isinstance(returned, str)
    assert len(returned) == 10
    debug("string", returned)


@pytest.mark.no_db
def test_truncate_string() -> None:
    """Test truncate_string()."""
    assert truncate_string("This is a test", 10) == "This i..."
    assert truncate_string("This is a test", 100) == "This is a test"


@pytest.mark.no_db
def test_get_trait_new_value() -> None:
    """Test get_trait_new_value()."""
    assert get_trait_new_value("Dominate", "Disciplines") == 10
    assert get_trait_new_value("Strength", "Physical") == 5
    assert get_trait_new_value("xxx", "xxx") == 1


@pytest.mark.no_db
def test_get_trait_multiplier() -> None:
    """Test get_trait_multiplier()."""
    assert get_trait_multiplier("Dominate", "Disciplines") == 7
    assert get_trait_multiplier("Humanity", "SPHERES") == 2
    assert get_trait_multiplier("xxx", "xxx") == 2


@pytest.mark.no_db
def test_get_max_trait_value() -> None:
    """Test get_max_trait_value()."""
    assert get_max_trait_value("Dominate", "Disciplines") == 5
    assert get_max_trait_value("Willpower", "Other") == 10
    assert get_max_trait_value("xxx", "xxx") == 5


@pytest.mark.no_db
def test_convert_int_to_emoji() -> None:
    """Test convert_int_to_emoji()."""
    assert convert_int_to_emoji(1) == ":one:"
    assert convert_int_to_emoji(10) == ":keycap_ten:"
    assert convert_int_to_emoji(11) == "11"
    assert convert_int_to_emoji(11, markdown=True) == "`11`"


@pytest.mark.no_db
@pytest.mark.parametrize(
    ("total", "num", "max_value", "min_value"),
    [
        (10, 3, 4, 3),
        (10, 3, 5, 1),
        (20, 4, 8, 0),
        (30, 6, 8, 1),
        (30, 4, 9, 0),
        (30, 3, None, 0),
        (30, 3, 10, 0),
        (6, 2, None, 3),
    ],
)
def test_divide_total_randomly(total, num, max_value, min_value):
    """Test the divide_total_randomly function with various input combinations."""
    for _ in range(100):
        result = divide_total_randomly(total, num, max_value, min_value)

        assert len(result) == num
        assert sum(result) == total
        assert not any(x < min_value for x in result)
        if max_value:
            assert not any(x > max_value for x in result)


def test_divide_total_randomly_raises_error() -> None:
    """Test that divide_total_randomly raises errors when it should."""
    with pytest.raises(ValueError, match="Impossible to divide"):
        divide_total_randomly(1, 2, min_value=1)

    with pytest.raises(ValueError, match="Impossible to divide"):
        divide_total_randomly(10, 2, 5, 6)

    with pytest.raises(ValueError, match="Impossible to divide"):
        divide_total_randomly(10, 2, 3)


@pytest.mark.no_db
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
