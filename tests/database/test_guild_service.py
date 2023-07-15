# type: ignore
"""Test the GuildService class."""
import pytest

from valentina.models.database import Guild
from valentina.models.database_services import GuildService

# ARG001


@pytest.mark.usefixtures("mock_db")
class TestGuildService:
    """Test the GuildService class."""

    def test_is_in_db(self):
        """Test GuildService.is_in_db()."""
        assert GuildService.is_in_db(1)
        assert not GuildService.is_in_db(2)

    def test_update_or_add_one(self, ctx_existing):
        """Test GuildService.update_or_add().

        GIVEN a database with a guild
        WHEN GuildService.update_or_add() is called with an existing guild
        THEN the guild is updated
        """
        GuildService.update_or_add(ctx_existing.guild)
        assert Guild.get_by_id(1).name == "test_guild"
        assert Guild.get_by_id(1).id == 1

    def test_update_or_add_two(self, ctx_new_user_guild):
        """Test GuildService.update_or_add().

        GIVEN a database with a guild
        WHEN GuildService.update_or_add() is called with a new guild
        THEN the guild is created in the db
        """
        GuildService.update_or_add(ctx_new_user_guild.guild)
        assert Guild.get_by_id(2).name == "Test Guild 2"
        assert Guild.get_by_id(2).id == 2

    def test_fetch_all_traits_one(self):
        """Test GuildService.fetch_all_traits().

        GIVEN a database with a guild
        WHEN GuildService.fetch_all_traits() is called
        THEN the traits are returned as a dictionary
        """
        returned = GuildService.fetch_all_traits(guild_id=1)
        assert isinstance(returned, dict)
        assert returned["Test_Category"] == ["Test_Trait"]
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
