# mypy: disable-error-code="valid-type"
"""Gameplay cog for Valentina."""

import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina import Valentina, user_svc
from valentina.models.dicerolls import DiceRoll
from valentina.views.roll_display import RollDisplay


class Roll(commands.Cog):
    """Commands used during gameplay."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    roll = discord.SlashCommandGroup("roll", "Roll dice")

    @roll.command(description="Throw a roll of d10s.")
    async def throw(
        self,
        ctx: discord.ApplicationContext,
        pool: discord.Option(int, "The number of dice to roll", required=True),
        difficulty: Option(
            int,
            "The difficulty of the roll",
            required=True,
        ),
        comment: Option(str, "A comment to display with the roll", required=False, default=None),
    ) -> None:
        """Roll the dice.

        Args:
            comment (str, optional): A comment to display with the roll. Defaults to None.
            ctx (discord.ApplicationContext): The context of the command
            difficulty (int): The difficulty of the roll
            pool (int): The number of dice to roll
        """
        if not user_svc.is_cached(ctx.guild.id, ctx.user.id) and not user_svc.is_in_db(
            ctx.guild.id, ctx.user.id
        ):
            user_svc.create(ctx.guild.id, ctx.user)

        try:
            roll = DiceRoll(pool=pool, difficulty=difficulty, dice_size=10)
            logger.debug(f"ROLL: {ctx.author.display_name} rolled {roll.roll}")
            await RollDisplay(ctx, roll, comment).display()
        except ValueError as e:
            await ctx.respond(f"Error rolling dice: {e}", ephemeral=True)

    @roll.command(description="Simple dice roll of any size.")
    async def simple(
        self,
        ctx: discord.ApplicationContext,
        pool: discord.Option(int, "The number of dice to roll", required=True),
        dice_size: Option(int, "Number of sides on the dice.", required=True),
        comment: Option(str, "A comment to display with the roll", required=False, default=None),
    ) -> None:
        """Roll any type of dice.

        Args:
            comment (str, optional): A comment to display with the roll. Defaults to None.
            ctx (discord.ApplicationContext): The context of the command
            dice_size (int): The number of sides on the dice
            pool (int): The number of dice to roll
        """
        if not user_svc.is_cached(ctx.guild.id, ctx.user.id) and not user_svc.is_in_db(
            ctx.guild.id, ctx.user.id
        ):
            user_svc.create(ctx.guild.id, ctx.user)

        try:
            roll = DiceRoll(pool=pool, dice_size=dice_size, difficulty=0)
            logger.debug(f"ROLL: {ctx.author.display_name} rolled {roll.roll}")
            await RollDisplay(ctx, roll, comment).display()
        except ValueError as e:
            await ctx.respond(f"Error rolling dice: {e}", ephemeral=True)


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Roll(bot))
