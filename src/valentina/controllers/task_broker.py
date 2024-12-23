"""A simple task broker for Valentina."""

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

        Iterates through all campaigns in the guild, deleting their existing Discord channels
        and recreating them with proper permissions and categories.

        Returns:
            None
        """
        channel_manager = ChannelManager(guild=self.discord_guild)
        for campaign in await Campaign.find_many(
            Campaign.guild == self.discord_guild.id, fetch_links=True
        ).to_list():
            await channel_manager.delete_campaign_channels(campaign)
            await channel_manager.confirm_campaign_channels(campaign)

    async def _rename_character_channel(self, task: BrokerTask) -> None:
        """Rename a character channel."""
        character = await Character.get(task.data["character_id"], fetch_links=True)
        if not character:
            logger.error(f"BROKER: Character {task.data['character_id']} not found")
            return

        channel_manager = ChannelManager(guild=self.discord_guild)
        await channel_manager.confirm_character_channel(
            character=character, campaign=character.campaign
        )

    async def _rename_book_channel(self, task: BrokerTask) -> None:
        """Rename a book channel."""
        book = await CampaignBook.get(task.data["book_id"], fetch_links=True)
        if not book:
            logger.error(f"BROKER: Book {task.data['book_id']} not found")
            return

        channel_manager = ChannelManager(guild=self.discord_guild)
        await channel_manager.confirm_book_channel(book=book)

    async def _rename_campaign_channel(self, task: BrokerTask) -> None:
        """Rename a campaign channel."""
        campaign = await Campaign.get(task.data["campaign_id"], fetch_links=True)
        if not campaign:
            logger.error(f"BROKER: Campaign {task.data['campaign_id']} not found")
            return

        channel_manager = ChannelManager(guild=self.discord_guild)
        await channel_manager.confirm_campaign_channels(campaign)

    async def run(self) -> None:
        """Poll database for pending tasks and execute them.

        Fetches all incomplete tasks for this guild from the database and processes them based on their type. After each task is executed, marks it as completed and saves the updated state.

        Returns:
            None
        """
        # Rebuilding channels is an expensive operation, so we only want to do it once per guild.
        rebuild_channel_tasks = await BrokerTask.find_many(
            BrokerTask.guild_id == self.discord_guild.id,
            BrokerTask.task == BrokerTaskType.REBUILD_CHANNELS,
            BrokerTask.completed == False,  # noqa: E712
        ).to_list()
        if len(rebuild_channel_tasks) > 0:
            logger.info(
                f"BROKER: Found {len(rebuild_channel_tasks)} rebuild channel tasks for guild {self.discord_guild.id}"
            )

            await self._rebuild_channels()

            for task in rebuild_channel_tasks:
                task.completed = True
                await task.save()

            if task.author_name:
                msg = f"BROKER: {task.author_name}'s task {task.task} completed"
            else:
                msg = f"BROKER: Task {task.task} completed"

            logger.info(msg)

        # Now we run other individual tasks
        tasks = await BrokerTask.find_many(
            BrokerTask.guild_id == self.discord_guild.id,
            BrokerTask.task != BrokerTaskType.REBUILD_CHANNELS,
            BrokerTask.completed == False,  # noqa: E712
        ).to_list()
        for task in tasks:
            match task.task:
                case BrokerTaskType.CONFIRM_CHARACTER_CHANNEL:
                    await self._rename_character_channel(task)
                case BrokerTaskType.CONFIRM_BOOK_CHANNEL:
                    await self._rename_book_channel(task)
                case BrokerTaskType.CONFIRM_CAMPAIGN_CHANNEL:
                    await self._rename_campaign_channel(task)
                case _:
                    assert_never(task)

            task.completed = True

            if task.author_name:
                msg = f"BROKER: {task.author_name}'s task {task.task} completed"
            else:
                msg = f"BROKER: Task {task.task} completed"

            logger.info(msg)
            await task.save()
