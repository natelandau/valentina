"""Manage entitlements for Valentina models."""

from datetime import UTC, datetime, timedelta
from typing import assert_never

from valentina.constants import (
    PermissionManageCampaign,
    PermissionsGrantXP,
    PermissionsKillCharacter,
    PermissionsManageTraits,
)
from valentina.models.character import Character
from valentina.models.guild import Guild, GuildPermissions


class PermissionManager:
    """Manage permissions for Valentina models."""

    def __init__(self, guild_id: int) -> None:
        self.guild_id = guild_id
        self._guild_db_obj: Guild = None

    async def _fetch_guild_permissions(self) -> GuildPermissions:
        """Retrieve the guild's permissions."""
        if not self._guild_db_obj:
            self._guild_db_obj = await Guild.get(self.guild_id)

        return self._guild_db_obj.permissions

    async def can_grant_xp(self, author_id: int, target_id: int) -> bool:
        """Determine if the user can grant XP.

        Args:
            author_id (int): The ID of the user requesting to grant XP.
            target_id (int): The ID of the user to grant XP to.

        Returns:
            bool: True if the user can grant XP; otherwise, False.
        """
        if await self.is_admin(author_id):
            return True

        # Grab the setting from the database
        guild_permissions = await self._fetch_guild_permissions()
        try:
            setting = PermissionsGrantXP(guild_permissions.grant_xp)
        except KeyError:
            setting = PermissionsGrantXP.PLAYER_ONLY

        match setting:
            case PermissionsGrantXP.UNRESTRICTED:
                return True
            case PermissionsGrantXP.PLAYER_ONLY:
                if not await self.is_storyteller(author_id):
                    return author_id == target_id
                return True
            case PermissionsGrantXP.STORYTELLER_ONLY:
                return await self.is_storyteller(author_id)

            case _:
                assert_never()

    async def can_manage_campaign(self, author_id: int) -> bool:
        """Determine if the current user has permission to manage the campaign.

        Check the guild's campaign management permission settings and the current user's roles
        to determine if they are allowed to manage the campaign. Consider various scenarios
        such as unrestricted access and storyteller-only permissions. Always allow
        administrators to manage campaigns.

        Args:
            author_id (int): The ID of the user requesting to manage the campaign.

        Returns:
            bool: True if the user has permission to manage the campaign, False otherwise.
        """
        # Always allow administrators to manage the campaign
        if await self.is_admin(author_id):
            return True

        # Grab the setting from the database
        guild_permissions = await self._fetch_guild_permissions()
        try:
            setting = PermissionManageCampaign(guild_permissions.manage_campaigns)
        except KeyError:
            setting = PermissionManageCampaign.STORYTELLER_ONLY

        match setting:
            case PermissionManageCampaign.UNRESTRICTED:
                return True

            case PermissionManageCampaign.STORYTELLER_ONLY:
                return await self.is_storyteller(author_id)

            case _:
                assert_never()

    async def can_manage_traits(self, author_id: int, character_id: str) -> bool:
        """Determine if the user has permission to manage traits for the specified character.

        Check the user's permissions against the guild's settings to decide if they
        can manage traits for the given character. Consider the user's role, guild
        permissions, character ownership, and time since character creation when
        making this determination.

        Args:
            author_id (int): The ID of the user requesting to manage the character's traits.
            character_id (str): The database ID of the character to manage.

        Returns:
            bool: True if the user has permission to manage the character's traits,
                  False otherwise.
        """
        # Always allow administrators to manage traits
        if await self.is_admin(author_id):
            return True

        # Grab the setting from the database
        guild_permissions = await self._fetch_guild_permissions()
        try:
            setting = PermissionsManageTraits(guild_permissions.manage_traits)
        except KeyError:
            setting = PermissionsManageTraits.WITHIN_24_HOURS

        # Allow the user to manage traits if the setting is unrestricted
        match setting:
            case PermissionsManageTraits.UNRESTRICTED:
                return True

            case PermissionsManageTraits.CHARACTER_OWNER_ONLY:
                character = await Character.get(character_id)
                return (author_id == character.user_owner) or await self.is_storyteller(author_id)

            case PermissionsManageTraits.WITHIN_24_HOURS:
                character = await Character.get(character_id)
                author_is_owner = author_id == character.user_owner
                is_within_24_hours = datetime.now(UTC) - character.date_created <= timedelta(
                    hours=24
                )

                return (author_is_owner and is_within_24_hours) or await self.is_storyteller(
                    author_id
                )

            case PermissionsManageTraits.STORYTELLER_ONLY:
                return await self.is_storyteller(author_id)

            case _:
                assert_never()

    async def can_kill_character(self, author_id: int, character_id: str) -> bool:
        """Determine if the user has permission to kill the specified character.

        Check the user's permissions against the guild's settings to decide if they
        can kill the given character. Consider the user's role, guild permissions,
        and character ownership when making this determination.

        Args:
            author_id (int): The ID of the user requesting to kill the character.
            character_id (str): The database ID of the character to kill.

        Returns:
            bool: True if the user has permission to kill the character, False otherwise.
        """
        # Always allow administrators to manage succeed
        if await self.is_admin(author_id):
            return True

        # Grab the setting from the database
        guild_permissions = await self._fetch_guild_permissions()
        try:
            setting = PermissionsKillCharacter(guild_permissions.kill_character)
        except KeyError:
            setting = PermissionsKillCharacter.CHARACTER_OWNER_ONLY

        match setting:
            case PermissionsKillCharacter.UNRESTRICTED:
                return True

            case PermissionsKillCharacter.CHARACTER_OWNER_ONLY:
                character = await Character.get(character_id)
                return author_id == character.user_owner or await self.is_storyteller(author_id)

            case PermissionsKillCharacter.STORYTELLER_ONLY:
                return await self.is_storyteller(author_id)

            case _:
                assert_never()

    async def is_storyteller(self, author_id: int) -> bool:
        """Determine if the author is a storyteller.

        Args:
            author_id (int): The ID of the author to check.

        Returns:
            bool: True if the author is a storyteller; otherwise, False.
        """
        if not self._guild_db_obj:
            self._guild_db_obj = await Guild.get(self.guild_id)

        # Finally, allow storytellers to grant XP and deny all others
        return author_id in self._guild_db_obj.storytellers

    async def is_admin(self, author_id: int) -> bool:
        """Determine if the author is an administrator.

        Args:
            author_id (int): The ID of the author to check.

        Returns:
            bool: True if the author is an administrator; otherwise, False.
        """
        if not self._guild_db_obj:
            self._guild_db_obj = await Guild.get(self.guild_id)

        return author_id in self._guild_db_obj.administrators
