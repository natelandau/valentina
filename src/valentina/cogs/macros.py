# mypy: disable-error-code="valid-type"
"""Create macros for quick rolls based on traits."""

import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina import Valentina, guild_svc, user_svc
from valentina.models.constants import MAX_OPTION_LIST_SIZE
from valentina.views import ConfirmCancelButtons, MacroCreateModal, present_embed


class Macros(commands.Cog):
    """Manage macros for quick rolls."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    async def __trait_one_autocomplete(self, ctx: discord.ApplicationContext) -> list[str]:
        """Populates the autocomplete for the trait option."""
        traits = []
        for trait in guild_svc.fetch_all_traits(ctx.interaction.guild.id, flat_list=True):
            if trait.lower().startswith(ctx.options["trait_one"].lower()):
                traits.append(trait)
            if len(traits) >= MAX_OPTION_LIST_SIZE:
                break
        return traits

    async def __trait_two_autocomplete(self, ctx: discord.ApplicationContext) -> list[str]:
        """Populates the autocomplete for the trait option."""
        traits = []
        for trait in guild_svc.fetch_all_traits(ctx.interaction.guild.id, flat_list=True):
            if trait.lower().startswith(ctx.options["trait_two"].lower()):
                traits.append(trait)
            if len(traits) >= MAX_OPTION_LIST_SIZE:
                break
        return traits

    async def __macro_autocomplete(self, ctx: discord.ApplicationContext) -> list[str]:
        """Populate a select list with a users' macros."""
        macros = []
        for macro in user_svc.fetch_macros(ctx):
            if macro.name.lower().startswith(ctx.options["macro"].lower()):
                macros.append(f"{macro.name} ({macro.abbreviation})")
            if len(macros) >= MAX_OPTION_LIST_SIZE:
                break
        return macros

    macros = discord.SlashCommandGroup("macros", "Manage macros for quick rolls")

    @macros.command(name="create", description="Create a new macro")
    @logger.catch
    async def create(
        self,
        ctx: discord.ApplicationContext,
        trait_one: Option(
            str,
            description="First trait to roll",
            required=True,
            autocomplete=__trait_one_autocomplete,
        ),
        trait_two: Option(
            str,
            description="Second trait to roll",
            required=True,
            autocomplete=__trait_two_autocomplete,
        ),
    ) -> None:
        """Create a new macro."""
        modal = MacroCreateModal(
            title="Enter the details for your macro",
            trait_one=trait_one,
            trait_two=trait_two,
        )
        await ctx.send_modal(modal)
        await modal.wait()
        name = modal.name
        abbreviation = modal.abbreviation
        description = modal.description

        macros = user_svc.fetch_macros(ctx)
        if any(macro.name.lower() == name.lower() for macro in macros) or any(
            macro.abbreviation.lower() == abbreviation.lower() for macro in macros
        ):
            await present_embed(
                ctx,
                title="Macro already exists",
                description=f"A macro already exists with the name **{name}** or abbreviation **{abbreviation}**\nPlease choose a different name or abbreviation or delete the existing macro with `/macros delete`",
                level="error",
            )
            return

        user_svc.create_macro(
            ctx,
            name=name.strip(),
            abbreviation=abbreviation.strip(),
            description=description.strip(),
            trait_one=trait_one,
            trait_two=trait_two,
        )

        await present_embed(
            ctx,
            title=f"Created Macro: {name}",
            description=f"{ctx.author.mention} created a new macro that combines **{trait_one}** and **{trait_two}**.",
            fields=[
                ("Macro Name", name),
                ("Abbreviation", abbreviation),
                ("Description", description),
            ],
            level="success",
        )

    @macros.command(name="list", description="List macros associated with your account")
    @logger.catch
    async def list_macros(
        self,
        ctx: discord.ApplicationContext,
    ) -> None:
        """List all macros associated with a user account."""
        macros = sorted(user_svc.fetch_macros(ctx), key=lambda macro: macro.name)
        if len(macros) > 0:
            await present_embed(
                ctx,
                title=f"Macros for {ctx.author.display_name}",
                description=f"{ctx.author.mention} has the following macros associated with their account.",
                fields=[
                    (
                        f"{macro.name} ({macro.abbreviation}) - `{macro.trait_one} + {macro.trait_two}`",
                        f"{macro.description}",
                    )
                    for macro in macros
                ],
                level="info",
            )
        else:
            await present_embed(
                ctx,
                title="No Macros",
                description=f"{ctx.author.mention} does not have any macros associated with their account.",
                level="info",
                ephemeral=True,
            )

    @macros.command(name="delete", description="Delete a macro")
    @logger.catch
    async def delete_macro(
        self,
        ctx: discord.ApplicationContext,
        macro: Option(
            str,
            description="Macro to delete",
            required=True,
            autocomplete=__macro_autocomplete,
        ),
    ) -> None:
        """Delete a macro from a user."""
        name = macro.split("(")[0].strip()
        view = ConfirmCancelButtons(ctx.author)
        await present_embed(
            ctx,
            title=f"Confirm deletion of macro: {name}",
            description=f"Are you sure you want to delete the macro **{name}**?",
            inline_fields=False,
            ephemeral=True,
            level="info",
            view=view,
        )
        await view.wait()
        if view.confirmed:
            user_svc.delete_macro(ctx, macro_name=name)

            await present_embed(
                ctx,
                title=f"Deleted Macro: {name}",
                description=f"{ctx.author.mention} deleted the macro **{name}**.",
                level="success",
            )
        else:
            await present_embed(ctx, title="Macro deletion cancelled", level="info", ephemeral=True)


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Macros(bot))