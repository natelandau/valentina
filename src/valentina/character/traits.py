"""Add a trait to a character."""
import discord

from valentina.models.db_tables import Character, CustomTrait, Trait, TraitCategory
from valentina.utils import errors
from valentina.views import ConfirmCancelButtons, present_embed


def __validate_trait_name(trait_name: str, character: Character) -> None:
    """Ensure the trait name is unique."""
    if trait_name.lower() in [x.name.lower() for x in Trait.select().order_by(Trait.name.asc())]:
        raise errors.ValidationError(f"Trait name `{trait_name}` already exists.")

    custom_traits = CustomTrait.select().where(CustomTrait.character == character.id)
    if trait_name.lower() in [x.name.lower() for x in custom_traits]:
        raise errors.ValidationError(f"Trait name `{trait_name}` already exists.")


async def add_trait(
    ctx: discord.ApplicationContext,
    trait_name: str,
    category: TraitCategory,
    trait_value: int,
    max_value: int,
    trait_description: str,
    character: Character,
) -> None:
    """Add a trait to a character."""
    __validate_trait_name(trait_name, character)

    view = ConfirmCancelButtons(ctx.author)
    await present_embed(
        ctx,
        title=f"Create {trait_name}",
        description=f"Confirm creating custom trait: **{trait_name}**",
        fields=[
            ("Category", category.name),
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
        ctx.bot.char_svc.add_custom_trait(  # type: ignore [attr-defined]
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
                ("Category", category.name),
                ("Description", trait_description),
                ("Value", f"`{trait_value!s}`"),
                ("Max Value", f"`{max_value!s}`"),
            ],
            inline_fields=True,
            level="success",
            log=True,
            ephemeral=True,
        )
