# mypy: disable-error-code="valid-type"
"""Create macros for quick rolls based on traits."""

import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina.models.bot import Valentina
from valentina.models.constants import EmbedColor
from valentina.models.database import Macro, MacroTrait, Trait
from valentina.utils.converters import ValidMacroFromID, ValidTrait
from valentina.utils.options import select_macro, select_trait, select_trait_two
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
            ValidTrait,
            description="First trait to roll",
            required=True,
            autocomplete=select_trait,
        ),
        trait_two: Option(
            ValidTrait,
            description="Second trait to roll",
            required=True,
            autocomplete=select_trait_two,
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

        macros = self.bot.user_svc.fetch_macros(ctx)
        if any(macro.name.lower() == name.lower() for macro in macros) or any(
            macro.abbreviation.lower() == abbreviation.lower() for macro in macros
        ):
            await present_embed(
                ctx,
                title="Macro already exists",
                description=f"A macro already exists with the name **{name}** or abbreviation **{abbreviation}**\nPlease choose a different name or abbreviation or delete the existing macro with `/macros delete`",
                level="error",
                ephemeral=True,
            )
            return

        macro = Macro.create(
            name=name,
            abbreviation=abbreviation,
            description=description,
            user=ctx.author.id,
            guild=ctx.guild.id,
        )
        MacroTrait.create_from_trait_name(macro, trait_one.name)
        MacroTrait.create_from_trait_name(macro, trait_two.name)

        self.bot.user_svc.purge_cache(ctx)

        logger.info(f"DATABASE: Create macro '{name}' for user '{ctx.author.display_name}'")

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
        macros = sorted(self.bot.user_svc.fetch_macros(ctx), key=lambda macro: macro.name)

        fields = []
        for macro in macros:
            # TODO: Handle custom traits
            traits = Trait.select().join(MacroTrait).where(MacroTrait.macro == macro)
            trait_one = traits[0]
            trait_two = traits[1]
            fields.append(
                (
                    f"{macro.name} ({macro.abbreviation}): `{trait_one.name}` + `{trait_two.name}`",
                    f"{macro.description}",
                )
            )

        if len(macros) > 0:
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
        macro.remove()
        self.bot.user_svc.purge_cache(ctx)

        logger.debug(
            f"DATABASE: Delete macro '{saved_macro_name}' for user '{ctx.author.display_name}'"
        )
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
