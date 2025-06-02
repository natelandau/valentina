# mypy: disable-error-code="valid-type"
"""Cog for the Campaign commands."""

import asyncio

import discord
import inflect
from discord.commands import Option
from discord.ext import commands
from loguru import logger

from valentina.constants import MAX_FIELD_COUNT, EmbedColor
from valentina.controllers import ChannelManager, PermissionManager
from valentina.discord.bot import Valentina, ValentinaContext
from valentina.discord.utils import fetch_channel_object
from valentina.discord.utils.autocomplete import (
    select_book,
    select_campaign,
    select_chapter,
    select_npc,
)
from valentina.discord.utils.converters import (
    ValidBookNumber,
    ValidCampaign,
    ValidCampaignBook,
    ValidCampaignBookChapter,
    ValidChapterNumber,
    ValidYYYYMMDD,
)
from valentina.discord.views import (
    BookModal,
    ChapterModal,
    NPCModal,
    auto_paginate,
    confirm_action,
    present_embed,
)
from valentina.discord.views.campaign_viewer import CampaignViewer
from valentina.models import (
    Campaign,
    CampaignBook,
    CampaignBookChapter,
    CampaignNPC,
    Guild,
)
from valentina.utils.helpers import truncate_string

p = inflect.engine()


class CampaignCog(commands.Cog):
    """Commands used for updating campaigns."""

    def __init__(self, bot: Valentina) -> None:
        self.bot: Valentina = bot

    campaign = discord.SlashCommandGroup("campaign", "Manage campaigns")
    chapter = campaign.create_subgroup(name="chapter", description="Manage campaign chapters")
    book = campaign.create_subgroup(name="book", description="Manage campaign books")
    npc = campaign.create_subgroup(name="npc", description="Manage campaign NPCs")
    notes = campaign.create_subgroup(name="notes", description="Manage campaign notes")
    admin = campaign.create_subgroup(name="admin", description="Administer the campaign")

    async def check_permissions(self, ctx: ValentinaContext) -> bool:
        """Check if the user has permissions to run the command."""
        permission_mngr = PermissionManager(ctx.guild.id)

        if not await permission_mngr.can_manage_campaign(ctx.author.id):
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
            ctx,
            title,
            hidden=hidden,
            audit=True,
        )

        if not is_confirmed:
            return

        # Update the database
        c = Campaign(name=name, guild=ctx.guild.id)
        campaign = await c.insert()

        # Add campaign to guild
        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        guild.campaigns.append(campaign)

        await guild.save()

        channel_manager = ChannelManager(guild=ctx.guild)
        await channel_manager.confirm_campaign_channels(campaign)

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
        channel_objects = await fetch_channel_object(ctx, need_campaign=True)
        campaign = channel_objects.campaign

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
            ctx,
            title,
            hidden=hidden,
            audit=True,
        )

        if not is_confirmed:
            return

        guild = await Guild.get(ctx.guild.id, fetch_links=True)
        await guild.delete_campaign(campaign)

        channel_manager = ChannelManager(guild=ctx.guild)
        await channel_manager.delete_campaign_channels(campaign)

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @campaign.command(name="view", description="View a campaign")
    async def view_campaign(self, ctx: ValentinaContext) -> None:
        """View a campaign."""
        channel_objects = await fetch_channel_object(ctx, need_campaign=True)
        campaign = channel_objects.campaign

        cv = CampaignViewer(ctx, campaign, max_chars=1000)
        paginator = await cv.display()
        await paginator.respond(ctx.interaction, ephemeral=True)
        await paginator.wait()

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

        if len(guild.campaigns) == 0:
            await present_embed(
                ctx,
                title="No campaigns",
                description="There are no campaigns\nCreate one with `/campaign create`",
                level="info",
                ephemeral=hidden,
            )
            return

        text = f"## {len(guild.campaigns)} {p.plural_noun('campaign', len(guild.campaigns))} on `{ctx.guild.name}`\n"
        for c in sorted(guild.campaigns, key=lambda x: x.name):
            characters = await c.fetch_player_characters()
            text += f"### **{c.name}**\n"
            text += f"{c.description}\n" if c.description else ""
            text += f"- `{len(c.books)}` {p.plural_noun('book', len(c.books))}\n"
            text += f"- `{len(c.npcs)}` NPCs\n"
            text += f"- `{len(characters)}` {p.plural_noun('character', len(characters))}\n"

        await auto_paginate(
            ctx=ctx,
            title="",
            text=text,
            color=EmbedColor.INFO,
            hidden=hidden,
            max_chars=900,
        )

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
        channel_objects = await fetch_channel_object(ctx, need_campaign=True)
        campaign = channel_objects.campaign

        modal = NPCModal(title=truncate_string("Create new NPC", 45))
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        name = modal.name.strip().title()
        npc_class = modal.npc_class.strip().title()
        description = modal.description.strip()

        npc = CampaignNPC(name=name, npc_class=npc_class, description=description)
        campaign.npcs.append(npc)
        await campaign.save()

        await ctx.post_to_audit_log(f"Create NPC: `{name}` in `{campaign.name}`")
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
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """List all NPCs."""
        channel_objects = await fetch_channel_object(ctx, need_campaign=True)
        campaign = channel_objects.campaign

        if len(campaign.npcs) == 0:
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
                for npc in sorted(campaign.npcs, key=lambda x: x.name)
            ],
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

        channel_objects = await fetch_channel_object(ctx, need_campaign=True)
        campaign = channel_objects.campaign

        try:
            npc = campaign.npcs[index]
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

        campaign.npcs[index].name = name
        campaign.npcs[index].npc_class = npc_class
        campaign.npcs[index].description = description
        await campaign.save()

        await ctx.post_to_audit_log(f"Update NPC: `{name}` in `{campaign.name}`")
        await present_embed(
            ctx,
            title=f"Update NPC: `{name}` in `{campaign.name}`",
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
        """Delete an NPC."""
        if not await self.check_permissions(ctx):
            return

        channel_objects = await fetch_channel_object(ctx, need_campaign=True)
        campaign = channel_objects.campaign

        try:
            npc = campaign.npcs[index]
        except IndexError:
            await present_embed(
                ctx,
                title="NPC not found",
                description="The NPC you are trying to edit does not exist",
                level="error",
                ephemeral=hidden,
            )
            return

        title = f"Delete NPC: `{npc.name}` in `{campaign.name}`"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx,
            title,
            hidden=hidden,
            audit=True,
        )

        if not is_confirmed:
            return

        del campaign.npcs[index]
        await campaign.save()

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    ### BOOK COMMANDS ####################################################################

    @book.command(name="create", description="Create a new book")
    async def create_book(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Create a new book."""
        if not await self.check_permissions(ctx):
            return

        channel_objects = await fetch_channel_object(ctx, need_campaign=True)
        campaign = channel_objects.campaign

        modal = BookModal(title=truncate_string("Create new book", 45))
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        books = await campaign.fetch_books()

        name = modal.name.strip().title()
        description_short = modal.description_short.strip()
        description_long = modal.description_long.strip()
        chapter_number = max([c.number for c in books], default=0) + 1

        book = CampaignBook(
            name=name,
            description_short=description_short,
            description_long=description_long,
            number=chapter_number,
            campaign=str(campaign.id),
        )
        await book.insert()
        campaign.books.append(book)
        await campaign.save()

        channel_manager = ChannelManager(guild=ctx.guild)
        await channel_manager.confirm_campaign_channels(campaign)

        await ctx.post_to_audit_log(
            f"Create book: `{book.number}. {book.name}` in `{campaign.name}`",
        )
        await present_embed(
            ctx,
            f"Create book: `{book.number}. {book.name}` in `{campaign.name}`",
            level="success",
            description=description_long,
            ephemeral=hidden,
        )

    @book.command(name="list", description="List all books")
    async def list_books(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """List all books."""
        channel_objects = await fetch_channel_object(ctx, need_campaign=True)
        campaign = channel_objects.campaign
        all_books = await campaign.fetch_books()

        if len(all_books) == 0:
            await present_embed(
                ctx,
                title="No books",
                description="There are no books\nCreate one with `/campaign create_book`",
                level="info",
                ephemeral=hidden,
            )
            return

        fields = []
        fields.extend(
            [
                (
                    f"**{book.number}.** **__{book.name}__** ({len(book.chapters)} chapters)",
                    f"{book.description_short}",
                )
                for book in sorted(all_books, key=lambda x: x.number)
            ],
        )

        await present_embed(ctx, title=f"All Books in {campaign.name}", fields=fields, level="info")

    @book.command(name="edit", description="Edit a book")
    @logger.catch
    async def edit_book(
        self,
        ctx: ValentinaContext,
        book: Option(
            ValidCampaignBook,
            name="book",
            description="Book to edit",
            required=True,
            autocomplete=select_book,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Edit a chapter."""
        if not await self.check_permissions(ctx):
            return

        channel_objects = await fetch_channel_object(ctx, need_campaign=True)
        campaign = channel_objects.campaign
        original_name = book.name

        modal = BookModal(title=truncate_string(f"Edit book {book.name}", 45), book=book)
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        name = modal.name.strip().title()
        description_short = modal.description_short.strip()
        description_long = modal.description_long.strip()

        book.name = name
        book.description_short = description_short
        book.description_long = description_long
        await book.save()

        if original_name != name:
            channel_manager = ChannelManager(guild=ctx.guild)
            await channel_manager.confirm_book_channel(book=book, campaign=campaign)
            await channel_manager.sort_campaign_channels(campaign)

        await ctx.post_to_audit_log(f"Update book: `{book.name}` in `{campaign.name}`")

        await present_embed(
            ctx,
            title=f"Update book: `{name}` in `{campaign.name}`",
            level="success",
            description=description_short,
            ephemeral=hidden,
        )

    @book.command(name="delete", description="Delete a book")
    async def delete_book(
        self,
        ctx: ValentinaContext,
        book: Option(
            ValidCampaignBook,
            name="book",
            description="Book to delete",
            required=True,
            autocomplete=select_book,
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

        channel_objects = await fetch_channel_object(ctx, need_campaign=True)
        campaign = channel_objects.campaign

        title = f"Delete book `{book.number}. {book.name}` from `{campaign.name}`"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx,
            title,
            hidden=hidden,
            audit=True,
        )

        if not is_confirmed:
            return

        channel_manager = ChannelManager(guild=ctx.guild)
        await channel_manager.delete_book_channel(book)

        await campaign.delete_book(book)

        for campaign_book in await CampaignBook.find(
            CampaignBook.campaign == campaign.id,
        ).to_list():
            await channel_manager.confirm_book_channel(book=campaign_book, campaign=campaign)
            await asyncio.sleep(1)

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @book.command(name="renumber", description="Renumber books")
    async def renumber_books(
        self,
        ctx: ValentinaContext,
        book: Option(
            ValidCampaignBook,
            name="book",
            description="Book to renumber",
            required=True,
            autocomplete=select_book,
        ),
        new_number: Option(
            ValidBookNumber,
            name="new_number",
            description="New chapter number",
            required=True,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Renumber books."""
        if not await self.check_permissions(ctx):
            return

        if book.number == new_number:
            await present_embed(
                ctx,
                title="book numbers are the same",
                description="The book numbers are the same",
                level="info",
                ephemeral=hidden,
            )
            return

        channel_objects = await fetch_channel_object(ctx, need_campaign=True)
        campaign = channel_objects.campaign

        original_number = book.number

        title = (
            f"Renumber book `{book.name}` from number `{original_number}` to number `{new_number}`"
        )
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx,
            title,
            hidden=hidden,
            audit=True,
        )

        if not is_confirmed:
            return

        all_books = await campaign.fetch_books()

        # Update the number of the selected book
        book.number = new_number

        channel_manager = ChannelManager(guild=ctx.guild)

        # Adjust the numbers of the other books
        if new_number > original_number:
            # Shift books down if the new number is higher
            for b in all_books:
                if original_number < b.number <= new_number:
                    b.number -= 1
                    await b.save()
                    await channel_manager.confirm_book_channel(book=b, campaign=campaign)
                    await asyncio.sleep(1)
        else:
            # Shift books up if the new number is lower
            for b in all_books:
                if new_number <= b.number < original_number:
                    b.number += 1
                    await b.save()
                    await channel_manager.confirm_book_channel(book=b, campaign=campaign)
                    await asyncio.sleep(1)

        # Save the selected book with its new number
        await book.save()

        await channel_manager.confirm_book_channel(book=book, campaign=campaign)
        await channel_manager.sort_campaign_channels(campaign)

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    ### CHAPTER COMMANDS ####################################################################

    @chapter.command(name="create", description="Create a new chapter")
    async def create_chapter(
        self,
        ctx: ValentinaContext,
        hidden: Option(
            bool,
            description="Make the response visible only to you (default false).",
            default=False,
        ),
    ) -> None:
        """Create a new chapter."""
        if not await self.check_permissions(ctx):
            return

        channel_objects = await fetch_channel_object(ctx, need_book=True)
        book = channel_objects.book
        if not book:
            await present_embed(
                ctx,
                title="No active book",
                description="Invoke this command from the appropriate book channel to create a chapter",
                level="ERROR",
                ephemeral=hidden,
            )
            return

        modal = ChapterModal(title="Create new chapter")
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        name = modal.name.strip().title()
        description_short = modal.description_short.strip()
        description_long = modal.description_long.strip()
        chapter_number = max([c.number for c in await book.fetch_chapters()], default=0) + 1

        chapter = CampaignBookChapter(
            name=name,
            description_short=description_short,
            description_long=description_long,
            number=chapter_number,
            book=str(book.id),
        )
        await chapter.insert()
        book.chapters.append(chapter)
        await book.save()

        await ctx.post_to_audit_log(
            f"Create chapter: `{chapter.number}. {chapter.name}` in book `{book.name}`",
        )
        await present_embed(
            ctx,
            f"Create chapter: `{chapter.number}. {chapter.name}` in book `{book.name}`",
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
        channel_objects = await fetch_channel_object(ctx, need_book=True)
        book = channel_objects.book
        if not book:
            await present_embed(
                ctx,
                title="No active book",
                description="Invoke this command from the appropriate book channel to create a chapter",
                level="ERROR",
                ephemeral=hidden,
            )
            return

        chapters = await book.fetch_chapters()

        if len(chapters) == 0:
            await present_embed(
                ctx,
                title="No Chapters",
                description="There are no chapters\nCreate one with `/campaign chapter create`",
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
                for chapter in sorted(chapters, key=lambda x: x.number)
            ],
        )

        await present_embed(ctx, title="Chapters", fields=fields, level="info")

    @chapter.command(name="edit", description="Edit a chapter")
    @logger.catch
    async def edit_chapter(
        self,
        ctx: ValentinaContext,
        chapter: Option(
            ValidCampaignBookChapter,
            name="chapter",
            description="Chapter to renumber",
            required=True,
            autocomplete=select_chapter,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default false).",
            default=False,
        ),
    ) -> None:
        """Edit a chapter."""
        if not await self.check_permissions(ctx):
            return

        channel_objects = await fetch_channel_object(ctx, need_book=True)
        book = channel_objects.book
        if not book:
            await present_embed(
                ctx,
                title="No active book",
                description="Invoke this command from the appropriate book channel to edit a chapter",
                level="ERROR",
                ephemeral=hidden,
            )
            return

        modal = ChapterModal(title=truncate_string("Edit chapter", 45), chapter=chapter)
        await ctx.send_modal(modal)
        await modal.wait()
        if not modal.confirmed:
            return

        name = modal.name.strip().title()
        description_short = modal.description_short.strip()
        description_long = modal.description_long.strip()

        chapter.name = name
        chapter.description_short = description_short
        chapter.description_long = description_long
        await chapter.save()

        await ctx.post_to_audit_log(f"Update chapter: `{name}` in `{book.name}`")

        await present_embed(
            ctx,
            title=f"Update chapter: `{name}` in `{book.name}`",
            level="success",
            description=description_short,
            ephemeral=hidden,
        )

    @chapter.command(name="delete", description="Delete a chapter")
    async def delete_chapter(
        self,
        ctx: ValentinaContext,
        chapter: Option(
            ValidCampaignBookChapter,
            name="chapter",
            description="Chapter to renumber",
            required=True,
            autocomplete=select_chapter,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default False).",
            default=False,
        ),
    ) -> None:
        """Delete a chapter."""
        if not await self.check_permissions(ctx):
            return

        channel_objects = await fetch_channel_object(ctx, need_book=True)
        book = channel_objects.book
        if not book:
            await present_embed(
                ctx,
                title="No active book",
                description="Invoke this command from the appropriate book channel to delete a chapter",
                level="ERROR",
                ephemeral=hidden,
            )
            return

        title = f"Delete Chapter `{chapter.number}. {chapter.name}` from `{book.name}`"
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx,
            title,
            hidden=hidden,
            audit=True,
        )

        if not is_confirmed:
            return

        await book.delete_chapter(chapter)

        await interaction.edit_original_response(embed=confirmation_embed, view=None)

    @chapter.command(name="renumber", description="Renumber chapters")
    async def renumber_chapters(
        self,
        ctx: ValentinaContext,
        chapter: Option(
            ValidCampaignBookChapter,
            name="chapter",
            description="Chapter to renumber",
            required=True,
            autocomplete=select_chapter,
        ),
        new_number: Option(
            ValidChapterNumber,
            name="new_number",
            description="New chapter number",
            required=True,
        ),
        hidden: Option(
            bool,
            description="Make the response visible only to you (default true).",
            default=True,
        ),
    ) -> None:
        """Renumber chapters."""
        if not await self.check_permissions(ctx):
            return

        channel_objects = await fetch_channel_object(ctx, need_book=True)
        book = channel_objects.book
        if not book:
            await present_embed(
                ctx,
                title="No active book",
                description="Invoke this command from the appropriate book channel to renumber chapters",
                level="ERROR",
                ephemeral=hidden,
            )
            return

        if chapter.number == new_number:
            await present_embed(
                ctx,
                title="Chapter numbers are the same",
                description="The chapter numbers are the same",
                level="info",
                ephemeral=hidden,
            )
            return

        original_number = chapter.number

        title = (
            f"Renumber book `{book.name}` from number `{original_number}` to number `{new_number}`"
        )
        is_confirmed, interaction, confirmation_embed = await confirm_action(
            ctx,
            title,
            hidden=hidden,
            audit=True,
        )

        if not is_confirmed:
            return

        all_chapters = await book.fetch_chapters()

        # Update the number of the selected book
        chapter.number = new_number

        # Adjust the numbers of the other books
        if new_number > original_number:
            # Shift books down if the new number is higher
            for c in all_chapters:
                if original_number < c.number <= new_number:
                    c.number -= 1
                    await c.save()
        else:
            # Shift books up if the new number is lower
            for c in all_chapters:
                if new_number <= c.number < original_number:
                    c.number += 1
                    await c.save()

        # Save the selected book with its new number
        await chapter.save()

        await interaction.edit_original_response(embed=confirmation_embed, view=None)


def setup(bot: Valentina) -> None:
    """Add the cog to the bot."""
    bot.add_cog(CampaignCog(bot))
