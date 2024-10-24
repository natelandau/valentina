"""View character."""

from typing import ClassVar

from flask_discord import requires_authorization
from quart import abort, request, session
from quart.views import MethodView

from valentina.constants import (
    HTTPStatus,
    InventoryItemType,
)
from valentina.controllers import CharacterSheetBuilder
from valentina.models import (
    AWSService,
    Campaign,
    Character,
    InventoryItem,
    Statistics,
    User,
)
from valentina.webui import catalog
from valentina.webui.utils import fetch_user, is_storyteller


class CharacterView(MethodView):
    """View to handle character operations."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self) -> None:
        self.session = session  # Assuming session is defined globally or passed in some way

    async def _get_character_object(self, character_id: str) -> Character:
        """Get a character db object by ID.

        Args:
            character_id (str): The character ID to fetch.

        Returns:
            Character: The character object.
        """
        try:
            character = await Character.get(character_id, fetch_links=True)
        except ValueError:
            abort(HTTPStatus.BAD_REQUEST.value)

        if not character:
            abort(HTTPStatus.BAD_REQUEST.value)

        return character

    async def _get_character_inventory(self, character: Character) -> dict:
        """Retrieve and return the character's inventory organized by item type.

        Fetch the inventory items associated with the specified character from the
        database, grouping them by their item type. Empty item type groups are
        removed from the final inventory dictionary.

        Args:
            character (Character): The character whose inventory is to be retrieved.

        Returns:
            dict: A dictionary where the keys are item types and the values are lists
                of `InventoryItem` objects. Empty item type groups are excluded.
        """
        inventory: dict[str, list[InventoryItem]] = {}
        for x in InventoryItemType:
            inventory[x.name] = []

        for item in await InventoryItem.find(
            InventoryItem.character == str(character.id)
        ).to_list():
            inventory[item.type].append(item)

        # remove all empty dictionary entries
        return {k: v for k, v in inventory.items() if v}

    async def _get_character_image_urls(self, character: Character) -> list[str]:
        """Retrieve and return a list of image URLs for the specified character.

        Fetch the URLs of the character's images stored in AWS by utilizing the
        AWS service.

        Args:
            character (Character): The character whose image URLs are to be retrieved.

        Returns:
            list[str]: A list of URLs corresponding to the character's images.
        """
        aws_svc = AWSService()

        return [aws_svc.get_url(x) for x in character.images]

    async def _get_campaign_experience(self, character: Character, user: User) -> int:
        """Retrieve and return the character's campaign experience."""
        # Only users who own a character should be able to upgrade the character with their experience points.  In addition, storyteller characters do not require experience points to upgrade.
        session_user = await fetch_user()
        if int(session_user.id) != int(character.user_owner) or character.type_storyteller:
            return 0

        campaign = await Campaign.get(character.campaign)
        campaign_experience, _, _ = user.fetch_campaign_xp(campaign)
        return campaign_experience

    async def _handle_tabs(self, character: Character, character_owner: User) -> str:
        """Handle HTMX tab requests and render the appropriate content.

        Based on the "tab" query parameter, render and return the corresponding section of the character view, such as the character sheet, inventory, profile, images, or statistics. If the requested tab is not recognized, return a 404 error.

        Args:
            character (Character): The character for which the tab content is to be rendered.
            character_owner (User): The owner of the character.

        Returns:
            str: The rendered HTML content for the selected tab.

        Raises:
            404: If the requested tab is not recognized.
        """
        if request.args.get("tab") == "sheet":
            sheet_builder = CharacterSheetBuilder(character=character)
            sheet_data = sheet_builder.fetch_sheet_character_traits(show_zeros=False)
            storyteller_data = await is_storyteller()
            profile_data = await sheet_builder.fetch_sheet_profile(
                storyteller_view=storyteller_data
            )
            return catalog.render(
                "character_view.Sheet",
                character=character,
                sheet_data=sheet_data,
                profile_data=profile_data,
                character_owner=character_owner,
            )

        if request.args.get("tab") == "inventory":
            return catalog.render(
                "character_view.Inventory",
                character=character,
                inventory=await self._get_character_inventory(character),
            )

        if request.args.get("tab") == "profile":
            return catalog.render("character_view.profile", character=character)

        if request.args.get("tab") == "images":
            return catalog.render(
                "character_view.Images",
                character=character,
                images=await self._get_character_image_urls(character),
            )

        if request.args.get("tab") == "statistics":
            stats_engine = Statistics(guild_id=session["GUILD_ID"])

            return catalog.render(
                "character_view.Statistics",
                character=character,
                statistics=await stats_engine.character_statistics(character, as_json=True),
            )

        return abort(HTTPStatus.NOT_FOUND.value)

    async def get(self, character_id: str = "") -> str:
        """Handle GET requests."""
        character = await self._get_character_object(character_id)
        character_owner = await User.get(character.user_owner, fetch_links=False)

        if request.headers.get("HX-Request"):
            return await self._handle_tabs(character, character_owner=character_owner)

        sheet_builder = CharacterSheetBuilder(character=character)
        sheet_data = sheet_builder.fetch_sheet_character_traits(show_zeros=False)
        user_is_storyteller = await is_storyteller()
        profile_data = await sheet_builder.fetch_sheet_profile(storyteller_view=user_is_storyteller)

        return catalog.render(
            "character_view.Main",
            character=character,
            profile_data=profile_data,
            sheet_data=sheet_data,
            character_owner=character_owner,
            campaign_experience=await self._get_campaign_experience(character, character_owner),
            error_msg=request.args.get("error_msg", ""),
            success_msg=request.args.get("success_msg", ""),
            info_msg=request.args.get("info_msg", ""),
            warning_msg=request.args.get("warning_msg", ""),
        )
