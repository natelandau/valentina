"""Discord user database models and services.

Note, due to ForeignKey constraints, models are defined in database.py.
"""
from collections.abc import Callable
from datetime import timedelta

import arrow
import discord
from loguru import logger
from peewee import DoesNotExist

from valentina.constants import (
    PermissionManageCampaign,
    PermissionsEditTrait,
    PermissionsEditXP,
    PermissionsKillCharacter,
)
from valentina.models.db_tables import Character, GuildUser, User
from valentina.utils import errors
from valentina.utils.helpers import time_now


class UserService:
    """User manager and in-memory cache."""

    def __init__(self) -> None:
        """Initialize the UserService."""
        self.user_cache: dict[str, User] = {}  # {user_key: User, ...}
        self.active_character_cache: dict[int, Character] = {}  # {user.id: Character, ...}

    @staticmethod
    def __get_user_key(guild: discord.Guild | int, user: discord.User | int) -> str:
        """Construct a string key from guild and user IDs. Used for keys in the user cache.

        Use the 'guild' and 'user' arguments to retrieve IDs. If 'guild' or 'user' is an
        instance of discord.Guild or discord.User, get the 'id' attribute. If they're
        integers, use them directly.

        Args:
            guild (discord.Guild | int): A discord.Guild instance or a guild ID.
            user (discord.User | int): A discord.User instance or a user ID.

        Returns:
            str: A string composed of guild and user IDs, joined by an underscore.
        """
        guild_id = guild.id if isinstance(guild, discord.Guild) else guild
        user_id = user.id if isinstance(user, discord.User) else user

        return f"{guild_id}_{user_id}"

    def can_manage_campaign(self, ctx: discord.ApplicationContext) -> bool:
        """Check if the user has permissions to manage campaigns.

        The function checks the following conditions in order:
        - If the author is an administrator, return True.
        - Fetch the guild settings. If they cannot be fetched, return False.
        - Use a mapping from trait permissions to functions to check the corresponding permission type and return the result.

        Args:
            ctx (ApplicationContext): The application context.


        Returns:
            bool: True if the user has permissions to update traits, False otherwise.
        """
        permissions_dict: dict[
            PermissionManageCampaign, Callable[[discord.ApplicationContext], bool]
        ] = {
            PermissionManageCampaign.UNRESTRICTED: lambda x: True,  # noqa: ARG005
            PermissionManageCampaign.STORYTELLER_ONLY: lambda ctx: "Storyteller"
            in [x.name for x in ctx.author.roles],
        }

        if ctx.author.guild_permissions.administrator:
            return True

        settings = ctx.bot.guild_svc.fetch_guild_settings(ctx.guild)  # type: ignore [attr-defined]
        if not settings:
            return False

        permission = PermissionManageCampaign(settings["permissions_manage_campaigns"])
        check_permission = permissions_dict.get(permission)
        if check_permission:
            return check_permission(ctx)

        return False

    def can_kill_character(
        self, ctx: discord.ApplicationContext, character: Character = None
    ) -> bool:
        """Check if the user has permissions to mark a character as dead.

        The function checks the following conditions in order:
        - If the author is an administrator, return True.
        - Fetch the guild settings. If they cannot be fetched, return False.
        - Use a mapping from PermissionsKillCharacter to functions to check the corresponding permission type and return the result.

        Args:
            ctx (ApplicationContext): The application context.
            character (Character, optional): The character to check permissions for. Defaults to None.

        Returns:
            bool: True if the user has permissions to kill a character, False otherwise.
        """
        permissions_dict: dict[
            PermissionsKillCharacter, Callable[[discord.ApplicationContext, Character], bool]
        ] = {
            PermissionsKillCharacter.UNRESTRICTED: lambda ctx, character: True,  # noqa: ARG005
            PermissionsKillCharacter.CHARACTER_OWNER_ONLY: lambda ctx, character: character
            and character.owned_by.id == ctx.author.id,
            PermissionsKillCharacter.STORYTELLER_ONLY: lambda ctx, character: "Storyteller"  # noqa: ARG005
            in [x.name for x in ctx.author.roles],
        }

        if ctx.author.guild_permissions.administrator:
            return True

        settings = ctx.bot.guild_svc.fetch_guild_settings(ctx.guild)  # type: ignore [attr-defined]
        if not settings:
            return False

        permission = PermissionsKillCharacter(settings["permissions_kill_character"])
        check_permission = permissions_dict.get(permission)
        if check_permission:
            return check_permission(ctx, character)

        return False

    def can_update_traits(
        self, ctx: discord.ApplicationContext, character: Character = None
    ) -> bool:
        """Check if the user has permissions to update character trait values.

        The function checks the following conditions in order:
        - If the author is an administrator, return True.
        - Fetch the guild settings. If they cannot be fetched, return False.
        - Use a mapping from trait permissions to functions to check the corresponding permission type and return the result.

        Args:
            ctx (ApplicationContext): The application context.
            character (Character, optional): The character to check permissions for. Defaults to None.

        Returns:
            bool: True if the user has permissions to update traits, False otherwise.
        """
        permissions_dict: dict[
            PermissionsEditTrait, Callable[[discord.ApplicationContext, Character], bool]
        ] = {
            PermissionsEditTrait.UNRESTRICTED: lambda ctx, character: True,  # noqa: ARG005
            PermissionsEditTrait.CHARACTER_OWNER_ONLY: lambda ctx, character: character
            and character.created_by.id == ctx.author.id,
            PermissionsEditTrait.WITHIN_24_HOURS: lambda ctx, character: character
            and character.created_by.id == ctx.author.id
            and (arrow.utcnow() - arrow.get(character.created) <= timedelta(hours=24)),
            PermissionsEditTrait.STORYTELLER_ONLY: lambda ctx, character: "Storyteller"  # noqa: ARG005
            in [x.name for x in ctx.author.roles],
        }

        if ctx.author.guild_permissions.administrator:
            return True

        settings = ctx.bot.guild_svc.fetch_guild_settings(ctx.guild)  # type: ignore [attr-defined]
        if not settings:
            return False

        permission = PermissionsEditTrait(settings["permissions_edit_trait"])
        check_permission = permissions_dict.get(permission)
        if check_permission:
            return check_permission(ctx, character)

        return False

    def can_update_xp(self, ctx: discord.ApplicationContext, character: Character = None) -> bool:
        """Check if the user has permissions to add experience points to their characters.

        The function checks the following conditions in order:
        - If the author is an administrator, return True.
        - Fetch the guild settings. If they cannot be fetched, return False.
        - Use a mapping from xp permissions to functions to check the corresponding permission type and return the result.

        Args:
            ctx (ApplicationContext): The application context.
            character (Character, optional): The character to check permissions for. Defaults to None.

        Returns:
            bool: True if the user has permissions to add xp, False otherwise.
        """
        permissions_dict: dict[
            PermissionsEditXP, Callable[[discord.ApplicationContext, Character], bool]
        ] = {
            PermissionsEditXP.UNRESTRICTED: lambda ctx, character: True,  # noqa: ARG005
            PermissionsEditXP.CHARACTER_OWNER_ONLY: lambda ctx, character: character
            and character.created_by.id == ctx.author.id,
            PermissionsEditXP.WITHIN_24_HOURS: lambda ctx, character: character
            and character.created_by.id == ctx.author.id
            and (arrow.utcnow() - arrow.get(character.created) <= timedelta(hours=24)),
            PermissionsEditXP.STORYTELLER_ONLY: lambda ctx, character: "Storyteller"  # noqa: ARG005
            in [x.name for x in ctx.author.roles],
        }

        if ctx.author.guild_permissions.administrator:
            return True

        settings = ctx.bot.guild_svc.fetch_guild_settings(ctx.guild)  # type: ignore [attr-defined]
        if not settings:
            return False

        permission = PermissionsEditXP(settings["permissions_edit_xp"])
        check_permission = permissions_dict.get(permission)
        if check_permission:
            return check_permission(ctx, character)

        return False

    def fetch_player_characters(
        self,
        ctx: discord.ApplicationContext | discord.AutocompleteContext,
        alive_only: bool = False,
    ) -> list[Character]:
        """Retrieve a list of all player characters owned by the user in the current guild.

        Args:
            ctx: The context object for the command invocation.
            alive_only (bool, optional): If True, only return characters that are currently alive. Defaults to False.

        Returns:
            list: Character objects representing the characters owned by the user in the current guild.


        Examples:
            To retrieve all player characters owned by the user in the current guild:
            ```
            characters = fetch_player_characters(ctx)
            ```
            To retrieve only the alive player characters owned by the user in the current guild:
            ```
            characters = fetch_player_characters(ctx, alive_only=True)
            ```
        """
        user = self.fetch_user(ctx=ctx)

        guild = ctx.guild if isinstance(ctx, discord.ApplicationContext) else ctx.interaction.guild

        if alive_only:
            return [
                x
                for x in Character.select().where(
                    Character.owned_by == user,
                    Character.guild == guild.id,
                    Character.data["player_character"] == True,  # noqa: E712
                    Character.data["is_alive"] == True,  # noqa: E712
                )
            ]

        return [
            x
            for x in Character.select().where(
                Character.owned_by == user,
                Character.guild == guild.id,
                Character.data["player_character"] == True,  # noqa: E712
            )
        ]

    def fetch_active_character(
        self, ctx: discord.ApplicationContext | discord.AutocompleteContext
    ) -> Character:
        """Fetch the active character for the user.

        Args:
            ctx (ApplicationContext | discord.AutocompleteContext): The context which contains the author and guild information.

        Returns:
            Character: The active character for the user.

        Raises:
            errors.NoActiveCharacterError: Raised if the user has no active character.
        """
        user = self.fetch_user(ctx=ctx)

        if user.id in self.active_character_cache:
            logger.debug(
                f"CACHE: Return active character '{self.active_character_cache[user.id].id}'"
            )
            return self.active_character_cache[user.id]

        guild = ctx.guild if isinstance(ctx, discord.ApplicationContext) else ctx.interaction.guild

        try:
            character = Character.get(
                Character.owned_by == user,
                Character.guild == guild.id,
                Character.data["player_character"] == True,  # noqa: E712
                Character.data["is_active"] == True,  # noqa: E712
            )
        except DoesNotExist as e:
            raise errors.NoActiveCharacterError from e

        logger.debug(f"DATABASE: Fetch active character '{character.id}'")
        self.active_character_cache[user.id] = character

        return character

    def fetch_user(
        self,
        ctx: discord.ApplicationContext | discord.AutocompleteContext = None,
        user: discord.User | discord.Member = None,
    ) -> User:
        """Retrieve and/or add a User object from the cache or the database.

        Use the application context 'ctx' to fetch a User. If the User isn't present
        in the cache or the database, create a new User in the database and the cache.

        Args:
            ctx (discord.ApplicationContext | discord.AutocompleteContext): The context containing author and guild.
            user (discord.User | discord.Member, optional): A specific user to fetch. Defaults to None.

        Returns:
            User: User database model instance.
        """
        # Extract member and guild information from the context or the provided user
        member, guild = self._get_member_and_guild(ctx, user)

        # Try to get or create the User from the database
        try:
            db_user, created = self._get_or_create_db_user(member)
        except Exception as e:
            logger.error(f"DATABASE: Error while getting or creating user. {e!s}")
            raise

        # Add user to guild-user lookup table and handle user caching
        if guild:
            GuildUser.get_or_create(user=member.id, guild=guild.id)
            return self._handle_user_caching(db_user, member, guild)

        return db_user

    def _get_member_and_guild(
        self,
        ctx: discord.ApplicationContext | discord.AutocompleteContext,
        user: discord.User | discord.Member,
    ) -> tuple[discord.Member | discord.User, discord.Guild | None]:
        """Extract member and guild from the context or the user.

        Determine the member and guild based on the application context. If a user is specifically
        provided, then that user will override any member found in the context.

        Args:
            ctx (discord.ApplicationContext | discord.AutocompleteContext): The application or autocomplete context.
            user (discord.User | discord.Member): A specific user to fetch, if provided.

        Returns:
            tuple[discord.Member | discord.User, discord.Guild | None]: A tuple containing the member and the guild.
        """
        guild: discord.Guild | None = None

        if ctx:
            # Use attributes common to both ApplicationContext and AutocompleteContext
            member = (
                ctx.author if isinstance(ctx, discord.ApplicationContext) else ctx.interaction.user
            )
            guild = (
                ctx.guild if isinstance(ctx, discord.ApplicationContext) else ctx.interaction.guild
            )

        # If user is explicitly provided, return it regardless of the context.
        if user:
            return user, guild

        return member, guild

    def _get_or_create_db_user(self, member: discord.User | discord.Member) -> tuple:
        """Retrieve or create a user record in the database.

        This function attempts to get a user from the database based on their Discord ID.
        If the user is not found, it creates a new user record with default values.

        Args:
            member (discord.User | discord.Member): The Discord user or member to fetch or create in the database.

        Returns:
            tuple: A tuple containing the database user and a boolean indicating if the user was created.
        """
        # Try to retrieve the user from the database, or create a new entry if not found.
        db_user, created = User.get_or_create(
            id=member.id,
            defaults={
                "name": member.display_name,
                "username": member.name,
                "mention": member.mention,
                "first_seen": time_now(),
                "last_seen": time_now(),
            },
        )

        # Log based on whether the user was created or updated
        if created:
            logger.info(f"DATABASE: Created a new user record for '{member.display_name}'")
        else:
            # Update the 'last_seen' timestamp for the existing user
            db_user.last_seen = time_now()
            db_user.save()
            logger.debug(
                f"DATABASE: Updated 'last_seen' timestamp for user '{member.display_name}'"
            )

        return db_user, created

    def _handle_user_caching(
        self, db_user: User, member: discord.User | discord.Member, guild: discord.Guild
    ) -> User:
        """Manage the user caching mechanism.

        This function checks if the user is already in the cache. If so, it returns
        the cached user. If not, it creates a new entry in the cache.

        Args:
            db_user (User): The user from the database.
            member (discord.User | discord.Member): The Discord user or member.
            guild (discord.Guild): The Discord guild.

        Returns:
            User: The cached or newly cached user.
        """
        # Generate a unique cache key for the user in this guild
        key = self.__get_user_key(guild.id, member.id)

        # Attempt to retrieve the user from the cache
        cached_user = self.user_cache.get(key, None)

        # If user is already in the cache, return it
        if cached_user:
            logger.debug(f"CACHE: Returned cached user with ID {member.id}")
            return cached_user

        # Cache the user
        self.user_cache[key] = db_user
        logger.debug(f"CACHE: Added user '{member.display_name}' to cache")

        return db_user

    def purge_cache(self, ctx: discord.ApplicationContext | None = None) -> None:
        """Purge the user service cache.

            If 'ctx' is provided, purge the cache for the specific user. If 'ctx' is None,
        purge all user caches.

        Args:
            ctx (ApplicationContext | None, optional): The application context. Defaults to None.
        """
        if ctx:
            for key in list(self.user_cache.keys()):
                if key.startswith(f"{ctx.guild.id}_"):
                    self.user_cache.pop(key, None)
                    logger.debug(f"CACHE: Purge user cache for user `{ctx.author.id}`")
            self.active_character_cache.pop(ctx.author.id, None)
        else:
            self.user_cache = {}
            self.active_character_cache = {}
            logger.debug("CACHE: Purge all user caches")

    def set_active_character(self, ctx: discord.ApplicationContext, character: Character) -> None:
        """Switch the active character for the user."""
        user = self.fetch_user(ctx=ctx)

        for c in Character.select().where(
            Character.owned_by == user,
            Character.guild == ctx.guild.id,
            Character.data["player_character"] == True,  # noqa: E712
        ):
            if c.id == character.id:
                c.data["is_active"] = True
                c.save()
            else:
                c.data["is_active"] = False
                c.save()

        self.active_character_cache[user.id] = character

        logger.debug(f"DATABASE: Set active character for {user.username} to '{character.id}'")

    def transfer_character_owner(
        self, ctx: discord.ApplicationContext, character: Character, new_owner: User
    ) -> None:
        """Transfer ownership of a character to another user."""
        current_user = self.fetch_user(ctx)
        new_user = self.fetch_user(ctx, new_owner)

        character.owned_by = new_user
        character.save()

        self.purge_cache()
        logger.debug(
            f"DATABASE: '{current_user.username}' transferred ownership of '{character.id}' to '{new_user.username}'"
        )
