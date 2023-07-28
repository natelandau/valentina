# type: ignore
"""Test the GuildService class."""
import pytest
from rich.console import Console

from valentina.models import GuildService
from valentina.models.database import Guild

# ARG001

c = Console()


@pytest.mark.usefixtures("mock_db")
class TestGuildService:
    """Test the GuildService class."""

    guild_svc = GuildService()

    def test_update_or_add_one(self, ctx_existing):
        """Test GuildService.update_or_add().

        GIVEN GuildService.update_or_add()
        WHEN called with an existing guild and no data
        THEN the modified time is updated
        """
        assert "modified" not in Guild.get_by_id(1).data

        self.guild_svc.update_or_add(ctx_existing.guild)
        assert Guild.get_by_id(1).name == "test_guild"
        assert Guild.get_by_id(1).id == 1
        assert "modified" in Guild.get_by_id(1).data

    def test_update_or_add_two(self, ctx_new_user_guild):
        """Test GuildService.update_or_add().

        GIVEN GuildService.update_or_add()
        WHEN called with a new guild
        THEN the guild is created in the db with default json data
        """
        self.guild_svc.update_or_add(ctx_new_user_guild.guild)
        assert Guild.get_by_id(2).name == "Test Guild 2"
        assert Guild.get_by_id(2).id == 2
        assert "modified" in Guild.get_by_id(2).data
        assert "log_channel_id" in Guild.get_by_id(2).data
        assert "xp_permissions" in Guild.get_by_id(2).data
        assert "use_audit_log" in Guild.get_by_id(2).data

    def test_update_or_add_three(self, ctx_existing):
        """Test GuildService.update_or_add().

        GIVEN GuildService.update_or_add()
        WHEN data is provided in a dictionary
        THEN the guild is updated
        """
        update_dict = {"log_channel_id": "xxx", "xp_permissions": None, "new_key": "new_value"}
        guild = Guild.get_by_id(2)

        self.guild_svc.update_or_add(guild, update_dict)
        data = Guild.get_by_id(2).data
        assert "xp_permissions" not in data
        assert data["log_channel_id"] == "xxx"
        assert data["new_key"] == "new_value"

    def test_fetch_all_traits_one(self):
        """Test GuildService.fetch_all_traits().

        GIVEN a database with a guild
        WHEN GuildService.fetch_all_traits() is called
        THEN the traits are returned as a dictionary
        """
        returned = GuildService.fetch_all_traits(guild_id=1)
        assert isinstance(returned, dict)
        assert "Test_Trait" in returned["Skills"]
        assert returned["Social"] == ["Appearance", "Charisma", "Manipulation"]

    def test_fetch_all_traits_two(self):
        """Test GuildService.fetch_all_traits().

        GIVEN a database with a guild
        WHEN GuildService.fetch_all_traits() is called with flat_list=True
        THEN the traits are returned as a list
        """
        returned = GuildService.fetch_all_traits(guild_id=1, flat_list=True)
        assert isinstance(returned, list)
        for i in ["Test_Trait", "Charisma", "Manipulation", "Appearance"]:
            assert i in returned

    def test_fetch_guild_settings(self, ctx_existing, caplog):
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
        returned = self.guild_svc.fetch_guild_settings(ctx_existing)
        caplog_text = caplog.text
        assert isinstance(returned, dict)
        assert "DATABASE:" in caplog_text  # confirm the database was queried b/c cache was empty
        assert returned["a"] == "b"
        assert returned["c"] == "d"

        # Fetch the guild settings again
        returned = self.guild_svc.fetch_guild_settings(ctx_existing)
        caplog_text = caplog.text
        assert isinstance(returned, dict)
        assert "CACHE:" in caplog_text  # confirm the cache was used
        assert returned["a"] == "b"
        assert returned["c"] == "d"

    def test_purge_cache_one(self, ctx_existing):
        """Test GuildService.purge_cache().

        GIVEN GuildService.purge_cache()
        WHEN called with a guild
        THEN the cache for that guild is emptied
        """
        # Populate the cache
        self.guild_svc.settings_cache = {1: {"a": "b"}, 2: {"c": "d"}}

        # Purge the cache
        self.guild_svc.purge_cache(ctx_existing.guild)

        # Confirm the cache was purged
        assert self.guild_svc.settings_cache == {2: {"c": "d"}}

    def test_purge_cache_two(self):
        """Test GuildService.purge_cache().

        GIVEN GuildService.purge_cache()
        WHEN called without specifying a guild
        THEN the entire cache is emptied
        """
        # Populate the cache
        self.guild_svc.settings_cache = {1: {"a": "b"}, 2: {"c": "d"}}

        # Purge the cache
        self.guild_svc.purge_cache()

        # Confirm the cache was purged
        assert self.guild_svc.settings_cache == {}
