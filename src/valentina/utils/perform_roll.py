"""Perform a diceroll."""

import discord

from valentina.constants import EmbedColor, Emoji
from valentina.models import Character, CharacterTrait, DiceRoll
from valentina.models.bot import ValentinaContext
from valentina.views import ReRollButton, RollDisplay


async def perform_roll(  # pragma: no cover
    ctx: ValentinaContext,
    pool: int,
    difficulty: int,
    dice_size: int,
    comment: str | None = None,
    hidden: bool = False,
    trait_one: CharacterTrait | None = None,
    trait_two: CharacterTrait | None = None,
    character: Character | None = None,
    desperation_pool: int = 0,
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
        desperation_pool (int, optional): The number of dice in the desperation pool. Defaults to 0.
    """
    roll = DiceRoll(
        ctx,
        pool=pool,
        difficulty=difficulty,
        dice_size=dice_size,
        character=character,
        desperation_pool=desperation_pool,
    )

    traits_to_log = []
    if trait_one:
        traits_to_log.append(trait_one.name)
    if trait_two:
        traits_to_log.append(trait_two.name)

    await roll.log_roll(traits=traits_to_log)

    view = ReRollButton(
        author=ctx.author,
        desperation_pool=desperation_pool,
        desperation_botch=roll.desperation_botches > 0 if roll.desperation_botches else False,
    )
    embed = await RollDisplay(
        ctx,
        roll,
        comment,
        trait_one,
        trait_two,
        desperation_pool=desperation_pool,
    ).get_embed()
    original_response = await ctx.respond(embed=embed, view=view, ephemeral=hidden)

    # Wait for a re-roll
    await view.wait()

    if view.overreach:
        active_campaign = await ctx.fetch_active_campaign()
        if active_campaign.danger < 5:  # noqa: PLR2004
            active_campaign.danger += 1
            await active_campaign.save()

        await original_response.edit_original_response(  # type: ignore [union-attr]
            view=None,
            embed=discord.Embed(
                title=None,
                description=f"# {Emoji.OVERREACH.value} Overreach!\nThe character overreached. This roll has succeeded but the danger level has increased to `{active_campaign.danger}`.",
                color=EmbedColor.WARNING.value,
            ),
        )

    if view.despair:
        await original_response.edit_original_response(  # type: ignore [union-attr]
            view=None,
            embed=discord.Embed(
                title=None,
                description=f"# {Emoji.DESPAIR.value} Despair!\n### This roll has failed and the character has entered Despair!\nYou can no longer use desperation dice until you redeem yourself.",
                color=EmbedColor.WARNING.value,
            ),
        )

    if view.timeout:
        if isinstance(original_response, discord.Interaction):
            await original_response.edit_original_response(view=None)
        if isinstance(original_response, discord.WebhookMessage):
            await original_response.edit(view=None)

    if view.reroll:
        await perform_roll(
            ctx,
            pool=pool,
            difficulty=difficulty,
            dice_size=dice_size,
            comment=comment,
            hidden=hidden,
            trait_one=trait_one,
            trait_two=trait_two,
            character=character,
            desperation_pool=desperation_pool,
        )
