# mypy: disable-error-code="valid-type"
"""Cog for the Campaign commands."""

import discord
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina.constants import MAX_FIELD_COUNT
from valentina.models import Campaign, CampaignChapter, CampaignNote, CampaignNPC, Guild
from valentina.models.bot import Valentina, ValentinaContext
from valentina.utils.autocomplete import select_campaign, select_chapter, select_note, select_npc
from valentina.utils.converters import ValidCampaign, ValidYYYYMMDD
from valentina.utils.helpers import truncate_string
from valentina.views import (
    ChapterModal,
    NoteModal,
    NPCModal,
    auto_paginate,
    confirm_action,
    present_embed,
)


class CampaignCog(commands.Cog):
    """Commands used for updating campaigns."""

    def __init__(self, bot: Valentina) -> None:
        self.bot: Valentina = bot

    campaign = discord.SlashCommandGroup("campaign", "Manage campaigns")
    chapter = campaign.create_subgroup(name="chapter", description="Manage campaign chapters")
    npc = campaign.create_subgroup(name="npc", description="Manage campaign NPCs")
    notes = campaign.create_subgroup(name="notes", description="Manage campaign notes")

    async def check_permissions(self, ctx: ValentinaContext) -> bool:
        """Check if the user has permissions to run the command."""
        if not await ctx.can_manage_campaign():
            await present_embed(
                ctx,
                title="Permission error",
                description="You do not have permissions to run this command\nSpeak to an administrator",
                level="error",
                ephemeral=True,
                delete_after=30,
            )
            return False

        return True

    ### CAMPAIGN COMMANDS ####################################################################

    @campaign.command(name="create", description="Create a new campaign")
    async def create_campaign(
        self,
        ctx: ValentinaContext,
        name: Option(str, description="Name of the campaign", required=True),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Create a new campaign."""
        # TODO: Migrate to modal to allow setting campaign description

        if not await self.check_permissions(ctx):
            return

        title = f"Create new campaign: `{name}`"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden, audit=True
        )

        if not is_confirmed:
            return

        # Update the database
        campaign = Campaign(name=name, guild=ctx.guild.id)
        await campaign.insert()

        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        guild.campaigns.append(campaign)
        await guild.save()

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @campaign.command(name="current_date", description="Set the current date of a campaign")
    async def current_date(
        self,
        ctx: ValentinaContext,
        date: Option(ValidYYYYMMDD, description="DOB in the format of YYYY-MM-DD", required=True),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Set current date of a campaign."""
        campaign = await ctx.fetch_active_campaign()

        campaign.date_in_game = date
        await campaign.save()

        await present_embed(
            ctx,
            title=f"Set date of campaign `{campaign.name}` to `{date:%Y-%m-%d}`",
            level="success",
            ephemeral=hidden,
        )

    @campaign.command(name="delete", description="Delete a campaign")
    async def delete_campaign(
        self,
        ctx: ValentinaContext,
        campaign: Option(
            ValidCampaign,
            description="Name of the campaign",
            required=True,
            autocomplete=select_campaign,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Delete a campaign."""
        if not await self.check_permissions(ctx):
            return

        title = f"Delete campaign: {campaign.name}"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden, audit=True
        )

        if not is_confirmed:
            return

        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        await guild.delete_campaign(campaign)

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @campaign.command(name="view", description="View a campaign")
    async def view_campaign(self, ctx: ValentinaContext) -> None:
        """View a campaign."""
        campaign = await ctx.fetch_active_campaign()

        chapter_list = sorted(campaign.chapters, key=lambda c: c.number)
        npc_list = sorted(campaign.npcs, key=lambda n: n.name)
        note_list = sorted(campaign.notes, key=lambda n: n.name)

        chapter_listing = "\n> ".join([f"{c.number}. {c.name}" for c in chapter_list])

        chapter_text = "\n\n".join([f"{c.campaign_display()}" for c in chapter_list])

        npc_text = "\n\n".join([f"{n.campaign_display()}" for n in npc_list])

        note_text = "\n\n".join([f"{n.campaign_display()}" for n in note_list])

        text = f"""
### __Overview of {campaign.name}__
> **Chapters** ({len(chapter_list)})
> {chapter_listing}

> **NPCs** ({len(npc_list)})
> {', '.join([f"{n.name}" for n in npc_list])}

> **Notes** ({len(note_list)})
> {', '.join([f"{n.name}" for n in note_list])}

### __Chapters__
{chapter_text}

### __NPCs__
{npc_text}

### __Notes__
{note_text}
            """

        await auto_paginate(ctx, title=f"Campaign Overview: __{campaign.name}__", text=text)

    @campaign.command(name="set_active", description="Set a campaign as active")
    async def campaign_set_active(
        self,
        ctx: ValentinaContext,
        campaign: Option(
            ValidCampaign,
            description="Name of the campaign",
            required=True,
            autocomplete=select_campaign,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Set a campaign as active."""
        if not await self.check_permissions(ctx):
            return

        title = f"Set campaign `{campaign.name}` as active"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden, audit=True
        )

        if not is_confirmed:
            return

        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        guild.active_campaign = campaign
        await guild.save()

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @campaign.command(name="set_inactive", description="Set a campaign as inactive")
    async def campaign_set_inactive(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Set the active campaign as inactive."""
        if not await self.check_permissions(ctx):
            return

        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        active_campaign = await guild.fetch_active_campaign()
        if not active_campaign:
            await present_embed(
                ctx,
                title="No active campaign",
                description="There is no active campaign",
                level="info",
                ephemeral=hidden,
            )
            return

        title = f"Set campaign `{active_campaign.name}` as inactive"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden, audit=True
        )

        if not is_confirmed:
            return

        guild.active_campaign = None
        await guild.save()

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @campaign.command(name="list", description="List all campaigns")
    async def campaign_list(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """List all campaigns."""
        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        active_campaign = await guild.fetch_active_campaign()

        if len(guild.campaigns) == 0:
            await present_embed(
                ctx,
                title="No campaigns",
                description="There are no campaigns\nCreate one with `/campaign create`",
                level="info",
                ephemeral=hidden,
            )
            return

        fields = []
        fields.extend([
            (
                f"**{c.name}** (Active)" if c == active_campaign else f"**{c.name}**",
                "",
            )
            for c in sorted(guild.campaigns, key=lambda x: x.name)
        ])

        await present_embed(ctx, title="Campaigns", fields=fields, level="info")

    ### NPC COMMANDS ####################################################################

    @npc.command(name="create", description="Create a new NPC")
    async def create_npc(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Create a new NPC."""
        active_campaign = await ctx.fetch_active_campaign()

        modal = NPCModal(title=truncate_string("Create new NPC", 45))
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        name = modal.name.strip().title()
        npc_class = modal.npc_class.strip().title()
        description = modal.description.strip()

        npc = CampaignNPC(name=name, npc_class=npc_class, description=description)
        active_campaign.npcs.append(npc)
        await active_campaign.save()

        await ctx.post_to_audit_log(f"Create NPC: `{name}` in `{active_campaign.name}`")
        await present_embed(
            ctx,
            title=f"Create NPC: `{name}` in `{active_campaign.name}`",
            level="success",
            fields=[
                ("Class", npc_class),
                (
                    "Description",
                    (description[:MAX_FIELD_COUNT] + " ...")
                    if len(description) > MAX_FIELD_COUNT
                    else description,
                ),
            ],
            ephemeral=hidden,
            inline_fields=True,
        )

    @npc.command(name="list", description="List all NPCs")
    async def list_npcs(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """List all NPCs."""
        active_campaign = await ctx.fetch_active_campaign()

        if len(active_campaign.npcs) == 0:
            await present_embed(
                ctx,
                title="No NPCs",
                description="There are no NPCs\nCreate one with `/campaign create_npc`",
                level="info",
                ephemeral=hidden,
            )
            return

        fields = []
        fields.extend([
            (
                f"**__{npc.name}__**",
                f"**Class:** {npc.npc_class}\n**Description:** {npc.description}",
            )
            for npc in sorted(active_campaign.npcs, key=lambda x: x.name)
        ])

        await present_embed(ctx, title="NPCs", fields=fields, level="info", ephemeral=hidden)

    @npc.command(name="edit", description="Edit an NPC")
    async def edit_npc(
        self,
        ctx: ValentinaContext,
        index: Option(
            int,
            name="npc",
            description="NPC to edit",
            required=True,
            autocomplete=select_npc,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Edit an NPC."""
        if not await self.check_permissions(ctx):
            return

        active_campaign = await ctx.fetch_active_campaign()
        try:
            npc = active_campaign.npcs[index]
        except IndexError:
            await present_embed(
                ctx,
                title="NPC not found",
                description="The NPC you are trying to edit does not exist",
                level="error",
                ephemeral=hidden,
            )
            return

        modal = NPCModal(title=truncate_string("Edit NPC", 45), npc=npc)
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        name = modal.name.strip().title()
        npc_class = modal.npc_class.strip().title()
        description = modal.description.strip()

        active_campaign.npcs[index].name = name
        active_campaign.npcs[index].npc_class = npc_class
        active_campaign.npcs[index].description = description
        await active_campaign.save()

        await ctx.post_to_audit_log(f"Update NPC: `{name}` in `{active_campaign.name}`")
        await present_embed(
            ctx,
            title=f"Update NPC: `{name}` in `{active_campaign.name}`",
            level="success",
            fields=[
                ("Class", npc_class),
                (
                    "Description",
                    (modal.description.strip()[:MAX_FIELD_COUNT] + " ...")
                    if len(modal.description.strip()) > MAX_FIELD_COUNT
                    else modal.description.strip(),
                ),
            ],
            ephemeral=hidden,
            inline_fields=True,
        )

    @npc.command(name="delete", description="Delete an NPC")
    async def delete_npc(
        self,
        ctx: ValentinaContext,
        index: Option(
            int, name="npc", description="NPC to edit", required=True, autocomplete=select_npc
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Delete an NPC."""
        if not await self.check_permissions(ctx):
            return

        active_campaign = await ctx.fetch_active_campaign()
        try:
            npc = active_campaign.npcs[index]
        except IndexError:
            await present_embed(
                ctx,
                title="NPC not found",
                description="The NPC you are trying to edit does not exist",
                level="error",
                ephemeral=hidden,
            )
            return

        title = f"Delete NPC: `{npc.name}` in `{active_campaign.name}`"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden, audit=True
        )

        if not is_confirmed:
            return

        del active_campaign.npcs[index]
        await active_campaign.save()

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    ### CHAPTER COMMANDS ####################################################################

    @chapter.command(name="create", description="Create a new chapter")
    async def create_chapter(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Create a new chapter."""
        active_campaign = await ctx.fetch_active_campaign()

        modal = ChapterModal(title=truncate_string("Create new chapter", 45))
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        name = modal.name.strip().title()
        description_short = modal.description_short.strip()
        description_long = modal.description_long.strip()
        chapter_number = max([c.number for c in active_campaign.chapters], default=0) + 1

        chapter = CampaignChapter(
            name=name,
            description_short=description_short,
            description_long=description_long,
            number=chapter_number,
        )
        active_campaign.chapters.append(chapter)
        await active_campaign.save()

        await ctx.post_to_audit_log(
            f"Create chapter: `{chapter.number}. {chapter.name}` in `{active_campaign.name}`",
        )
        await present_embed(
            ctx,
            f"Create chapter: `{chapter.number}. {chapter.name}` in `{active_campaign.name}`",
            level="success",
            description=description_long,
            ephemeral=hidden,
        )

    @chapter.command(name="list", description="List all chapters")
    async def list_chapters(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """List all chapters."""
        active_campaign = await ctx.fetch_active_campaign()

        if len(active_campaign.chapters) == 0:
            await present_embed(
                ctx,
                title="No Chapters",
                description="There are no chapters\nCreate one with `/campaign create_chapter`",
                level="info",
                ephemeral=hidden,
            )
            return

        fields = []
        fields.extend([
            (
                f"**{chapter.number}.** **__{chapter.name}__**",
                f"{chapter.description_short}",
            )
            for chapter in sorted(active_campaign.chapters, key=lambda x: x.number)
        ])

        await present_embed(ctx, title="Chapters", fields=fields, level="info")

    @chapter.command(name="edit", description="Edit a chapter")
    @logger.catch
    async def edit_chapter(
        self,
        ctx: ValentinaContext,
        index: Option(
            int,
            name="chapter",
            description="Chapter to edit",
            required=True,
            autocomplete=select_chapter,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Edit a chapter."""
        active_campaign = await ctx.fetch_active_campaign()
        chapter = active_campaign.chapters[index]

        modal = ChapterModal(title=truncate_string("Edit chapter", 45), chapter=chapter)
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        name = modal.name.strip().title()
        description_short = modal.description_short.strip()
        description_long = modal.description_long.strip()

        active_campaign.chapters[index].name = name
        active_campaign.chapters[index].description_short = description_short
        active_campaign.chapters[index].description_long = description_long
        await active_campaign.save()

        await ctx.post_to_audit_log(f"Update chapter: `{name}` in `{active_campaign.name}`")

        await present_embed(
            ctx,
            title=f"Update chapter: `{name}` in `{active_campaign.name}`",
            level="success",
            description=description_short,
            ephemeral=hidden,
        )

    @chapter.command(name="delete", description="Delete a chapter")
    async def delete_chapter(
        self,
        ctx: ValentinaContext,
        index: Option(
            int,
            name="chapter",
            description="Chapter to edit",
            required=True,
            autocomplete=select_chapter,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Delete a chapter."""
        if not await self.check_permissions(ctx):
            return

        active_campaign = await ctx.fetch_active_campaign()
        chapter = active_campaign.chapters[index]

        title = f"Delete Chapter `{chapter.number}. {chapter.name}` from `{active_campaign.name}`"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden, audit=True
        )

        if not is_confirmed:
            return

        del active_campaign.chapters[index]
        await active_campaign.save()

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    ### NOTE COMMANDS ####################################################################

    @notes.command(name="create", description="Create a new note")
    async def create_note(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Create a new note."""
        active_campaign = await ctx.fetch_active_campaign()

        modal = NoteModal(title=truncate_string("Create new note", 45))
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        name = modal.name.strip().title()
        description = modal.description.strip()

        note = CampaignNote(
            name=name,
            description=description,
        )

        active_campaign.notes.append(note)
        await active_campaign.save()

        await ctx.post_to_audit_log(f"Create note: `{name}` in `{active_campaign.name}`")
        await present_embed(
            ctx,
            title=f"Create note: `{name}` in `{active_campaign.name}`",
            level="success",
            description=(description[:MAX_FIELD_COUNT] + " ...")
            if len(description) > MAX_FIELD_COUNT
            else description,
            ephemeral=hidden,
        )

    @notes.command(name="list", description="List all notes")
    async def list_notes(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """List all notes."""
        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        active_campaign = await guild.fetch_active_campaign()

        if len(active_campaign.notes) == 0:
            await present_embed(
                ctx,
                title="No Notes",
                description="There are no notes\nCreate one with `/campaign create_note`",
                level="info",
                ephemeral=hidden,
            )
            return

        fields = []
        fields.extend([
            (f"**__{note.name}__**", f"{note.description}")
            for note in sorted(active_campaign.notes, key=lambda x: x.name)
        ])

        await present_embed(
            ctx, title=f"Notes for **{active_campaign.name}**", fields=fields, level="info"
        )

    @notes.command(name="edit", description="Edit a note")
    async def edit_note(
        self,
        ctx: ValentinaContext,
        index: Option(
            int,
            name="note",
            description="Note to edit",
            required=True,
            autocomplete=select_note,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Edit a note."""
        active_campaign = await ctx.fetch_active_campaign()
        note = active_campaign.notes[index]

        modal = NoteModal(title=truncate_string("Edit note", 45), note=note)
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        name = modal.name.strip().title()
        description = modal.description.strip()

        active_campaign.notes[index].name = name
        active_campaign.notes[index].description = description
        await active_campaign.save()

        await ctx.post_to_audit_log(f"Update note: `{name}` in `{active_campaign.name}`")

        await present_embed(
            ctx,
            title=f"Update note: `{name}` in `{active_campaign.name}`",
            level="success",
            description=(modal.description.strip()[:MAX_FIELD_COUNT] + " ...")
            if len(modal.description.strip()) > MAX_FIELD_COUNT
            else modal.description.strip(),
            ephemeral=hidden,
        )

    @notes.command(name="delete", description="Delete a note")
    async def delete_note(
        self,
        ctx: ValentinaContext,
        index: Option(
            int,
            name="note",
            description="Note to edit",
            required=True,
            autocomplete=select_note,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Delete a note."""
        if not await self.check_permissions(ctx):
            return

        active_campaign = await ctx.fetch_active_campaign()
        note = active_campaign.notes[index]

        title = f"Delete note: `{note.name}` from `{active_campaign.name}`"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx, title, hidden=hidden, audit=True
        )

        if not is_confirmed:
            return

        del active_campaign.notes[index]
        await active_campaign.save()

        await interaction.edit_original_response(embed=confirmation_embed, view=None)


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(CampaignCog(bot))
