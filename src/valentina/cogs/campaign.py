# mypy: disable-error-code="valid-type"
"""Cog for the Campaign commands."""

import discord
from discord.commands import Option
from discord.ext import commands, pages
from loguru import logger

from valentina.constants import MAX_FIELD_COUNT, MAX_PAGE_CHARACTER_COUNT
from valentina.models.bot import Valentina, ValentinaContext
from valentina.models.mongo_collections import (
    Campaign,
    CampaignChapter,
    CampaignNote,
    CampaignNPC,
    Guild,
)
from valentina.utils.converters import ValidCampaign, ValidYYYYMMDD
from valentina.utils.helpers import truncate_string
from valentina.utils.options import select_campaign, select_chapter, select_note, select_npc
from valentina.views import ChapterModal, NoteModal, NPCModal, confirm_action, present_embed


class CampaignCog(commands.Cog):
    """Commands used for updating campaigns."""

    # TODO: Add paginator to long embeds (e.g. campaign list, campaign chapters, etc.)

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
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        # Update the database
        campaign = Campaign(name=name, guild=ctx.guild.id)
        await campaign.insert()

        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        guild.campaigns.append(campaign)
        await guild.save()

        await ctx.post_to_audit_log(title)
        await confirmation_response_msg

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
        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        campaign = await guild.fetch_active_campaign()

        campaign.date_in_game = date
        await campaign.save()

        await ctx.post_to_audit_log(f"Set date of campaign `{campaign.name}` to `{date:%Y-%m-%d}`")
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
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        await guild.delete_campaign(campaign)

        await ctx.post_to_audit_log(title)
        await confirmation_response_msg

    @campaign.command(name="view", description="View a campaign")
    async def view_campaign(self, ctx: ValentinaContext) -> None:
        """View a campaign."""
        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        campaign = await guild.fetch_active_campaign()

        #################################
        chapter_list = sorted(campaign.chapters, key=lambda c: c.number)
        npc_list = sorted(campaign.npcs, key=lambda n: n.name)
        note_list = sorted(campaign.notes, key=lambda n: n.name)

        chapter_listing = "\n".join([f"{c.number}. {c.name}" for c in chapter_list])

        intro = f"""
\u200b\n**__{campaign.name.upper()}__**
An overview of {campaign.name}.

**{len(chapter_list)} Chapters**
{chapter_listing}

**{len(npc_list)} NPCs**
{', '.join([f"{n.name}" for n in npc_list])}

**{len(note_list)} Notes**
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
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        guild.active_campaign = campaign
        await guild.save()

        await ctx.post_to_audit_log(title)
        await confirmation_response_msg

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
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        guild.active_campaign = None
        await guild.save()

        await ctx.post_to_audit_log(title)
        await confirmation_response_msg

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
        fields.extend(
            [
                (
                    f"**{c.name}** (Active)" if c == active_campaign else f"**{c.name}**",
                    "",
                )
                for c in sorted(guild.campaigns, key=lambda x: x.name)
            ]
        )

        await present_embed(ctx, title="Campaigns", fields=fields, level="info")
        logger.debug("CAMPAIGN: List all campaigns")

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
        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        active_campaign = await guild.fetch_active_campaign()

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
        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        active_campaign = await guild.fetch_active_campaign()

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
        fields.extend(
            [
                (
                    f"**__{npc.name}__**",
                    f"**Class:** {npc.npc_class}\n**Description:** {npc.description}",
                )
                for npc in sorted(active_campaign.npcs, key=lambda x: x.name)
            ]
        )

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

        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        active_campaign = await guild.fetch_active_campaign()
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

        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        active_campaign = await guild.fetch_active_campaign()
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
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        del active_campaign.npcs[index]
        await active_campaign.save()

        await ctx.post_to_audit_log(title)
        await confirmation_response_msg

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
        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        active_campaign = await guild.fetch_active_campaign()

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
        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        active_campaign = await guild.fetch_active_campaign()

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
        fields.extend(
            [
                (
                    f"**{chapter.number}.** **__{chapter.name}__**",
                    f"{chapter.description_short}",
                )
                for chapter in sorted(active_campaign.chapters, key=lambda x: x.number)
            ]
        )

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
        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        active_campaign = await guild.fetch_active_campaign()
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

        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        active_campaign = await guild.fetch_active_campaign()
        chapter = active_campaign.chapters[index]

        title = f"Delete Chapter `{chapter.number}. {chapter.name}` from `{active_campaign.name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        del active_campaign.chapters[index]
        await active_campaign.save()

        await ctx.post_to_audit_log(title)
        await confirmation_response_msg

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
        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        active_campaign = await guild.fetch_active_campaign()

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
        fields.extend(
            [
                (f"**__{note.name}__**", f"{note.description}")
                for note in sorted(active_campaign.notes, key=lambda x: x.name)
            ]
        )

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
        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        active_campaign = await guild.fetch_active_campaign()
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

        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        active_campaign = await guild.fetch_active_campaign()
        note = active_campaign.notes[index]

        title = f"Delete note: `{note.name}` from `{active_campaign.name}`"
        is_confirmed, confirmation_response_msg = await confirm_action(ctx, title, hidden=hidden)

        if not is_confirmed:
            return

        del active_campaign.notes[index]
        await active_campaign.save()

        await ctx.post_to_audit_log(title)
        await confirmation_response_msg


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(CampaignCog(bot))
