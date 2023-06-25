# mypy: disable-error-code="valid-type"
"""Sample cog used for testing purposes."""
from pathlib import Path

import discord
from discord.ext import commands
from loguru import logger
from sh import tail

from valentina import CONFIG, Valentina, __version__
from valentina.views import present_embed


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
        await present_embed(
            ctx,
            title="Connection Information",
            description="",
            fields=[
                ("Status", str(self.bot.status)),
                ("Latency", f"`{self.bot.latency!s}`"),
                ("Connected Guilds", str(len(self.bot.guilds))),
                ("Bot Version", f"`{__version__}`"),
            ],
            level="info",
            ephemeral=True,
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

        await present_embed(
            ctx, "Reload Bot", f"{count} cogs successfully reloaded", level="info", ephemeral=True
        )

    @debug.command(description="Tail last 15 lines of the bot's logs")
    @commands.is_owner()
    async def logs(self, ctx: discord.ApplicationContext) -> None:
        """Tail the bot's logs."""
        logger.debug("debug:logs: Tailing the logs")
        logs = tail("-n15", CONFIG["VALENTINA_LOG_FILE"], _bg=True)
        await ctx.send("```" + str(logs) + "```")


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Debug(bot))
