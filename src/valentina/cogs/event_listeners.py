"""Respond to events that occur in the Discord server."""

import discord
from discord.ext import commands
from loguru import logger

from valentina.constants import BAD_WORD_LIST
from valentina.models.bot import Valentina
from valentina.models.db_tables import Guild
from valentina.models.errors import reporter
from valentina.utils.bot_hooks import respond_to_mentions


class Events(commands.Cog, name="Events"):
    """Respond to events that occur in the Discord server."""

    def __init__(self, bot: Valentina) -> None:
        self.bot: Valentina = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """on_message event handling."""
        # Do not reply to bot's own messages
        if message.author.bot:
            return

        # Do not reply to messages that start with the prefix
        if message.content.startswith(self.bot.command_prefix):
            logger.warning(f"BOT: Ignoring command message: {message.content}")
            return

        # Respond to @mentions of the  bot
        if self.bot.user.mentioned_in(message) and message.mention_everyone is False:
            await respond_to_mentions(self.bot, message)
            return

        if any(word in message.content.lower() for word in BAD_WORD_LIST):
            await message.channel.send("You kiss your mother with that mouth?")
            return

    @commands.Cog.listener()
    async def on_application_command_error(
        self, ctx: discord.ApplicationContext, error: discord.DiscordException
    ) -> None:
        """Use centralized reporter to handle errors in slash commands."""
        await reporter.report_error(ctx, error)

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: discord.ApplicationContext, error: discord.DiscordException
    ) -> None:
        """Use centralized reporter to handle errors in prefix commands."""
        await reporter.report_error(ctx, error)

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild) -> None:
        """Log guild name changes and update the database."""
        if before.name != after.name:
            logger.info(f"BOT: Rename guild `{before.name}` => `{after.name}`")
            Guild.update(name=after.name).where(Guild.id == before.id).execute()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Called when a member joins the server."""
        logger.info(f"EVENT: {member.display_name} has joined the server")

        # Add user to the database
        self.bot.user_svc.fetch_user(user=member)


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Events(bot))
