"""Add a trait to a character."""
import discord

from valentina import char_svc
from valentina.models.constants import FLAT_COMMON_TRAITS
from valentina.models.database import Character, CustomTrait
from valentina.views import ConfirmCancelButtons, present_embed


def __validate_trait_name(trait_name: str, character: Character) -> None:
    """Ensure the trait name is unique."""
    if trait_name.lower() in [x.lower() for x in FLAT_COMMON_TRAITS]:
        raise ValueError(f"Trait name **{trait_name}** already exists.")

    custom_traits = CustomTrait.select().where(CustomTrait.character == character.id)
    if trait_name.lower() in [x.name.lower() for x in custom_traits]:
        raise ValueError(f"Trait name **{trait_name}** already exists.")


async def add_trait(
    ctx: discord.ApplicationContext,
    trait_name: str,
    category: str,
    trait_value: int,
    max_value: int,
    trait_description: str,
    character: Character,
) -> None:
    """Add a trait to a character."""
    try:
        __validate_trait_name(trait_name, character)
        view = ConfirmCancelButtons(ctx.author)
        await present_embed(
            ctx,
            title=f"Create {trait_name}",
            description=f"Confirm creating custom trait: **{trait_name}**",
            fields=[
                ("Category", category),
                ("Value", f"`{trait_value!s}`"),
                ("Max Value", f"`{max_value!s}`"),
                ("Description", trait_description),
            ],
            inline_fields=False,
            ephemeral=True,
            level="info",
            view=view,
        )
        await view.wait()
        if view.confirmed:
            char_svc.add_trait(
                ctx,
                character,
                name=trait_name,
                description=trait_description,
                category=category,
                value=trait_value,
                max_value=max_value,
            )
            await present_embed(
                ctx=ctx,
                title=f"Custom trait added to {character.name}",
                fields=[
                    ("Trait", f"**{trait_name.title()}**"),
                    ("Category", category),
                    ("Description", trait_description),
                    ("Value", f"`{trait_value!s}`"),
                    ("Max Value", f"`{max_value!s}`"),
                ],
                inline_fields=False,
                level="success",
                log=True,
                ephemeral=True,
            )
    except ValueError as e:
        await present_embed(ctx=ctx, title="Error adding trait", description=str(e), level="ERROR")
