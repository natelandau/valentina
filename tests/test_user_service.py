# type: ignore
"""Test the UserService class."""

import arrow
import discord
import pytest
from discord import ApplicationContext, Role

from valentina.constants import PermissionManageCampaign, PermissionsEditTrait, PermissionsEditXP
from valentina.models import UserService
from valentina.models.db_tables import Character, GuildUser, User
from valentina.utils import errors


@pytest.mark.usefixtures("mock_db")
class TestUserService:
    """Test the user service."""

    user_svc = UserService()

    def _clear_tests(self):
        """Clear the test database."""
        for user in User.select():
            user.delete_instance(recursive=True, delete_nullable=True)

        for guild_user in GuildUser.select():
            guild_user.delete_instance(recursive=True, delete_nullable=True)

        self.user_svc.purge_cache()

    def test_fetch_user(self, mock_ctx, mock_member2, caplog):
        """Test fetching a user."""
        self._clear_tests()

        # GIVEN a user in the database
        user = User.create(id=1, name="Test User")

        # WHEN fetch_user is called with a context object
        caplog.clear()
        result = self.user_svc.fetch_user(mock_ctx)
        logs = caplog.text

        # THEN return the correct result and update the cache
        assert result == user
        assert self.user_svc.user_cache["1_1"] == user
        assert "DATABASE: Fetch user" in logs
        assert "CACHE" not in logs

        # WHEN fetch_user is called again
        caplog.clear()
        result = self.user_svc.fetch_user(mock_ctx)
        logs = caplog.text

        # THEN return the correct result from the cache
        assert result == user
        assert "CACHE: Return user" in logs
        assert "DATABASE" not in logs

        # GIVEN a specified user
        # WHEN fetch_user is called
        caplog.clear()
        result = self.user_svc.fetch_user(mock_ctx, user=mock_member2)
        logs = caplog.text

        # THEN return the correct result and update the cache
        assert result == User.get_by_id(2)
        assert self.user_svc.user_cache["1_2"] == User.get_by_id(2)

    def test_purge_all(self):
        """Test purging all users from the cache.

        Given a cache with users
        When the cache is purged
        Then the cache is empty
        """
        self.user_svc.user_cache = {"1_1": "a", "2_2": "b"}
        self.guild_user_cache = {"1_1": "a", "2_2": "b"}
        self.user_svc.active_character_cache = {"1": "a", "2": "b"}
        self.user_svc.purge_cache()
        assert self.user_svc.user_cache == {}
        assert self.user_svc.active_character_cache == {}
        assert self.user_svc.guild_user_cache == {}

    def test_purge_by_id(self, mock_ctx):
        """Test purging a user from the cache.

        Given a cache with two users
        When one user is purged
        Then the cache contains only the other user
        """
        # GIVEN data in the caches
        self.user_svc.user_cache = {"1_1": "a", "1_600": "b", "100_1": "c"}
        self.user_svc.guild_user_cache = {"1_1": "a", "1_600": "b", "100_1": "c"}
        self.user_svc.active_character_cache = {"1_1": "a", "1_600": "b", "100_1": "c"}

        # WHEN a guild is cached
        self.user_svc.purge_cache(mock_ctx)

        # THEN only that guild's data is removed from the cache
        assert self.user_svc.user_cache == {"100_1": "c"}
        assert self.user_svc.guild_user_cache == {"100_1": "c"}
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

        GIVEN a user
        WHEN the user is checked
        THEN the correct result is returned
        """
        # GIVEN mock ApplicationContexts
        mock_role1 = mocker.Mock(spec=Role)
        mock_role1.name = "Player"

        mock_role2 = mocker.Mock(spec=Role)
        mock_role2.name = "Storyteller"

        mock_ctx = mocker.Mock(spec=ApplicationContext)
        mock_ctx.author.guild_permissions.administrator = is_admin

        if is_storyteller:
            mock_ctx.author.roles = [mock_role1, mock_role2]
        else:
            mock_ctx.author.roles = [mock_role1]

        mock_ctx.author.id = 1

        # Create mock bot and guild_svc and set them on mock_ctx
        mock_bot = mocker.Mock()
        mock_guild_svc = mocker.Mock()

        # Set up the mock fetch_guild_settings function
        mock_settings = {"permissions_manage_campaigns": permission_value}
        mock_guild_svc.fetch_guild_settings = mocker.Mock(return_value=mock_settings)

        mock_bot.guild_svc = mock_guild_svc
        mock_ctx.bot = mock_bot

        # WHEN calling the method with the mock context and character
        result = self.user_svc.can_manage_campaign(mock_ctx)

        # THEN return the correct result
        assert result is expected

    def test_fetch_player_characters(self, mock_ctx) -> None:
        """Test fetching all player characters."""
        # GIVEN a character
        character = Character.create(
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
        character2 = Character.create(
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
        # A dead character
        character3 = Character.create(
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
                "first_name": "char15",
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

        # WHEN fetch_active_characters is called
        result = self.user_svc.fetch_player_characters(mock_ctx)

        # THEN return the correct result
        assert result == [character, character2, character3]

        # WHEN fetch_active_characters is called specifying only alive characters
        result = self.user_svc.fetch_player_characters(mock_ctx, alive_only=True)

        # THEN return the correct result
        assert result == [character, character2]

    def test_fetch_active_character(self, mock_ctx, caplog) -> None:
        """Test fetching an active character."""
        # GIVEN no active characters and an empty cache
        self.user_svc.character_cache = {}
        self.user_svc.active_character_cache = {}

        # WHEN fetch_active_character is called
        # THEN raise NoActiveCharacterError
        with pytest.raises(errors.NoActiveCharacterError):
            self.user_svc.fetch_active_character(mock_ctx)

        # GIVEN an active character and an empty cache
        character = Character.get_by_id(2)
        character.data["is_active"] = True
        character.save()

        # WHEN fetch_active_character is called
        result = self.user_svc.fetch_active_character(mock_ctx)
        logged = caplog.text

        # THEN return the correct result from the database
        assert result == character
        assert "DATABASE: Fetch active character" in logged
        assert "CACHE: Return active character" not in logged

        # WHEN fetch_active_character is called again
        caplog.clear()
        result = self.user_svc.fetch_active_character(mock_ctx)
        logged = caplog.text

        # THEN return the correct result from the cache
        assert result == character
        assert "CACHE: Return active character" in logged
        assert "DATABASE: Fetch active character" not in logged

    def test_set_active_character(self, mock_ctx) -> None:
        """Test switching active characters."""
        # GIVEN an active and an inactive character and a cache
        character1 = Character.create(
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
        character2 = Character.create(
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
        self.user_svc.active_character_cache = {"1_1": character1}

        # WHEN set_active_character is called
        self.user_svc.set_active_character(mock_ctx, character2)

        # THEN the active character is switched
        assert not Character.get_by_id(character1.id).data["is_active"]
        assert Character.get_by_id(character2.id).data["is_active"]
        assert self.user_svc.active_character_cache == {"1_1": character2}

    def test_transfer_character_owner(self, mock_ctx, mocker) -> None:
        """Test transferring character ownership."""
        # Given a character owned by one user and a second user
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
        self.user_svc.active_character_cache = {1_1: Character.get_by_id(character1.id)}

        mock_member = mocker.MagicMock()
        mock_member.id = 15001500051
        mock_member.display_name = "Test User 15001500051"
        mock_member.name = "testuser 15001500051"
        mock_member.mention = "<@15001500051>"
        mock_member.__class__ = discord.Member

        # WHEN transfer_character_owner is called
        self.user_svc.transfer_character_owner(mock_ctx, character1, mock_member)

        # THEN the character is owned by the second user
        assert Character.get_by_id(character1.id).owned_by.id == 15001500051
        assert self.user_svc.active_character_cache == {}

    def test_fetch_guild_user_one(self, mock_ctx, caplog) -> None:
        """Test fetching a guild user."""
        self._clear_tests()

        # WHEN fetch_guild_user is called and a user is not in the cache or database
        result = self.user_svc.fetch_guild_user(mock_ctx)
        logs = caplog.text

        # THEN return the correct result and update the cache and database
        assert result == GuildUser.get(user=1, guild=1)
        assert self.user_svc.guild_user_cache["1_1"] == GuildUser.get(user=1, guild=1)
        assert "DATABASE: Create GuildUser for" in logs

        # WHEN fetch_guild_user is called again
        caplog.clear()
        result = self.user_svc.fetch_guild_user(mock_ctx)
        logs = caplog.text

        # THEN return the correct result from the cache
        assert result == GuildUser.get(user=1, guild=1)
        assert "CACHE: GuildUser for" in logs
        assert "DATABASE" not in logs

        # GIVEN a guild user that is not in the cache but is in the database
        self.user_svc.guild_user_cache = {}

        # WHEN fetch_guild_user is called
        caplog.clear()
        result = self.user_svc.fetch_guild_user(mock_ctx)
        logs = caplog.text

        # THEN return the correct result from the database and update the cache
        assert result == GuildUser.get(user=1, guild=1)
        assert self.user_svc.guild_user_cache["1_1"] == GuildUser.get(user=1, guild=1)
        assert "DATABASE: GuildUser for" in logs
        assert "CACHE" not in logs
        assert "DATABASE: Updated GuildUser" not in logs

    def test_update_or_add_guild_user(self, mock_ctx, mock_member2) -> None:
        """Test updating or adding a guild user."""
        # Set up the tests
        self._clear_tests()

        data = {"test": "data"}

        # WHEN update_or_add_guild_user is called and a user is not in database
        result = self.user_svc.update_or_add_guild_user(mock_ctx, data=data)

        # THEN return the correct result and update the database with default values
        assert result == GuildUser.get(user=1, guild=1)
        assert result.data["test"] == "data"
        assert result.data["experience"] == 0
        assert "modified" in result.data

        # GIVEN updates to the user
        updates = {"test": "data2", "experience": 100, "new_key": "new_value"}

        # WHEN update_or_add_guild_user is called again
        result = self.user_svc.update_or_add_guild_user(mock_ctx, data=updates)

        # THEN return the correct result and update the database with the new values
        assert result == GuildUser.get(user=1, guild=1)
        assert result.data["test"] == "data2"
        assert result.data["experience"] == 100
        assert result.data["new_key"] == "new_value"

        # WHEN update_or_add_guild_user is called again with a specified user
        result = self.user_svc.update_or_add_guild_user(mock_ctx, user=mock_member2, data=data)

        # THEN return the correct result and update the database with the new values
        assert result == GuildUser.get(user=2, guild=1)
        assert result.data["test"] == "data"
        assert result.data["experience"] == 0

    def test_update_or_add_user(self, mock_ctx, mock_member2) -> None:
        """Test updating or adding a user."""
        self._clear_tests()
        data = {"test": "data"}
        self.user_svc.user_cache = {"1_1": "a", "1_600": "b", "100_1": "c"}
        # WHEN update_or_add_user is called and a user is not in database
        result = self.user_svc.update_or_add_user(mock_ctx, data=data)

        # THEN return the correct result and update the database with default values and the cache is intact
        assert result == User.get_by_id(1)
        assert result.name == "Test User"
        assert result.data["test"] == "data"
        assert self.user_svc.user_cache == {"1_1": "a", "1_600": "b", "100_1": "c"}

        # GIVEN updates to the user
        updates = {"test": "data2", "new_key": "new_value"}

        # WHEN update_or_add_user is called again
        result = self.user_svc.update_or_add_user(mock_ctx, data=updates)

        # THEN return the correct result and update the database with the new values and the cache is cleared
        assert result == User.get_by_id(1)
        assert result.name == "Test User"
        assert result.data["test"] == "data2"
        assert result.data["new_key"] == "new_value"
        assert self.user_svc.user_cache == {"100_1": "c"}

        # WHEN update_or_add_user is called again with a specified user
        result = self.user_svc.update_or_add_user(ctx=None, user=mock_member2, data=data)

        # THEN return the correct result and update the database with the new values
        assert result == User.get_by_id(2)
        assert result.name == "Test User2"
        assert result.data["test"] == "data"
