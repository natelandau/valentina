# mypy: disable-error-code="valid-type"
"""Gameplay cog for Valentina."""

import discord
from discord.commands import Option
from discord.ext import commands

from valentina.constants import DEFAULT_DIFFICULTY, DiceType, EmbedColor, RollResultType
from valentina.models import Probability
from valentina.models.bot import Valentina
from valentina.utils import errors
from valentina.utils.cogs import confirm_action
from valentina.utils.converters import ValidCharTrait, ValidImageURL, ValidMacroFromID
from valentina.utils.options import select_char_trait, select_char_trait_two, select_macro
from valentina.utils.perform_roll import perform_roll


class Roll(commands.Cog):
    """Commands used during gameplay."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    roll = discord.SlashCommandGroup("roll", "Roll dice")

    @roll.command(description="Throw a roll of d10s")
    async def throw(
        self,
        ctx: discord.ApplicationContext,
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
            ctx (discord.ApplicationContext): The context of the command
            difficulty (int): The difficulty of the roll
            pool (int): The number of dice to roll
        """
        # Grab the player's active character for statistic logging purposes
        try:
            character = self.bot.user_svc.fetch_active_character(ctx)
        except errors.NoActiveCharacterError:
            character = None

        await perform_roll(ctx, pool, difficulty, DiceType.D10.value, comment, character=character)

    @roll.command(name="probability", description="Calculate the probability of a roll")
    async def probability(
        self,
        ctx: discord.ApplicationContext,
        pool: discord.Option(int, "The number of dice to roll", required=True),
        difficulty: Option(
            int,
            "The difficulty of the roll",
            required=True,
        ),
        hidden: Option(
            bool,
            description="Make the probability only visible to you (default False).",
            default=False,
        ),
    ) -> None:
        """Roll the dice.

        Args:
            hidden (bool, optional): Make the statistics only visible to you (default true). Defaults to True.
            ctx (discord.ApplicationContext): The context of the command
            difficulty (int): The difficulty of the roll
            pool (int): The number of dice to roll
        """
        probabilities = Probability(
            ctx, pool=pool, difficulty=difficulty, dice_size=DiceType.D10.value
        )
        embed = await probabilities.get_embed()
        await ctx.respond(embed=embed, ephemeral=hidden)

    @roll.command(name="traits", description="Throw a roll based on trait names")
    async def traits(
        self,
        ctx: discord.ApplicationContext,
        trait_one: Option(
            ValidCharTrait,
            description="First trait to roll",
            required=True,
            autocomplete=select_char_trait,
        ),
        trait_two: Option(
            ValidCharTrait,
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
        character = self.bot.user_svc.fetch_active_character(ctx)
        trait_one_value = character.get_trait_value(trait_one)
        trait_two_value = character.get_trait_value(trait_two)

        pool = trait_one_value + trait_two_value

        await perform_roll(
            ctx,
            pool,
            difficulty,
            DiceType.D10.value,
            comment,
            trait_one=trait_one,
            trait_one_value=trait_one_value,
            trait_two=trait_two,
            trait_two_value=trait_two_value,
            character=character,
        )

    @roll.command(description="Simple dice roll of any size.")
    async def dice(
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
        await perform_roll(ctx, pool, 0, dice_size, comment)

    @roll.command(name="macro", description="Roll a macro")
    async def roll_macro(
        self,
        ctx: discord.ApplicationContext,
        macro: Option(
            ValidMacroFromID,
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
        character = self.bot.user_svc.fetch_active_character(ctx)

        traits = self.bot.macro_svc.fetch_macro_traits(macro)
        trait_one = traits[0]
        trait_two = traits[1]

        trait_one_value = character.get_trait_value(trait_one)
        trait_two_value = character.get_trait_value(trait_two)

        pool = trait_one_value + trait_two_value

        await perform_roll(
            ctx,
            pool,
            difficulty,
            DiceType.D10.value,
            comment,
            trait_one=trait_one,
            trait_one_value=trait_one_value,
            trait_two=trait_two,
            trait_two_value=trait_two_value,
            character=character,
        )

    @roll.command(description="Add images to roll result embeds")
    async def upload_thumbnail(
        self,
        ctx: discord.ApplicationContext,
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
        confirmed, msg = await confirm_action(ctx, title, hidden=hidden, url=url)

        if not confirmed:
            return

        self.bot.guild_svc.add_roll_result_thumb(ctx, roll_type, url)

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await msg.edit_original_response(
            embed=discord.Embed(
                title=title,
                color=EmbedColor.SUCCESS.value,
            ).set_image(url=url)
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Roll(bot))
