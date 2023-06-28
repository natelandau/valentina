"""Game information cog for Valentina."""

import discord
from discord.ext import commands
from loguru import logger

from valentina import Valentina
from valentina.views import present_embed


class Info(commands.Cog):
    """Reference information for the game. Remind yourself of the rules."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    info = discord.SlashCommandGroup("info", "Get information about the game")

    async def cog_command_error(
        self, ctx: discord.ApplicationContext, error: discord.ApplicationCommandError | Exception
    ) -> None:
        """Handle exceptions and errors from the cog."""
        if hasattr(error, "original"):
            error = error.original

        command_name = ""
        if ctx.command.parent.name:
            command_name = f"{ctx.command.parent.name} "
        command_name += ctx.command.name

        await present_embed(
            ctx,
            title=f"Error running `{command_name}` command",
            description=str(error),
            level="error",
            ephemeral=True,
            delete_after=15,
        )

    @info.command(description="See health levels.")
    async def health(self, ctx: discord.ApplicationContext) -> None:
        """Display health levels."""
        description = "```\n"
        description += "Bruised       :\n"
        description += "Hurt          : -1\n"
        description += "Injured       : -1\n"
        description += "Wounded       : -2\n"
        description += "Mauled        : -2\n"
        description += "Crippled      : -5\n"
        description += "Incapacitated :\n"
        description += "```"

        embed = discord.Embed(
            title="Health Levels",
            description=description,
            color=discord.Color.red(),
        )
        logger.debug(f"INFO: {ctx.author.display_name} requested health levels")
        await ctx.send(embed=embed)


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Info(bot))
