"""Perform a diceroll."""
from typing import cast

import discord

from valentina.models.bot import Valentina
from valentina.models.db_tables import Character, CustomTrait, Trait
from valentina.models.dicerolls import DiceRoll
from valentina.views import ReRollButton, RollDisplay


async def perform_roll(
    ctx: discord.ApplicationContext,
    pool: int,
    difficulty: int,
    dice_size: int,
    comment: str | None = None,
    hidden: bool = False,
    from_macro: bool = False,
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
        from_macro (bool, optional): Whether the roll is from a macro. Defaults to False.
        trait_one (CustomTrait, Trait, optional): The name of the first trait. Defaults to None.
        trait_one_value (int, optional): The value of the first trait. Defaults to None.
        trait_two (CustomTrait, Trait, optional): The name of the second trait. Defaults to None.
        trait_two_value (int, optional): The value of the second trait. Defaults to None.
        character (Character, optional): The ID of the character to log the roll for. Defaults to None.
    """
    roll = DiceRoll(ctx, pool=pool, difficulty=difficulty, dice_size=dice_size, character=character)
    await roll.log_roll()

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

        # If rolling traits and not from a macro, add some friendly hints
        if not from_macro and trait_one is not None and trait_two is not None:
            bot = cast(Valentina, ctx.bot)
            if macro := bot.macro_svc.fetch_macro_from_traits(ctx, trait_one, trait_two):
                await ctx.respond(
                    f"🙋‍♂️ Did you know that you already have a macro for this roll? Save time with `/roll macro {macro.name}`",
                    ephemeral=True,
                    delete_after=10,
                )
            else:
                await ctx.respond(
                    "🙋‍♂️ Did you know that you if you roll these traits often, you can save time by creating a macro? Just run `/macro create`",
                    ephemeral=True,
                    delete_after=10,
                )

        # Wait for a re-roll
        await view.wait()
        if view.confirmed:
            roll = DiceRoll(
                ctx, pool=pool, difficulty=difficulty, dice_size=dice_size, character=character
            )
            await roll.log_roll()
        else:
            break
