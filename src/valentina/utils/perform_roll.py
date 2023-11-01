"""Perform a diceroll."""

from valentina.models import Character, CharacterTrait
from valentina.models.bot import ValentinaContext
from valentina.models.dicerolls import DiceRoll
from valentina.views import ReRollButton, RollDisplay


async def perform_roll(
    ctx: ValentinaContext,
    pool: int,
    difficulty: int,
    dice_size: int,
    comment: str | None = None,
    hidden: bool = False,
    trait_one: CharacterTrait | None = None,
    trait_two: CharacterTrait | None = None,
    character: Character | None = None,
) -> None:
    """Perform a dice roll and display the result.

    Args:
        ctx (ValentinaContext): The context of the command.
        pool (int): The number of dice to roll.
        difficulty (int): The difficulty of the roll.
        dice_size (int): The size of the dice.
        comment (str, optional): A comment to display with the roll. Defaults to None.
        hidden (bool, optional): Whether to hide the response from other users. Defaults to False.
        from_macro (bool, optional): Whether the roll is from a macro. Defaults to False.
        trait_one (CustomTrait, Trait, optional): The name of the first trait. Defaults to None.
        trait_two (CustomTrait, Trait, optional): The name of the second trait. Defaults to None.
        character (Character, optional): The ID of the character to log the roll for. Defaults to None.
    """
    roll = DiceRoll(ctx, pool=pool, difficulty=difficulty, dice_size=dice_size, character=character)

    traits_to_log = []
    if trait_one:
        traits_to_log.append(trait_one.name)
    if trait_two:
        traits_to_log.append(trait_two.name)

    await roll.log_roll(traits=traits_to_log)

    while True:
        view = ReRollButton(ctx.author)
        embed = await RollDisplay(
            ctx,
            roll,
            comment,
            trait_one,
            trait_two,
        ).get_embed()
        await ctx.respond(embed=embed, view=view, ephemeral=hidden)

        # Wait for a re-roll
        await view.wait()
        if view.confirmed:
            roll = DiceRoll(
                ctx, pool=pool, difficulty=difficulty, dice_size=dice_size, character=character
            )
            await roll.log_roll(traits=traits_to_log)
        else:
            break
