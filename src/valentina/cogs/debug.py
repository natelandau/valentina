"""Sample cog used for testing purposes."""
import discord
from discord.ext import commands
from loguru import logger

from valentina.models import Valentina


class Debug(commands.Cog):
    """Commands for debugging purposes."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    debug = discord.SlashCommandGroup("debug", "Debug related commands")

    @debug.command(description="Receive debug information about the bot.")
    async def ping(self, ctx: discord.ApplicationContext) -> None:
        """Ping the bot to get debug information."""
        logger.info("debug:ping: Generating debug information")
        await ctx.respond(
            f"Status is {self.bot.status}\nLatency is {self.bot.latency}\nConnected to {len(self.bot.guilds)} guilds"
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Debug(bot))
