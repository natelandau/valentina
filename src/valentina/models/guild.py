"""Guild models for Valentina."""

import random
from datetime import datetime
from typing import TYPE_CHECKING

import discord
from beanie import (
    Document,
    Insert,
    Link,
    Replace,
    Save,
    SaveChanges,
    Update,
    before_event,
)
from loguru import logger
from pydantic import BaseModel, Field

from valentina.constants import (
    DICEROLL_THUMBS,
    PermissionManageCampaign,
    PermissionsGrantXP,
    PermissionsKillCharacter,
    PermissionsManageTraits,
    RollResultType,
)
from valentina.discord.utils import create_player_role, create_storyteller_role
from valentina.utils import errors
from valentina.utils.helpers import time_now

if TYPE_CHECKING:
    from valentina.discord.bot import ValentinaContext
    from valentina.models import Campaign


class GuildRollResultThumbnail(BaseModel):
    """Represents a thumbnail for a roll result as a subdocument attached to a Guild."""

    url: str
    roll_type: RollResultType
    user: int
    date_created: datetime = Field(default_factory=time_now)


class GuildPermissions(BaseModel):
    """Representation of a guild's permission settings as a subdocument attached to a Guild."""

    manage_traits: PermissionsManageTraits = PermissionsManageTraits.WITHIN_24_HOURS
    grant_xp: PermissionsGrantXP = PermissionsGrantXP.PLAYER_ONLY
    kill_character: PermissionsKillCharacter = PermissionsKillCharacter.CHARACTER_OWNER_ONLY
    manage_campaigns: PermissionManageCampaign = PermissionManageCampaign.STORYTELLER_ONLY


class GuildChannels(BaseModel):
    """Representation of a guild's channel ids as a subdocument attached to a Guild."""

    audit_log: int | None = None
    changelog: int | None = None
    error_log: int | None = None
    storyteller: int | None = None


