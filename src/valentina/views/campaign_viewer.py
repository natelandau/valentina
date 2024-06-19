"""Interactive campaign viewer."""

import textwrap

import discord
from discord.ext import pages

from valentina.constants import ABS_MAX_EMBED_CHARACTERS, EmbedColor, Emoji
from valentina.models import Campaign
from valentina.models.bot import ValentinaContext
from valentina.utils.helpers import num_to_circles


class CampaignViewer:
    """Manage and display interactive views of a campaign in a Discord context.

    This class provides an interface for creating and managing different views (pages) of a campaign, such as home, notes, NPCs, and chapters. It utilizes embeds and pagination to present information in an organized and user-friendly manner.

    Attributes:
        ctx (ValentinaContext): The context of the Discord command invoking this viewer.
        campaign (Campaign): The campaign object to be displayed.
        max_chars (int): Maximum character limit for text in a single embed.
    """

    def __init__(
        self, ctx: ValentinaContext, campaign: Campaign, max_chars: int = ABS_MAX_EMBED_CHARACTERS
    ) -> None:
        self.ctx: ValentinaContext = ctx
        self.campaign: Campaign = campaign
        self.max_chars: int = max_chars

    async def _get_pages(self) -> list[pages.PageGroup]:
        """Compile all relevant pages for the campaign view.

        Gather and create page groups for various sections of the campaign like home, notes, NPCs, and chapters, ensuring inclusion of only sections with content.

        Returns:
            list[pages.PageGroup]: A list of PageGroup objects, each representing a different section of the campaign.
        """
        pages = [await self._home_page()]

        if len(self.campaign.notes) > 0:
            pages.append(await self._notes_pages())

        if len(self.campaign.npcs) > 0:
            pages.append(await self._npc_pages())

        if len(self.campaign.books) > 0:
            pages.extend(await self._book_pages())

        return pages

    async def _home_page(self) -> pages.PageGroup:
        """Construct the home page view of the campaign.

        Build the home page embed summarizing key campaign information, including description, number of books, NPCs, and notes, with proper formatting and styling for presentation.

        Returns:
            pages.PageGroup: A PageGroup object representing the home view of the campaign.
        """
        campaign_description = (
            f"### Description\n{self.campaign.description}" if self.campaign.description else ""
        )

        description = f"""\
# {self.campaign.name}
{campaign_description}
### Details
```scala
{Emoji.DESPERATION.value} Desperation : {num_to_circles(self.campaign.desperation)}
{Emoji.DANGER.value} Danger      : {num_to_circles(self.campaign.danger)}
```
```scala
Created  : {self.campaign.date_created.strftime("%Y-%M-%d")}
Modified : {self.campaign.date_modified.strftime("%Y-%M-%d")}
Books    : {len(self.campaign.books)}
NPCs     : {len(self.campaign.npcs)}
Notes    : {len(self.campaign.notes)}
```
"""

        home_embed = discord.Embed(
            title="",
            description=description,
            color=EmbedColor.DEFAULT.value,
        )
        home_embed.set_author(name="Campaign Overview")
        home_embed.set_footer(text="Navigate Sections with the Dropdown Menu")

        return pages.PageGroup(
            pages=[pages.Page(embeds=[home_embed])],
            label="home",
            description="Campaign Overview",
            use_default_buttons=False,
            emoji="🏠",
        )

    async def _notes_pages(self) -> pages.PageGroup:
        """Generate pages for the campaign's notes section.

        Create multiple pages to display the campaign's notes, formatting each note in a separate embed. Implement pagination for notes that exceed the embed character limit.

        Returns:
            pages.PageGroup: A PageGroup object containing the notes section of the campaign.
        """
        note_list = sorted(self.campaign.notes, key=lambda n: n.name)
        note_text = "\n\n".join([f"{n.campaign_display()}" for n in note_list])
        lines = textwrap.wrap(
            note_text,
            self.max_chars,
            break_long_words=False,
            replace_whitespace=False,
        )
        embeds = []
        for line in lines:
            embed = discord.Embed(
                title=f"{self.campaign.name} Notes",
                description=line,
                color=EmbedColor.DEFAULT.value,
            )
            embeds.append(embed)

        buttons = []
        if len(embeds) > 1:
            buttons.extend(
                [
                    pages.PaginatorButton(
                        "prev", label="←", style=discord.ButtonStyle.green, disabled=True
                    ),
                    pages.PaginatorButton(
                        "page_indicator", style=discord.ButtonStyle.gray, disabled=True
                    ),
                    pages.PaginatorButton(
                        "next", label="→", style=discord.ButtonStyle.green, disabled=False
                    ),
                ]
            )

        return pages.PageGroup(
            pages=[pages.Page(embeds=[embed]) for embed in embeds],
            label="Campaign Notes",
            description=f"{len(note_list)} Notes",
            custom_buttons=buttons,
            show_disabled=len(embeds) > 1,
            show_indicator=len(embeds) > 1,
            loop_pages=False,
            emoji="📝",
        )

    async def _npc_pages(self) -> pages.PageGroup:
        """Produce the NPC section pages of the campaign.

        Construct pages to showcase the campaign's non-player characters (NPCs). Format each NPC in an embed and use pagination for content exceeding the character limit.

        Returns:
            pages.PageGroup: A PageGroup object containing the NPC section of the campaign.
        """
        npc_list = sorted(self.campaign.npcs, key=lambda n: n.name)
        npc_text = "\n\n".join([f"{n.campaign_display()}" for n in npc_list])
        lines = textwrap.wrap(
            npc_text,
            self.max_chars,
            break_long_words=False,
            replace_whitespace=False,
        )
        embeds = []
        for line in lines:
            embed = discord.Embed(
                title=f"{self.campaign.name} NPCs",
                description=line,
                color=EmbedColor.DEFAULT.value,
            )
            embeds.append(embed)

        buttons = []
        if len(embeds) > 1:
            buttons.extend(
                [
                    pages.PaginatorButton(
                        "prev", label="←", style=discord.ButtonStyle.green, disabled=True
                    ),
                    pages.PaginatorButton(
                        "page_indicator", style=discord.ButtonStyle.gray, disabled=True
                    ),
                    pages.PaginatorButton(
                        "next", label="→", style=discord.ButtonStyle.green, disabled=False
                    ),
                ]
            )

        return pages.PageGroup(
            pages=[pages.Page(embeds=[embed]) for embed in embeds],
            label="Non Player Characters",
            description=f"{len(npc_list)} NPCs",
            custom_buttons=buttons,
            show_disabled=len(embeds) > 1,
            show_indicator=len(embeds) > 1,
            loop_pages=False,
            emoji="👥",
        )

    async def _book_pages(self) -> list[pages.PageGroup]:
        """Assemble pages for the campaign's books.

        Create a series of pages, one for each book in the campaign. Present books in individual embeds, using pagination for extensive descriptions.

        Returns:
            list[pages.PageGroup]: A list of PageGroup objects, each signifying a book in the campaign.
        """
        book_pages = []

        for book in sorted(await self.campaign.fetch_books(), key=lambda b: b.number):
            chapters = await book.fetch_chapters()
            book_chapter_text = "### Chapters\n"
            book_chapter_text += "\n".join([f"{c.number}. {c.name}" for c in chapters])

            description_text = (
                f"{book_chapter_text}\n### Description\n{book.description_long}"
                if chapters
                else f"### Description\n{book.description_long}"
            )

            lines = textwrap.wrap(
                description_text,
                self.max_chars,
                break_long_words=False,
                replace_whitespace=False,
            )
            embeds = []
            for line in lines:
                embed = discord.Embed(
                    title="",
                    description=f"## Book #{book.number}: {book.name}\n" + line,
                    color=EmbedColor.DEFAULT.value,
                )
                embeds.append(embed)

            book_page = pages.PageGroup(
                pages=[pages.Page(embeds=[embed]) for embed in embeds],
                label=f"{book.name}",
                description=f"Book #{book.number}",
                custom_buttons=[
                    pages.PaginatorButton("prev", label="←", style=discord.ButtonStyle.green),
                    pages.PaginatorButton(
                        "page_indicator", style=discord.ButtonStyle.gray, disabled=True
                    ),
                    pages.PaginatorButton("next", label="→", style=discord.ButtonStyle.green),
                ],
                show_disabled=True,
                show_indicator=True,
                loop_pages=False,
                emoji="📖",
            )
            book_pages.append(book_page)

        return book_pages

    async def display(self) -> pages.Paginator:
        """Display the campaign in a Discord paginator.

        Construct a Paginator object that encompasses all pages of the campaign, enabling interactive navigation through the campaign sections in Discord.

        Returns:
            pages.Paginator: A Paginator object for navigating the campaign's views.
        """
        return pages.Paginator(
            pages=await self._get_pages(),
            show_menu=True,
            menu_placeholder="Campaign viewer",
            show_disabled=False,
            show_indicator=False,
            use_default_buttons=False,
            custom_buttons=[],
        )
