# type: ignore
"""Tests for helper utilities."""
import pytest

from valentina.constants import RollResultType
from valentina.models.db_tables import VampireClan
from valentina.utils.helpers import diceroll_thumbnail, fetch_random_vampire_clan, num_to_circles


@pytest.mark.usefixtures("mock_db")
class TestsWithDatabase:
    """Tests which require the a mock database."""

    @staticmethod
    def test_random_vampire_clan():
        """Test the random_vampire_clan function."""
        result = fetch_random_vampire_clan()
        assert isinstance(result, VampireClan)
        assert result.name in [
            "Assamite",
            "Brujah",
            "Followers of Set",
            "Gangrel",
            "Giovanni",
            "Lasombra",
            "Malkavian",
            "Nosferatu",
            "Ravnos",
            "Toreador",
            "Tremere",
            "Tzimisce",
            "Ventrue",
        ]


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
