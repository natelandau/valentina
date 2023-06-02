# mypy: disable-error-code="valid-type"
"""Gameplay cog for Valentina."""

import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina.models import Valentina
from valentina.models.dicerolls import Roll
from valentina.models.enums import DiceType


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
        dice_type: Option(
            str, "The type of dice to roll in the format 'd10'", required=False, default="d10"
        ),
        comment: Option(str, "A comment to display with the roll", required=False, default=""),
    ) -> None:
        """Roll the dice."""
        dice_type = DiceType[dice_type.upper()]

        roll = Roll(pool=pool, difficulty=difficulty, dice_type=dice_type)
        logger.info("ROLL: Rolling dice")
        await ctx.respond("Rolling dice...\n" + str(roll.roll) + "\n" + comment)


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Gameplay(bot))
