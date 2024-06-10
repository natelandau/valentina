# mypy: disable-error-code="valid-type"
"""Gameplay cog for Valentina."""

import random

import discord
from discord.commands import Option
from discord.ext import commands

from valentina.constants import DEFAULT_DIFFICULTY, DiceType, LogLevel
from valentina.models import User
from valentina.models.bot import Valentina, ValentinaContext
from valentina.utils import random_num
from valentina.utils.autocomplete import (
    select_char_trait,
    select_char_trait_two,
    select_desperation_dice,
    select_macro,
)
from valentina.utils.converters import ValidTraitFromID
from valentina.utils.discord_utils import character_from_channel
from valentina.utils.perform_roll import perform_roll
from valentina.views import present_embed


class Roll(commands.Cog):
    """Commands used during gameplay."""

    def __init__(self, bot: Valentina) -> None:
        self.bot: Valentina = bot

    ### DICEROLL COMMANDS ###
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
        desperation: Option(
            int,
            description="Add desperation dice",
            required=False,
            default=0,
            autocomplete=select_desperation_dice,
        ),
        comment: Option(str, "A comment to display with the roll", required=False, default=None),
    ) -> None:
        """Roll the dice.

        Args:
            comment (str, optional): A comment to display with the roll. Defaults to None.
            ctx (ValentinaContext): The context of the command
            difficulty (int): The difficulty of the roll
            desperation (int): Add x desperation dice to the roll
            pool (int): The number of dice to roll
        """
        # Grab the player's active character for statistic logging purposes
        character = await character_from_channel(ctx) or await ctx.fetch_active_character()

        if desperation > 0:
            active_campaign = await ctx.fetch_active_campaign()
            if active_campaign.desperation == 0 or desperation > 5:  # noqa: PLR2004
                await present_embed(
                    ctx,
                    title="Can not roll desperation",
                    description="The current desperation level is 0. No dice to roll.",
                    level="error",
                    ephemeral=True,
                )
                return

        await perform_roll(
            ctx,
            pool,
            difficulty,
            DiceType.D10.value,
            comment,
            character=character,
            desperation_pool=desperation,
        )

    @roll.command(name="traits", description="Throw a roll based on trait names")
    async def traits(
        self,
        ctx: ValentinaContext,
        trait_one: Option(
            ValidTraitFromID,
            name="trait_one",
            description="First trait to roll",
            required=True,
            autocomplete=select_char_trait,
        ),
        trait_two: Option(
            ValidTraitFromID,
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
        desperation: Option(
            int,
            description="Add desperation dice",
            required=False,
            default=0,
            autocomplete=select_desperation_dice,
        ),
        comment: Option(str, "A comment to display with the roll", required=False, default=None),
    ) -> None:
        """Roll the total number of d10s for two given traits against a difficulty."""
        character = await character_from_channel(ctx) or await ctx.fetch_active_character()

        pool = trait_one.value + trait_two.value

        ctx.log_command(
            f"{trait_one.name} ({trait_one.id}) + {trait_two.name} ({trait_two.id})",
            LogLevel.DEBUG,
        )

        if desperation > 0:
            active_campaign = await ctx.fetch_active_campaign()
            if active_campaign.desperation == 0 or desperation > 5:  # noqa: PLR2004
                await present_embed(
                    ctx,
                    title="Can not roll desperation",
                    description="The current desperation level is 0. No dice to roll.",
                    level="error",
                    ephemeral=True,
                )
                return

        await perform_roll(
            ctx,
            pool,
            difficulty,
            DiceType.D10.value,
            comment,
            trait_one=trait_one,
            trait_two=trait_two,
            character=character,
            desperation_pool=desperation,
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
        desperation: Option(
            int,
            description="Add desperation dice",
            required=False,
            default=0,
            autocomplete=select_desperation_dice,
        ),
        comment: Option(str, "A comment to display with the roll", required=False, default=None),
    ) -> None:
        """Roll a macro."""
        character = await character_from_channel(ctx) or await ctx.fetch_active_character()
        user = await User.get(ctx.author.id, fetch_links=True)
        macro = user.macros[index]

        trait_one = await character.fetch_trait_by_name(macro.trait_one)
        trait_two = await character.fetch_trait_by_name(macro.trait_two)

        if not trait_one or not trait_two:
            msg = "Macro traits not found on character"
            raise commands.BadArgument(msg)

        if desperation > 0:
            active_campaign = await ctx.fetch_active_campaign()
            if active_campaign.desperation == 0 or desperation > 5:  # noqa: PLR2004
                await present_embed(
                    ctx,
                    title="Can not roll desperation",
                    description="The current desperation level is 0. No dice to roll.",
                    level="error",
                    ephemeral=True,
                )
                return

        ctx.log_command(
            f"Macro: {macro.name}: {trait_one.name} ({trait_one.id}) + {trait_two.name} ({trait_two.id})",
            LogLevel.DEBUG,
        )

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
            desperation_pool=desperation,
        )

    @roll.command(name="desperation", description="Roll desperation")
    async def roll_desperation(
        self,
        ctx: ValentinaContext,
        desperation: Option(
            int,
            description="Add desperation dice",
            required=True,
            autocomplete=select_desperation_dice,
        ),
        difficulty: Option(
            int,
            "The difficulty of the roll",
            required=False,
            default=DEFAULT_DIFFICULTY,
        ),
        comment: Option(str, "A comment to display with the roll", required=False, default=None),
    ) -> None:
        """Roll desperation dice."""
        active_campaign = await ctx.fetch_active_campaign()
        if active_campaign.desperation == 0 or desperation > 5:  # noqa: PLR2004
            await present_embed(
                ctx,
                title="Can not roll desperation",
                description="The current desperation level is 0. No dice to roll.",
                level="error",
                ephemeral=True,
            )
            return

        # Grab the player's active character for statistic logging purposes
        character = await character_from_channel(ctx.channel) or await ctx.fetch_active_character()

        await perform_roll(
            ctx,
            0,
            difficulty,
            DiceType.D10.value,
            comment,
            character=character,
            desperation_pool=desperation,
        )

    ### GAMEPLAY COMMANDS ###
    gameplay = discord.SlashCommandGroup("gameplay", "Gameplay commands")

    @gameplay.command(name="damage", description="determine damage")
    async def damage(
        self,
        ctx: ValentinaContext,
        damage: Option(
            int,
            name="damage",
            description="Damage taken",
            required=True,
        ),
        soak: Option(
            int,
            name="soak",
            description="Soak to apply",
            required=False,
            default=0,
        ),
    ) -> None:
        """Determine damage."""
        damage = damage + random_num(10) - soak

        if damage <= 0:
            result = ("No Damage", "Miracles happen, no damage taken")

        if 1 <= damage <= 6:  # noqa: PLR2004
            result = ("Stunned", "Spend 1 Willpower or lose one turn.")

        elif 7 <= damage <= 8:  # noqa: PLR2004
            result = ("Severe head trauma", "Physical rolls lose 1 die; Mental rolls lose 2.")

        elif 9 <= damage <= 10:  # noqa: PLR2004
            one = ("Broken limb or joint", "Rolls using the affected limb lose 3 dice.")
            two = ("Blinded", "Vision-related rolls lose 3 dice.")
            result = random.choice([one, two])

        elif damage == 11:  # noqa: PLR2004
            result = ("Massive wound", "All rolls lose 2 dice. Add 1 to all damage suffered.")

        elif damage == 12:  # noqa: PLR2004
            result = ("Crippled", "Limb is lost or mangled beyond use. Lose 3 dice when using it.")

        elif damage >= 13:  # noqa: PLR2004
            result = ("Death or torpor", "Mortals die. Vampires enter immediate torpor.")

        title, description = result
        await present_embed(ctx, title, description, level="info")


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Roll(bot))
