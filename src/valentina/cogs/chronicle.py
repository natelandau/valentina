# mypy: disable-error-code="valid-type"
"""Cog for the Chronicle commands."""

import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina import Valentina, chron_svc
from valentina.models.constants import MAX_OPTION_LIST_SIZE, EmbedColor
from valentina.views import ConfirmCancelButtons, NPCModal, present_embed


class Chronicle(commands.Cog):
    """Commands used for updating chronicles."""

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    async def cog_command_error(
        self, ctx: discord.ApplicationContext, error: discord.ApplicationCommandError | Exception
    ) -> None:
        """Handle exceptions and errors from the cog."""
        if hasattr(error, "original"):
            error = error.original

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

    async def __chronicle_autocomplete(self, ctx: discord.ApplicationContext) -> list[str]:
        """Populates the autocomplete for the trait option."""
        chronicles = []
        for c in chron_svc.fetch_all(ctx):
            if c.name.lower().startswith(ctx.options["chronicle"].lower()):
                chronicles.append(c.name)
            if len(chronicles) >= MAX_OPTION_LIST_SIZE:
                break

        return chronicles

    async def __npc_autocomplete(self, ctx: discord.ApplicationContext) -> list[str]:
        """Populates the autocomplete for the npc option."""
        try:
            chronicle = chron_svc.fetch_active(ctx)
        except ValueError:
            return ["No active chronicle"]

        npcs = []
        for npc in chron_svc.fetch_all_npcs(ctx, chronicle=chronicle):
            if npc.name.lower().startswith(ctx.options["npc"].lower()):
                npcs.append(npc.name)
            if len(npcs) >= MAX_OPTION_LIST_SIZE:
                break

        return npcs

    chronicle = discord.SlashCommandGroup("chronicle", "Manage chronicles")

    @chronicle.command(name="create", description="Create a new chronicle")
    @commands.has_permissions(administrator=True)
    async def create_chronicle(
        self,
        ctx: discord.ApplicationContext,
        name: Option(str, description="Name of the chronicle", required=True),
    ) -> None:
        """Create a new chronicle."""
        view = ConfirmCancelButtons(ctx.author)
        msg = await present_embed(
            ctx,
            title="Create new chronicle?",
            description=f"Create new chronicle named: **{name}**",
            view=view,
            ephemeral=True,
            log=True,
        )
        await view.wait()
        if not view.confirmed:
            embed = discord.Embed(
                title="Cancelled",
                description="Cancelled creating chronicle",
                color=EmbedColor.INFO.value,
            )
            await msg.edit_original_response(embed=embed, view=None)
            return

        if view.confirmed:
            chronicle = chron_svc.create_chronicle(ctx, name=name)
            await msg.delete_original_response()
            await present_embed(
                ctx,
                title=f"Created new chronicle: {chronicle.name}",
                ephemeral=True,
                log=True,
                level="success",
            )

    @chronicle.command(name="set_active", description="Set a chronicle as active")
    @commands.has_permissions(administrator=True)
    async def chronicle_set_active(
        self,
        ctx: discord.ApplicationContext,
        chronicle: Option(
            str,
            description="Name of the chronicle",
            required=True,
            autocomplete=__chronicle_autocomplete,
        ),
    ) -> None:
        """Set a chronicle as active."""
        view = ConfirmCancelButtons(ctx.author)
        msg = await present_embed(
            ctx,
            title="Set chronicle as active?",
            description=f"Set chronicle **{chronicle}** as active",
            view=view,
            ephemeral=True,
            log=True,
        )
        await view.wait()
        if not view.confirmed:
            embed = discord.Embed(
                title="Cancelled",
                description="Cancelled setting chronicle as active",
                color=EmbedColor.INFO.value,
            )
            await msg.edit_original_response(embed=embed, view=None)
            return

        if view.confirmed:
            chron_svc.set_active(ctx, chronicle)
            await msg.delete_original_response()
            await present_embed(
                ctx,
                title=f"Set chronicle as active: {chronicle}",
                ephemeral=True,
                log=True,
                level="success",
            )

    @chronicle.command(name="set_inactive", description="Set a chronicle as inactive")
    @commands.has_permissions(administrator=True)
    async def chronicle_set_inactive(self, ctx: discord.ApplicationContext) -> None:
        """Set the active chronicle as inactive."""
        chronicle = chron_svc.fetch_active(ctx)
        view = ConfirmCancelButtons(ctx.author)
        msg = await present_embed(
            ctx,
            title="Set chronicle as inactive?",
            description=f"Set chronicle **{chronicle.name}** as inactive",
            view=view,
            ephemeral=True,
            log=True,
        )
        await view.wait()
        if not view.confirmed:
            embed = discord.Embed(
                title="Cancelled",
                description="Cancelled setting chronicle as inactive",
                color=EmbedColor.INFO.value,
            )
            await msg.edit_original_response(embed=embed, view=None)
            return

        if view.confirmed:
            chron_svc.set_inactive(ctx)
            await msg.delete_original_response()
            await present_embed(
                ctx,
                title=f"Set chronicle as inactive: {chronicle.name}",
                ephemeral=True,
                log=True,
                level="success",
            )

    @chronicle.command(name="list", description="List all chronicles")
    async def chronicle_list(self, ctx: discord.ApplicationContext) -> None:
        """List all chronicles."""
        chronicles = chron_svc.fetch_all(ctx)
        if len(chronicles) == 0:
            await present_embed(
                ctx,
                title="No chronicles",
                description="There are no chronicles\nCreate one with `/chronicle create`",
                level="info",
            )
            return

        fields = []
        for c in sorted(chronicles, key=lambda x: x.name):
            fields.append((f"**{c.name}** (Active)" if c.is_active else f"**{c.name}**", ""))

        await present_embed(ctx, title="Chronicles", fields=fields, level="info")
        logger.debug("CHRONICLE: Listed all chronicles")

    @chronicle.command(name="create_npc", description="Create a new NPC")
    async def create_npc(self, ctx: discord.ApplicationContext) -> None:
        """Create a new NPC."""
        chronicle = chron_svc.fetch_active(ctx)

        modal = NPCModal(title="Create new NPC")
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        name = modal.name.strip().title()
        npc_class = modal.npc_class.strip().title()
        description = modal.description.strip()

        chron_svc.create_npc(
            ctx, chronicle=chronicle, name=name, npc_class=npc_class, description=description
        )

        await present_embed(
            ctx,
            title=f"Created NPC in {chronicle.name}",
            level="success",
            log=True,
            fields=[("Name", name), ("Class", npc_class), ("Description", description)],
            ephemeral=True,
            inline_fields=True,
        )

    @chronicle.command(name="list_npcs", description="List all NPCs")
    async def list_npcs(self, ctx: discord.ApplicationContext) -> None:
        """List all NPCs."""
        chronicle = chron_svc.fetch_active(ctx)
        npcs = chron_svc.fetch_all_npcs(ctx, chronicle)
        if len(npcs) == 0:
            await present_embed(
                ctx,
                title="No NPCs",
                description="There are no NPCs\nCreate one with `/chronicle create_npc`",
                level="info",
            )
            return

        fields = []
        for npc in sorted(npcs, key=lambda x: x.name):
            fields.append(
                (
                    f"**__{npc.name}__**",
                    f"**Class:** {npc.npc_class}\n**Description:** {npc.description}",
                )
            )

        await present_embed(ctx, title="NPCs", fields=fields, level="info")

    @chronicle.command(name="edit_npc", description="Edit an NPC")
    async def edit_npc(
        self,
        ctx: discord.ApplicationContext,
        npc: Option(str, description="NPC to edit", required=True, autocomplete=__npc_autocomplete),
    ) -> None:
        """Edit an NPC."""
        chronicle = chron_svc.fetch_active(ctx)
        npc = chron_svc.fetch_npc_by_name(chronicle, npc)

        modal = NPCModal(title="Edit NPC", npc=npc)
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        updates = {
            "name": modal.name.strip().title(),
            "npc_class": modal.npc_class.strip().title(),
            "description": modal.description.strip(),
        }
        chron_svc.update_npc(ctx, npc, **updates)

        await present_embed(
            ctx,
            title=f"Updated NPC in {chronicle.name}",
            level="success",
            log=True,
            fields=[
                ("Name", updates["name"]),
                ("Class", updates["npc_class"]),
                ("Description", updates["description"]),
            ],
            ephemeral=True,
            inline_fields=True,
        )

    @chronicle.command(name="delete_npc", description="Delete an NPC")
    async def delete_npc(
        self,
        ctx: discord.ApplicationContext,
        npc: Option(str, description="NPC to edit", required=True, autocomplete=__npc_autocomplete),
    ) -> None:
        """Delete an NPC."""
        chronicle = chron_svc.fetch_active(ctx)
        npc = chron_svc.fetch_npc_by_name(chronicle, npc)

        view = ConfirmCancelButtons(ctx.author)
        msg = await present_embed(
            ctx,
            title="Delete NPC?",
            description=f"Delete NPC **{npc.name}**",
            view=view,
            ephemeral=True,
        )
        await view.wait()
        if not view.confirmed:
            embed = discord.Embed(
                title="Cancelled",
                description="Cancelled deleting NPC",
                color=EmbedColor.INFO.value,
            )
            await msg.edit_original_response(embed=embed, view=None)
            return

        chron_svc.delete_npc(ctx, npc)
        await msg.delete_original_response()
        await present_embed(
            ctx,
            title=f"Delete NPC: {npc.name}",
            ephemeral=True,
            log=True,
            level="success",
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Chronicle(bot))
