"""Sample cog used for testing purposes."""
from pathlib import Path

import discord
from discord.ext import commands
from loguru import logger

from valentina import Valentina


class Debug(commands.Cog):
    """Commands for debugging purposes."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    debug = discord.SlashCommandGroup("debug", "Debug related commands")

    @debug.command(description="Receive debug information about the bot.")
    @commands.is_owner()
    async def ping(self, ctx: discord.ApplicationContext) -> None:
        """Ping the bot to get debug information."""
        logger.info("debug:ping: Generating debug information")
        await ctx.respond(
            f"Status is {self.bot.status}\nLatency is {self.bot.latency}\nConnected to {len(self.bot.guilds)} guilds"
        )

    @debug.command(description="Live reload the bot.")
    @commands.is_owner()
    async def reload(self, ctx: discord.ApplicationContext) -> None:
        """Reloads all cogs."""
        logger.debug("debug:reload: Reloading the bot...")
        count = 0
        for cog in Path(self.bot.parent_dir / "src" / "valentina" / "cogs").glob("*.py"):
            if cog.stem[0] != "_":
                count += 1
                logger.info(f"COGS: Reloading - {cog.stem}")
                self.bot.reload_extension(f"valentina.cogs.{cog.stem}")

        embed = discord.Embed(
            title="Reload Bot", description=f"{count} cogs successfully reloaded", color=0xFF00C8
        )
        await ctx.respond(embed=embed)


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Debug(bot))
