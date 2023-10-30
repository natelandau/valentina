# mypy: disable-error-code="valid-type"
"""Gameplay cog for Valentina."""

import discord
from discord.commands import Option
from discord.ext import commands

from valentina.constants import DEFAULT_DIFFICULTY, DiceType, RollResultType
from valentina.models.bot import Valentina, ValentinaContext
from valentina.models.mongo_collections import User
from valentina.utils.converters import ValidImageURL
from valentina.utils.options import select_char_trait, select_char_trait_two, select_macro
from valentina.utils.perform_roll import perform_roll
from valentina.views import confirm_action


class Roll(commands.Cog):
    """Commands used during gameplay."""

    def __init__(self, bot: Valentina) -> None:
        self.bot: Valentina = bot

    roll = discord.SlashCommandGroup("roll", "Roll dice")

    @roll.command(description="Throw a roll of d10s")
    async def throw(
        self,
        ctx: ValentinaContext,
        pool: discord.Option(int, "The number of dice to roll", required=True),
        difficulty: Option(
            int,
            "The difficulty of the roll",
            required=False,
            default=DEFAULT_DIFFICULTY,
        ),
        comment: Option(str, "A comment to display with the roll", required=False, default=None),
    ) -> None:
        """Roll the dice.

        Args:
            comment (str, optional): A comment to display with the roll. Defaults to None.
            ctx (ValentinaContext): The context of the command
            difficulty (int): The difficulty of the roll
            pool (int): The number of dice to roll
        """
        # Grab the player's active character for statistic logging purposes
        character = await ctx.fetch_active_character(raise_error=False)

        await perform_roll(ctx, pool, difficulty, DiceType.D10.value, comment, character=character)

    @roll.command(name="traits", description="Throw a roll based on trait names")
    async def traits(
        self,
        ctx: ValentinaContext,
        index1: Option(
            int,
            name="trait_one",
            description="First trait to roll",
            required=True,
            autocomplete=select_char_trait,
        ),
        index2: Option(
            int,
            name="trait_two",
            description="Second trait to roll",
            required=True,
            autocomplete=select_char_trait_two,
        ),
        difficulty: Option(
            int,
            "The difficulty of the roll",
            required=False,
            default=DEFAULT_DIFFICULTY,
        ),
        comment: Option(str, "A comment to display with the roll", required=False, default=None),
    ) -> None:
        """Roll the total number of d10s for two given traits against a difficulty."""
        character = await ctx.fetch_active_character()
        trait_one = character.traits[index1]
        trait_two = character.traits[index2]

        pool = trait_one.value + trait_two.value

        await perform_roll(
            ctx,
            pool,
            difficulty,
            DiceType.D10.value,
            comment,
            trait_one=trait_one,
            trait_two=trait_two,
            character=character,
        )

    @roll.command(description="Simple dice roll of any size.")
    async def dice(
        self,
        ctx: ValentinaContext,
        pool: discord.Option(int, "The number of dice to roll", required=True),
        dice_size: Option(int, "Number of sides on the dice.", required=True),
        comment: Option(str, "A comment to display with the roll", required=False, default=None),
    ) -> None:
        """Roll any type of dice.

        Args:
            comment (str, optional): A comment to display with the roll. Defaults to None.
            ctx (ValentinaContext): The context of the command
            dice_size (int): The number of sides on the dice
            pool (int): The number of dice to roll
        """
        await perform_roll(ctx, pool, 0, dice_size, comment)

    @roll.command(name="macro", description="Roll a macro")
    async def roll_macro(
        self,
        ctx: ValentinaContext,
        index: Option(
            int,
            name="macro",
            description="Macro to roll",
            required=True,
            autocomplete=select_macro,
        ),
        difficulty: Option(
            int,
            "The difficulty of the roll",
            required=False,
            default=DEFAULT_DIFFICULTY,
        ),
        comment: Option(str, "A comment to display with the roll", required=False, default=None),
    ) -> None:
        """Roll a macro."""
        character = await ctx.fetch_active_character()
        user = await User.get(ctx.author.id, fetch_links=True)
        macro = user.macros[index]

        trait_one = await character.fetch_trait_by_name(macro.trait_one)
        trait_two = await character.fetch_trait_by_name(macro.trait_two)

        if not trait_one or not trait_two:
            msg = "Macro traits not found on character"
            raise commands.BadArgument(msg)

        pool = trait_one.value + trait_two.value

        await perform_roll(
            ctx,
            pool,
            difficulty,
            DiceType.D10.value,
            comment,
            trait_one=trait_one,
            trait_two=trait_two,
            character=character,
        )

    @roll.command(description="Add images to roll result embeds")
    async def upload_thumbnail(
        self,
        ctx: ValentinaContext,
        roll_type: Option(
            str,
            description="Type of roll to add the thumbnail to",
            required=True,
            choices=[roll_type.name for roll_type in RollResultType],
        ),
        url: Option(ValidImageURL, description="URL of the thumbnail", required=True),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Add a roll result thumbnail to the bot."""
        title = f"Upload roll result thumbnail\n{url}"
        is_confirmed, confirmation_response_msg = await confirm_action(
            ctx, title, hidden=hidden, image=url
        )

        if not is_confirmed:
            return

        await self.bot.guild_svc.add_roll_result_thumb(ctx, roll_type, url)

        await self.bot.guild_svc.post_to_audit_log(title)
        await confirmation_response_msg


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Roll(bot))
