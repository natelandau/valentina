"""Campaign models for Valentina."""

from datetime import datetime
from typing import Optional

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

from valentina.constants import CHANNEL_PERMISSIONS, CampaignChannelNames
from valentina.utils.helpers import time_now

from .character import Character


class CampaignChapter(BaseModel):
    """Represents a chapter as a subdocument within Campaign."""

    description_long: str = None
    description_short: str = None
    name: str
    number: int
    date_created: datetime = Field(default_factory=time_now)

    def campaign_display(self) -> str:
        """Return the display for campaign overview."""
        display = f"**{self.number}: __{self.name}__**"
        display += f"\n{self.description_long}" if self.description_long else ""

        return display


class CampaignNPC(BaseModel):
    """Represents a campaign NPC as a subdocument within Campaign."""

    description: str
    name: str
    npc_class: str

    def campaign_display(self) -> str:
        """Return the display for campaign overview."""
        display = f"**{self.name}**"
        display += f" ({self.npc_class})" if self.npc_class else ""
        display += f"\n{self.description}" if self.description else ""

        return display


class CampaignNote(BaseModel):
    """Represents a campaign note as a subdocument within Campaign."""

    # TODO: Remove user-specific notes from cogs/views
    description: str
    name: str

    def campaign_display(self) -> str:
        """Return the display for campaign overview."""
        display = f"**{self.name}**\n"
        display += f"{self.description}" if self.description else ""

        return display


class CampaignChannels(BaseModel):
    """Representation of a campaign's channel ids as a subdocument attached to a Campaign."""

    category_channel: int | None = None
    gameplay: int | None = None
    log: int | None = None
    character_channels: dict[str, int] = Field(default_factory=dict)


class Campaign(Document):
    """Represents a campaign in the database."""

    date_created: datetime = Field(default_factory=time_now)
    date_modified: datetime = Field(default_factory=time_now)
    date_in_game: Optional[datetime] = None
    description: str | None = None
    desperation: int = 0
    danger: int = 0
    guild: int
    name: str
    chapters: list[CampaignChapter] = Field(default_factory=list)
    notes: list[CampaignNote] = Field(default_factory=list)
    npcs: list[CampaignNPC] = Field(default_factory=list)
    channels: CampaignChannels = CampaignChannels()
    characters: list[Link["Character"]] = Field(default_factory=list)

    @before_event(Insert, Replace, Save, Update, SaveChanges)
    async def update_modified_date(self) -> None:
        """Update the date_modified field."""
        self.date_modified = time_now()

    async def _confirm_character_channels(
        self,
        ctx: discord.ApplicationContext,
        category: discord.CategoryChannel,
        channels: list[discord.TextChannel],
    ) -> None:
        """Create the character channels for the campaign."""
        for character in self.characters:
            channel_db_id = str(character.id)  # type: ignore [attr-defined]
            channel_name = character.name  # type: ignore [attr-defined]
            owned_by_user = discord.utils.get(ctx.bot.users, id=character.user_owner)  # type: ignore [attr-defined]

            if (
                self.channels.character_channels.get(channel_db_id, None)
                and self.channels.character_channels.get(channel_db_id)
                in [channel.id for channel in channels]
                and channel_name not in [channel.name for channel in channels]
            ):
                channel_object = discord.utils.get(
                    ctx.guild.text_channels,
                    id=self.channels.character_channels.get(channel_db_id),
                )

                await ctx.channel_update_or_add(  # type: ignore [attr-defined]
                    channel=channel_object,
                    name=channel_name,
                    category=category,
                    permissions=CHANNEL_PERMISSIONS["campaign_character_channel"],
                    permissions_user_post=owned_by_user,
                    topic=f"Character channel for {channel_name}",
                )
                logger.debug(
                    f"{channel_name} channel renamed for campaign '{self.name}' in '{ctx.guild.name}'"
                )
            elif (
                self.channels.character_channels.get(channel_db_id, None)
                and not any(
                    channel.id == self.channels.character_channels.get(channel_db_id)
                    for channel in channels
                )
            ) or not any(channel.name == channel_name for channel in channels):
                created_channel = await ctx.channel_update_or_add(  # type: ignore [attr-defined]
                    name=channel_name,
                    category=category,
                    permissions=CHANNEL_PERMISSIONS["campaign_character_channel"],
                    permissions_user_post=owned_by_user,
                    topic=f"Character channel for {channel_name}",
                )

                self.channels.character_channels[channel_db_id] = created_channel.id
                await self.save()
                logger.debug(
                    f"{channel_name} channel created for campaign '{self.name}' in '{ctx.guild.name}'"
                )

    async def _confirm_campaign_channels(
        self,
        ctx: discord.ApplicationContext,
        category: discord.CategoryChannel,
        channels: list[discord.TextChannel],
    ) -> None:
        """Create the campaign channels in the guild."""
        # Static channels
        channel_list = {
            "gameplay": CampaignChannelNames.GAMEPLAY.value,
            "log": CampaignChannelNames.LOG.value,
        }
        for channel_db_id, channel_name in channel_list.items():
            if (
                getattr(self.channels, channel_db_id, None)
                and getattr(self.channels, channel_db_id) in [channel.id for channel in channels]
                and channel_name not in [channel.name for channel in channels]
            ):
                channel_object = discord.utils.get(
                    ctx.guild.text_channels, id=getattr(self.channels, channel_db_id)
                )

                await ctx.channel_update_or_add(  # type: ignore [attr-defined]
                    channel=channel_object,
                    name=channel_name,
                    category=category,
                    permissions=CHANNEL_PERMISSIONS["default"],
                )

                logger.debug(
                    f"{channel_name} channel renamed for campaign '{self.name}' in '{ctx.guild.name}'"
                )
            elif (
                getattr(self.channels, channel_db_id, None)
                and not any(
                    channel.id == getattr(self.channels, channel_db_id) for channel in channels
                )
            ) or not any(channel.name == channel_name for channel in channels):
                created_channel = await ctx.channel_update_or_add(  # type: ignore [attr-defined]
                    name=channel_name,
                    category=category,
                    permissions=CHANNEL_PERMISSIONS["default"],
                )
                setattr(self.channels, channel_db_id, created_channel.id)
                await self.save()
                logger.debug(
                    f"{channel_name} channel created for campaign '{self.name}' in '{ctx.guild.name}'"
                )

    async def create_channels(self, ctx: discord.ApplicationContext) -> None:
        """Create the campaign channels in the guild."""
        if self.channels.category_channel:
            channel_object = ctx.guild.get_channel(self.channels.category_channel)
            if not channel_object:
                category = await ctx.guild.create_category(self.name)
                self.channels.category_channel = category.id
                logger.debug(f"Campaign category '{self.name}' created in '{ctx.guild.name}'")
                await self.save()

            elif channel_object.name != self.name:
                await channel_object.edit(name=self.name)
                logger.debug(f"Campaign category '{self.name}' renamed in '{ctx.guild.name}'")
            else:
                logger.debug(f"Category {self.name} already exists in {ctx.guild.name}")
        else:
            category = await ctx.guild.create_category(self.name)
            self.channels.category_channel = category.id
            await self.save()

        for category, channels in ctx.guild.by_category():
            if category and category.id == self.channels.category_channel:
                await self._confirm_campaign_channels(ctx, category=category, channels=channels)
                await self._confirm_character_channels(ctx, category=category, channels=channels)
                break

        logger.debug(f"All channels confirmed for campaign '{self.name}' in '{ctx.guild.name}'")
