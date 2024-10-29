"""Process changes from the webui.

The webui has no idea of a discord ctx object which is required for creating, renaming, and deleting channels or permissions on Discord. We need to poll the database for changes and process them.
"""

from typing import TYPE_CHECKING, assert_never

import discord
from loguru import logger

from valentina.constants import DBSyncModelType, DBSyncUpdateType
from valentina.models import Campaign, CampaignBook, Character, WebDiscordSync

from .channel_mngr import ChannelManager

if TYPE_CHECKING:
    from valentina.discord.bot import Valentina


class SyncDiscordFromWebManager:
    """Manage syncing changes from the webui to Discord."""

    def __init__(self, bot: "Valentina"):
        self.bot = bot

    async def _process_character_change(self, sync: WebDiscordSync) -> None:
        """Process a character change."""
        # Grab items from the database
        guild = await discord.utils.get_or_fetch(self.bot, "guild", sync.guild_id)
        member = discord.utils.get(guild.members, id=sync.user_id)

        # Process the change
        channel_manager = ChannelManager(guild=guild, user=member)

        match sync.update_type:
            case DBSyncUpdateType.CREATE | DBSyncUpdateType.UPDATE:
                character = await Character.get(sync.object_id)
                if not character:
                    logger.error(f"SYNC: Character {sync.object_id} not found in database")
                    return

                campaign = await Campaign.get(character.campaign)
                if not campaign:
                    logger.error(f"SYNC: Campaign {character.campaign} not found in database")
                    return

                await channel_manager.confirm_character_channel(
                    character=character, campaign=campaign
                )
                await channel_manager.sort_campaign_channels(campaign=campaign)
                logger.info(f"SYNC: Synced character {character.name} from webui to discord")

            case DBSyncUpdateType.DELETE:
                campaign = await Campaign.get(sync.guild_id)
                if not campaign:
                    logger.error(f"SYNC: Campaign {sync.guild_id} not found in database")
                    return

                await channel_manager.confirm_campaign_channels(campaign=campaign)
                logger.info(
                    f"SYNC: Synced deleted character {sync.object_id} from webui to discord"
                )

            case _:
                assert_never(sync.update_type)

    async def _process_campaign_change(self, sync: WebDiscordSync) -> None:
        """Process a campaign change."""
        # Grab items from the database
        guild = await discord.utils.get_or_fetch(self.bot, "guild", sync.guild_id)
        member = discord.utils.get(guild.members, id=sync.user_id)
        campaign = await Campaign.get(sync.object_id)
        if not campaign:
            logger.error(f"SYNC: Campaign {sync.object_id} not found in database")
            return

        # Process the change
        channel_manager = ChannelManager(guild=guild, user=member)

        match sync.update_type:
            case DBSyncUpdateType.CREATE | DBSyncUpdateType.UPDATE:
                await channel_manager.confirm_campaign_channels(campaign=campaign)
                logger.info(f"SYNC: Synced campaign {campaign.name} from webui to discord")

            case DBSyncUpdateType.DELETE:
                await channel_manager.delete_campaign_channels(campaign=campaign)
                logger.info(f"SYNC: Synced deleted campaign {sync.object_id} from webui to discord")

            case _:
                assert_never(sync.update_type)

    async def _process_book_change(self, sync: WebDiscordSync) -> None:
        """Process a book change."""
        guild = await discord.utils.get_or_fetch(self.bot, "guild", sync.guild_id)
        member = discord.utils.get(guild.members, id=sync.user_id)
        book = await CampaignBook.get(sync.object_id)
        if not book:
            logger.error(f"SYNC: Book {sync.object_id} not found in database")
            return

        campaign = await Campaign.get(book.campaign)
        if not campaign:
            logger.error(f"SYNC: Campaign {book.campaign} not found in database")
            return

        channel_manager = ChannelManager(guild=guild, user=member)

        match sync.update_type:
            case DBSyncUpdateType.CREATE | DBSyncUpdateType.UPDATE:
                await channel_manager.confirm_book_channel(book=book, campaign=campaign)
                logger.info(f"SYNC: Synced book {book.name} from webui to discord")

            case DBSyncUpdateType.DELETE:
                await channel_manager.delete_book_channel(book=book)
                logger.info(f"SYNC: Synced deleted book {sync.object_id} from webui to discord")

            case _:
                assert_never(sync.update_type)

    async def run(self) -> None:
        """Run the sync process."""
        async for sync in WebDiscordSync.find(
            WebDiscordSync.target == "discord",
            WebDiscordSync.processed == False,  # noqa: E712
        ):
            model = DBSyncModelType(sync.object_type)

            match model:
                case DBSyncModelType.CAMPAIGN:
                    await self._process_campaign_change(sync)
                case DBSyncModelType.BOOK:
                    await self._process_book_change(sync)
                case DBSyncModelType.CHARACTER:
                    await self._process_character_change(sync)
                case DBSyncModelType.GUILD | DBSyncModelType.ROLE | DBSyncModelType.USER:
                    pass
                case _:
                    assert_never(model)

            await sync.mark_processed()
