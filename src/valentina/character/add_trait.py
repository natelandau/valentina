"""Add a trait to a character."""
import discord
from loguru import logger

from valentina.models.constants import FLAT_TRAITS
from valentina.models.database import Character, CustomTrait
from valentina.views.embeds import ConfirmCancelView, present_embed


def __validate_trait_name(trait_name: str, character: Character) -> None:
    """Ensure the trait name is unique."""
    if trait_name.lower() in [x.lower() for x in FLAT_TRAITS]:
        raise ValueError(f"Trait name **{trait_name}** already exists.")

    custom_traits = CustomTrait.select().where(CustomTrait.character == character.id)
    if trait_name.lower() in [x.name.lower() for x in custom_traits]:
        raise ValueError(f"Trait name **{trait_name}** already exists.")


async def add_trait(
    ctx: discord.ApplicationContext,
    trait_name: str,
    trait_area: str,
    trait_value: int,
    trait_description: str,
    character: Character,
) -> None:
    """Add a trait to a character."""
    try:
        __validate_trait_name(trait_name, character)
        view = ConfirmCancelView(ctx.author)
        await present_embed(
            ctx,
            title=f"Create {trait_name}",
            description=f"Confirm creating custom trait: **{trait_name}**",
            fields=[
                ("Area", trait_area),
                ("Value", f"`{trait_value!s}`"),
                ("Description", trait_description),
            ],
            inline_fields=False,
            ephemeral=True,
            level="info",
            view=view,
        )
        await view.wait()
        if view.confirmed:
            CustomTrait.create(
                name=trait_name,
                description=trait_description,
                trait_area=trait_area,
                value=trait_value,
                character=character.id,
            )
            logger.info(f"Created custom trait {trait_name} for {character.name}")
            await present_embed(
                ctx=ctx,
                title=f"Custom trait added to {character.name}",
                fields=[
                    ("Name", trait_name),
                    ("Area", trait_area),
                    ("Value", f"`{trait_value!s}`"),
                    ("Description", trait_description),
                ],
                inline_fields=False,
                level="success",
            )
    except ValueError as e:
        await present_embed(ctx=ctx, title="Error adding trait", description=str(e), level="ERROR")
