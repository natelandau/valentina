# mypy: disable-error-code="valid-type"
"""Create macros for quick rolls based on traits."""

import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina.models.bot import Valentina
from valentina.models.constants import EmbedColor
from valentina.utils.converters import ValidMacroFromID, ValidTraitOrCustomTrait
from valentina.utils.options import (
    select_char_trait,
    select_char_trait_two,
    select_macro,
)
from valentina.views import ConfirmCancelButtons, MacroCreateModal, present_embed


class Macros(commands.Cog):
    """Manage macros for quick rolls."""

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

    macros = discord.SlashCommandGroup("macros", "Manage macros for quick rolls")

    @macros.command(name="create", description="Create a new macro")
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

        #################################################
        try:
            self.bot.macro_svc.create_macro(
                ctx, name, trait_one, trait_two, abbreviation, description
            )
        except ValueError:
            await present_embed(
                ctx,
                title="Macro already exists",
                description=f"A macro already exists with the name **{name}** or abbreviation **{abbreviation}**\nPlease choose a different name or abbreviation or delete the existing macro with `/macros delete`",
                level="error",
                ephemeral=True,
            )
            return

        await present_embed(
            ctx,
            title=f"Created Macro: {name}",
            description=f"Created a macro that combines **{trait_one.name}** and **{trait_two.name}**.",
            fields=[
                ("Abbreviation", abbreviation),
                ("Description", description),
            ],
            inline_fields=True,
            level="success",
            ephemeral=True,
            log=True,
        )

    @macros.command(name="list", description="List macros associated with your account")
    async def list_macros(
        self,
        ctx: discord.ApplicationContext,
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
                ephemeral=True,
            )
        else:
            await present_embed(
                ctx,
                title="No Macros",
                description="You do not have any macros associated with your account.",
                level="info",
                ephemeral=True,
            )

    @macros.command(name="delete", description="Delete a macro")
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

        saved_macro_name = macro.name
        self.bot.macro_svc.delete_macro(ctx, macro)

        await msg.delete_original_response()
        await present_embed(
            ctx,
            title=f"Deleted Macro: {saved_macro_name}",
            level="success",
            log=True,
            ephemeral=True,
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Macros(bot))
