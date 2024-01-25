"""Guild models for Valentina."""

import random
from datetime import datetime

import discord
from beanie import (
    DeleteRules,
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
from valentina.models import Campaign
from valentina.utils import errors
from valentina.utils.discord_utils import create_player_role, create_storyteller_role
from valentina.utils.helpers import time_now


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
    """Represents a guild in the database."""

    id: int  # type: ignore [assignment]

    active_campaign: Link["Campaign"] = None
    campaigns: list[Link["Campaign"]] = Field(default_factory=list)
    changelog_posted_version: str | None = None
    channels: GuildChannels = GuildChannels()
    date_created: datetime = Field(default_factory=time_now)
    date_modified: datetime = Field(default_factory=time_now)
    name: str
    permissions: GuildPermissions = GuildPermissions()
    roll_result_thumbnails: list[GuildRollResultThumbnail] = Field(default_factory=list)

    @before_event(Insert, Replace, Save, Update, SaveChanges)
    async def update_modified_date(self) -> None:
        """Update the date_modified field."""
        self.date_modified = time_now()

    def fetch_changelog_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
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

    def fetch_storyteller_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
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

    def fetch_audit_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
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

    def fetch_error_log_channel(self, guild: discord.Guild) -> discord.TextChannel | None:
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

    async def setup_roles(self, guild: discord.Guild) -> None:
        """Create or update the guild's roles.

        Args:
            guild (discord.Guild): The guild to create/update roles for.
        """
        # Create roles
        await create_storyteller_role(guild)
        await create_player_role(guild)
        logger.debug(f"GUILD: Roles created/updated on {self.name}")

    async def fetch_active_campaign(self) -> "Campaign":
        """Fetch the active campaign for the guild."""
        try:
            return await Campaign.get(self.active_campaign.id, fetch_links=True)  # type: ignore [attr-defined]
        except AttributeError as e:
            raise errors.NoActiveCampaignError from e

    async def delete_campaign(self, campaign: "Campaign") -> None:
        """Delete a campaign from the guild. Remove the campaign from the guild's list of campaigns and delete the campaign from the database.

        Args:
            campaign (Campaign): The campaign to delete.
        """
        # Remove the campaign from the active campaign if it is active
        if self.active_campaign and self.active_campaign == campaign:
            self.active_campaign = None

        if campaign in self.campaigns:
            self.campaigns.remove(campaign)

        await campaign.delete(link_rule=DeleteRules.DELETE_LINKS)

        await self.save()

    async def add_roll_result_thumbnail(
        self, ctx: discord.ApplicationContext, roll_type: RollResultType, url: str
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
        """Take a string and return a random gif url.

        Args:
            ctx (): The application context.
            result (RollResultType): The roll result type.

        Returns:
        Optional[str]: The thumbnail URL, or None if no thumbnail is found.
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
