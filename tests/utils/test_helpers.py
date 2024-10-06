# type: ignore
"""Tests for helper utilities."""

import pytest

from valentina.utils import ValentinaConfig, errors
from valentina.utils.helpers import divide_total_randomly, num_to_circles


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
