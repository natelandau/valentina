# type: ignore
"""Test the GuildService class."""
import discord
import pytest
from dirty_equals import IsPartialDict
from discord.ext import commands
from rich.console import Console

from valentina.constants import GUILD_DEFAULTS
from valentina.models import GuildService
from valentina.models.db_tables import Guild

# ARG001

c = Console()


def local_mock_bot(mocker):
    """A mock of a discord.Bot object."""
    mock_bot = mocker.MagicMock()
    mock_bot.__class__ = commands.Bot
    return mock_bot


@pytest.mark.usefixtures("mock_db")
class TestGuildService:
    """Test the GuildService class."""

    guild_svc = GuildService(bot=local_mock_bot)

    def test_update_or_add(self, mocker):
        """Test GuildService.update_or_add()."""
        # GIVEN a guild that is not in the database and items in the cache
        self.guild_svc.settings_cache = {1002002002: {"a": "b"}, 1: {"a": "b"}, 2: {"c": "d"}}
        mock_guild = mocker.MagicMock()
        mock_guild.id = 1002002002
        mock_guild.name = "Test Guild"
        mock_guild.__class__ = discord.Guild

        # WHEN update_or_add is called
        self.guild_svc.update_or_add(guild=mock_guild, updates={"key": "value"})

        # THEN the guild is added to the database with the correct default values and the cache for that guild is purged
        assert self.guild_svc.settings_cache == {1: {"a": "b"}, 2: {"c": "d"}}
        result = Guild.get_by_id(1002002002)
        assert result.name == "Test Guild"
        assert result.data == IsPartialDict(
            key="value", permissions_edit_trait=GUILD_DEFAULTS["permissions_edit_trait"]
        )
        assert result.data.get("modified")
        for k, v in GUILD_DEFAULTS.items():
            assert result.data[k] == v

        # WHEN update_or_add is called again with new data
        updates = {"key": "new_value", "new_key": "new_value"}
        self.guild_svc.update_or_add(guild=mock_guild, updates=updates)

        # THEN the guild is updated with the new data
        result = Guild.get_by_id(1002002002)
        assert result.name == "Test Guild"
        assert result.data == IsPartialDict(
            key="new_value",
            new_key="new_value",
            permissions_edit_trait=GUILD_DEFAULTS["permissions_edit_trait"],
        )

    def test_fetch_guild_settings(self, mock_ctx, caplog):
        """Test GuildService.fetch_guild_settings().

        GIVEN a database with a guild
        WHEN GuildService.fetch_guild_settings() is called
        THEN the guild settings are returned
        """
        # reset the cache
        self.guild_svc.settings_cache = {}

        # Add fields
        update_dict = {"a": "b", "c": "d"}
        Guild.update(data=Guild.data.update(update_dict)).where(Guild.id == 1).execute()

        # Fetch the guild settings
        returned = self.guild_svc.fetch_guild_settings(mock_ctx.guild)
        caplog_text = caplog.text
        assert isinstance(returned, dict)
        assert "DATABASE:" in caplog_text  # confirm the database was queried b/c cache was empty
        assert returned == IsPartialDict(
            a="b",
            c="d",
            key="value",
            permissions_edit_trait=GUILD_DEFAULTS["permissions_edit_trait"],
        )

        # Fetch the guild settings again
        returned = self.guild_svc.fetch_guild_settings(mock_ctx.guild)
        caplog_text = caplog.text
        assert isinstance(returned, dict)
        assert "CACHE:" in caplog_text  # confirm the cache was used
        assert returned == IsPartialDict(
            a="b",
            c="d",
            key="value",
            permissions_edit_trait=GUILD_DEFAULTS["permissions_edit_trait"],
        )

    def test_purge_cache_one(self, mock_ctx):
        """Test GuildService.purge_cache().

        GIVEN GuildService.purge_cache()
        WHEN called with a guild
        THEN the cache for that guild is emptied
        """
        # Populate the cache
        self.guild_svc.settings_cache = {1: {"a": "b"}, 2: {"c": "d"}}
        self.guild_svc.changelog_versions_cache = ["a", "b", "c"]

        # Purge the cache
        self.guild_svc.purge_cache(mock_ctx)

        # Confirm the cache was purged
        assert self.guild_svc.settings_cache == {2: {"c": "d"}}
        assert self.guild_svc.changelog_versions_cache == []

    def test_purge_cache_two(self):
        """Test GuildService.purge_cache().

        GIVEN GuildService.purge_cache()
        WHEN called without specifying a guild
        THEN the entire cache is emptied
        """
        # Populate the cache
        self.guild_svc.settings_cache = {1: {"a": "b"}, 2: {"c": "d"}}
        self.guild_svc.changelog_versions_cache = ["a", "b", "c"]

        # Purge the cache
        self.guild_svc.purge_cache()

        # Confirm the cache was purged
        assert self.guild_svc.settings_cache == {}
        assert self.guild_svc.changelog_versions_cache == []
