# type: ignore
"""Test the UserService class."""

import arrow
import discord
import pytest
from discord import ApplicationContext, Role

from valentina.constants import PermissionManageCampaign, PermissionsEditTrait, PermissionsEditXP
from valentina.models import UserService
from valentina.models.db_tables import Character, User
from valentina.utils import errors


@pytest.mark.usefixtures("mock_db")
class TestUserService:
    """Test the user service."""

    user_svc = UserService()

    def _clear_tests(self):
        """Clear the test database."""
        for user in User.select():
            user.delete_instance(recursive=True, delete_nullable=True)

        self.user_svc.purge_cache()

    def test_fetch_user_from_database_and_cache(self, mock_ctx, mock_member2, caplog) -> None:
        """Test fetching a user from the database and cache.

        GIVEN: A user in the database.
        WHEN: The user is fetched using a context object.
        THEN: The correct user should be returned and the cache should be updated.
        """
        # Clear any previous test data
        self._clear_tests()

        # GIVEN: A user in the database
        existing_user = User.create(id=1, name="Test User")

        # WHEN: fetch_user is called with a context object
        caplog.clear()
        fetched_user = self.user_svc.fetch_user(mock_ctx)
        logs_from_database_fetch = caplog.text

        # THEN: Return the correct user and update the cache
        assert fetched_user == existing_user
        assert self.user_svc.user_cache["1_1"] == existing_user
        assert "DATABASE: Fetch user" in logs_from_database_fetch
        assert "CACHE" not in logs_from_database_fetch

        # WHEN: fetch_user is called again with the same context
        caplog.clear()
        fetched_user = self.user_svc.fetch_user(mock_ctx)
        logs_from_cache_fetch = caplog.text

        # THEN: Return the correct user from the cache
        assert fetched_user == existing_user
        assert "CACHE: Return user" in logs_from_cache_fetch
        assert "DATABASE" not in logs_from_cache_fetch

        # GIVEN: A specified user (mock_member2)
        # WHEN: fetch_user is called with the specified user
        fetched_user = self.user_svc.fetch_user(mock_ctx, user=mock_member2)

        # THEN: Return the correct user and update the cache
        assert fetched_user == User.get_by_id(2)
        assert self.user_svc.user_cache["1_2"] == User.get_by_id(2)

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

    def test_fetch_player_characters(self, mock_ctx) -> None:
        """Test fetching all player characters.

        This test ensures that:
        1. All player characters are fetched correctly.
        2. Only alive player characters are fetched when specified.
        """
        # Setup: Clear any existing tests or data
        self._clear_tests()

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
            created_by=mock_ctx.author.id,
            owned_by=mock_ctx.author.id,
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
            created_by=mock_ctx.author.id,
            owned_by=mock_ctx.author.id,
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
            created_by=mock_ctx.author.id,
            owned_by=mock_ctx.author.id,
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
            created_by=mock_ctx.author.id,
            owned_by=mock_ctx.author.id,
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
            created_by=mock_ctx.author.id,
            owned_by=mock_ctx.author.id,
            clan=1,
        )

        # WHEN fetch_player_characters is called
        fetched_characters = self.user_svc.fetch_player_characters(mock_ctx)

        # THEN all player characters should be fetched
        assert fetched_characters == [alive_character1, alive_character2, dead_character]

        # WHEN fetch_player_characters is called with alive_only=True
        fetched_alive_characters = self.user_svc.fetch_player_characters(mock_ctx, alive_only=True)

        # THEN only alive player characters should be fetched
        assert fetched_alive_characters == [alive_character1, alive_character2]

    def test_fetch_active_character(self, mock_ctx, caplog) -> None:
        """Test fetching an active character.

        This test ensures that:
        1. An error is raised when no active character exists.
        2. The database is queried when the cache is empty.
        3. The cache is used when it contains the active character.
        """
        # Setup: Clear any existing tests or data
        self._clear_tests()
        character = Character.create(
            data={
                "first_name": "character",
                "last_name": "character4",
                "player_character": True,
                "is_active": False,
            },
            char_class=1,
            guild=1,
            created_by=1,
            owned_by=1,
            clan=1,
        )

        # WHEN fetch_active_character is called
        # THEN an error should be raised indicating that no active character exists
        with pytest.raises(errors.NoActiveCharacterError):
            self.user_svc.fetch_active_character(mock_ctx)

        # GIVEN an active character in the database and an empty cache
        character.data["is_active"] = True
        character.save()

        # WHEN fetch_active_character is called
        fetched_character = self.user_svc.fetch_active_character(mock_ctx)
        logged_messages = caplog.text

        # THEN the active character should be fetched from the database
        assert fetched_character == character
        assert "DATABASE: Fetch active character" in logged_messages
        assert "CACHE: Return active character" not in logged_messages

        # Clear the log for the next test
        caplog.clear()

        # WHEN fetch_active_character is called again
        fetched_character = self.user_svc.fetch_active_character(mock_ctx)
        logged_messages = caplog.text

        # THEN the active character should be fetched from the cache
        assert fetched_character == character
        assert "CACHE: Return active character" in logged_messages
        assert "DATABASE: Fetch active character" not in logged_messages

    def test_set_active_character(self, mock_ctx) -> None:
        """Test switching active characters.

        This test ensures that when the active character is switched:
        1. The database is updated correctly.
        2. The active character cache is updated.
        """
        # Setup: Clear any existing tests or data
        self._clear_tests()

        # GIVEN two characters owned by the same user, one active and one inactive, and an active character cache
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
            created_by=mock_ctx.author.id,
            owned_by=mock_ctx.author.id,
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
            created_by=mock_ctx.author.id,
            owned_by=mock_ctx.author.id,
            clan=1,
        )
        self.user_svc.active_character_cache = {
            f"{mock_ctx.guild.id}_{mock_ctx.author.id}": active_character
        }

        # WHEN the active character is switched to the inactive one
        self.user_svc.set_active_character(mock_ctx, inactive_character)

        # THEN the previously active character should now be inactive, the previously inactive character should now be active, and the active character cache should be updated
        assert not Character.get_by_id(active_character.id).data["is_active"]
        assert Character.get_by_id(inactive_character.id).data["is_active"]
        assert self.user_svc.active_character_cache == {
            f"{mock_ctx.guild.id}_{mock_ctx.author.id}": inactive_character
        }

    def test_transfer_character_owner(self, mock_ctx, mocker) -> None:
        """Test transferring character ownership from one user to another.

        This test ensures that when a character's ownership is transferred, the database is updated correctly, and the active character cache is cleared.
        """
        self._clear_tests()

        # GIVEN a character owned by one user and a second user
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
            created_by=mock_ctx.author.id,
            owned_by=mock_ctx.author.id,
            clan=1,
        )
        self.user_svc.active_character_cache = {
            f"{mock_ctx.guild.id}_{mock_ctx.author.id}": Character.get_by_id(character1.id)
        }

        mock_member = mocker.MagicMock()
        mock_member.id = 15001500051
        mock_member.display_name = "Test User 15001500051"
        mock_member.name = "testuser 15001500051"
        mock_member.mention = "<@15001500051>"
        mock_member.__class__ = discord.Member

        # WHEN transfer_character_owner is called
        self.user_svc.transfer_character_owner(mock_ctx, character1, mock_member)

        # THEN the character is owned by the second user and the active character cache is cleared
        assert Character.get_by_id(character1.id).owned_by.id == 15001500051
        assert self.user_svc.active_character_cache == {}

    def test_update_or_add_user_new_user(self, mock_ctx) -> None:
        """Test updating or adding a new user."""
        # Setup
        self._clear_tests()
        data = {"test": "data"}
        self.user_svc.user_cache = {"1_1": "a", "1_600": "b", "100_1": "c"}

        # WHEN update_or_add_user is called and a user is not in the database
        result = self.user_svc.update_or_add_user(mock_ctx, data=data)

        # THEN return the correct result and update the database with default values, and the cache is intact
        assert result == User.get_by_id(1)
        assert result.name == "Test User"
        assert result.data["test"] == "data"
        assert str(mock_ctx.guild.id) in result.data
        assert "modified" in result.data[str(mock_ctx.guild.id)]
        assert "experience" in result.data[str(mock_ctx.guild.id)]
        assert self.user_svc.user_cache == {"1_1": "a", "1_600": "b", "100_1": "c"}

    def test_update_or_add_user_existing_user(self, mock_ctx) -> None:
        """Test updating an existing user."""
        # Setup
        self._clear_tests()
        User.create(id=1, name="Test User", data={"test": "data"})
        updates = {
            "new_key": "new_value",
            "test": "new_data",
            str(mock_ctx.guild.id): {"test": "data", "key": "value"},
        }
        self.user_svc.user_cache = {"1_1": "a", "1_600": "b", "100_1": "c"}

        # WHEN update_or_add_user is called again
        result = self.user_svc.update_or_add_user(mock_ctx, data=updates)

        # THEN return the correct result and update the database with the new values, and the cache is cleared
        assert result == User.get_by_id(1)
        assert result.name == "Test User"
        assert result.data["test"] == "new_data"
        assert result.data["new_key"] == "new_value"
        assert str(mock_ctx.guild.id) in result.data
        assert result.data[str(mock_ctx.guild.id)]["test"] == "data"
        assert result.data[str(mock_ctx.guild.id)]["key"] == "value"
        assert self.user_svc.user_cache == {"100_1": "c"}

    def test_update_or_add_user_specified_user(self, mock_member2) -> None:
        """Test updating or adding a user when a specific user is provided."""
        # Setup
        self._clear_tests()
        data = {"test": "data"}

        # WHEN update_or_add_user is called again with a specified user that doesn't exist
        result = self.user_svc.update_or_add_user(ctx=None, user=mock_member2, data=data)

        # THEN return the correct result and update the database with the new values
        assert result == User.get_by_id(2)
        assert result.name == "Test User2"
        assert result.data["test"] == "data"

    def test_update_or_add_user_no_default_values(self, mock_ctx, mocker) -> None:
        """Test updating or adding a user that exists but does not have default values."""
        # Setup
        self._clear_tests()
        mock_member3 = mocker.MagicMock()
        mock_member3.id = 300
        mock_member3.display_name = "Test User3"
        mock_member3.name = "testuser3"
        mock_member3.mention = "<@3>"
        mock_member3.__class__ = discord.Member
        User.create(id=300, name="Test User3")

        # WHEN update_or_add_user is called for that user
        result = self.user_svc.update_or_add_user(mock_ctx, user=mock_member3)

        # THEN return the correct result and update the database with the default values
        assert result == User.get_by_id(300)
        assert result.name == "Test User3"
        assert result.data[str(mock_ctx.guild.id)]["experience"] == 0
        assert "modified" in result.data[str(mock_ctx.guild.id)]

    def test_fetch_guild_users_current_guild(self, mock_ctx, mocker) -> None:
        """Test fetching all users in the current guild."""
        # Setup
        self._clear_tests()
        mocker.patch(
            "valentina.models.users.UserService.fetch_user",
            return_value=None,
        )
        User.create(
            id=1,
            name="Test User1",
            data={
                "test": "data",
                str(mock_ctx.guild.id): {"test": "data"},
            },
        )
        User.create(
            id=2,
            name="Test User2",
            data={
                "test": "data",
                str(mock_ctx.guild.id): {"test": "data"},
            },
        )

        # WHEN fetch_guild_users is called
        result = self.user_svc.fetch_guild_users(mock_ctx)

        # THEN return only users in the current guild
        assert set(result) == set(User.select().where(User.id << [1, 2]))

    def test_fetch_guild_users_different_guild(self, mock_ctx2, mocker) -> None:
        """Test fetching all users in a different guild."""
        # Setup
        self._clear_tests()
        mocker.patch(
            "valentina.models.users.UserService.fetch_user",
            return_value=None,
        )
        User.create(
            id=2,
            name="Test User2",
            data={
                "test": "data",
                str(mock_ctx2.guild.id): {"test": "data"},
            },
        )
        User.create(
            id=3,
            name="Test User3",
            data={
                "test": "data",
                str(mock_ctx2.guild.id): {"test": "data"},
            },
        )

        # WHEN fetch_guild_users is called
        result = self.user_svc.fetch_guild_users(mock_ctx2)

        # THEN return only users in the current guild
        assert set(result) == set(User.select().where(User.id << [2, 3]))

    def test_fetch_guild_users_no_users(self, mock_ctx4, mocker) -> None:
        """Test fetching all users in a guild with no users."""
        # Setup
        self._clear_tests()
        mocker.patch(
            "valentina.models.users.UserService.fetch_user",
            return_value=None,
        )

        # WHEN fetch_guild_users is called
        result = self.user_svc.fetch_guild_users(mock_ctx4)

        # THEN return an empty list
        assert result == []

    def test__get_member_and_guild_application_context(self, mock_ctx):
        """Test getting the member and guild from an ApplicationContext."""
        # GIVEN a context object with a guild and a user
        # WHEN _get_member_and_guild is called
        member, guild = self.user_svc._get_member_and_guild(mock_ctx)

        # THEN return the correct member and guild
        assert member == mock_ctx.author
        assert guild == mock_ctx.guild

    def test__get_member_and_guild_autocomplete_context(self, mock_autocomplete_ctx1):
        """Test getting the member and guild from an AutocompleteContext."""
        # GIVEN an autocomplete context object with a guild and a user
        # WHEN _get_member_and_guild is called
        member, guild = self.user_svc._get_member_and_guild(mock_autocomplete_ctx1)

        # THEN return the correct member and guild
        assert member == mock_autocomplete_ctx1.interaction.user
        assert guild == mock_autocomplete_ctx1.interaction.guild

    def test__get_member_and_guild_with_user_object(self, mock_ctx, mocker):
        """Test getting the member and guild when a User object is provided."""
        # Setup the tests
        self._clear_tests()
        user1 = User.create(
            id=1,
            name="Test User1",
            data={
                "test": "data",
                str(mock_ctx.guild.id): {"test": "data"},
            },
        )

        # GIVEN a context object and a User object
        mocker.patch("discord.utils.get", return_value=user1)  # patch discord.utils.get

        # WHEN _get_member_and_guild is called
        member, guild = self.user_svc._get_member_and_guild(mock_ctx, user=mock_ctx.author)

        # THEN return the correct member and guild
        assert guild.id == mock_ctx.guild.id
        assert member == mock_ctx.author
