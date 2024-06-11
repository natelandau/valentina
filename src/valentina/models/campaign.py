"""Campaign models for Valentina."""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import discord
from beanie import (
    Document,
    Indexed,
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

from valentina.constants import CHANNEL_PERMISSIONS, Emoji
from valentina.utils.helpers import time_now

from .character import Character

if TYPE_CHECKING:
    from valentina.models.bot import ValentinaContext


class CampaignChapter(BaseModel):
    """Represents a chapter as a subdocument within Campaign.

    # TODO: Remove after migration
    """

    description_long: str = None
    description_short: str = None
    name: str
    number: int
    date_created: datetime = Field(default_factory=time_now)
    channel: int | None = None


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


class CampaignNote(BaseModel):  # pragma: no cover
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
    """Representation of a campaign's channel ids as a subdocument attached to a Campaign.

    TODO: Remove after migration
    """

    category_channel: int | None = None
    storyteller: int | None = None
    log: int | None = None
    general: int | None = None


class CampaignBookChapter(Document):
    """Represents a chapter as a subdocument within CampaignBook."""

    book: Indexed(str)  # type: ignore [valid-type]
    date_created: datetime = Field(default_factory=time_now)
    description_long: str = None
    description_short: str = None
    name: str
    number: int


class CampaignBook(Document):
    """Represents a book as a sub-document within Campaign."""

    campaign: Indexed(str)  # type: ignore [valid-type]
    channel: int | None = None
    chapters: list[Link[CampaignBookChapter]] = Field(default_factory=list)
    date_created: datetime = Field(default_factory=time_now)
    description_long: str = None
    description_short: str = None
    name: str
    number: int

    async def fetch_chapters(self) -> list[CampaignBookChapter]:
        """Fetch all chapters in the book."""
        return sorted(
            self.chapters,  # type: ignore [arg-type]
            key=lambda x: x.number,
        )


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
    channels: Optional[CampaignChannels] = None  # TODO: Remove after migration
    books: list[Link[CampaignBook]] = Field(default_factory=list)
    channel_campaign_category: int | None = None
    channel_storyteller: int | None = None
    channel_general: int | None = None

    @before_event(Insert, Replace, Save, Update, SaveChanges)
    async def update_modified_date(self) -> None:
        """Update the date_modified field."""
        self.date_modified = time_now()

    async def _confirm_book_channels(
        self,
        ctx: "ValentinaContext",
        category: discord.CategoryChannel,
        channels: list[discord.TextChannel],
    ) -> None:  # pragma: no cover
        """Create the book channels for the campaign."""
        for book in await self.fetch_books():
            channel_name = (
                f"{Emoji.BOOK.value}-{book.number:0>2}-{book.name.lower().replace(' ', '-')}"
            )
            channel_db_id = book.channel
            channel_name_in_category = any(channel_name == channel.name for channel in channels)
            channel_id_in_category = (
                any(channel_db_id == channel.id for channel in channels) if channel_db_id else False
            )

            if channel_name_in_category and not channel_db_id:
                await asyncio.sleep(1)  # Keep the rate limit happy
                for channel in channels:
                    if channel.name == channel_name:
                        book.channel = channel.id
                        await book.save()
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
                    topic=f"Channel for book {book.number}. {book.name}",
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
                    topic=f"Channel for Chapter {book.number}. {book.name}",
                )
                book.channel = created_channel.id
                await book.save()
                logger.info(
                    f"Channel {channel_name} does not exist in {category}. Create new channel and add to database"
                )

    async def _confirm_character_channels(
        self,
        ctx: "ValentinaContext",
        category: discord.CategoryChannel,
        channels: list[discord.TextChannel],
    ) -> None:  # pragma: no cover
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
    ) -> None:  # pragma: no cover
        """Create the campaign channels in the guild."""
        # Static channels
        common_channel_list = {  # channel_db_key: channel_name
            "channel_storyteller": f"{Emoji.LOCK.value}-storyteller",
            "channel_general": f"{Emoji.SPARKLES.value}-general",
        }
        for channel_db_key, channel_name in common_channel_list.items():
            # Set permissions
            if channel_name.startswith(Emoji.LOCK.value):
                permissions = CHANNEL_PERMISSIONS["storyteller_channel"]
            else:
                permissions = CHANNEL_PERMISSIONS["default"]

            channel_db_id = getattr(self, channel_db_key, None)

            channel_name_in_category = any(channel_name == channel.name for channel in channels)
            channel_id_in_category = (
                any(channel_db_id == channel.id for channel in channels) if channel_db_id else False
            )

            if channel_name_in_category and not channel_db_id:
                await asyncio.sleep(1)  # Keep the rate limit happy
                for channel in channels:
                    if channel.name == channel_name:
                        setattr(self, channel_db_key, channel.id)
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
                setattr(self, channel_db_key, created_channel.id)
                await self.save()
                logger.info(
                    f"Channel {channel_name} does not exist in {category}. Create new channel and add to database"
                )

    @staticmethod
    def _custom_channel_sort(channel: discord.TextChannel) -> tuple[int, str]:  # pragma: no cover
        """Custom sorting key to for campaign channels.

        Args:
            channel: The channel to generate the sort key for.

        Returns:
            A tuple indicating the sort priority and the channel name.
        """
        if channel.name.startswith(Emoji.SPARKLES.value):
            return (0, channel.name)

        if channel.name.startswith(Emoji.BOOK.value):
            return (1, channel.name)

        if channel.name.startswith(Emoji.LOCK.value):
            return (2, channel.name)

        return (3, channel.name)

    async def create_channels(self, ctx: "ValentinaContext") -> None:  # pragma: no cover
        """Create the campaign channels in the guild."""
        # Migrate channels
        await self.migrate_campaign_channels()

        category_name = f"{Emoji.BOOKS.value}-{self.name.lower().replace(' ', '-')}"

        if self.channel_campaign_category:
            channel_object = ctx.guild.get_channel(self.channel_campaign_category)

            if not channel_object:
                category = await ctx.guild.create_category(category_name)
                self.channel_campaign_category = category.id
                logger.debug(f"Campaign category '{category_name}' created in '{ctx.guild.name}'")
                await self.save()

            elif channel_object.name != category_name:
                await channel_object.edit(name=category_name)
                logger.debug(f"Campaign category '{category_name}' renamed in '{ctx.guild.name}'")

            else:
                logger.debug(f"Category {category_name} already exists in {ctx.guild.name}")
        else:
            category = await ctx.guild.create_category(category_name)
            self.channel_campaign_category = category.id
            await self.save()
            logger.debug(f"Campaign category '{category_name}' created in '{ctx.guild.name}'")

        # Create the channels
        for category, channels in ctx.guild.by_category():
            if category and category.id == self.channel_campaign_category:
                await self._confirm_common_channels(ctx, category=category, channels=channels)
                await asyncio.sleep(1)  # Keep the rate limit happy
                await self._confirm_book_channels(ctx, category=category, channels=channels)
                await asyncio.sleep(1)  # Keep the rate limit happy
                await self._confirm_character_channels(ctx, category=category, channels=channels)
                await asyncio.sleep(1)  # Keep the rate limit happy
                break

        for category, channels in ctx.guild.by_category():
            if category and category.id == self.channel_campaign_category:
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

    async def migrate_campaign_channels(self) -> None:  # pragma: no cover
        """Migrate campaign channels to the new structure.

        TODO: Remove this method after all campaigns have been migrated.
        """
        if getattr(self, "channels", None) is None:
            return

        did_migrate_channels = False

        if self.channels.category_channel:
            self.channel_campaign_category = self.channels.category_channel
            logger.info("Migrated category channel to new structure.")
            did_migrate_channels = True

        if self.channels.storyteller:
            self.channel_storyteller = self.channels.storyteller
            logger.info("Migrated storyteller channel to new structure.")
            did_migrate_channels = True

        if self.channels.general:
            self.channel_general = self.channels.general
            logger.info("Migrated general channel to new structure.")
            did_migrate_channels = True

        if did_migrate_channels:
            await self.save()
            logger.info("Campaign channel migration complete.")

    async def fetch_books(self) -> list[CampaignBook]:
        """Fetch all books in the campaign."""
        return sorted(
            self.books,  # type: ignore [arg-type]
            key=lambda x: x.number,
        )
