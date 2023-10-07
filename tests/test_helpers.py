# type: ignore
"""Tests for helper utilities."""
import pytest

from valentina.constants import RollResultType, VampireClanType
from valentina.utils.helpers import (
    adjust_sum_to_match_total,
    diceroll_thumbnail,
    divide_into_three,
    num_to_circles,
)


@pytest.mark.usefixtures("mock_db")
class TestsWithDatabase:
    """Tests which require the a mock database."""

    @staticmethod
    def test_random_vampire_clan():
        """Test the random_vampire_clan function."""
        result = VampireClanType.random_member()
        assert result.name in VampireClanType.__members__


@pytest.mark.parametrize(
    (
        "values",
        "total",
        "max_value",
        "min_value",
    ),
    [
        ([1, 2, 3, 4, 5], 5, 5, 0),
        ([1, 2, 1, 0, 1, 5], 10, 5, 1),
        ([1, 2], 10, 6, 1),
        ([23, 11, 1, 1, 1], 5, 5, 1),
        ([0, 0], 5, None, 0),
        ([1, 5, 0], 3, 5, 1),
        ([5, 1, 6], 12, 5, 1),
    ],
)
def test_adjust_sum_to_match_total(values, total, max_value, min_value) -> None:
    """Test adjust_sum_to_match_total()."""
    # GIVEN a list of integers and a total and a max value
    # WHEN adjust_sum_to_match_total() is called
    result = adjust_sum_to_match_total(values, total, max_value, min_value)

    # THEN check that the result is correct
    assert sum(result) == total
    assert not any(x < 0 for x in result)
    if sum(values) == total:
        assert result == values
    if max_value:
        assert not any(x > max_value for x in result)
    if min_value:
        assert not any(x < min_value for x in result)


def test_divide_into_three() -> None:
    """Test divide_into_three()."""
    for i in range(3, 100):
        one, two, three = divide_into_three(i)
        assert one + two + three == i

    with pytest.raises(ValueError, match="Total should be greater than 2"):
        divide_into_three(2)


def test_diceroll_thumbnail(mocker):
    """Test the diceroll_thumbnail function.

    GIVEN a mocked discord.ApplicationContext object and a RollResultType
    WHEN the diceroll_thumbnail function is called
    THEN check that the correct thumbnail URL is returned.
    """
    # GIVEN a mocked discord.ApplicationContext object and a RollResultType
    ctx = mocker.MagicMock()
    result = RollResultType.SUCCESS

    # Mock the fetch_roll_result_thumbs method and the random.choice function
    ctx.bot.guild_svc.fetch_roll_result_thumbs.return_value = {"SUCCESS": ["url1", "url2", "url3"]}
    mock_random_choice = mocker.patch("random.choice", return_value="random_thumbnail_url")

    # WHEN the diceroll_thumbnail function is called
    thumbnail_url = diceroll_thumbnail(ctx, result)

    # THEN check that the correct thumbnail URL is returned.
    assert thumbnail_url == "random_thumbnail_url"
    mock_random_choice.assert_called_once()


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
