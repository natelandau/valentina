# mypy: disable-error-code="valid-type"
"""Cog for the Chronicle commands."""

import discord
from discord.commands import Option
from discord.ext import commands, pages
from loguru import logger

from valentina.models.bot import Valentina
from valentina.models.constants import MAX_FIELD_COUNT, MAX_PAGE_CHARACTER_COUNT, EmbedColor
from valentina.utils.options import select_chapter, select_chronicle, select_note, select_npc
from valentina.views import ChapterModal, ConfirmCancelButtons, NoteModal, NPCModal, present_embed


class Chronicle(commands.Cog):
    """Commands used for updating chronicles."""

    # TODO: Add paginator to long embeds (e.g. chronicle list, chronicle chapters, etc.)

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

    chronicle = discord.SlashCommandGroup("chronicle", "Manage chronicles")
    chapter = chronicle.create_subgroup(name="chapter", description="Manage chronicle chapters")
    npc = chronicle.create_subgroup(name="npc", description="Manage chronicle NPCs")
    notes = chronicle.create_subgroup(name="notes", description="Manage chronicle notes")

    ### CHRONICLE COMMANDS ####################################################################

    @chronicle.command(name="create", description="Create a new chronicle")
    @commands.has_permissions(administrator=True)
    async def create_chronicle(
        self,
        ctx: discord.ApplicationContext,
        name: Option(str, description="Name of the chronicle", required=True),
    ) -> None:
        """Create a new chronicle."""
        # TODO: Migrate to modal to allow setting chronicle description
        view = ConfirmCancelButtons(ctx.author)
        msg = await present_embed(
            ctx,
            title="Create new chronicle?",
            description=f"Create new chronicle named: **{name}**",
            view=view,
            ephemeral=True,
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
            chronicle = self.bot.chron_svc.create_chronicle(ctx, name=name)
            await msg.delete_original_response()
            await present_embed(
                ctx,
                title=f"Created new chronicle: {chronicle.name}",
                ephemeral=True,
                log=True,
                level="success",
            )

    @chronicle.command(name="delete", description="Delete a chronicle")
    @commands.has_permissions(administrator=True)
    async def delete_chronicle(
        self,
        ctx: discord.ApplicationContext,
        chronicle: Option(
            str,
            description="Name of the chronicle",
            required=True,
            autocomplete=select_chronicle,
        ),
    ) -> None:
        """Delete a chronicle."""
        view = ConfirmCancelButtons(ctx.author)
        msg = await present_embed(
            ctx,
            title="Delete chronicle?",
            description=f"Delete chronicle: **{chronicle}** and all associated data (NPCs, notes, chapters)?",
            view=view,
            ephemeral=True,
        )
        await view.wait()
        if not view.confirmed:
            embed = discord.Embed(
                title="Cancelled",
                description="Cancelled deleting chronicle",
                color=EmbedColor.INFO.value,
            )
            await msg.edit_original_response(embed=embed, view=None)
            return

        if view.confirmed:
            chronicle_object = self.bot.chron_svc.fetch_chronicle_by_name(ctx, chronicle)
            self.bot.chron_svc.delete_chronicle(ctx, chronicle_object)
            await msg.delete_original_response()
            await present_embed(
                ctx,
                title=f"Deleted chronicle: {chronicle}",
                ephemeral=True,
                log=True,
                level="success",
            )

    @chronicle.command(name="view", description="View a chronicle")
    async def view_chronicle(self, ctx: discord.ApplicationContext) -> None:
        """View a chronicle."""
        # TODO: Allow viewing any chronicle

        chronicle = self.bot.chron_svc.fetch_active(ctx)
        npcs = self.bot.chron_svc.fetch_all_npcs(ctx, chronicle)
        chapters = self.bot.chron_svc.fetch_all_chapters(ctx, chronicle)
        notes = self.bot.chron_svc.fetch_all_notes(ctx, chronicle)

        chapter_list = sorted([c for c in chapters], key=lambda c: c.chapter)
        npc_list = sorted([n for n in npcs], key=lambda n: n.name)
        note_list = sorted([n for n in notes], key=lambda n: n.name)

        chapter_listing = "\n".join([f"{c.chapter}. {c.name}" for c in chapter_list])

        intro = f"""
\u200b\n**__{chronicle.name.upper()}__**
An overview of {chronicle.name}.

**{len(chapters)} Chapters**
{chapter_listing}

**{len(npcs)} NPCs**
{', '.join([f"{n.name}" for n in npc_list])}

**{len(notes)} Notes**
{', '.join([f"{n.name}" for n in note_list])}
            """

        ### CHAPTERS ###
        chapter_pages = []
        current_string = ""
        for chapter in chapter_list:
            if len(current_string) + len(chapter.chronicle_display()) > MAX_PAGE_CHARACTER_COUNT:
                chapter_pages.append(f"\u200b\nChapters in **{chronicle.name}**" + current_string)
                current_string = ""
            current_string += f"\n \n{chapter.chronicle_display()}"

        if current_string:
            chapter_pages.append(f"\u200b\nChapters in **{chronicle.name}**" + current_string)

        ## NPCS ##
        npc_pages = []
        current_string = ""
        for npc in npc_list:
            if len(current_string) + len(npc.chronicle_display()) > MAX_PAGE_CHARACTER_COUNT:
                npc_pages.append(f"\u200b\nNPCs in **{chronicle.name}**" + current_string)
                current_string = ""
            current_string += f"\n \n{npc.chronicle_display()}"

        if current_string:
            npc_pages.append(f"\u200b\nNPCs in **{chronicle.name}**" + current_string)

        ## NOTES ##
        note_pages = []
        current_string = ""
        for note in note_list:
            if len(current_string) + len(note.chronicle_display()) > MAX_PAGE_CHARACTER_COUNT:
                note_pages.append(f"\u200b\nNotes in **{chronicle.name}**" + current_string)
                current_string = ""
            current_string += f"\n \n{note.chronicle_display()}"

        if current_string:
            note_pages.append(f"\u200b\nNotes in **{chronicle.name}**" + current_string)

        # Create a paginator with the intro page
        paginator = pages.Paginator(pages=[intro, *chapter_pages, *npc_pages, *note_pages])
        paginator.remove_button("first")
        paginator.remove_button("last")

        # Send the paginator as a dm to the user
        await paginator.respond(
            ctx.interaction,
            target=ctx.author,
            ephemeral=True,
            target_message=f"Please check your DMs! The chronicle **{chronicle.name}** has been sent to you.",
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
            autocomplete=select_chronicle,
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
            self.bot.chron_svc.set_active(ctx, chronicle)
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
        chronicle = self.bot.chron_svc.fetch_active(ctx)
        view = ConfirmCancelButtons(ctx.author)
        msg = await present_embed(
            ctx,
            title="Set chronicle as inactive?",
            description=f"Set chronicle **{chronicle.name}** as inactive",
            view=view,
            ephemeral=True,
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
            self.bot.chron_svc.set_inactive(ctx)
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
        chronicles = self.bot.chron_svc.fetch_all(ctx)
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
        logger.debug("CHRONICLE: List all chronicles")

    ### NPC COMMANDS ####################################################################

    @npc.command(name="create", description="Create a new NPC")
    async def create_npc(self, ctx: discord.ApplicationContext) -> None:
        """Create a new NPC."""
        chronicle = self.bot.chron_svc.fetch_active(ctx)

        modal = NPCModal(title="Create new NPC")
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        name = modal.name.strip().title()
        npc_class = modal.npc_class.strip().title()
        description = modal.description.strip()

        self.bot.chron_svc.create_npc(
            ctx, chronicle=chronicle, name=name, npc_class=npc_class, description=description
        )

        await present_embed(
            ctx,
            title=f"Created NPC in {chronicle.name}",
            level="success",
            log=True,
            fields=[
                ("Name", name),
                ("Class", npc_class),
                (
                    "Description",
                    (description[:MAX_FIELD_COUNT] + " ...")
                    if len(description) > MAX_FIELD_COUNT
                    else description,
                ),
            ],
            ephemeral=True,
            inline_fields=True,
        )

    @npc.command(name="list", description="List all NPCs")
    async def list_npcs(self, ctx: discord.ApplicationContext) -> None:
        """List all NPCs."""
        chronicle = self.bot.chron_svc.fetch_active(ctx)
        npcs = self.bot.chron_svc.fetch_all_npcs(ctx, chronicle)
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

    @npc.command(name="edit", description="Edit an NPC")
    async def edit_npc(
        self,
        ctx: discord.ApplicationContext,
        npc: Option(str, description="NPC to edit", required=True, autocomplete=select_npc),
    ) -> None:
        """Edit an NPC."""
        chronicle = self.bot.chron_svc.fetch_active(ctx)
        npc = self.bot.chron_svc.fetch_npc_by_name(chronicle, npc)

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
        self.bot.chron_svc.update_npc(ctx, npc, **updates)

        await present_embed(
            ctx,
            title=f"Updated NPC in {chronicle.name}",
            level="success",
            log=True,
            fields=[
                ("Name", updates["name"]),
                ("Class", updates["npc_class"]),
                (
                    "Description",
                    (modal.description.strip()[:MAX_FIELD_COUNT] + " ...")
                    if len(modal.description.strip()) > MAX_FIELD_COUNT
                    else modal.description.strip(),
                ),
            ],
            ephemeral=True,
            inline_fields=True,
        )

    @npc.command(name="delete", description="Delete an NPC")
    @commands.has_permissions(administrator=True)
    async def delete_npc(
        self,
        ctx: discord.ApplicationContext,
        npc: Option(str, description="NPC to edit", required=True, autocomplete=select_npc),
    ) -> None:
        """Delete an NPC."""
        chronicle = self.bot.chron_svc.fetch_active(ctx)
        npc = self.bot.chron_svc.fetch_npc_by_name(chronicle, npc)

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

        self.bot.chron_svc.delete_npc(ctx, npc)
        await msg.delete_original_response()
        await present_embed(
            ctx,
            title=f"Delete NPC: {npc.name}",
            ephemeral=True,
            log=True,
            level="success",
        )

    ### CHAPTER COMMANDS ####################################################################

    @chapter.command(name="create", description="Create a new chapter")
    async def create_chapter(self, ctx: discord.ApplicationContext) -> None:
        """Create a new chapter."""
        chronicle = self.bot.chron_svc.fetch_active(ctx)

        modal = ChapterModal(title="Create new chapter")
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        name = modal.name.strip().title()
        short_description = modal.short_description.strip()
        description = modal.description.strip()

        chapter = self.bot.chron_svc.create_chapter(
            ctx,
            chronicle=chronicle,
            name=name,
            short_description=short_description,
            description=description,
        )

        await present_embed(
            ctx,
            title=f"Created chapter in {chronicle.name}",
            level="success",
            log=True,
            fields=[
                ("Name", name),
                ("Chapter Number", chapter.chapter),
                ("Short Description", short_description),
            ],
            ephemeral=True,
            inline_fields=True,
        )

    @chapter.command(name="list", description="List all chapters")
    async def list_chapters(self, ctx: discord.ApplicationContext) -> None:
        """List all chapters."""
        chronicle = self.bot.chron_svc.fetch_active(ctx)
        chapters = self.bot.chron_svc.fetch_all_chapters(ctx, chronicle)
        if len(chapters) == 0:
            await present_embed(
                ctx,
                title="No Chapters",
                description="There are no chapters\nCreate one with `/chronicle create_chapter`",
                level="info",
            )
            return

        fields = []
        for chapter in sorted(chapters, key=lambda x: x.chapter):
            fields.append(
                (
                    f"**{chapter.chapter}.** **__{chapter.name}__**",
                    f"{chapter.short_description}",
                )
            )

        await present_embed(ctx, title="Chapters", fields=fields, level="info")

    @chapter.command(name="edit", description="Edit a chapter")
    @logger.catch
    async def edit_chapter(
        self,
        ctx: discord.ApplicationContext,
        chapter_select: Option(
            str,
            name="chapter",
            description="Chapter to edit",
            required=True,
            autocomplete=select_chapter,
        ),
    ) -> None:
        """Edit a chapter."""
        chronicle = self.bot.chron_svc.fetch_active(ctx)
        chapter = self.bot.chron_svc.fetch_chapter_by_name(
            ctx, chronicle, chapter_select.split(":")[1]
        )

        modal = ChapterModal(title="Edit chapter", chapter=chapter)
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        updates = {
            "name": modal.name.strip().title(),
            "short_description": modal.short_description.strip(),
            "description": modal.description.strip(),
        }
        self.bot.chron_svc.update_chapter(ctx, chapter, **updates)
        await present_embed(
            ctx,
            title=f"Updated chapter in {chronicle.name}",
            level="success",
            log=True,
            fields=[
                ("Name", updates["name"]),
                ("Chapter Number", chapter.chapter),
                ("Short Description", updates["short_description"]),
            ],
            ephemeral=True,
            inline_fields=True,
        )

    @chapter.command(name="delete", description="Delete a chapter")
    @commands.has_permissions(administrator=True)
    async def delete_chapter(
        self,
        ctx: discord.ApplicationContext,
        chapter_select: Option(
            str,
            name="chapter",
            description="Chapter to edit",
            required=True,
            autocomplete=select_chapter,
        ),
    ) -> None:
        """Delete a chapter."""
        chronicle = self.bot.chron_svc.fetch_active(ctx)
        chapter = self.bot.chron_svc.fetch_chapter_by_name(
            ctx, chronicle, chapter_select.split(":")[1]
        )

        view = ConfirmCancelButtons(ctx.author)
        msg = await present_embed(
            ctx,
            title="Delete Chapter?",
            description=f"Delete Chapter **{chapter.chapter}. {chapter.name}** from **{chronicle.name}**",
            view=view,
            ephemeral=True,
        )
        await view.wait()
        if not view.confirmed:
            embed = discord.Embed(
                title="Cancelled",
                description="Cancelled deleting chapter",
                color=EmbedColor.INFO.value,
            )
            await msg.edit_original_response(embed=embed, view=None)
            return

        self.bot.chron_svc.delete_chapter(ctx, chapter)
        await msg.delete_original_response()
        await present_embed(
            ctx,
            title=f"Delete Chapter: {chapter.chapter}. {chapter.name}",
            ephemeral=True,
            log=True,
            level="success",
        )

    ### NOTE COMMANDS ####################################################################

    @notes.command(name="create", description="Create a new note")
    async def create_note(
        self,
        ctx: discord.ApplicationContext,
        chapter_select: Option(
            str,
            name="chapter",
            description="Chapter to edit",
            required=False,
            autocomplete=select_chapter,
            default=None,
        ),
    ) -> None:
        """Create a new note."""
        chronicle = self.bot.chron_svc.fetch_active(ctx)
        chapter = (
            self.bot.chron_svc.fetch_chapter_by_name(ctx, chronicle, chapter_select.split(":")[1])
            if chapter_select
            else None
        )

        modal = NoteModal(title="Create new note")
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        name = modal.name.strip().title()
        description = modal.description.strip()

        self.bot.chron_svc.create_note(
            ctx,
            chronicle=chronicle,
            name=name,
            description=description,
            chapter=chapter,
        )

        await present_embed(
            ctx,
            title=f"Created note in {chronicle.name}",
            level="success",
            log=True,
            fields=[
                ("Name", name),
                (
                    "Description",
                    (description[:MAX_FIELD_COUNT] + " ...")
                    if len(description) > MAX_FIELD_COUNT
                    else description,
                ),
            ],
            ephemeral=True,
            inline_fields=True,
        )

    @notes.command(name="list", description="List all notes")
    async def list_notes(self, ctx: discord.ApplicationContext) -> None:
        """List all notes."""
        chronicle = self.bot.chron_svc.fetch_active(ctx)
        notes = self.bot.chron_svc.fetch_all_notes(ctx, chronicle)
        if len(notes) == 0:
            await present_embed(
                ctx,
                title="No Notes",
                description="There are no notes\nCreate one with `/chronicle create_note`",
                level="info",
            )
            return

        fields = []
        for note in sorted(notes, key=lambda x: x.name):
            fields.append(
                (
                    f"**__{note.name}__**",
                    f"**Chapter:** {note.chapter.chapter}\n{note.description}"
                    if note.chapter
                    else f"{note.description}",
                )
            )

        await present_embed(
            ctx, title=f"Notes for **{chronicle.name}**", fields=fields, level="info"
        )

    @notes.command(name="edit", description="Edit a note")
    async def edit_note(
        self,
        ctx: discord.ApplicationContext,
        note_select: Option(
            str,
            name="note",
            description="Note to edit",
            required=True,
            autocomplete=select_note,
        ),
    ) -> None:
        """Edit a note."""
        chronicle = self.bot.chron_svc.fetch_active(ctx)
        note = self.bot.chron_svc.fetch_note_by_id(ctx, note_select.split(":")[0])

        modal = NoteModal(title="Edit note", note=note)
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        updates = {
            "name": modal.name.strip().title(),
            "description": modal.description.strip(),
        }
        self.bot.chron_svc.update_note(ctx, note, **updates)
        await present_embed(
            ctx,
            title=f"Updated note in {chronicle.name}",
            level="success",
            log=True,
            fields=[
                ("Name", updates["name"]),
                (
                    "Description",
                    (modal.description.strip()[:MAX_FIELD_COUNT] + " ...")
                    if len(modal.description.strip()) > MAX_FIELD_COUNT
                    else modal.description.strip(),
                ),
            ],
            ephemeral=True,
            inline_fields=True,
        )

    @notes.command(name="delete", description="Delete a note")
    async def delete_note(
        self,
        ctx: discord.ApplicationContext,
        note_select: Option(
            str,
            name="note",
            description="Note to edit",
            required=True,
            autocomplete=select_note,
        ),
    ) -> None:
        """Delete a note."""
        chronicle = self.bot.chron_svc.fetch_active(ctx)
        note = self.bot.chron_svc.fetch_note_by_id(ctx, note_select.split(":")[0])

        view = ConfirmCancelButtons(ctx.author)
        msg = await present_embed(
            ctx,
            title="Delete Note?",
            description=f"Delete Note **{note.name}** from **{chronicle.name}**",
            view=view,
            ephemeral=True,
        )
        await view.wait()
        if not view.confirmed:
            embed = discord.Embed(
                title="Cancelled",
                description="Cancelled deleting note",
                color=EmbedColor.INFO.value,
            )
            await msg.edit_original_response(embed=embed, view=None)
            return

        self.bot.chron_svc.delete_note(ctx, note)
        await msg.delete_original_response()
        await present_embed(
            ctx,
            title="Delete Note",
            description=f"**{note.name}** deleted from **{chronicle.name}**",
            ephemeral=True,
            log=True,
            level="success",
        )


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Chronicle(bot))
