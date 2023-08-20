"""Perform a diceroll."""
import discord

from valentina.models.db_tables import Character, CustomTrait, Trait
from valentina.models.dicerolls import DiceRoll
from valentina.views import ReRollButton
from valentina.views.roll_display import RollDisplay


async def perform_roll(
    ctx: discord.ApplicationContext,
    pool: int,
    difficulty: int,
    dice_size: int,
    comment: str | None = None,
    hidden: bool = False,
    trait_one: Trait | CustomTrait | None = None,
    trait_one_value: int | None = None,
    trait_two: Trait | CustomTrait | None = None,
    trait_two_value: int | None = None,
    character: Character | None = None,
) -> None:
    """Perform a dice roll and display the result.

    Args:
        ctx (discord.ApplicationContext): The context of the command.
        pool (int): The number of dice to roll.
        difficulty (int): The difficulty of the roll.
        dice_size (int): The size of the dice.
        comment (str, optional): A comment to display with the roll. Defaults to None.
        hidden (bool, optional): Whether to hide the response from other users. Defaults to False.
        trait_one (CustomTrait, Trait, optional): The name of the first trait. Defaults to None.
        trait_one_value (int, optional): The value of the first trait. Defaults to None.
        trait_two (CustomTrait, Trait, optional): The name of the second trait. Defaults to None.
        trait_two_value (int, optional): The value of the second trait. Defaults to None.
        character (Character, optional): The ID of the character to log the roll for. Defaults to None.
    """
    roll = DiceRoll(ctx, pool=pool, difficulty=difficulty, dice_size=dice_size, character=character)

    while True:
        view = ReRollButton(ctx.author)
        embed = await RollDisplay(
            ctx,
            roll,
            comment,
            trait_one,
            trait_one_value,
            trait_two,
            trait_two_value,
        ).get_embed()
        await ctx.respond(embed=embed, view=view, ephemeral=hidden)

        # Wait for a re-roll
        await view.wait()
        if view.confirmed:
            roll = DiceRoll(
                ctx, pool=pool, difficulty=difficulty, dice_size=dice_size, character=character
            )
        else:
            break
