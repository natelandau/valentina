"""Campaign models for Valentina."""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import discord
from beanie import (
    Document,
    Insert,
    Replace,
    Save,
    SaveChanges,
    Update,
    before_event,
)
from loguru import logger
from pydantic import BaseModel, Field

from valentina.constants import CHANNEL_PERMISSIONS, Emoji
from valentina.utils.helpers import time_now

from .character import Character

if TYPE_CHECKING:
    from valentina.models.bot import ValentinaContext


class CampaignChapter(BaseModel):
    """Represents a chapter as a subdocument within Campaign."""

    description_long: str = None
    description_short: str = None
    name: str
    number: int
    date_created: datetime = Field(default_factory=time_now)
    channel: int | None = None

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
    storyteller: int | None = None
    log: int | None = None
    general: int | None = None


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

    @before_event(Insert, Replace, Save, Update, SaveChanges)
    async def update_modified_date(self) -> None:
        """Update the date_modified field."""
        self.date_modified = time_now()

    async def _confirm_chapter_channels(
        self,
        ctx: "ValentinaContext",
        category: discord.CategoryChannel,
        channels: list[discord.TextChannel],
    ) -> None:
        """Create the chapter channels for the campaign."""
        for chapter in self.chapters:
            channel_name = f"{Emoji.CHAPTER.value}-{chapter.number:0>2}-{chapter.name.lower().replace(' ', '-')}"
            channel_db_id = chapter.channel
            channel_name_in_category = any(channel_name == channel.name for channel in channels)
            channel_id_in_category = (
                any(channel_db_id == channel.id for channel in channels) if channel_db_id else False
            )

            if channel_name_in_category and not channel_db_id:
                await asyncio.sleep(1)  # Keep the rate limit happy
                for channel in channels:
                    if channel.name == channel_name:
                        chapter.channel = channel.id
                        await self.save()
                logger.info(
                    f"Channel {channel_name} exists in {category} but not in database. Add channel id to database."
                )
            elif channel_db_id and channel_id_in_category and not channel_name_in_category:
                await asyncio.sleep(1)  # Keep the rate limit happy
                channel_object = next(
                    (channel for channel in channels if channel_db_id == channel.id), None
                )

                await ctx.channel_update_or_add(
                    channel=channel_object,
                    name=channel_name,
                    category=category,
                    permissions=CHANNEL_PERMISSIONS["default"],
                    topic=f"Channel for Chapter {chapter.number}. {chapter.name}",
                )

                logger.info(
                    f"Channel {channel_name} exists in database and {category} but name is different. Renamed channel."
                )

            elif not channel_name_in_category:
                await asyncio.sleep(1)  # Keep the rate limit happy
                created_channel = await ctx.channel_update_or_add(
                    name=channel_name,
                    category=category,
                    permissions=CHANNEL_PERMISSIONS["default"],
                    topic=f"Channel for Chapter {chapter.number}. {chapter.name}",
                )
                chapter.channel = created_channel.id
                await self.save()
                logger.info(
                    f"Channel {channel_name} does not exist in {category}. Create new channel and add to database"
                )

    async def _confirm_character_channels(
        self,
        ctx: "ValentinaContext",
        category: discord.CategoryChannel,
        channels: list[discord.TextChannel],
    ) -> None:
        """Create the character channels for the campaign."""
        for character in await self.fetch_characters():
            channel_name = f"{Emoji.SILHOUETTE.value}-{character.name.lower().replace(' ', '-')}"
            owned_by_user = discord.utils.get(ctx.bot.users, id=character.user_owner)
            await asyncio.sleep(1)  # Keep the rate limit happy
            channel_name_in_category = any(channel_name == channel.name for channel in channels)
            channel_db_id = character.channel
            channel_id_in_category = (
                any(channel_db_id == channel.id for channel in channels) if channel_db_id else False
            )

            if channel_name_in_category and not channel_db_id:
                await asyncio.sleep(1)  # Keep the rate limit happy
                for channel in channels:
                    if channel.name == channel_name:
                        character.channel = channel.id
                        await character.save()
                logger.info(
                    f"Channel {channel_name} exists in {category} but not in database. Add channel id to database."
                )

            elif channel_db_id and channel_id_in_category and not channel_name_in_category:
                await asyncio.sleep(1)  # Keep the rate limit happy
                channel_object = next(
                    (channel for channel in channels if channel_db_id == channel.id), None
                )

                await ctx.channel_update_or_add(
                    channel=channel_object,
                    name=channel_name,
                    category=category,
                    permissions=CHANNEL_PERMISSIONS["campaign_character_channel"],
                    permissions_user_post=owned_by_user,
                    topic=f"Character channel for {character.name}",
                )

                logger.info(
                    f"Channel {channel_name} exists in database and {category} but name is different. Renamed channel."
                )

            elif not channel_name_in_category:
                await asyncio.sleep(1)  # Keep the rate limit happy
                created_channel = await ctx.channel_update_or_add(
                    name=channel_name,
                    category=category,
                    permissions=CHANNEL_PERMISSIONS["campaign_character_channel"],
                    permissions_user_post=owned_by_user,
                    topic=f"Character channel for {character.name}",
                )
                character.channel = created_channel.id
                await character.save()
                logger.info(
                    f"Channel {channel_name} does not exist in {category}. Create new channel and add to database"
                )

    async def _confirm_common_channels(
        self,
        ctx: "ValentinaContext",
        category: discord.CategoryChannel,
        channels: list[discord.TextChannel],
    ) -> None:
        """Create the campaign channels in the guild."""
        # Static channels
        common_channel_list = {  # channel_db_key: channel_name
            "storyteller": f"{Emoji.LOCK.value}-storyteller",
            "general": f"{Emoji.SPARKLES.value}-general",
        }
        for channel_db_key, channel_name in common_channel_list.items():
            # Set permissions
            if channel_name.startswith(Emoji.LOCK.value):
                permissions = CHANNEL_PERMISSIONS["storyteller_channel"]
            else:
                permissions = CHANNEL_PERMISSIONS["default"]

            channel_db_id = getattr(self.channels, channel_db_key, None)

            channel_name_in_category = any(channel_name == channel.name for channel in channels)
            channel_id_in_category = (
                any(channel_db_id == channel.id for channel in channels) if channel_db_id else False
            )

            if channel_name_in_category and not channel_db_id:
                await asyncio.sleep(1)  # Keep the rate limit happy
                for channel in channels:
                    if channel.name == channel_name:
                        setattr(self.channels, channel_db_key, channel.id)
                        await self.save()

                logger.info(
                    f"Channel {channel_name} exists in {category} but not in database. Add channel id to database."
                )

            elif channel_db_id and channel_id_in_category and not channel_name_in_category:
                channel_object = next(
                    (channel for channel in channels if channel_db_id == channel.id), None
                )
                await asyncio.sleep(1)  # Keep the rate limit happy
                await ctx.channel_update_or_add(
                    channel=channel_object,
                    name=channel_name,
                    category=category,
                    permissions=permissions,
                )

                logger.info(
                    f"Channel {channel_name} exists in database and {category} but name is different. Renamed channel."
                )

            elif not channel_name_in_category:
                await asyncio.sleep(1)  # Keep the rate limit happy
                created_channel = await ctx.channel_update_or_add(
                    name=channel_name,
                    category=category,
                    permissions=permissions,
                )
                setattr(self.channels, channel_db_key, created_channel.id)
                await self.save()
                logger.info(
                    f"Channel {channel_name} does not exist in {category}. Create new channel and add to database"
                )

    @staticmethod
    def _custom_channel_sort(channel: discord.TextChannel) -> tuple[int, str]:
        """Custom sorting key to for campaign channels.

        Args:
            channel: The channel to generate the sort key for.

        Returns:
            A tuple indicating the sort priority and the channel name.
        """
        if channel.name.startswith(Emoji.SPARKLES.value):
            return (0, channel.name)

        if channel.name.startswith(Emoji.CHAPTER.value):
            return (1, channel.name)

        if channel.name.startswith(Emoji.LOCK.value):
            return (2, channel.name)

        return (3, channel.name)

    async def create_channels(self, ctx: "ValentinaContext") -> None:
        """Create the campaign channels in the guild."""
        category_name = f"{Emoji.BOOKS.value}-{self.name.lower().replace(' ', '-')}"

        if self.channels.category_channel:
            channel_object = ctx.guild.get_channel(self.channels.category_channel)

            if not channel_object:
                category = await ctx.guild.create_category(category_name)
                self.channels.category_channel = category.id
                logger.debug(f"Campaign category '{category_name}' created in '{ctx.guild.name}'")
                await self.save()

            elif channel_object.name != category_name:
                await channel_object.edit(name=category_name)
                logger.debug(f"Campaign category '{category_name}' renamed in '{ctx.guild.name}'")

            else:
                logger.debug(f"Category {category_name} already exists in {ctx.guild.name}")
        else:
            category = await ctx.guild.create_category(category_name)
            self.channels.category_channel = category.id
            await self.save()
            logger.debug(f"Campaign category '{category_name}' created in '{ctx.guild.name}'")

        # Create the channels
        for category, channels in ctx.guild.by_category():
            if category and category.id == self.channels.category_channel:
                await self._confirm_chapter_channels(ctx, category=category, channels=channels)
                await asyncio.sleep(1)  # Keep the rate limit happy
                await self._confirm_character_channels(ctx, category=category, channels=channels)
                await asyncio.sleep(1)  # Keep the rate limit happy
                await self._confirm_common_channels(ctx, category=category, channels=channels)
                await asyncio.sleep(1)  # Keep the rate limit happy
                break

        for category, channels in ctx.guild.by_category():
            if category and category.id == self.channels.category_channel:
                sorted_channels = sorted(channels, key=self._custom_channel_sort)
                for i, channel in enumerate(sorted_channels):
                    await channel.edit(position=i)
                    await asyncio.sleep(2)  # Keep the rate limit happy

                logger.debug(f"Sorted channels: {[channel.name for channel in sorted_channels]}")
                break

        logger.debug(f"All channels confirmed for campaign '{self.name}' in '{ctx.guild.name}'")

    async def fetch_characters(self) -> list[Character]:
        """Fetch all characters in the campaign."""
        return await Character.find(Character.campaign == str(self.id)).to_list()
