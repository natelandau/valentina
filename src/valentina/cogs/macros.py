# mypy: disable-error-code="valid-type"
"""Create macros for quick rolls based on traits."""

import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina import Valentina, guild_svc, user_svc
from valentina.models.constants import MAX_OPTION_LIST_SIZE
from valentina.views import MacroCreateModal, present_embed


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

        user_svc.create_macro(
            ctx,
            name=name,
            abbreviation=abbreviation,
            description=description,
            trait_one=trait_one,
            trait_two=trait_one,
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

    @macros.command(name="delete", description="Delete a macro")
    @logger.catch
    async def delete_macro(
        self,
        ctx: discord.ApplicationContext,
    ) -> None:
        """Create a new macro."""
        ...


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Macros(bot))
