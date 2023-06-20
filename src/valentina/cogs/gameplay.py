# mypy: disable-error-code="valid-type"
"""Gameplay cog for Valentina."""

import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina import Valentina, char_svc
from valentina.models.constants import MAX_OPTION_LIST_SIZE
from valentina.models.dicerolls import DiceRoll
from valentina.utils.errors import NoClaimError, TraitNotFoundError
from valentina.views.embeds import present_embed
from valentina.views.roll_display import RollDisplay


async def trait_one_autocomplete(ctx: discord.ApplicationContext) -> list[str]:
    """Populates the autocomplete for the trait option."""
    try:
        character = char_svc.fetch_claim(ctx.interaction.guild.id, ctx.interaction.user.id)
    except NoClaimError:
        return ["No character claimed"]

    traits = []
    for trait in char_svc.fetch_all_character_traits(character, flat_list=True):
        if trait.lower().startswith(ctx.options["trait_one"].lower()):
            traits.append(trait)
        if len(traits) >= MAX_OPTION_LIST_SIZE:
            break
    return traits


async def trait_two_autocomplete(ctx: discord.ApplicationContext) -> list[str]:
    """Populates the autocomplete for the trait option."""
    try:
        character = char_svc.fetch_claim(ctx.interaction.guild.id, ctx.interaction.user.id)
    except NoClaimError:
        return ["No character claimed"]

    traits = []
    for trait in char_svc.fetch_all_character_traits(character, flat_list=True):
        if trait.lower().startswith(ctx.options["trait_two"].lower()):
            traits.append(trait)
        if len(traits) >= MAX_OPTION_LIST_SIZE:
            break
    return traits


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
        try:
            roll = DiceRoll(pool=pool, difficulty=difficulty, dice_size=10)
            logger.debug(f"ROLL: {ctx.author.display_name} rolled {roll.roll}")
            await RollDisplay(ctx, roll, comment).display()
        except ValueError as e:
            await ctx.respond(f"Error rolling dice: {e}", ephemeral=True)

    @roll.command(name="traits", description="Throw a roll based on trait names")
    @logger.catch
    async def traits(
        self,
        ctx: discord.ApplicationContext,
        trait_one: Option(
            str,
            description="First trait to roll",
            required=True,
            autocomplete=trait_one_autocomplete,
        ),
        trait_two: Option(
            str,
            description="Second trait to roll",
            required=False,
            autocomplete=trait_two_autocomplete,
            default=None,
        ),
        difficulty: Option(
            int,
            "The difficulty of the roll",
            required=False,
            default=6,
        ),
        comment: Option(str, "A comment to display with the roll", required=False, default=None),
    ) -> None:
        """Roll the total number of d10s for two given traits against a difficulty."""
        try:
            character = char_svc.fetch_claim(ctx.guild.id, ctx.user.id)
            trait_one_value = char_svc.fetch_trait_value(character, trait_one)
            trait_two_value = char_svc.fetch_trait_value(character, trait_two) if trait_two else 0
            pool = trait_one_value + trait_two_value

            roll = DiceRoll(pool=pool, difficulty=difficulty, dice_size=10)
            logger.debug(f"ROLL: {ctx.author.display_name} rolled {roll.roll}")
            await RollDisplay(
                ctx,
                roll=roll,
                comment=comment,
                trait_one_name=trait_one,
                trait_one_value=trait_one_value,
                trait_two_name=trait_two,
                trait_two_value=trait_two_value,
            ).display()

        except NoClaimError:
            await present_embed(
                ctx=ctx,
                title="Error: No character claimed",
                description="You must claim a character before you can update its bio.\nTo claim a character, use `/character claim`.",
                level="error",
                ephemeral=True,
            )
            return
        except TraitNotFoundError as e:
            await present_embed(
                ctx=ctx,
                title="Error: Trait not found",
                description=str(e),
                level="error",
                ephemeral=True,
            )
            return

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
        try:
            roll = DiceRoll(pool=pool, dice_size=dice_size, difficulty=0)
            logger.debug(f"ROLL: {ctx.author.display_name} rolled {roll.roll}")
            await RollDisplay(ctx, roll, comment).display()
        except ValueError as e:
            await ctx.respond(f"Error rolling dice: {e}", ephemeral=True)


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Roll(bot))
