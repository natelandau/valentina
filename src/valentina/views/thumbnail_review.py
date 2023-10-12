"""A paginated view of all the thumbnails in the database."""

import discord
from discord.ext import pages
from discord.ui import Button

from valentina.constants import ChannelPermission, EmbedColor, Emoji, RollResultType
from valentina.models.db_tables import RollThumbnail


class DeleteOrCategorizeThumbnails(discord.ui.View):
    """A view for deleting or categorizing a roll result thumbnails."""

    def __init__(
        self, ctx: discord.ApplicationContext, thumbnail_id: int, thumbnail_url: str
    ) -> None:
        super().__init__()
        self.ctx = ctx
        self.thumbnail_id = thumbnail_id
        self.thumbnail_url = thumbnail_url

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
        RollThumbnail.delete_by_id(self.thumbnail_id)
        self.ctx.bot.guild_svc.purge_cache(self.ctx)  # type: ignore [attr-defined]

        # Log to audit log
        await self.ctx.bot.guild_svc.send_to_audit_log(  # type: ignore [attr-defined]
            self.ctx, f"Deleted thumbnail id `{self.thumbnail_id}`\n{self.thumbnail_url}"
        )

        # Respond to user
        await interaction.response.edit_message(
            embed=discord.Embed(
                title=f"Deleted thumbnail id `{self.thumbnail_id}`", color=EmbedColor.SUCCESS.value
            ).set_thumbnail(url=self.thumbnail_url),
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
        self, button: Button, interaction: discord.Interaction  # noqa: ARG002
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
        options=[discord.SelectOption(label=x.name, value=x.name) for x in RollResultType],
    )
    async def select_callback(self, select, interaction: discord.Interaction) -> None:  # type: ignore [no-untyped-def]
        """Callback for the select menu."""
        # Update the thumbnail in the database
        RollThumbnail.set_by_id(self.thumbnail_id, {"roll_type": select.values[0]})
        self.ctx.bot.guild_svc.purge_cache(self.ctx)  # type: ignore [attr-defined]

        # Log to audit log
        await self.ctx.bot.guild_svc.send_to_audit_log(  # type: ignore [attr-defined]
            self.ctx,
            f"Thumbnail id `{self.thumbnail_id}` categorized to {select.values[0]} \n{self.thumbnail_url}",
        )

        # Respond to user
        await interaction.response.edit_message(
            embed=discord.Embed(
                title=f"Thumbnail id `{self.thumbnail_id}` categorized to {select.values[0]} \n",
                color=EmbedColor.SUCCESS.value,
            ).set_thumbnail(url=self.thumbnail_url),
            view=None,
        )
        self.stop()


class ThumbnailReview:
    """A paginated view of all the thumbnails in the database."""

    def __init__(self, ctx: discord.ApplicationContext, roll_type: ChannelPermission) -> None:
        """Initialize the thumbnail review."""
        self.ctx = ctx
        self.roll_type = roll_type
        self.thumbnails = self._get_thumbnails()

    def _get_thumbnails(self) -> dict[int, str]:
        """Get all the thumbnails in the database.

        Return:
            A dictionary of thumbnail IDs and URLs.
        """
        return {
            x.id: x.url
            for x in RollThumbnail.select().where(
                (RollThumbnail.roll_type == self.roll_type.name)
                & (RollThumbnail.guild == self.ctx.guild.id)
            )
        }

    @staticmethod
    async def _get_embed(db_id: int, url: str) -> discord.Embed:
        """Get an embed for a thumbnail."""
        embed = discord.Embed(title=f"Thumbnail id `{db_id}`", color=EmbedColor.DEFAULT.value)
        embed.set_image(url=url)
        return embed

    async def _build_pages(self) -> list[pages.Page]:
        """Build the pages for the paginator. Create an embed for each thumbnail and add it to a single page paginator with a custom view allowing it to be deleted/categorized.  Then return a list of all the paginators."""
        pages_to_send: list[pages.Page] = []

        for db_id, url in self.thumbnails.items():
            view = DeleteOrCategorizeThumbnails(ctx=self.ctx, thumbnail_id=db_id, thumbnail_url=url)

            embed = await self._get_embed(db_id, url)

            pages_to_send.append(
                pages.Page(
                    embeds=[embed],
                    label=f"Database Id: {db_id}",
                    description="Pages for Things",
                    use_default_buttons=False,
                    custom_view=view,
                )
            )

        return pages_to_send

    async def send(self, ctx: discord.ApplicationContext) -> None:
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
