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

from valentina.constants import CHANNEL_PERMISSIONS, CampaignChannelName, Emoji
from valentina.utils.helpers import time_now

from .character import Character
from .note import Note

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
    notes: list[Link[Note]] = Field(default_factory=list)

    @property
    def channel_name(self) -> str:
        """Channel name for the book."""
        return f"{Emoji.BOOK.value}-{self.number:0>2}-{self.name.lower().replace(' ', '-')}"

    async def fetch_chapters(self) -> list[CampaignBookChapter]:
        """Fetch all chapters in the book.

        This method retrieves and sorts all chapters associated with the book by their number.

        Returns:
            list[CampaignBookChapter]: A sorted list of CampaignBookChapter objects associated with the book.
        """
        return sorted(
            self.chapters,  # type: ignore [arg-type]
            key=lambda x: x.number,
        )

    async def delete_channel(self, ctx: "ValentinaContext") -> None:  # pragma: no cover
        """Delete the channel associated with the book.

        This method removes the channel linked to the book from the guild and updates the book's channel information.

        Args:
            ctx (ValentinaContext): The context object containing guild information.

        Returns:
            None
        """
        if not self.channel:
            return

        channel = ctx.guild.get_channel(self.channel)

        if not channel:
            return

        await channel.delete()
        self.channel = None
        await self.save()

    async def confirm_channel(
        self, ctx: "ValentinaContext", campaign: Optional["Campaign"]
    ) -> discord.TextChannel | None:
        """Confirm or create the channel for the book within the campaign.

        This method ensures the book's channel exists within the campaign's category. It updates the channel information in the database if necessary, renames a channel if it has the wrong name, or creates a new one if it doesn't exist.

        Args:
            ctx (ValentinaContext): The context object containing guild information.
            campaign (Optional[Campaign]): The campaign object. If not provided, it will be fetched using the book's campaign ID.

        Returns:
            discord.TextChannel | None: The channel object if found or created, otherwise None.
        """
        campaign = campaign or await Campaign.get(self.campaign)
        if not campaign:
            return None

        category, channels = await campaign.fetch_campaign_category_channels(ctx)

        if not category:
            return None

        is_channel_name_in_category = any(self.channel_name == channel.name for channel in channels)
        is_channel_id_in_category = (
            any(self.channel == channel.id for channel in channels) if self.channel else False
        )

        # If channel name exists in category but not in database, add channel id to self
        if is_channel_name_in_category and not self.channel:
            await asyncio.sleep(1)  # Keep the rate limit happy
            for channel in channels:
                if channel.name == self.channel_name:
                    self.channel = channel.id
                    await self.save()
                    return channel

        # If channel.id exists but has wrong name, rename it
        elif self.channel and is_channel_id_in_category and not is_channel_name_in_category:
            channel_object = next(
                (channel for channel in channels if self.channel == channel.id), None
            )
            return await ctx.channel_update_or_add(
                channel=channel_object,
                name=self.channel_name,
                category=category,
                permissions=CHANNEL_PERMISSIONS["default"],
                topic=f"Channel for book {self.number}. {self.name}",
            )

        # If channel does not exist, create it
        elif not is_channel_name_in_category:
            await asyncio.sleep(1)  # Keep the rate limit happy
            book_channel = await ctx.channel_update_or_add(
                name=self.channel_name,
                category=category,
                permissions=CHANNEL_PERMISSIONS["default"],
                topic=f"Channel for Chapter {self.number}. {self.name}",
            )
            self.channel = book_channel.id
            await self.save()
            return book_channel

        await asyncio.sleep(1)  # Keep the rate limit happy
        return discord.utils.get(channels, name=self.channel_name)


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
    is_deleted: bool = False  # Campaigns are never deleted from the DB, only marked as deleted
    chapters: list[CampaignChapter] = Field(default_factory=list)
    npcs: list[CampaignNPC] = Field(default_factory=list)
    books: list[Link[CampaignBook]] = Field(default_factory=list)
    channel_campaign_category: int | None = None
    channel_storyteller: int | None = None
    channel_general: int | None = None

    @before_event(Insert, Replace, Save, Update, SaveChanges)
    async def update_modified_date(self) -> None:
        """Update the date_modified field."""
        self.date_modified = time_now()

    async def _confirm_common_channels(
        self,
        ctx: "ValentinaContext",
        category: discord.CategoryChannel,
        channels: list[discord.TextChannel],
    ) -> None:  # pragma: no cover
        """Create or update common campaign channels in the guild.

        This method ensures that the common channels (e.g., storyteller and general channels)
        are created or updated as necessary in the specified category. It checks existing
        channels, updates database references, and creates new channels if necessary.

        Args:
            ctx (ValentinaContext): The context of the command invocation.
            category (discord.CategoryChannel): The category where common channels are managed.
            channels (list[discord.TextChannel]): The list of existing text channels in the category.

        Returns:
            None: This function does not return a value.
        """
        # Static channels
        common_channel_list = {  # channel_db_key: channel_name
            "channel_storyteller": CampaignChannelName.STORYTELLER.value,
            "channel_general": CampaignChannelName.GENERAL.value,
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

    async def fetch_campaign_category_channels(
        self, ctx: "ValentinaContext"
    ) -> tuple[discord.CategoryChannel, list[discord.TextChannel]]:
        """Fetch the campaign category channels in the guild.

        Args:
            ctx (ValentinaContext): The context object containing guild information.

        Returns:
            tuple[discord.CategoryChannel, list[discord.TextChannel]]: A tuple containing the campaign category channel and a list of text channels within that category. If the category is not found, returns (None, []).
        """
        for category, channels in ctx.guild.by_category():
            if category and category.id == self.channel_campaign_category:
                return category, channels

        return None, []

    @staticmethod
    def _custom_channel_sort(channel: discord.TextChannel) -> tuple[int, str]:  # pragma: no cover
        """Generate a custom sorting key for campaign channels.

        This method prioritizes channels based on their channel names.

        Args:
            channel (discord.TextChannel): The channel to generate the sort key for.

        Returns:
            tuple[int, str]: A tuple indicating the sort priority and the channel name.

        """
        if channel.name.startswith(Emoji.SPARKLES.value):
            return (0, channel.name)

        if channel.name.startswith(Emoji.BOOK.value):
            return (1, channel.name)

        if channel.name.startswith(Emoji.LOCK.value):
            return (2, channel.name)

        if channel.name.startswith(Emoji.SILHOUETTE.value):
            return (3, channel.name)

        if channel.name.startswith(Emoji.DEAD.value):
            return (4, channel.name)

        return (5, channel.name)

    async def create_channels(self, ctx: "ValentinaContext") -> None:  # pragma: no cover
        """Create and organize the campaign channels in the guild.

        This method ensures the campaign category and its channels are correctly created and named.
        If the campaign category already exists, it renames it if necessary. Then, it creates the necessary channels for books and characters, confirming their existence and respecting the rate limits.

        Args:
            ctx (ValentinaContext): The context object containing guild information.

        Returns:
            None
        """
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

                for book in await self.fetch_books():
                    await book.confirm_channel(ctx, campaign=self)
                    await asyncio.sleep(1)  # Keep the rate limit happy

                for character in await self.fetch_characters():
                    await character.confirm_channel(ctx, campaign=self)
                    await asyncio.sleep(1)  # Keep the rate limit happy
                break

        await self.sort_channels(ctx)

        logger.info(f"All channels confirmed for campaign '{self.name}' in '{ctx.guild.name}'")

    async def delete_channels(self, ctx: "ValentinaContext") -> None:  # pragma: no cover
        """Delete the channels associated with the campaign.

        This method removes all channels related to the campaign, including book channels,
        character channels, storyteller channel, general channel, and the campaign category channel.

        Args:
            ctx (ValentinaContext): The context object containing guild information.

        Returns:
            None
        """
        for book in await self.fetch_books():
            await book.delete_channel(ctx)

        for character in await self.fetch_characters():
            await character.delete_channel(ctx)

        if self.channel_storyteller:
            channel = ctx.guild.get_channel(self.channel_storyteller)

            if channel:
                await channel.delete()
                self.channel_storyteller = None

        if self.channel_general:
            channel = ctx.guild.get_channel(self.channel_general)

            if channel:
                await channel.delete()
                self.channel_general = None

        if self.channel_campaign_category:
            category = ctx.guild.get_channel(self.channel_campaign_category)

            if category:
                await category.delete()
                self.channel_campaign_category = None

        await self.save()

    async def fetch_characters(self) -> list[Character]:
        """Fetch all player characters in the campaign.

        This method retrieves a list of all player characters associated with the campaign.

        Returns:
            list[Character]: A list of Character objects representing player characters in the campaign.
        """
        return await Character.find(
            Character.campaign == str(self.id),
            Character.type_player == True,  # noqa: E712
        ).to_list()

    async def fetch_books(self) -> list[CampaignBook]:
        """Fetch all books in the campaign.

        This method retrieves and sorts a list of all books associated with the campaign by their number.

        Returns:
            list[CampaignBook]: A sorted list of CampaignBook objects associated with the campaign.
        """
        return sorted(
            self.books,  # type: ignore [arg-type]
            key=lambda x: x.number,
        )

    async def sort_channels(self, ctx: "ValentinaContext") -> None:
        """Sort the campaign channels in the guild.

        This method sorts the campaign channels within their category according to a custom sorting key.

        Args:
            ctx (ValentinaContext): The context object containing guild information.

        Returns:
            None
        """
        for category, channels in ctx.guild.by_category():
            if category and category.id == self.channel_campaign_category:
                sorted_channels = sorted(channels, key=self._custom_channel_sort)
                for i, channel in enumerate(sorted_channels):
                    if channel.position and channel.position == i:
                        continue
                    await channel.edit(position=i)
                    await asyncio.sleep(2)  # Keep the rate limit happy

                logger.debug(f"Sorted channels: {[channel.name for channel in sorted_channels]}")
                break

        logger.info(f"Channels sorted for campaign '{self.name}' in '{ctx.guild.name}'")
