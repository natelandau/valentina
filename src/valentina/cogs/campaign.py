# mypy: disable-error-code="valid-type"
"""Cog for the Campaign commands."""

import discord
from discord.commands import Option
from discord.ext import commands, pages
from loguru import logger

from valentina.constants import MAX_FIELD_COUNT, MAX_PAGE_CHARACTER_COUNT
from valentina.models.bot import Valentina
from valentina.utils.converters import ValidCampaign, ValidYYYYMMDD
from valentina.utils.helpers import truncate_string
from valentina.utils.options import select_campaign, select_chapter, select_note, select_npc
from valentina.views import ChapterModal, NoteModal, NPCModal, confirm_action, present_embed


class Campaign(commands.Cog):
    """Commands used for updating campaigns."""

    # TODO: Add paginator to long embeds (e.g. campaign list, campaign chapters, etc.)

    def __init__(self, bot: Valentina) -> None:
        self.bot = bot

    campaign = discord.SlashCommandGroup("campaign", "Manage campaigns")
    chapter = campaign.create_subgroup(name="chapter", description="Manage campaign chapters")
    npc = campaign.create_subgroup(name="npc", description="Manage campaign NPCs")
    notes = campaign.create_subgroup(name="notes", description="Manage campaign notes")

    async def check_permissions(self, ctx: discord.ApplicationContext) -> bool:
        """Check if the user has permissions to run the command."""
        if not self.bot.user_svc.can_manage_campaign(ctx):
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
        ctx: discord.ApplicationContext,
        name: Option(str, description="Name of the campaign", required=True),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Create a new campaign."""
        # TODO: Migrate to modal to allow setting campaign description

        if not self.check_permissions(ctx):
            return

        title = f"Create new campaign: `{name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        self.bot.campaign_svc.create_campaign(ctx, name=name)

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await confirmation_response_msg

    @campaign.command(name="current_date", description="Set the current date of a campaign")
    async def current_date(
        self,
        ctx: discord.ApplicationContext,
        date: Option(ValidYYYYMMDD, description="DOB in the format of YYYY-MM-DD", required=True),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Set current date of a campaign."""
        campaign = self.bot.campaign_svc.fetch_active(ctx)

        self.bot.campaign_svc.update_campaign(ctx, campaign, current_date=date)
        await self.bot.guild_svc.send_to_audit_log(
            ctx, f"Set date of campaign `{campaign.name}` to `{date:%Y-%m-%d}`"
        )
        await present_embed(
            ctx,
            title=f"Set date of campaign `{campaign.name}` to `{date:%Y-%m-%d}`",
            level="success",
            ephemeral=hidden,
        )

    @campaign.command(name="delete", description="Delete a campaign")
    async def delete_campaign(
        self,
        ctx: discord.ApplicationContext,
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
        if not self.check_permissions(ctx):
            return

        title = f"Delete campaign: {campaign.name}"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        self.bot.campaign_svc.delete_campaign(ctx, campaign)

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await confirmation_response_msg

    @campaign.command(name="view", description="View a campaign")
    async def view_campaign(self, ctx: discord.ApplicationContext) -> None:
        """View a campaign."""
        campaign = self.bot.campaign_svc.fetch_active(ctx)
        npcs = self.bot.campaign_svc.fetch_all_npcs(campaign)
        chapters = self.bot.campaign_svc.fetch_all_chapters(campaign)
        notes = self.bot.campaign_svc.fetch_all_notes(campaign)

        chapter_list = sorted(chapters, key=lambda c: c.chapter_number)
        npc_list = sorted(npcs, key=lambda n: n.name)
        note_list = sorted(notes, key=lambda n: n.name)

        chapter_listing = "\n".join([f"{c.chapter_number}. {c.name}" for c in chapter_list])

        intro = f"""
\u200b\n**__{campaign.name.upper()}__**
An overview of {campaign.name}.

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
            if len(current_string) + len(chapter.campaign_display()) > MAX_PAGE_CHARACTER_COUNT:
                chapter_pages.append(f"\u200b\nChapters in **{campaign.name}**" + current_string)
                current_string = ""
            current_string += f"\n\n{chapter.campaign_display()}"

        if current_string:
            chapter_pages.append(f"\u200b\nChapters in **{campaign.name}**" + current_string)

        ## NPCS ##
        npc_pages = []
        current_string = ""
        for npc in npc_list:
            if len(current_string) + len(npc.campaign_display()) > MAX_PAGE_CHARACTER_COUNT:
                npc_pages.append(f"\u200b\nNPCs in **{campaign.name}**" + current_string)
                current_string = ""
            current_string += f"\n\n{npc.campaign_display()}"

        if current_string:
            npc_pages.append(f"\u200b\nNPCs in **{campaign.name}**" + current_string)

        ## NOTES ##
        note_pages = []
        current_string = ""
        for note in note_list:
            if len(current_string) + len(note.campaign_display()) > MAX_PAGE_CHARACTER_COUNT:
                note_pages.append(f"\u200b\nNotes in **{campaign.name}**" + current_string)
                current_string = ""
            current_string += f"\n\n{note.campaign_display()}"

        if current_string:
            note_pages.append(f"\u200b\nNotes in **{campaign.name}**" + current_string)

        # Create a paginator with the intro page
        paginator = pages.Paginator(pages=[intro, *chapter_pages, *npc_pages, *note_pages])
        paginator.remove_button("first")
        paginator.remove_button("last")

        # Send the paginator as a dm to the user
        await paginator.respond(
            ctx.interaction,
            target=ctx.author,
            ephemeral=True,
            target_message=f"Please check your DMs! The campaign **{campaign.name}** has been sent to you.",
        )

    @campaign.command(name="set_active", description="Set a campaign as active")
    async def campaign_set_active(
        self,
        ctx: discord.ApplicationContext,
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
        if not self.check_permissions(ctx):
            return

        title = f"Set campaign `{campaign.name}` as active"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        self.bot.campaign_svc.set_active(ctx, campaign)

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await confirmation_response_msg

    @campaign.command(name="set_inactive", description="Set a campaign as inactive")
    async def campaign_set_inactive(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Set the active campaign as inactive."""
        if not self.check_permissions(ctx):
            return

        campaign = self.bot.campaign_svc.fetch_active(ctx)

        title = f"Set campaign `{campaign.name}` as inactive"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        self.bot.campaign_svc.set_inactive(ctx)

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await confirmation_response_msg

    @campaign.command(name="list", description="List all campaigns")
    async def campaign_list(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """List all campaigns."""
        campaigns = self.bot.campaign_svc.fetch_all(ctx)
        if len(campaigns) == 0:
            await present_embed(
                ctx,
                title="No campaigns",
                description="There are no campaigns\nCreate one with `/campaign create`",
                level="info",
                ephemeral=hidden,
            )
            return

        fields = []
        for c in sorted(campaigns, key=lambda x: x.name):
            fields.append((f"**{c.name}** (Active)" if c.is_active else f"**{c.name}**", ""))

        await present_embed(ctx, title="Campaigns", fields=fields, level="info")
        logger.debug("CAMPAIGN: List all campaigns")

    ### NPC COMMANDS ####################################################################

    @npc.command(name="create", description="Create a new NPC")
    async def create_npc(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Create a new NPC."""
        campaign = self.bot.campaign_svc.fetch_active(ctx)

        modal = NPCModal(title=truncate_string("Create new NPC", 45))
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        name = modal.name.strip().title()
        npc_class = modal.npc_class.strip().title()
        description = modal.description.strip()

        self.bot.campaign_svc.create_npc(
            ctx, campaign=campaign, name=name, npc_class=npc_class, description=description
        )

        await self.bot.guild_svc.send_to_audit_log(
            ctx, f"Create NPC: `{name}` in `{campaign.name}`"
        )
        await present_embed(
            ctx,
            title=f"Create NPC: `{name}` in `{campaign.name}`",
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
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """List all NPCs."""
        campaign = self.bot.campaign_svc.fetch_active(ctx)
        npcs = self.bot.campaign_svc.fetch_all_npcs(campaign)
        if len(npcs) == 0:
            await present_embed(
                ctx,
                title="No NPCs",
                description="There are no NPCs\nCreate one with `/campaign create_npc`",
                level="info",
                ephemeral=hidden,
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

        await present_embed(ctx, title="NPCs", fields=fields, level="info", ephemeral=hidden)

    @npc.command(name="edit", description="Edit an NPC")
    async def edit_npc(
        self,
        ctx: discord.ApplicationContext,
        npc: Option(str, description="NPC to edit", required=True, autocomplete=select_npc),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Edit an NPC."""
        campaign = self.bot.campaign_svc.fetch_active(ctx)
        npc = self.bot.campaign_svc.fetch_npc_by_name(ctx, campaign, npc)

        modal = NPCModal(title=truncate_string("Edit NPC", 45), npc=npc)
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        updates = {
            "name": modal.name.strip().title(),
            "npc_class": modal.npc_class.strip().title(),
            "description": modal.description.strip(),
        }
        self.bot.campaign_svc.update_npc(ctx, npc, **updates)

        await self.bot.guild_svc.send_to_audit_log(
            ctx, f"Update NPC: `{updates['name']}` in `{campaign.name}`"
        )
        await present_embed(
            ctx,
            title=f"Update NPC: `{updates['name']}` in `{campaign.name}`",
            level="success",
            fields=[
                ("Class", updates["npc_class"]),
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
        ctx: discord.ApplicationContext,
        npc: Option(str, description="NPC to edit", required=True, autocomplete=select_npc),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Delete an NPC."""
        if not self.check_permissions(ctx):
            return

        campaign = self.bot.campaign_svc.fetch_active(ctx)
        npc = self.bot.campaign_svc.fetch_npc_by_name(ctx, campaign, npc)

        title = f"Delete NPC: `{npc.name}` in `{campaign.name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        self.bot.campaign_svc.delete_npc(ctx, npc)

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await confirmation_response_msg

    ### CHAPTER COMMANDS ####################################################################

    @chapter.command(name="create", description="Create a new chapter")
    async def create_chapter(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Create a new chapter."""
        campaign = self.bot.campaign_svc.fetch_active(ctx)

        modal = ChapterModal(title=truncate_string("Create new chapter", 45))
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        name = modal.name.strip().title()
        short_description = modal.short_description.strip()
        description = modal.description.strip()

        chapter = self.bot.campaign_svc.create_chapter(
            ctx,
            campaign=campaign,
            name=name,
            short_description=short_description,
            description=description,
        )

        await self.bot.guild_svc.send_to_audit_log(
            ctx,
            f"Create chapter: `{chapter.chapter_number}. {chapter.name}` in `{campaign.name}`",
        )
        await present_embed(
            ctx,
            f"Create chapter: `{chapter.chapter_number}. {chapter.name}` in `{campaign.name}`",
            level="success",
            description=short_description,
            ephemeral=hidden,
        )

    @chapter.command(name="list", description="List all chapters")
    async def list_chapters(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """List all chapters."""
        campaign = self.bot.campaign_svc.fetch_active(ctx)
        chapters = self.bot.campaign_svc.fetch_all_chapters(campaign)
        if len(chapters) == 0:
            await present_embed(
                ctx,
                title="No Chapters",
                description="There are no chapters\nCreate one with `/campaign create_chapter`",
                level="info",
                ephemeral=hidden,
            )
            return

        fields = []
        for chapter in sorted(chapters, key=lambda x: x.chapter_number):
            fields.append(
                (
                    f"**{chapter.chapter_number}.** **__{chapter.name}__**",
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
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Edit a chapter."""
        campaign = self.bot.campaign_svc.fetch_active(ctx)
        chapter = self.bot.campaign_svc.fetch_chapter_by_name(
            campaign, chapter_select.split(":")[1]
        )

        modal = ChapterModal(title=truncate_string("Edit chapter", 45), chapter=chapter)
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        updates = {
            "name": modal.name.strip().title(),
            "short_description": modal.short_description.strip(),
            "description": modal.description.strip(),
        }
        self.bot.campaign_svc.update_chapter(ctx, chapter, **updates)

        await self.bot.guild_svc.send_to_audit_log(
            ctx, f"Update chapter: `{updates['name']}` in `{campaign.name}`"
        )

        await present_embed(
            ctx,
            title=f"Update chapter: `{updates['name']}` in `{campaign.name}`",
            level="success",
            description=updates["short_description"],
            ephemeral=hidden,
        )

    @chapter.command(name="delete", description="Delete a chapter")
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
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Delete a chapter."""
        if not self.check_permissions(ctx):
            return

        campaign = self.bot.campaign_svc.fetch_active(ctx)
        chapter = self.bot.campaign_svc.fetch_chapter_by_name(
            campaign, chapter_select.split(":")[1]
        )

        title = f"Delete Chapter `{chapter.chapter_number}. {chapter.name}` from `{campaign.name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        self.bot.campaign_svc.delete_chapter(ctx, chapter)

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await confirmation_response_msg

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
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Create a new note."""
        campaign = self.bot.campaign_svc.fetch_active(ctx)
        chapter = (
            self.bot.campaign_svc.fetch_chapter_by_name(campaign, chapter_select.split(":")[1])
            if chapter_select
            else None
        )

        modal = NoteModal(title=truncate_string("Create new note", 45))
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        name = modal.name.strip().title()
        description = modal.description.strip()

        self.bot.campaign_svc.create_note(
            ctx,
            campaign=campaign,
            name=name,
            description=description,
            chapter=chapter,
        )

        await self.bot.guild_svc.send_to_audit_log(
            ctx, f"Create note: `{name}` in `{campaign.name}`"
        )

        await present_embed(
            ctx,
            title=f"Create note: `{name}` in `{campaign.name}`",
            level="success",
            description=(description[:MAX_FIELD_COUNT] + " ...")
            if len(description) > MAX_FIELD_COUNT
            else description,
            ephemeral=hidden,
        )

    @notes.command(name="list", description="List all notes")
    async def list_notes(
        self,
        ctx: discord.ApplicationContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """List all notes."""
        campaign = self.bot.campaign_svc.fetch_active(ctx)
        notes = self.bot.campaign_svc.fetch_all_notes(campaign)
        if len(notes) == 0:
            await present_embed(
                ctx,
                title="No Notes",
                description="There are no notes\nCreate one with `/campaign create_note`",
                level="info",
                ephemeral=hidden,
            )
            return

        fields = []
        for note in sorted(notes, key=lambda x: x.name):
            fields.append(
                (
                    f"**__{note.name}__**",
                    f"**Chapter:** {note.chapter.chapter_number}\n{note.description}"
                    if note.chapter
                    else f"{note.description}",
                )
            )

        await present_embed(
            ctx, title=f"Notes for **{campaign.name}**", fields=fields, level="info"
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
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Edit a note."""
        campaign = self.bot.campaign_svc.fetch_active(ctx)
        note = self.bot.campaign_svc.fetch_note_by_id(note_select.split(":")[0])

        modal = NoteModal(title=truncate_string("Edit note", 45), note=note)
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        updates = {
            "name": modal.name.strip().title(),
            "description": modal.description.strip(),
        }
        self.bot.campaign_svc.update_note(ctx, note, **updates)

        await self.bot.guild_svc.send_to_audit_log(
            ctx, f"Update note: `{updates['name']}` in `{campaign.name}`"
        )

        await present_embed(
            ctx,
            title=f"Update note: `{updates['name']}` in `{campaign.name}`",
            level="success",
            description=(modal.description.strip()[:MAX_FIELD_COUNT] + " ...")
            if len(modal.description.strip()) > MAX_FIELD_COUNT
            else modal.description.strip(),
            ephemeral=hidden,
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
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Delete a note."""
        if not self.check_permissions(ctx):
            return

        campaign = self.bot.campaign_svc.fetch_active(ctx)
        note = self.bot.campaign_svc.fetch_note_by_id(note_select.split(":")[0])

        title = f"Delete note: `{note.name}` from `{campaign.name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        self.bot.campaign_svc.delete_note(ctx, note)

        await self.bot.guild_svc.send_to_audit_log(ctx, title)
        await confirmation_response_msg


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(Campaign(bot))
