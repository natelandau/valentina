"""A paginated view of all the thumbnails in the database."""

import discord
from discord.ext import pages
from discord.ui import Button

from valentina.constants import EmbedColor, Emoji, RollResultType
from valentina.discord.bot import ValentinaContext
from valentina.models import Guild, GuildRollResultThumbnail


class DeleteOrCategorizeThumbnails(discord.ui.View):
    """A view for deleting or categorizing a roll result thumbnails."""

    def __init__(
        self, ctx: ValentinaContext, guild: Guild, index: int, thumbnail: GuildRollResultThumbnail
    ) -> None:
        super().__init__()
        self.ctx = ctx
        self.guild = guild
        self.index = index
        self.thumbnail = thumbnail

    def _disable_all(self) -> None:
        """Disable all buttons in the view."""
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

    @discord.ui.button(
        label=f"{Emoji.WARNING.value} Delete thumbnail",
        style=discord.ButtonStyle.danger,
        custom_id="delete",
        row=1,
    )
    async def confirm_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the confirm button."""
        button.label = f"{Emoji.YES.value} Deleted Thumbnail"
        button.style = discord.ButtonStyle.secondary
        self._disable_all()

        # Delete from database
        self.guild.roll_result_thumbnails.pop(self.index)
        await self.guild.save()

        # Log to audit log
        await self.ctx.post_to_audit_log(f"Delete thumbnail `{self.index}`\n{self.thumbnail.url}")

        # Respond to user
        await interaction.response.edit_message(
            embed=discord.Embed(
                title=f"Deleted thumbnail id `{self.index}`", color=EmbedColor.SUCCESS.value
            ).set_thumbnail(url=self.thumbnail.url),
            view=None,
        )  # view=None removes all buttons
        self.stop()

    @discord.ui.button(
        label=f"{Emoji.YES.value} Complete Review",
        style=discord.ButtonStyle.primary,
        custom_id="done",
        row=1,
    )
    async def done_callback(
        self,
        button: Button,  # noqa: ARG002
        interaction: discord.Interaction,
    ) -> None:
        """Callback for the re-roll button."""
        await interaction.response.edit_message(
            embed=discord.Embed(title="Done reviewing thumbnails", color=EmbedColor.INFO.value),
            view=None,
        )  # view=None remove all buttons
        self.stop()

    @discord.ui.select(
        placeholder="Move to a different roll result type",
        custom_id="category",
        row=2,
        min_values=1,
        max_values=1,
        options=[discord.SelectOption(label=x.name.title(), value=x.name) for x in RollResultType],
    )
    async def select_callback(self, select, interaction: discord.Interaction) -> None:  # type: ignore [no-untyped-def]
        """Callback for the select menu."""
        # Update the thumbnail in the database
        new_cat = select.values[0]

        self.thumbnail.roll_type = RollResultType[new_cat]
        self.guild.roll_result_thumbnails[self.index] = self.thumbnail
        await self.guild.save()

        # Log to audit log
        await self.ctx.post_to_audit_log(
            f"Thumbnail `{self.index}` categorized to {new_cat} \n{self.thumbnail.url}",
        )

        # Respond to user
        await interaction.response.edit_message(
            embed=discord.Embed(
                title=f"Thumbnail id `{self.index}` categorized to {new_cat} \n",
                color=EmbedColor.SUCCESS.value,
            ).set_thumbnail(url=self.thumbnail.url),
            view=None,
        )
        self.stop()


class ThumbnailReview:
    """A paginated view of all the thumbnails in the database."""

    def __init__(self, ctx: ValentinaContext, guild: Guild, roll_type: RollResultType) -> None:
        """Initialize the thumbnail review."""
        self.ctx = ctx
        self.guild = guild
        self.roll_type = roll_type
        self.thumbnails = self._get_thumbnails()

    def _get_thumbnails(self) -> dict[int, GuildRollResultThumbnail]:
        """Get all the thumbnails in the database.

        Return:
            A dictionary of thumbnail indexes and GuildRollResultThumbnail.
        """
        filtered_thumbs = {}
        original_index = 0

        for thumbnail in self.guild.roll_result_thumbnails:
            if thumbnail.roll_type == self.roll_type:
                filtered_thumbs[original_index] = thumbnail

            original_index += 1  # noqa: SIM113

        return filtered_thumbs

    @staticmethod
    async def _get_embed(index: int, url: str) -> discord.Embed:
        """Get an embed for a thumbnail."""
        embed = discord.Embed(title=f"Thumbnail id `{index}`", color=EmbedColor.DEFAULT.value)
        embed.set_image(url=url)
        return embed

    async def _build_pages(self) -> list[pages.Page]:
        """Build the pages for the paginator. Create an embed for each thumbnail and add it to a single page paginator with a custom view allowing it to be deleted/categorized.  Then return a list of all the paginators."""
        pages_to_send: list[pages.Page] = []

        for index, thumbnail in self.thumbnails.items():
            view = DeleteOrCategorizeThumbnails(
                ctx=self.ctx, guild=self.guild, index=index, thumbnail=thumbnail
            )

            embed = await self._get_embed(index, thumbnail.url)

            pages_to_send.append(
                pages.Page(
                    embeds=[embed],
                    label=f"Index: {index}",
                    description="Pages for Things",
                    use_default_buttons=False,
                    custom_view=view,
                )
            )

        return pages_to_send

    async def send(self, ctx: ValentinaContext) -> None:
        """Send the paginator."""
        if not self.thumbnails:
            await self.ctx.respond(
                embed=discord.Embed(
                    title=f"No thumbnails to review for result type {self.roll_type.name}",
                    color=EmbedColor.INFO.value,
                ),
                ephemeral=True,
            )
            return

        paginators = await self._build_pages()

        paginator = pages.Paginator(pages=paginators, show_menu=False, disable_on_timeout=True)
        paginator.remove_button("first")
        paginator.remove_button("last")
        await paginator.respond(ctx.interaction, ephemeral=True)
