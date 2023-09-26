# type: ignore
"""Test the UserService class."""

import arrow
import discord
import pytest
from discord import ApplicationContext, Role

from valentina.constants import PermissionManageCampaign, PermissionsEditTrait, PermissionsEditXP
from valentina.models import UserService
from valentina.models.db_tables import Character, Guild, GuildUser
from valentina.utils import errors


@pytest.mark.usefixtures("mock_db")
class TestUserService:
    """Test the user service."""

    user_svc = UserService()

    def _create_user_from_ctx(self, ctx):
        """Create a GuildUser object from a context object."""
        return GuildUser.create(
            guild=ctx.guild.id,
            user=ctx.author.id,
            data={
                "id": ctx.author.id,
                "name": "testuser",
                "nick": "testnick",
                "display_name": "testdisplayname",
            },
        )

    def _clear_tests(self):
        """Clear the test database."""
        for guild in Guild.select():
            if guild.id != 1:  # Always keep the default guild
                guild.delete_instance(recursive=True, delete_nullable=True)

        for guild_user in GuildUser.select():
            guild_user.delete_instance(recursive=True, delete_nullable=True)

        self.user_svc.purge_cache()

    @pytest.mark.asyncio()
    async def test__get_member_and_guild_application_context(self, mock_ctx):
        """Test getting the member and guild from an ApplicationContext."""
        self._clear_tests()

        # GIVEN a context object with a guild and a user
        # WHEN _get_member_and_guild is called
        member, guild = await self.user_svc._get_member_and_guild(mock_ctx)

        # THEN return the correct member and guild
        assert member == mock_ctx.author
        assert guild == mock_ctx.guild

    @pytest.mark.asyncio()
    async def test__get_member_and_guild_autocomplete_context(self, mock_autocomplete_ctx1):
        """Test getting the member and guild from an AutocompleteContext."""
        # GIVEN an autocomplete context object with a guild and a user
        # WHEN _get_member_and_guild is called
        member, guild = await self.user_svc._get_member_and_guild(mock_autocomplete_ctx1)

        # THEN return the correct member and guild
        assert member == mock_autocomplete_ctx1.interaction.user
        assert guild == mock_autocomplete_ctx1.interaction.guild

    @pytest.mark.asyncio()
    async def test__get_member_and_guild_with_guilduser_object(self, mock_ctx, mocker):
        """Test getting the member and guild when a discord.User object is provided."""
        # Setup the tests
        self._clear_tests()
        guild_user = GuildUser.create(
            guild=1,
            user=mock_ctx.author.id,
            data={
                "test": "data",
                str(mock_ctx.guild.id): {"test": "data"},
            },
        )

        # GIVEN a discord.Guild object and a discord.User object
        mocker.patch("discord.utils.get", return_value=mock_ctx.author)  # patch discord.utils.get
        mocker.patch(
            "discord.utils.get_or_fetch", return_value=mock_ctx.guild
        )  # patch discord.utils.get

        # WHEN _get_member_and_guild is called
        member, guild = await self.user_svc._get_member_and_guild(mock_ctx, user=guild_user)

        # THEN return the correct member and guild
        assert guild.id == mock_ctx.guild.id
        assert member.id == mock_ctx.author.id

    @pytest.mark.asyncio()
    async def test__get_member_and_guild_with_only_user(self, mock_member2):
        """Test getting the member and guild when a discord.User object is provided and not CTX."""
        # WHEN _get_member_and_guild is called with a ctx object and a discord.User object
        member, guild = await self.user_svc._get_member_and_guild(ctx=None, user=mock_member2)

        # THEN return the correct member and guild
        assert member == mock_member2
        assert guild.id == 200

    @pytest.mark.asyncio()
    async def test__get_member_with_guild(self, mock_ctx, mock_guild2):
        """Test getting the member and guild when a discord.User object is provided and not CTX."""
        # WHEN _get_member_and_guild is called with a ctx object and a discord.User object
        member, guild = await self.user_svc._get_member_and_guild(ctx=mock_ctx, guild=mock_guild2)

        # THEN return the correct member and guild
        assert member.id == 1
        assert guild.id == 2

    @pytest.mark.asyncio()
    async def test_update_or_add_new_user_ctx(self, mock_ctx) -> None:
        """Test updating or adding a new user."""
        # Setup
        self._clear_tests()

        data = {"test": "data"}
        self.user_svc.user_cache = {"1_1": "a", "1_600": "b", "100_1": "c"}

        # WHEN update_or_add is called and a user is not in the database
        result = await self.user_svc.update_or_add(mock_ctx, data=data)

        # THEN return the correct result and update the database with default values, and the cache is intact
        assert result == GuildUser.get_by_id(1)
        assert result.data["name"] == "testuser"
        assert result.data["test"] == "data"
        assert result.data["lifetime_experience"] == 0
        assert "modified" in result.data
        assert self.user_svc.user_cache == {"1_1": "a", "1_600": "b", "100_1": "c"}

    @pytest.mark.asyncio()
    async def test_update_or_add_new_user_from_user(self, mock_ctx, mock_member2) -> None:
        """Test updating or adding a new user with a specified user object."""
        # Setup
        self._clear_tests()

        self.user_svc.user_cache = {"1_1": "a", "1_600": "b", "100_1": "c"}

        # WHEN update_or_add is called and a user is not in the database
        result = await self.user_svc.update_or_add(mock_ctx, user=mock_member2)

        # THEN return the correct result and update the database with default values, and the cache is intact
        assert result == GuildUser.get_by_id(1)
        assert result.data["name"] == "testuser2"
        assert result.data["lifetime_experience"] == 0
        assert "modified" in result.data
        assert self.user_svc.user_cache == {"1_1": "a", "1_600": "b", "100_1": "c"}

    @pytest.mark.asyncio()
    async def test_update_or_add_new_user_from_guild(self, mock_ctx, mock_guild2) -> None:
        """Test updating or adding a new user with a specified guild object."""
        # Setup
        self._clear_tests()
        new_guild = Guild.create(id=mock_guild2.id, name="Test Guild2")
        self.user_svc.user_cache = {"1_1": "a", "1_600": "b", "100_1": "c"}

        # WHEN update_or_add is called and a user is not in the database
        result = await self.user_svc.update_or_add(mock_ctx, guild=mock_guild2)

        # THEN return the correct result and update the database with default values, and the cache is intact
        assert result == GuildUser.get_by_id(1)
        assert result.guild == new_guild
        assert result.data["name"] == "testuser"
        assert result.data["lifetime_experience"] == 0
        assert "modified" in result.data
        assert self.user_svc.user_cache == {"1_1": "a", "1_600": "b", "100_1": "c"}

    @pytest.mark.asyncio()
    async def test_update_or_add_no_ctx(self, mock_member2, mock_guild2) -> None:
        """Test updating or adding a new user with a specified guild object."""
        # Setup
        self._clear_tests()
        new_guild = Guild.create(id=mock_guild2.id, name="Test Guild2")
        self.user_svc.user_cache = {"1_1": "a", "1_600": "b", "100_1": "c"}

        # WHEN update_or_add is called and a user is not in the database
        result = await self.user_svc.update_or_add(user=mock_member2, guild=mock_guild2)

        # THEN return the correct result and update the database with default values, and the cache is intact
        assert result == GuildUser.get_by_id(1)
        assert result.guild == new_guild
        assert result.data["name"] == "testuser2"
        assert result.data["lifetime_experience"] == 0
        assert "modified" in result.data
        assert self.user_svc.user_cache == {"1_1": "a", "1_600": "b", "100_1": "c"}

    @pytest.mark.asyncio()
    async def test_update_or_add_existing_user(self, mock_ctx) -> None:
        """Test updating an existing user."""
        # Setup
        self._clear_tests()
        GuildUser.create(guild=1, user=1, data={"test": "data"})
        updates = {
            "new_key": "new_value",
            "test": "new_data",
        }
        self.user_svc.user_cache = {"1_1": "a", "1_600": "b", "100_1": "c"}

        # WHEN update_or_add is called again
        result = await self.user_svc.update_or_add(mock_ctx, data=updates)

        # THEN return the correct result and update the database with the new values, and the cache is cleared
        assert result == GuildUser.get_by_id(1)
        assert result.data["name"] == "testuser"
        assert result.data["test"] == "new_data"
        assert result.data["new_key"] == "new_value"
        assert result.data["lifetime_experience"] == 0
        assert self.user_svc.user_cache == {"100_1": "c"}

    @pytest.mark.asyncio()
    async def test_update_or_add_existing_user_existing_data(self, mock_ctx) -> None:
        """Test updating an existing user with existing data."""
        # Setup
        self._clear_tests()
        GuildUser.create(
            guild=1,
            user=mock_ctx.author.id,
            data={
                "test": "data",
                "experience": 100,
                "lifetime_experience": 200,
                "name": "testuser_old",
            },
        )
        updates = {
            "new_key": "new_value",
            "test": "new_data",
        }
        self.user_svc.user_cache = {"1_1": "a", "1_600": "b", "100_1": "c"}

        # WHEN update_or_add is called again
        result = await self.user_svc.update_or_add(mock_ctx, data=updates)

        # THEN return the correct result and update the database with the new values, and the cache is cleared
        assert result == GuildUser.get_by_id(1)
        assert result.data["name"] == "testuser"
        assert result.data["test"] == "new_data"
        assert result.data["new_key"] == "new_value"
        assert result.data["experience"] == 100
        assert result.data["lifetime_experience"] == 200
        assert self.user_svc.user_cache == {"100_1": "c"}

    @pytest.mark.asyncio()
    async def test_update_or_add_existing_user_with_user(self, mock_ctx, mocker) -> None:
        """Test updating an existing user with existing data."""
        # Setup
        self._clear_tests()
        user = GuildUser.create(
            guild=1,
            user=1,
            data={
                "test": "data",
                "experience": 100,
                "lifetime_experience": 200,
                "name": "testuser_old",
            },
        )
        updates = {
            "new_key": "new_value",
            "test": "new_data",
        }
        self.user_svc.user_cache = {"1_1": "a", "1_600": "b", "100_1": "c"}

        # GIVEN a discord.Guild object and a discord.User object
        mocker.patch("discord.utils.get", return_value=mock_ctx.author)  # patch discord.utils.get
        mocker.patch(
            "discord.utils.get_or_fetch", return_value=mock_ctx.guild
        )  # patch discord.utils.get

        # WHEN update_or_add is called again
        result = await self.user_svc.update_or_add(mock_ctx, user=user, data=updates)

        # THEN return the correct result and update the database with the new values, and the cache is cleared
        assert result == GuildUser.get_by_id(1)
        assert result.data["name"] == "testuser"
        assert result.data["test"] == "new_data"
        assert result.data["new_key"] == "new_value"
        assert result.data["experience"] == 100
        assert result.data["lifetime_experience"] == 200
        assert self.user_svc.user_cache == {"100_1": "c"}

    @pytest.mark.parametrize(
        (
            "permission_value",
            "is_admin",
            "is_storyteller",
            "expected",
        ),
        [
            (PermissionManageCampaign.UNRESTRICTED.value, True, False, True),
            (PermissionManageCampaign.UNRESTRICTED.value, False, False, True),
            (PermissionManageCampaign.UNRESTRICTED.value, False, True, True),
            (PermissionManageCampaign.STORYTELLER_ONLY.value, True, False, True),
            (PermissionManageCampaign.STORYTELLER_ONLY.value, False, False, False),
            (PermissionManageCampaign.STORYTELLER_ONLY.value, False, True, True),
        ],
    )
    def test_can_manage_campaigns(
        self, mocker, permission_value, is_admin, is_storyteller, expected
    ):
        """Test checking if a user has campaign management permissions.

        This test ensures that:
        1. The correct permission is checked based on the user's roles and admin status.
        2. The expected boolean value is returned.
        """
        # GIVEN a mock ApplicationContext with specific roles and permissions
        mock_player_role = mocker.Mock(spec=Role)
        mock_player_role.name = "Player"

        mock_storyteller_role = mocker.Mock(spec=Role)
        mock_storyteller_role.name = "Storyteller"

        mock_ctx = mocker.Mock(spec=ApplicationContext)
        mock_ctx.author.guild_permissions.administrator = is_admin

        mock_ctx.author.roles = [mock_player_role]
        if is_storyteller:
            mock_ctx.author.roles.append(mock_storyteller_role)

        mock_ctx.author.id = 1

        # Mock bot and guild service objects
        mock_bot = mocker.Mock()
        mock_guild_service = mocker.Mock()

        # Mock the fetch_guild_settings function to return specific settings
        mock_settings = {"permissions_manage_campaigns": permission_value}
        mock_guild_service.fetch_guild_settings = mocker.Mock(return_value=mock_settings)

        mock_bot.guild_svc = mock_guild_service
        mock_ctx.bot = mock_bot

        # WHEN the can_manage_campaign method is called with the mock context
        actual_result = self.user_svc.can_manage_campaign(mock_ctx)

        # THEN the actual result should match the expected result
        assert actual_result is expected

    @pytest.mark.parametrize(
        (
            "trait_permissions_value",
            "is_admin",
            "is_char_owner",
            "hours_since_creation",
            "expected",
        ),
        [
            (PermissionsEditTrait.UNRESTRICTED.value, False, True, 38, True),
            (PermissionsEditTrait.WITHIN_24_HOURS.value, False, True, 1, True),
            (PermissionsEditTrait.WITHIN_24_HOURS.value, False, True, 38, False),
            (PermissionsEditTrait.WITHIN_24_HOURS.value, True, True, 38, True),
            (PermissionsEditTrait.WITHIN_24_HOURS.value, False, False, 1, False),
            (PermissionsEditTrait.CHARACTER_OWNER_ONLY.value, True, False, 38, True),
            (PermissionsEditTrait.CHARACTER_OWNER_ONLY.value, False, False, 38, False),
            (PermissionsEditTrait.CHARACTER_OWNER_ONLY.value, False, True, 38, True),
            (PermissionsEditTrait.STORYTELLER_ONLY.value, False, True, 1, False),
            (PermissionsEditTrait.STORYTELLER_ONLY.value, False, False, 1, False),
            (PermissionsEditTrait.STORYTELLER_ONLY.value, True, False, 1, True),
        ],
    )
    def test_has_update_trait_permissions(
        self,
        mocker,
        trait_permissions_value,
        is_admin,
        is_char_owner,
        hours_since_creation,
        expected,
    ):
        """Test checking if a user has update trait permissions.

        GIVEN a user and a character
        WHEN the user and character are checked
        THEN the correct result is returned
        """
        # GIVEN a mock ApplicationContext and Character
        mock_role1 = mocker.Mock(spec=Role)
        mock_role1.name = "Player"

        mock_role2 = mocker.Mock(spec=Role)
        mock_role2.name = "@everyone"

        mock_ctx = mocker.Mock(spec=ApplicationContext)
        mock_ctx.author.guild_permissions.administrator = is_admin
        mock_ctx.author.roles = [mock_role1]
        mock_ctx.author.id = 1

        mock_character = mocker.Mock(spec=Character)
        mock_character.created_by.id = 1 if is_char_owner else 2
        mock_character.created = arrow.utcnow().shift(hours=-hours_since_creation).datetime
        # the author is the creator of the character

        # Create mock bot and guild_svc and set them on mock_ctx
        mock_bot = mocker.Mock()
        mock_guild_svc = mocker.Mock()

        # Set up the mock fetch_guild_settings function
        mock_settings = {"permissions_edit_trait": trait_permissions_value}
        mock_guild_svc.fetch_guild_settings = mocker.Mock(return_value=mock_settings)

        mock_bot.guild_svc = mock_guild_svc
        mock_ctx.bot = mock_bot

        # WHEN calling the method with the mock context and character
        result = self.user_svc.can_update_traits(mock_ctx, mock_character)

        # THEN return the correct result
        assert result is expected

    @pytest.mark.parametrize(
        ("xp_permissions_value", "is_admin", "is_char_owner", "hours_since_creation", "expected"),
        [
            (PermissionsEditXP.UNRESTRICTED.value, False, True, 38, True),
            (PermissionsEditXP.WITHIN_24_HOURS.value, False, True, 1, True),
            (PermissionsEditXP.WITHIN_24_HOURS.value, False, True, 38, False),
            (PermissionsEditXP.WITHIN_24_HOURS.value, True, True, 38, True),
            (PermissionsEditXP.WITHIN_24_HOURS.value, False, False, 1, False),
            (PermissionsEditXP.CHARACTER_OWNER_ONLY.value, True, False, 38, True),
            (PermissionsEditXP.CHARACTER_OWNER_ONLY.value, False, False, 38, False),
            (PermissionsEditXP.CHARACTER_OWNER_ONLY.value, False, True, 38, True),
            (PermissionsEditXP.STORYTELLER_ONLY.value, False, True, 1, False),
            (PermissionsEditXP.STORYTELLER_ONLY.value, False, False, 1, False),
            (PermissionsEditXP.STORYTELLER_ONLY.value, True, False, 1, True),
        ],
    )
    def test_can_update_xp(
        self, mocker, xp_permissions_value, is_admin, is_char_owner, hours_since_creation, expected
    ):
        """Test checking if a user has xp permissions.

        GIVEN a user and a character
        WHEN the user and character are checked
        THEN the correct result is returned
        """
        # GIVEN a mock ApplicationContext and Character
        mock_role1 = mocker.Mock(spec=Role)
        mock_role1.name = "Player"

        mock_ctx = mocker.Mock(spec=ApplicationContext)
        mock_ctx.author.guild_permissions.administrator = is_admin
        mock_ctx.author.roles = [mock_role1]

        mock_character = mocker.Mock(spec=Character)
        mock_character.created_by.id = 1 if is_char_owner else 2
        mock_character.created = arrow.utcnow().shift(hours=-hours_since_creation).datetime
        mock_ctx.author.id = 1  # the author is the creator of the character

        # Create mock bot and guild_svc and set them on mock_ctx
        mock_bot = mocker.Mock()
        mock_guild_svc = mocker.Mock()

        # Set up the mock fetch_guild_settings function
        mock_settings = {"permissions_edit_xp": xp_permissions_value}
        mock_guild_svc.fetch_guild_settings = mocker.Mock(return_value=mock_settings)

        mock_bot.guild_svc = mock_guild_svc
        mock_ctx.bot = mock_bot

        # WHEN calling the method with the mock context and character
        result = self.user_svc.can_update_xp(mock_ctx, mock_character)

        # THEN return the correct result
        assert result is expected

    def test_purge_all(self):
        """Test purging all users from the cache.

        Given a cache with users
        When the cache is purged
        Then the cache is empty
        """
        # GIVEN: A populated user and active character cache
        self.user_svc.user_cache = {"1_1": "user_a", "2_2": "user_b"}
        self.user_svc.active_character_cache = {"1": "character_a", "2": "character_b"}

        # WHEN: The cache is purged
        self.user_svc.purge_cache()

        # THEN: Both caches should be empty
        assert self.user_svc.user_cache == {}
        assert self.user_svc.active_character_cache == {}

    def test_purge_by_id(self, mock_ctx):
        """Test purging a user from the cache.

        Given a cache with two users
        When one user is purged
        Then the cache contains only the other user
        """
        # GIVEN data in the caches
        self.user_svc.user_cache = {"1_1": "a", "1_600": "b", "100_1": "c"}
        self.user_svc.active_character_cache = {"1_1": "a", "1_600": "b", "100_1": "c"}

        # WHEN purging the cache with a ctx object
        self.user_svc.purge_cache(mock_ctx)

        # # THEN only data related to other guilds should remain in the cache
        assert self.user_svc.user_cache == {"100_1": "c"}
        assert self.user_svc.active_character_cache == {"100_1": "c"}

    @pytest.mark.asyncio()
    async def test_fetch_user_from_database_and_cache(self, mock_ctx, caplog) -> None:
        """Test fetching a user from the database and cache.

        GIVEN: A user in the database.
        WHEN: The user is fetched using a context object.
        THEN: The correct user should be returned and the cache should be updated.
        """
        # Clear any previous test data
        self._clear_tests()

        # GIVEN: A user in the database
        existing_user = GuildUser.create(guild=mock_ctx.guild.id, user=mock_ctx.author.id)
        self.user_svc.user_cache["1_2"] = "a"
        self.user_svc.user_cache["2_1"] = "b"

        # WHEN: fetch_user is called with a context object
        caplog.clear()
        fetched_user = await self.user_svc.fetch_user(mock_ctx)
        logs_from_database_fetch = caplog.text

        # THEN: Return the correct user and update the cache
        assert fetched_user == existing_user
        assert self.user_svc.user_cache["1_1"] == existing_user
        assert self.user_svc.user_cache["1_2"] == "a"
        assert self.user_svc.user_cache["2_1"] == "b"
        assert "DATABASE: Fetch user" in logs_from_database_fetch
        assert "CACHE" not in logs_from_database_fetch

        # WHEN: fetch_user is called again with the same context
        caplog.clear()
        fetched_user = await self.user_svc.fetch_user(mock_ctx)
        logs_from_cache_fetch = caplog.text

        # THEN: Return the correct user from the cache
        assert fetched_user == existing_user
        assert "CACHE: Return user" in logs_from_cache_fetch
        assert "DATABASE" not in logs_from_cache_fetch

    @pytest.mark.asyncio()
    async def test_fetch_user_with_user(self, mock_ctx, mock_member2) -> None:
        """Test fetching a user from the database and cache while specifying a user."""
        # Clear any previous test data
        self._clear_tests()

        # GIVEN: A specified user (mock_member2)
        # WHEN: fetch_user is called with the specified user which does not exist in the database
        fetched_user = await self.user_svc.fetch_user(mock_ctx, user=mock_member2)

        # THEN: Create the user in the database, return the correct user, and update the cache
        assert fetched_user == GuildUser.get_by_id(1)
        assert self.user_svc.user_cache["1_2"] == GuildUser.get_by_id(1)

    @pytest.mark.asyncio()
    async def test_fetch_guild_users_current_guild(self, mock_ctx, mocker, mock_member2) -> None:
        """Test fetching all users in the current guild."""
        # Setup
        self._clear_tests()

        # GIVEN a discord.Guild object and a discord.User object
        user1 = GuildUser.create(
            guild=mock_ctx.guild.id,
            user=1,
            name="Test User1",
            data={"test": "data"},
        )
        user2 = GuildUser.create(
            guild=mock_ctx.guild.id,
            user=2,
            name="Test User2",
            data={"test": "data"},
        )

        # WHEN fetch_guild_users is called
        mocker.patch(
            "discord.utils.get", side_effect=[mock_ctx.author, mock_member2]
        )  # patch discord.utils.get
        mocker.patch(
            "discord.utils.get_or_fetch", return_value=mock_ctx.guild
        )  # patch discord.utils.get
        result = await self.user_svc.fetch_guild_users(mock_ctx)

        # THEN return only users in the current guild
        assert result == [user1, user2]
        assert self.user_svc.user_cache["1_1"] == user1
        assert self.user_svc.user_cache["1_2"] == user2

    @pytest.mark.asyncio()
    async def test_fetch_guild_users_no_users(self, mock_ctx4, mocker) -> None:
        """Test fetching all users in a guild with no users."""
        # Setup
        self._clear_tests()
        mocker.patch(
            "valentina.models.users.UserService.fetch_user",
            return_value=None,
        )

        # WHEN fetch_guild_users is called
        result = await self.user_svc.fetch_guild_users(mock_ctx4)

        # THEN return an empty list
        assert result == []

    @pytest.mark.asyncio()
    async def test_fetch_player_characters(self, mock_ctx) -> None:
        """Test fetching all player characters.

        This test ensures that:
        1. All player characters are fetched correctly.
        2. Only alive player characters are fetched when specified.
        """
        # Setup: Clear any existing tests or data
        self._clear_tests()

        user1 = self._create_user_from_ctx(mock_ctx)
        user2 = GuildUser.create(guild=mock_ctx.guild.id, user=200200)

        # GIVEN multiple characters with different attributes
        alive_character1 = Character.create(
            data={
                "first_name": "char1",
                "last_name": "character",
                "storyteller_character": False,
                "player_character": True,
                "is_alive": True,
            },
            char_class=1,
            guild=mock_ctx.guild.id,
            created_by=user1,
            owned_by=user1,
            clan=1,
        )
        alive_character2 = Character.create(
            data={
                "first_name": "char2",
                "last_name": "character",
                "storyteller_character": False,
                "player_character": True,
                "is_alive": True,
            },
            char_class=1,
            guild=mock_ctx.guild.id,
            created_by=user1,
            owned_by=user1,
            clan=1,
        )
        dead_character = Character.create(
            data={
                "first_name": "char3",
                "last_name": "character",
                "storyteller_character": False,
                "player_character": True,
                "is_alive": False,
            },
            char_class=1,
            guild=mock_ctx.guild.id,
            created_by=user1,
            owned_by=user1,
            clan=1,
        )
        # Create additional characters that should not be fetched
        Character.create(
            data={
                "first_name": "char4",
                "last_name": "character",
                "storyteller_character": True,
                "player_character": False,
                "is_alive": True,
            },
            char_class=1,
            guild=mock_ctx.guild.id,
            created_by=user1,
            owned_by=user1,
            clan=1,
        )
        Character.create(
            data={
                "first_name": "char5",
                "last_name": "character",
                "storyteller_character": False,
                "player_character": True,
                "is_alive": True,
            },
            char_class=1,
            guild=mock_ctx.guild.id,
            created_by=user2,
            owned_by=user2,
            clan=1,
        )
        Character.create(
            data={
                "first_name": "char5",
                "last_name": "character",
                "storyteller_character": False,
                "player_character": True,
                "is_alive": True,
            },
            char_class=1,
            guild=mock_ctx.guild.id + 1,
            created_by=user1,
            owned_by=user1,
            clan=1,
        )

        # WHEN fetch_player_characters is called
        fetched_characters = await self.user_svc.fetch_player_characters(mock_ctx)

        # THEN all player characters should be fetched
        assert fetched_characters == [alive_character1, alive_character2, dead_character]

        # WHEN fetch_player_characters is called with alive_only=True
        fetched_alive_characters = await self.user_svc.fetch_player_characters(
            mock_ctx, alive_only=True
        )

        # THEN only alive player characters should be fetched
        assert fetched_alive_characters == [alive_character1, alive_character2]

    @pytest.mark.asyncio()
    async def test_fetch_active_character(self, mock_ctx, caplog) -> None:
        """Test fetching an active character.

        This test ensures that:
        1. An error is raised when no active character exists.
        2. The database is queried when the cache is empty.
        3. The cache is used when it contains the active character.
        """
        # Setup: Clear any existing tests or data
        self._clear_tests()
        user1 = self._create_user_from_ctx(mock_ctx)
        character = Character.create(
            data={
                "first_name": "character",
                "last_name": "character4",
                "player_character": True,
                "is_active": False,
            },
            char_class=1,
            guild=mock_ctx.guild.id,
            created_by=user1,
            owned_by=user1,
            clan=1,
        )

        # WHEN fetch_active_character is called
        # THEN an error should be raised indicating that no active character exists
        with pytest.raises(errors.NoActiveCharacterError):
            await self.user_svc.fetch_active_character(mock_ctx)

        # GIVEN an active character in the database and an empty cache
        character.data["is_active"] = True
        character.save()

        # WHEN fetch_active_character is called
        fetched_character = await self.user_svc.fetch_active_character(mock_ctx)
        logged_messages = caplog.text

        # THEN the active character should be fetched from the database
        assert fetched_character == character
        assert "DATABASE: Fetch active character" in logged_messages
        assert "CACHE: Return active character" not in logged_messages

        # Clear the log for the next test
        caplog.clear()

        # WHEN fetch_active_character is called again
        fetched_character = await self.user_svc.fetch_active_character(mock_ctx)
        logged_messages = caplog.text

        # THEN the active character should be fetched from the cache
        assert fetched_character == character
        assert "CACHE: Return active character" in logged_messages
        assert "DATABASE: Fetch active character" not in logged_messages

    @pytest.mark.asyncio()
    async def test_set_active_character(self, mock_ctx) -> None:
        """Test switching active characters.

        This test ensures that when the active character is switched:
        1. The database is updated correctly.
        2. The active character cache is updated.
        """
        # Setup: Clear any existing tests or data
        self._clear_tests()

        # GIVEN two characters owned by the same user, one active and one inactive, and an active character cache
        user1 = self._create_user_from_ctx(mock_ctx)
        active_character = Character.create(
            data={
                "first_name": "char1",
                "last_name": "character",
                "storyteller_character": False,
                "player_character": True,
                "is_alive": True,
                "is_active": True,
            },
            char_class=1,
            guild=mock_ctx.guild.id,
            created_by=user1,
            owned_by=user1,
            clan=1,
        )
        inactive_character = Character.create(
            data={
                "first_name": "char2",
                "last_name": "character",
                "storyteller_character": False,
                "player_character": True,
                "is_alive": True,
                "is_active": False,
            },
            char_class=1,
            guild=mock_ctx.guild.id,
            created_by=user1,
            owned_by=user1,
            clan=1,
        )
        self.user_svc.active_character_cache = {
            f"{mock_ctx.guild.id}_{mock_ctx.author.id}": active_character
        }

        # WHEN the active character is switched to the inactive one
        await self.user_svc.set_active_character(mock_ctx, inactive_character)

        # THEN the previously active character should now be inactive, the previously inactive character should now be active, and the active character cache should be updated
        assert not Character.get_by_id(active_character.id).data["is_active"]
        assert Character.get_by_id(inactive_character.id).data["is_active"]
        assert self.user_svc.active_character_cache == {
            f"{mock_ctx.guild.id}_{mock_ctx.author.id}": inactive_character
        }

    @pytest.mark.asyncio()
    async def test_transfer_character_owner(self, mock_ctx, mocker) -> None:
        """Test transferring character ownership from one user to another.

        This test ensures that when a character's ownership is transferred, the database is updated correctly, and the active character cache is cleared.
        """
        self._clear_tests()

        # GIVEN a character owned by one user and a second user
        user1 = self._create_user_from_ctx(mock_ctx)
        character1 = Character.create(
            data={
                "first_name": "char1_to_transfer",
                "last_name": "character",
                "storyteller_character": False,
                "player_character": True,
                "is_alive": True,
                "is_active": True,
            },
            char_class=1,
            guild=mock_ctx.guild.id,
            created_by=user1,
            owned_by=user1,
            clan=1,
        )
        self.user_svc.active_character_cache = {
            f"{mock_ctx.guild.id}_{mock_ctx.author.id}": character1
        }

        mock_member = mocker.MagicMock()
        mock_member.id = 15001500051
        mock_member.display_name = "Test User 15001500051"
        mock_member.name = "testuser 15001500051"
        mock_member.mention = "<@15001500051>"
        mock_member.nick = "nickname"
        mock_member.__class__ = discord.Member

        # WHEN transfer_character_owner is called
        await self.user_svc.transfer_character_owner(mock_ctx, character1, mock_member)

        # THEN the character is owned by the second user and the active character cache is cleared
        assert Character.get_by_id(character1.id).owned_by.user == 15001500051
        assert self.user_svc.active_character_cache == {}
