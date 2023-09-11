# type: ignore
"""Tests for discord_utils.py helper utilities."""
from unittest.mock import MagicMock, patch

from valentina.constants import ChannelPermission
from valentina.utils.discord_utils import set_channel_perms


class PermissionOverwriteMock(MagicMock):
    """Mock the discord.PermissionOverwrite class."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._attributes = {}

    def __setattr__(self, name, value):
        """Set the attributes on the mock object."""
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
