"""A simple task broker for Valentina."""

import asyncio
from typing import assert_never

import discord
from loguru import logger

from valentina.constants import BrokerTaskType
from valentina.models import BrokerTask, Campaign, CampaignBook, Character

from .channel_mngr import ChannelManager


class TaskBroker:
    """A simple task broker for Valentina. Call the run() method from the Dicord bot at a set interval to poll the database for tasks to run."""

    def __init__(self, discord_guild: discord.Guild) -> None:
        self.discord_guild = discord_guild

    async def _rebuild_channels(self) -> None:
        """Delete and recreate all campaign channels in the Discord guild.

        Rebuild all campaign channels from scratch by first deleting existing channels and then
        recreating them with proper permissions and categories. This ensures channel structure
        matches the current campaign configuration in the database.

        The rebuild process:
        1. Fetch all campaigns for the guild from database
        2. For each campaign, delete all associated Discord channels
        3. Recreate campaign channels with updated permissions and categories

        Returns:
            None: This method modifies Discord channels but does not return a value

        Raises:
            discord.Forbidden: If bot lacks permissions to manage channels
            discord.HTTPException: If Discord API request fails
        """
        # Batch all rebuild tasks together since rebuilding channels is expensive.
        # This prevents multiple redundant rebuilds from running in parallel.
        rebuild_channel_tasks = await BrokerTask.find_many(
            BrokerTask.guild_id == self.discord_guild.id,
            BrokerTask.task == BrokerTaskType.REBUILD_CHANNELS,
            BrokerTask.has_error == False,  # noqa: E712
        ).to_list()
        if len(rebuild_channel_tasks) > 0:
            logger.info(
                f"BROKER: Found {len(rebuild_channel_tasks)} rebuild channel tasks for guild {self.discord_guild.id}",
            )

            channel_manager = ChannelManager(guild=self.discord_guild)
            for campaign in await Campaign.find_many(
                Campaign.guild == self.discord_guild.id,
                fetch_links=True,
            ).to_list():
                await channel_manager.delete_campaign_channels(campaign)
                # Add delay between operations to avoid hitting Discord rate limits
                await asyncio.sleep(1)
                await channel_manager.confirm_campaign_channels(campaign)
                await asyncio.sleep(1)

            # Clean up all rebuild tasks at once since they've been handled as a batch
            for task in rebuild_channel_tasks:
                await task.delete()

            if task.author_name:
                msg = f"BROKER: {task.author_name}'s task {task.task} completed"
            else:
                msg = f"BROKER: Task {task.task} completed"

            logger.info(msg)

    async def _rename_character_channel(self, task: BrokerTask) -> None:
        """Rename a character's Discord channel to match their current name.

        Process a character channel rename task by fetching the character from the database and using
        the channel manager to update the Discord channel. This ensures channel names stay
        synchronized with character data.

        Args:
            task (BrokerTask): The broker task containing character_id in its data field.

        Returns:
            None

        Raises:
            None: Sets task.has_error=True if character_id is invalid or character not found.
        """
        if not task.data.get("character_id"):
            task.has_error = True
            await task.save()
            return

        character = await Character.get(task.data["character_id"], fetch_links=True)
        if not character:
            logger.error(f"BROKER: Character {task.data['character_id']} not found")
            return

        channel_manager = ChannelManager(guild=self.discord_guild)
        await channel_manager.confirm_character_channel(
            character=character,
            campaign=character.campaign,
        )

    async def _rename_campaign_channel(self, task: BrokerTask) -> None:
        """Rename a campaign channel and update associated Discord channels.

        Process a campaign channel rename task by fetching the campaign from the database and
        using the channel manager to update all associated Discord channels. This ensures
        channel names stay synchronized with campaign data.

        Args:
            task (BrokerTask): The broker task containing campaign_id in its data field.

        Returns:
            None

        Raises:
            None: Sets task.has_error=True if campaign_id is invalid or campaign not found.
        """
        campaign = await Campaign.get(task.data.get("campaign_id"), fetch_links=True)
        if not campaign:
            task.has_error = True
            await task.save()
            return

        channel_manager = ChannelManager(guild=self.discord_guild)
        await channel_manager.confirm_campaign_channels(campaign)

    async def _rebuild_book_channels(self) -> None:
        """Delete and recreate all book channels in the Discord guild.

        Process all pending book channel tasks by deleting existing book channels and recreating them
        with updated names and positions. This ensures channel names and order stay synchronized with
        book data in the database.

        Returns:
            None: This method modifies Discord channels but does not return a value.

        Note:
            This is an expensive operation that should be used sparingly, as it involves multiple
            Discord API calls with rate limiting considerations.
        """
        # Find all pending book chapter channel tasks for this guild
        tasks = await BrokerTask.find_many(
            BrokerTask.guild_id == self.discord_guild.id,
            BrokerTask.task == BrokerTaskType.CONFIRM_BOOK_CHANNEL,
            BrokerTask.has_error == False,  # noqa: E712
        ).to_list()

        if not tasks:
            return

        channel_manager = ChannelManager(guild=self.discord_guild)

        # Track campaigns and books to avoid duplicate processing
        # We need to track campaigns separately since multiple books can be in the same campaign
        campaigns_to_sort = set()
        books_processed = set()

        for task in tasks:
            # Skip invalid tasks that are missing required data
            if not task.data.get("campaign_id") or not task.data.get("book_id"):
                task.has_error = True
                await task.save()
                continue

            campaigns_to_sort.add(task.data["campaign_id"])
            books_processed.add(task.data["book_id"])

            # Only process each book once to avoid unnecessary Discord API calls
            if not task.data["book_id"] not in books_processed:
                book = await CampaignBook.get(task.data["book_id"])
                await channel_manager.confirm_book_channel(book=book)
                # Sleep to avoid hitting Discord rate limits
                await asyncio.sleep(1)

            await task.delete()

        # After processing all books, sort channels in each affected campaign
        # This ensures proper ordering of channelsafter any book changes
        for campaign in campaigns_to_sort:
            await channel_manager.sort_campaign_channels(
                await Campaign.get(campaign, fetch_links=True),
            )

        logger.info(f"BROKER: {len(tasks)} book channel tasks completed")

    async def run(self) -> None:
        """Poll database for pending tasks and execute them.

        Fetches all incomplete tasks for this guild from the database and processes them based on their type. After each task is executed, marks it as completed and saves the updated state.

        Returns:
            None
        """
        await self._rebuild_channels()
        await self._rebuild_book_channels()

        tasks = await BrokerTask.find_many(
            BrokerTask.guild_id == self.discord_guild.id,
            BrokerTask.has_error == False,  # noqa: E712
        ).to_list()
        for task in tasks:
            match task.task:
                case BrokerTaskType.CONFIRM_CHARACTER_CHANNEL:
                    await self._rename_character_channel(task)
                    await asyncio.sleep(1)
                case BrokerTaskType.CONFIRM_CAMPAIGN_CHANNEL:
                    await self._rename_campaign_channel(task)
                    await asyncio.sleep(1)
                case _:
                    assert_never(task)

            if task.author_name:
                msg = f"BROKER: {task.author_name}'s task {task.task} completed"
            else:
                msg = f"BROKER: Task {task.task} completed"

            logger.info(msg)
            await task.delete()