class Guild(Document):
    """Represent a Discord guild in the database.

    This class models a Discord guild (server) and stores relevant information
    such as campaigns, channel IDs, permissions, and roll result thumbnails.
    """

    id: int  # type: ignore [assignment]

    campaigns: list[Link["Campaign"]] = Field(default_factory=list)
    changelog_posted_version: str | None = None
    channels: GuildChannels = GuildChannels()
    date_created: datetime = Field(default_factory=time_now)
    date_modified: datetime = Field(default_factory=time_now)
    name: str
    permissions: GuildPermissions = GuildPermissions()
    roll_result_thumbnails: list[GuildRollResultThumbnail] = Field(default_factory=list)
    storytellers: list[int] = Field(default_factory=list)
    administrators: list[int] = Field(default_factory=list)

    @before_event(Insert, Replace, Save, Update, SaveChanges)
    async def update_modified_date(self) -> None:
        """Update the date_modified field."""
        self.date_modified = time_now()

    def fetch_changelog_channel(
        self, guild: discord.Guild
    ) -> discord.TextChannel | None:  # pragma: no cover
        """Retrieve the changelog channel for the guild from the settings.

        Fetch the guild's settings to determine if a changelog channel has been set.  If set, return the corresponding TextChannel object; otherwise, return None.

        Args:
            guild (discord.Guild): The guild to fetch the changelog channel for.

        Returns:
            discord.TextChannel|None: The changelog channel, if it exists and is set; otherwise, None.
        """
        if self.channels.changelog:
            return discord.utils.get(guild.text_channels, id=self.channels.changelog)

        return None

    def fetch_storyteller_channel(
        self, guild: discord.Guild
    ) -> discord.TextChannel | None:  # pragma: no cover
        """Retrieve the storyteller channel for the guild from the settings.

        Fetch the guild's settings to determine if a storyteller channel has been set.  If set, return the corresponding TextChannel object; otherwise, return None.

        Args:
            guild (discord.Guild): The guild to fetch the storyteller channel for.

        Returns:
            discord.TextChannel|None: The storyteller channel, if it exists and is set; otherwise, None.
        """
        if self.channels.storyteller:
            return discord.utils.get(guild.text_channels, id=self.channels.storyteller)

        return None

    def fetch_audit_log_channel(
        self, guild: discord.Guild
    ) -> discord.TextChannel | None:  # pragma: no cover
        """Retrieve the audit log channel for the guild from the settings.

        Fetch the guild's settings to determine if an audit log channel has been set.  If set, return the corresponding TextChannel object; otherwise, return None.

        Args:
            guild (discord.Guild): The guild to fetch the audit log channel for.

        Returns:
            discord.TextChannel|None: The audit log channel, if it exists and is set; otherwise, None.
        """
        if self.channels.audit_log:
            return discord.utils.get(guild.text_channels, id=self.channels.audit_log)

        return None

    def fetch_error_log_channel(
        self, guild: discord.Guild
    ) -> discord.TextChannel | None:  # pragma: no cover
        """Retrieve the error log channel for the guild from the settings.

        Fetch the guild's settings to determine if an error log channel has been set.  If set, return the corresponding TextChannel object; otherwise, return None.

        Args:
            guild (discord.Guild): The guild to fetch the error log channel for.

        Returns:
            discord.TextChannel|None: The error log channel, if it exists and is set; otherwise, None.
        """
        if self.channels.error_log:
            return discord.utils.get(guild.text_channels, id=self.channels.error_log)

        return None

    async def setup_roles(self, guild: discord.Guild) -> None:  # pragma: no cover
        """Create or update the guild's roles.

        Create or update the storyteller and player roles for the given guild.
        Ensure these roles exist and have the appropriate permissions.

        Args:
            guild (discord.Guild): The Discord guild to create or update roles for.
        """
        # Create roles
        await create_storyteller_role(guild)
        await create_player_role(guild)
        logger.debug(f"GUILD: Roles created/updated on {self.name}")

    async def delete_campaign(self, campaign: "Campaign") -> None:
        """Delete a campaign from the guild and mark it as deleted in the database.

        Remove the campaign from the guild's list of campaigns and mark it as deleted
        in the database. This method does not permanently delete the campaign data,
        but rather sets a flag to indicate its deleted status.

        Args:
            campaign (Campaign): The campaign object to be deleted.
        """
        if campaign in self.campaigns:
            self.campaigns.remove(campaign)

        await self.save()

        campaign.is_deleted = True
        await campaign.save()

    async def add_roll_result_thumbnail(
        self, ctx: "ValentinaContext", roll_type: RollResultType, url: str
    ) -> None:
        """Add a roll result thumbnail to the database."""
        for thumb in self.roll_result_thumbnails:
            if thumb.url == url:
                msg = "That thumbnail already exists"
                raise errors.ValidationError(msg)

        self.roll_result_thumbnails.append(
            GuildRollResultThumbnail(url=url, roll_type=roll_type, user=ctx.author.id)
        )
        await self.save()

        logger.info(
            f"DATABASE: Add '{roll_type.name}' roll result thumbnail for '{ctx.guild.name}'"
        )

    async def fetch_diceroll_thumbnail(self, result: RollResultType) -> str:
        """Fetch a random thumbnail URL for a given roll result type.

        Retrieve a random thumbnail URL from a combined list of default thumbnails
        and guild-specific thumbnails for the specified roll result type.

        Args:
            result (RollResultType): The roll result type to fetch a thumbnail for.

        Returns:
            str | None: A random thumbnail URL if available, or None if no thumbnails are found.
        """
        # Get the list of default thumbnails for the result type
        thumb_list = DICEROLL_THUMBS.get(result.name, [])

        # Find the matching category in the database thumbnails (case insensitive)

        thumb_list.extend([x.url for x in self.roll_result_thumbnails if x.roll_type == result])

        # If there are no thumbnails, return None
        if not thumb_list:
            return None

        # Return a random thumbnail
        return random.choice(thumb_list)
