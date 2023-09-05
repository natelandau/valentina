"""A paginated view of all the thumbnails in the database."""

import discord
from discord.ext import pages
from discord.ui import Button
from loguru import logger

from valentina.constants import EmbedColor
from valentina.models.db_tables import Character


class DeleteS3Images(discord.ui.View):
    """A view for deleting S3 Images."""

    def __init__(
        self, ctx: discord.ApplicationContext, key: str, url: str, review_type: str
    ) -> None:
        super().__init__()
        self.ctx = ctx
        self.key = key
        self.url = url
        self.review_type = review_type

    @discord.ui.button(
        label="⚠️ Delete image", style=discord.ButtonStyle.danger, custom_id="delete", row=1
    )
    async def confirm_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the confirm button."""
        button.label = "✅ Image deleted"
        button.style = discord.ButtonStyle.secondary
        button.disabled = True

        for child in self.children:
            if type(child) == Button:
                child.disabled = True
            if type(child) == discord.ui.Select:
                child.disabled = True

        # Delete from database
        if self.review_type == "character":
            # Delete the image from the character's data
            character_id = self.key.split("/")[-2]
            character = Character.get_by_id(character_id)
            self.ctx.bot.char_svc.delete_character_image(  # type: ignore [attr-defined]
                self.ctx, character=character, key=self.key
            )

        # Log to audit log
        await self.ctx.bot.guild_svc.send_to_audit_log(  # type: ignore [attr-defined]
            self.ctx, f"Delete image from {character.name}"
        )

        # Respond to user
        await interaction.response.edit_message(
            embed=discord.Embed(
                title=f"Delete image id `{self.key}`", color=EmbedColor.SUCCESS.value
            ),
            view=None,
        )  # view=None removes all buttons
        self.stop()

    @discord.ui.button(
        label="✅ Complete Review", style=discord.ButtonStyle.primary, custom_id="done", row=1
    )
    async def done_callback(
        self, button: Button, interaction: discord.Interaction  # noqa: ARG002
    ) -> None:
        """Callback for the re-roll button."""
        await interaction.response.edit_message(
            embed=discord.Embed(title="Done reviewing images", color=EmbedColor.INFO.value),
            view=None,
        )  # view=None remove all buttons
        self.stop()


class S3ImageReview:
    """A paginated view of all the images in S3 matching a key prefix."""

    def __init__(
        self, ctx: discord.ApplicationContext, prefix: str, review_type: str, hidden: bool = True
    ) -> None:
        """Initialize the thumbnail review.

        Args:
            ctx (discord.ApplicationContext): The application context.
            prefix (str): The prefix to match in S3.
            review_type (str): The type of review being performed (character, campaign, etc.)
            hidden (bool, optional): Whether or not the paginator should be hidden. Defaults to True.
        """
        self.ctx = ctx
        self.prefix = prefix
        self.review_type = review_type
        self.images = self._get_images()
        self.hidden = hidden

    def _get_images(self) -> dict[str, str]:
        """Retrieve all the images in the database that match the specified prefix.

        This function queries the AWS service to list all objects with the given prefix and then fetches their URLs.
        It returns a dictionary where the keys are thumbnail IDs and the values are corresponding URLs.

        Returns:
            Dict[str, str]: A dictionary mapping thumbnail IDs to their URLs.

        Raises:
            Any exceptions raised by the AWS service will propagate up.
        """
        try:
            # Use dictionary comprehension to build the images dictionary
            return {x: self.ctx.bot.aws_svc.get_url(x) for x in self.ctx.bot.aws_svc.list_objects(self.prefix)}  # type: ignore [attr-defined]
        except Exception as e:
            logger.error(f"An error occurred while fetching image URLs: {e}")
            raise

    async def _get_embed(self, image_name: str, url: str) -> discord.Embed:
        """Get an embed for an image."""
        embed = discord.Embed(title=image_name, color=EmbedColor.DEFAULT.value)
        embed.set_image(url=url)
        return embed

    async def _build_pages(self) -> list[pages.Page]:
        """Build the pages for the paginator. Create an embed for each thumbnail and add it to a single page paginator with a custom view allowing it to be deleted/categorized.  Then return a list of all the paginators."""
        pages_to_send: list[pages.Page] = []

        for key, url in self.images.items():
            image_name = key.split("/")[-1]

            view = DeleteS3Images(ctx=self.ctx, key=key, url=url, review_type=self.review_type)

            embed = await self._get_embed(image_name, url)

            pages_to_send.append(
                pages.Page(
                    embeds=[embed],
                    label=f"Image: {image_name}",
                    description="Use the buttons below to delete this image",
                    use_default_buttons=False,
                    custom_view=view,
                )
            )

        return pages_to_send

    async def send(self, ctx: discord.ApplicationContext) -> None:
        """Send the paginator."""
        if not self.images:
            await self.ctx.respond(
                embed=discord.Embed(
                    title="No images to review",
                    color=EmbedColor.INFO.value,
                ),
                ephemeral=self.hidden,
            )
            return

        paginators = await self._build_pages()

        paginator = pages.Paginator(pages=paginators, show_menu=False, disable_on_timeout=True)
        paginator.remove_button("first")
        paginator.remove_button("last")
        await paginator.respond(ctx.interaction, ephemeral=self.hidden)
