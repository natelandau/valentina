# mypy: disable-error-code="valid-type"
"""Gameplay cog for Valentina."""
import random

import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina.models.bot import Valentina
from valentina.models.constants import EmbedColor, RollResultType
from valentina.models.database import MacroTrait, Trait
from valentina.models.dicerolls import DiceRoll
from valentina.utils.converters import ValidCharTrait, ValidMacroFromID, ValidThumbnailURL
from valentina.utils.options import select_char_trait, select_char_trait_two, select_macro
from valentina.views import ConfirmCancelButtons, ReRollButton, present_embed
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

        logger.exception(error)

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

    roll = discord.SlashCommandGroup("roll", "Roll dice")

    @roll.command(description="Throw a roll of d10s")
    @logger.catch
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

        while True:
            view = ReRollButton(ctx.author)
            embed = await RollDisplay(ctx, roll, comment).get_embed()
            await ctx.respond(embed=embed, view=view)
            await view.wait()
            if view.confirmed:
                roll = DiceRoll(ctx, pool=pool, difficulty=difficulty, dice_size=10)
            if not view.confirmed:
                break

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
            default=6,
        ),
        comment: Option(str, "A comment to display with the roll", required=False, default=None),
    ) -> None:
        """Roll the total number of d10s for two given traits against a difficulty."""
        character = self.bot.char_svc.fetch_claim(ctx)
        trait_one_value = character.trait_value(trait_one)
        trait_two_value = character.trait_value(trait_two)

        pool = trait_one_value + trait_two_value

        roll = DiceRoll(ctx, pool=pool, difficulty=difficulty, dice_size=10)

        while True:
            view = ReRollButton(ctx.author)
            embed = await RollDisplay(
                ctx,
                roll=roll,
                comment=comment,
                trait_one_name=trait_one.name,
                trait_one_value=trait_one_value,
                trait_two_name=trait_two.name,
                trait_two_value=trait_two_value,
            ).get_embed()
            await ctx.respond(embed=embed, view=view)
            await view.wait()
            if view.confirmed:
                roll = DiceRoll(ctx, pool=pool, difficulty=difficulty, dice_size=10)
            if not view.confirmed:
                break

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

            while True:
                view = ReRollButton(ctx.author)
                embed = await RollDisplay(ctx, roll, comment).get_embed()
                await ctx.respond(embed=embed, view=view)
                await view.wait()
                if view.confirmed:
                    roll = DiceRoll(ctx, pool=pool, dice_size=dice_size, difficulty=0)
                if not view.confirmed:
                    break
        except ValueError as e:
            await ctx.respond(f"Error rolling dice: {e}", ephemeral=True)

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
            default=6,
        ),
        comment: Option(str, "A comment to display with the roll", required=False, default=None),
    ) -> None:
        """Roll a macro."""
        character = self.bot.char_svc.fetch_claim(ctx)
        traits = Trait.select().join(MacroTrait).where(MacroTrait.macro == macro)
        trait_one = traits[0]
        trait_two = traits[1]

        trait_one_value = character.trait_value(trait_one)
        trait_two_value = character.trait_value(trait_two)
        ###########################################3333

        pool = trait_one_value + trait_two_value

        roll = DiceRoll(ctx, pool=pool, difficulty=difficulty, dice_size=10)

        while True:
            view = ReRollButton(ctx.author)
            embed = await RollDisplay(
                ctx,
                roll=roll,
                comment=comment,
                trait_one_name=trait_one.name,
                trait_one_value=trait_one_value,
                trait_two_name=trait_two.name,
                trait_two_value=trait_two_value,
            ).get_embed()
            await ctx.respond(embed=embed, view=view)
            await view.wait()
            if view.confirmed:
                roll = DiceRoll(ctx, pool=pool, difficulty=difficulty, dice_size=10)
            if not view.confirmed:
                break

    @roll.command(description="Add images to roll result embeds")
    async def upload_thumbnail(
        self,
        ctx: discord.ApplicationContext,
        roll_type: Option(
            str,
            description="Type of roll to add the thumbnail to",
            required=True,
            choices=[roll_type.value for roll_type in RollResultType],
        ),
        url: Option(ValidThumbnailURL, description="URL of the thumbnail", required=True),
    ) -> None:
        """Add a roll result thumbnail to the bot."""
        view = ConfirmCancelButtons(ctx.author)
        msg = await present_embed(
            ctx,
            title="Upload image?",
            description=f"Your image may be seen when for **{roll_type}** rolls. Are you sure you want to upload it?",
            image=url,
            level="info",
            ephemeral=True,
            view=view,
        )
        await view.wait()

        if not view.confirmed:
            embed = discord.Embed(title="Upload cancelled", color=EmbedColor.INFO.value)
            await msg.edit_original_response(embed=embed, view=None)
            return
        if view.confirmed:
            self.bot.guild_svc.add_roll_result_thumb(ctx, roll_type, url)
            await msg.delete_original_response()

            await present_embed(
                ctx,
                title="Roll Result Thumbnail Added",
                description=f"Added thumbnail for `{roll_type}` roll results",
                image=url,
                level="success",
                ephemeral=True,
                log=True,
            )

    @roll.command(name="coinflip", help="Flip a coin")
    async def coinflip(self, ctx: discord.ApplicationContext) -> None:
        """Coinflip!"""
        coinsides = ["Heads", "Tails"]
        await ctx.respond(
            f"**{ctx.author.name}** flipped a coin and got **{random.choice(coinsides)}**!"
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Roll(bot))
