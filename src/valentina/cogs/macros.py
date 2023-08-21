# mypy: disable-error-code="valid-type"
"""Create macros for quick rolls based on traits."""

import discord
from discord.commands import Option
from discord.ext import commands

from valentina.constants import EmbedColor
from valentina.models.bot import Valentina
from valentina.utils.converters import ValidMacroFromID, ValidTraitOrCustomTrait
from valentina.utils.options import (
    select_char_trait,
    select_char_trait_two,
    select_macro,
)
from valentina.views import ConfirmCancelButtons, MacroCreateModal, present_embed


class Macro(commands.Cog):
    """Manage macros for quick rolls."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    macro = discord.SlashCommandGroup("macro", "Create & manage macros for quick rolling traits")

    @macro.command(name="create", description="Create a new macro")
    async def create(
        self,
        ctx: discord.ApplicationContext,
        trait_one: Option(
            ValidTraitOrCustomTrait,
            description="First trait to roll",
            required=True,
            autocomplete=select_char_trait,
        ),
        trait_two: Option(
            ValidTraitOrCustomTrait,
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
        """Create a new macro."""
        self.bot.user_svc.fetch_user(ctx)

        modal = MacroCreateModal(
            title="Enter the details for your macro",
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

        self.bot.macro_svc.create_macro(ctx, name, trait_one, trait_two, abbreviation, description)

        await self.bot.guild_svc.send_to_audit_log(
            ctx, f"Create macro: `{name}`(`{trait_one.name}` + `{trait_two.name}`)"
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
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the list only visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """List all macros associated with a user account."""
        macros = self.bot.macro_svc.fetch_macros(ctx.guild.id, ctx.author.id)

        if len(macros) > 0:
            fields = []
            for macro in macros:
                traits = self.bot.macro_svc.fetch_macro_traits(macro)
                trait_one = traits[0]
                trait_two = traits[1]
                fields.append(
                    (
                        f"{macro.name} ({macro.abbreviation}): `{trait_one.name}` + `{trait_two.name}`",
                        f"{macro.description}",
                    )
                )
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
        ctx: discord.ApplicationContext,
        macro: Option(
            ValidMacroFromID,
            description="Macro to delete",
            required=True,
            autocomplete=select_macro,
        ),
    ) -> None:
        """Delete a macro from a user."""
        view = ConfirmCancelButtons(ctx.author)

        msg = await present_embed(
            ctx,
            title=f"Confirm deletion of macro: {macro.name}",
            description=f"Are you sure you want to delete the macro **{macro.name}**?",
            inline_fields=False,
            ephemeral=True,
            level="info",
            view=view,
        )
        await view.wait()
        if not view.confirmed:
            embed = discord.Embed(title="Macro deletion cancelled", color=EmbedColor.INFO.value)
            await msg.edit_original_response(embed=embed, view=None)
            return

        self.bot.macro_svc.delete_macro(ctx, macro)

        await self.bot.guild_svc.send_to_audit_log(ctx, f"Delete macro: `{macro.name}`")
        await msg.edit_original_response(
            embed=discord.Embed(
                title=f"Delete macro: `{macro.name}`",
                description="",
                color=EmbedColor.SUCCESS.value,
            )
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Macro(bot))
