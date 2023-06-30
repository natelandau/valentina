# mypy: disable-error-code="valid-type"
"""Gameplay cog for Valentina."""

import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina import Valentina, char_svc, user_svc
from valentina.models.constants import MAX_OPTION_LIST_SIZE
from valentina.models.dicerolls import DiceRoll
from valentina.utils.errors import MacroNotFoundError, NoClaimError
from valentina.views import present_embed
from valentina.views.roll_display import RollDisplay


class Roll(commands.Cog):
    """Commands used during gameplay."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

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

    async def __trait_one_autocomplete(self, ctx: discord.ApplicationContext) -> list[str]:
        """Populates the autocomplete for the trait option."""
        try:
            character = char_svc.fetch_claim(ctx)
        except NoClaimError:
            return ["No character claimed"]

        traits = []
        for trait in char_svc.fetch_all_character_traits(character, flat_list=True):
            if trait.lower().startswith(ctx.options["trait_one"].lower()):
                traits.append(trait)
            if len(traits) >= MAX_OPTION_LIST_SIZE:
                break
        return traits

    async def __trait_two_autocomplete(self, ctx: discord.ApplicationContext) -> list[str]:
        """Populates the autocomplete for the trait option."""
        try:
            character = char_svc.fetch_claim(ctx)
        except NoClaimError:
            return ["No character claimed"]

        traits = []
        for trait in char_svc.fetch_all_character_traits(character, flat_list=True):
            if trait.lower().startswith(ctx.options["trait_two"].lower()):
                traits.append(trait)
            if len(traits) >= MAX_OPTION_LIST_SIZE:
                break
        return traits

    async def __macro_autocomplete(self, ctx: discord.ApplicationContext) -> list[str]:
        """Populate a select list with a users' macros."""
        macros = []
        for macro in user_svc.fetch_macros(ctx):
            if macro.name.lower().startswith(ctx.options["macro"].lower()):
                macros.append(f"{macro.name} ({macro.abbreviation})")
            if len(macros) >= MAX_OPTION_LIST_SIZE:
                break
        return macros

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
        roll = DiceRoll(ctx, pool=pool, difficulty=difficulty, dice_size=10)
        logger.debug(f"ROLL: {ctx.author.display_name} rolled {roll.roll}")
        await RollDisplay(ctx, roll, comment).display()

    @roll.command(name="traits", description="Throw a roll based on trait names")
    async def traits(
        self,
        ctx: discord.ApplicationContext,
        trait_one: Option(
            str,
            description="First trait to roll",
            required=True,
            autocomplete=__trait_one_autocomplete,
        ),
        trait_two: Option(
            str,
            description="Second trait to roll",
            required=False,
            autocomplete=__trait_two_autocomplete,
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
        character = char_svc.fetch_claim(ctx)
        trait_one_value = char_svc.fetch_trait_value(ctx, character, trait_one)
        trait_two_value = char_svc.fetch_trait_value(ctx, character, trait_two) if trait_two else 0
        pool = trait_one_value + trait_two_value

        roll = DiceRoll(ctx, pool=pool, difficulty=difficulty, dice_size=10)
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
            roll = DiceRoll(ctx, pool=pool, dice_size=dice_size, difficulty=0)
            logger.debug(f"ROLL: {ctx.author.display_name} rolled {roll.roll}")
            await RollDisplay(ctx, roll, comment).display()
        except ValueError as e:
            await ctx.respond(f"Error rolling dice: {e}", ephemeral=True)

    @roll.command(name="macro", description="Roll a macro")
    async def roll_macro(
        self,
        ctx: discord.ApplicationContext,
        macro: Option(
            str,
            description="Macro to roll",
            required=True,
            autocomplete=__macro_autocomplete,
        ),
        difficulty: Option(
            int,
            "The difficulty of the roll",
            required=False,
            default=6,
        ),
        comment: Option(str, "A comment to display with the roll", required=False, default=None),
    ) -> None:
        """Roll a macro."""
        m = user_svc.fetch_macro(ctx, macro.split("(")[0].strip())
        if not m:
            raise MacroNotFoundError(macro=macro)

        character = char_svc.fetch_claim(ctx)
        trait_one_value = char_svc.fetch_trait_value(ctx, character, m.trait_one)
        trait_two_value = (
            char_svc.fetch_trait_value(ctx, character, m.trait_two) if m.trait_two else 0
        )
        pool = trait_one_value + trait_two_value

        roll = DiceRoll(ctx, pool=pool, difficulty=difficulty, dice_size=10)
        logger.debug(f"ROLL: {ctx.author.display_name} macro {m.name} rolled {roll.roll}")
        await RollDisplay(
            ctx,
            roll=roll,
            comment=comment,
            trait_one_name=m.trait_one,
            trait_one_value=trait_one_value,
            trait_two_name=m.trait_two,
            trait_two_value=trait_two_value,
        ).display()


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Roll(bot))
