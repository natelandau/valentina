# mypy: disable-error-code="valid-type"
"""Gameplay cog for Valentina."""

import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina.models import Valentina
from valentina.models.dicerolls import Roll
from valentina.views.roll_display import RollDisplay


class Gameplay(commands.Cog):
    """Commands for gameplay."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    @commands.slash_command()
    async def roll(
        self,
        ctx: discord.ApplicationContext,
        pool: discord.Option(int, "The number of dice to roll", required=True),
        difficulty: Option(
            int,
            "The difficulty of the roll",
            required=True,
        ),
        dice_size: Option(
            int, "Number of sides on the dice. (Default: 10)", required=False, default=10
        ),
        comment: Option(str, "A comment to display with the roll", required=False, default=None),
    ) -> None:
        """Roll the dice."""
        try:
            roll = Roll(pool=pool, difficulty=difficulty, dice_size=dice_size)
            logger.debug(f"ROLL: {ctx.author.display_name} rolled {roll.roll}")
            await RollDisplay(ctx, roll, comment).display()
        except ValueError as e:
            await ctx.respond(f"Error rolling dice: {e}", ephemeral=True)


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Gameplay(bot))
