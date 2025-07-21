# mypy: disable-error-code="valid-type"
"""Cog for adding notes to campaigns, books, and characters."""

from typing import Annotated

import discord
from discord.commands import Option
from discord.ext import commands

from valentina.constants import MAX_FIELD_COUNT
from valentina.discord.bot import Valentina, ValentinaContext
from valentina.discord.utils import fetch_channel_object
from valentina.discord.utils.autocomplete import select_note
from valentina.discord.utils.converters import ValidNote
from valentina.discord.views import NoteModal, auto_paginate, confirm_action, present_embed
from valentina.models import Note as DbNote


class Note(commands.Cog):
    """Miscellaneous commands."""

    def __init__(self, bot: Valentina) -> None:
        self.bot: Valentina = bot

    note = discord.SlashCommandGroup("note", "Add, remove, edit, or view notes")

    @note.command(name="add", description="Add a note to a book or character")
    async def add_note(
        self,
        ctx: ValentinaContext,
        note: Annotated[str, Option(name="note", description="The note to add", required=True)],
        hidden: Annotated[
            bool,
            Option(
                name="hidden",
                description="Make the response visible only to you (default true).",
                required=False,
            ),
        ] = True,
    ) -> None:
        """Add a note."""
        channel_objects = await fetch_channel_object(ctx, raise_error=False)
        channel_object = channel_objects.book or channel_objects.character

        if not channel_object:
            await present_embed(
                ctx,
                title="Add note",
                description="Notes can only be added to books and characters.",
                ephemeral=hidden,
                level="error",
            )
            return

        title = f"Add note to `{channel_object.name}`"
        description = f"```\n{note.strip().capitalize()}\n```"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx,
            title,
            description=description,
            hidden=hidden,
            audit=True,
        )

        if not is_confirmed:
            return

        note = await DbNote(
            created_by=ctx.author.id,
            text=note.strip().capitalize(),
            parent_id=str(channel_object.id),
        ).insert()
        channel_object.notes.append(note)  # type: ignore [arg-type]
        await channel_object.save()

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @note.command(name="view", description="View notes for a book or character")
    async def view_notes(
        self,
        ctx: ValentinaContext,
        hidden: Annotated[
            bool,
            Option(
                name="hidden",
                description="Make the response visible only to you (default true).",
                required=False,
            ),
        ] = True,
    ) -> None:
        """View notes."""
        channel_objects = await fetch_channel_object(ctx, raise_error=False)
        channel_object = channel_objects.book or channel_objects.character

        if not channel_object:
            await present_embed(
                ctx,
                title="Add note",
                description="Notes can only be viewed for books and characters.",
                ephemeral=hidden,
                level="error",
            )
            return

        sorted_notes = sorted(channel_object.notes, key=lambda x: x.date_created)  # type: ignore [attr-defined]
        notes = [await x.display(ctx) for x in sorted_notes]  # type: ignore [attr-defined]

        await auto_paginate(
            ctx=ctx,
            title=f"Notes for `{channel_object.name}`",
            text="\n".join(f"{i}. {n}" for i, n in enumerate(notes, start=1))
            if notes
            else "No notes found.",
            hidden=hidden,
        )

    @note.command(name="edit", description="Edit a note for a book or character")
    async def edit_note(
        self,
        ctx: ValentinaContext,
        note: Option(
            ValidNote,
            name="note",
            description="The note to edit",
            required=True,
            autocomplete=select_note,
        ),
        hidden: Option(
            bool,
            name="hidden",
            description="Make the response visible only to you (default true).",
            required=False,
            default=True,
        ),
    ) -> None:
        """Edit a note."""
        modal = NoteModal(title="Edit note", note=note)
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        note.text = modal.note_text.strip().capitalize()
        note.guild_id = ctx.guild.id
        await note.save()

        await ctx.post_to_audit_log(f"Update note: `{note.id}`")

        await present_embed(
            ctx,
            title="Update note",
            level="success",
            description=(note.text[:MAX_FIELD_COUNT] + " ...")
            if len(note.text) > MAX_FIELD_COUNT
            else note.text,
            ephemeral=hidden,
        )

    @note.command(name="delete", description="delete a note for a book or character")
    async def delete_note(
        self,
        ctx: ValentinaContext,
        note_to_delete: Option(
            ValidNote,
            name="note",
            description="The note to edit",
            required=True,
            autocomplete=select_note,
        ),
        hidden: Option(
            bool,
            name="hidden",
            description="Make the response visible only to you (default true).",
            required=False,
            default=True,
        ),
    ) -> None:
        """Delete a note."""
        channel_objects = await fetch_channel_object(ctx, raise_error=False)
        channel_object = channel_objects.book or channel_objects.character

        if not channel_object:
            await present_embed(
                ctx,
                title="Add note",
                description="Notes can only be deleted from books and characters.",
                ephemeral=hidden,
                level="error",
            )
            return

        title = f"Delete note from {channel_object.name}"
        description = f"```\n{note_to_delete.text}\n```"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx,
            title,
            description=description,
            hidden=hidden,
            audit=True,
            footer="Careful, this action is irreversible.",
        )

        if not is_confirmed:
            return

        channel_object.remove(note_to_delete)
        await channel_object.save()

        await note_to_delete.delete()

        await interaction.edit_original_response(embed=confirmation_embed, view=None)


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Note(bot))
