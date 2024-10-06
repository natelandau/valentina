# mypy: disable-error-code="valid-type"
"""Create macros for quick rolls based on traits."""

import discord
from discord.commands import Option
from discord.ext import commands

from valentina.discord.bot import Valentina, ValentinaContext
from valentina.discord.utils.autocomplete import (
    select_char_trait,
    select_char_trait_two,
    select_macro,
)
from valentina.discord.utils.converters import ValidTraitFromID
from valentina.discord.views import MacroCreateModal, confirm_action, present_embed
from valentina.models import User, UserMacro
from valentina.utils.helpers import truncate_string


class Macro(commands.Cog):
    """Manage macros for quick rolls."""

    def __init__(self, bot: Valentina) -> None:
        self.bot: Valentina = bot

    macro = discord.SlashCommandGroup("macro", "Create & manage macros for quick rolling traits")

    @macro.command(name="create", description="Create a new macro")
    async def create(
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
        hidden: Option(
            bool,
            description="Make the result only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Create a new macro.

        Args:
            ctx (ValentinaContext): The context of the application.
            trait_one (CharacterTrait): The index for the first trait.
            trait_two (CharacterTrait): The index for the second trait.
            hidden (Option[bool]): Whether to make the result only to you (default true).
        """
        user = await User.get(ctx.author.id, fetch_links=True)

        modal = MacroCreateModal(
            title=truncate_string("Enter the details for your macro", 45),
            trait_one=trait_one.name,
            trait_two=trait_two.name,
        )
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        name = modal.name.strip()
        abbreviation = modal.abbreviation.strip() if modal.abbreviation else None
        description = modal.description.strip() if modal.description else None

        macro = UserMacro(
            name=name,
            abbreviation=abbreviation,
            description=description,
            trait_one=trait_one.name,
            trait_two=trait_two.name,
        )
        user.macros.append(macro)
        await user.save()

        await ctx.post_to_audit_log(
            f"Create macro: `{name}`(`{trait_one.name}` + `{trait_two.name}`)"
        )
        await present_embed(
            ctx,
            title=f"Created Macro: {name}",
            description=f"Create macro: `{name}`(`{trait_one.name}` + `{trait_two.name}`)",
            fields=[
                ("Abbreviation", abbreviation),
                ("Description", description),
            ],
            inline_fields=True,
            level="success",
            ephemeral=hidden,
        )

    @macro.command(name="list", description="List macros associated with your account")
    async def list_macros(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the list only visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """List all macros associated with a user account."""
        user = await User.get(ctx.author.id, fetch_links=True)

        if len(user.macros) > 0:
            fields = [
                (
                    f"{macro.name} ({macro.abbreviation}): `{macro.trait_one}` + `{macro.trait_two}`",
                    f"{macro.description}" if macro.description else "",
                )
                for macro in user.macros
            ]

            await present_embed(
                ctx,
                title=f"Macros for {ctx.author.display_name}",
                description="You have the following macros associated with your account.",
                fields=fields,
                level="info",
                ephemeral=hidden,
            )
        else:
            await present_embed(
                ctx,
                title="No Macros",
                description="You do not have any macros associated with your account.",
                level="info",
                ephemeral=hidden,
            )

    @macro.command(name="delete", description="Delete a macro")
    async def delete_macro(
        self,
        ctx: ValentinaContext,
        index: Option(
            int,
            name="macro",
            description="Macro to delete",
            required=True,
            autocomplete=select_macro,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Delete a macro from a user."""
        user = await User.get(ctx.author.id, fetch_links=True)
        macro = user.macros[index]

        title = f"Delete macro `{macro.name}`"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden, footer="This action is irreversible.", audit=True
        )

        if not is_confirmed:
            return

        del user.macros[index]
        await user.save()

        await interaction.edit_original_response(embed=confirmation_embed, view=None)


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Macro(bot))
