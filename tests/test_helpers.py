# type: ignore
"""Tests for helper utilities."""

from unittest.mock import MagicMock, patch

import pytest

from valentina.models.constants import ChannelPermission, RollResultType
from valentina.utils.helpers import diceroll_thumbnail, num_to_circles, set_channel_perms


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


class PermissionOverwriteMock(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._attributes = {}

    def __setattr__(self, name, value):
        if name in (
            "send_messages",
            "read_messages",
            "manage_messages",
            "add_reactions",
            "view_channel",
        ):
            self._attributes[name] = value
        else:
            super().__setattr__(name, value)


@patch("discord.PermissionOverwrite", new_callable=PermissionOverwriteMock)
def test_set_channel_perms(mock_permission_overwrite):
    """Test the set_channel_perms function.

    GIVEN a mocked discord.PermissionOverwrite object
    WHEN the set_channel_perms function is called with different ChannelPermission values
    THEN check that the correct attributes are set on the mocked PermissionOverwrite object.
    """
    # The mock object will return itself when called, simulating object instantiation
    mock_permission_overwrite.return_value = mock_permission_overwrite

    # Test for ChannelPermission.HIDDEN
    result = set_channel_perms(ChannelPermission.HIDDEN)
    assert mock_permission_overwrite._attributes == {
        "send_messages": False,
        "read_messages": False,
        "manage_messages": False,
        "add_reactions": False,
        "view_channel": False,
    }
    assert isinstance(result, MagicMock)

    mock_permission_overwrite.reset_mock()

    # Test for ChannelPermission.READ_ONLY
    result = set_channel_perms(ChannelPermission.READ_ONLY)
    assert mock_permission_overwrite._attributes == {
        "send_messages": False,
        "read_messages": True,
        "manage_messages": False,
        "add_reactions": True,
        "view_channel": True,
    }
    assert isinstance(result, MagicMock)
