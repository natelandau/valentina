"""A paginated view of all the thumbnails in the database."""

import re

import discord
from discord.ext import pages
from discord.ui import Button
from loguru import logger

from valentina.constants import EmbedColor, Emoji
from valentina.models import AWSService, Character
from valentina.models.bot import ValentinaContext


class DeleteS3Images(discord.ui.View):
    """A view for deleting S3 Images."""

    def __init__(self, ctx: ValentinaContext, key: str, url: str) -> None:
        super().__init__()
        self.ctx = ctx
        self.key = key
        self.url = url

    def _disable_all(self) -> None:
        """Disable all buttons in the view."""
        for child in self.children:
            if isinstance(child, Button | discord.ui.Select):
                child.disabled = True

    @discord.ui.button(
        label=f"{Emoji.WARNING.value} Delete image",
        style=discord.ButtonStyle.danger,
        custom_id="delete",
        row=1,
    )
    async def confirm_callback(self, button: Button, interaction: discord.Interaction) -> None:
        """Callback for the confirm button."""
        button.label = f"{Emoji.SUCCESS.value} Image deleted"
        button.style = discord.ButtonStyle.secondary
        self._disable_all()

        # If a character image, delete it from character.images
        char_id = re.search(r"characters?\/(.*)\/", self.key)
        if char_id:
            character = await Character.get(char_id.group(1))
            await character.delete_image(self.key)
            await self.ctx.post_to_audit_log(f"Delete image from {character.name}")

        # Respond to user
        await interaction.response.edit_message(
            embed=discord.Embed(
                title=f"Delete image id `{self.key}`", color=EmbedColor.SUCCESS.value
            ),
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
            embed=discord.Embed(title="Done reviewing images", color=EmbedColor.INFO.value),
            view=None,
        )  # view=None remove all buttons
        self.stop()


class S3ImageReview:
    """A paginated view of all the images in S3 matching a key prefix."""

    def __init__(
        self,
        ctx: ValentinaContext,
        prefix: str,
        known_images: list[str] = [],
        hidden: bool = True,
    ) -> None:
        """Initialize the thumbnail review.

        Args:
            ctx (ValentinaContext): The application context.
            prefix (str): The prefix to match in S3.
            known_images (list[str]): A list of known images to include in the review.
            review_type (str): The type of review being performed (character, campaign, etc.)
            hidden (bool, optional): Whether or not the paginator should be hidden. Defaults to True.
        """
        self.aws_svc = AWSService()
        self.ctx = ctx
        self.prefix = prefix
        self.known_images = {x: self.aws_svc.get_url(x) for x in known_images}
        self.images_by_prefix = self._get_images_by_prefix()
        self.images = self.images_by_prefix | self.known_images
        self.hidden = hidden

    def _get_images_by_prefix(self) -> dict[str, str]:
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
            return {
                x: self.aws_svc.get_url(x)
                for x in self.aws_svc.list_objects(self.prefix)
                if x not in self.known_images
            }
        except Exception as e:
            logger.error(f"An error occurred while fetching image URLs: {e}")
            raise

    @staticmethod
    async def _get_embed(image_name: str, url: str) -> discord.Embed:
        """Get an embed for an image."""
        embed = discord.Embed(title=image_name, color=EmbedColor.DEFAULT.value)
        embed.set_image(url=url)
        return embed

    async def _build_pages(self) -> list[pages.Page]:
        """Build the pages for the paginator. Create an embed for each thumbnail and add it to a single page paginator with a custom view allowing it to be deleted/categorized.  Then return a list of all the paginators."""
        pages_to_send: list[pages.Page] = []

        for key, url in self.images.items():
            image_name = key.split("/")[-1]

            view = DeleteS3Images(ctx=self.ctx, key=key, url=url)

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

    async def send(self, ctx: ValentinaContext) -> None:
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
