"""View character."""

from typing import ClassVar, assert_never

from flask_discord import requires_authorization
from quart import abort, request, session, url_for
from quart.views import MethodView

from valentina.constants import DiceType, HTTPStatus
from valentina.controllers import CharacterSheetBuilder
from valentina.models import (
    AWSService,
    Campaign,
    Character,
    Statistics,
    User,
)
from valentina.webui import catalog
from valentina.webui.constants import CharacterEditableInfo, CharacterViewTab, TableType, TextType
from valentina.webui.utils import fetch_active_campaign, fetch_user, is_storyteller
from valentina.webui.utils.forms import ValentinaForm

gameplay_form = ValentinaForm()


class CharacterView(MethodView):
    """View to handle character operations."""

    decorators: ClassVar = [requires_authorization]

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

    async def _get_character_image_urls(
        self, character: Character
    ) -> list[str]:  # pragma: no cover
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

    async def _get_campaign_experience(
        self, character: Character, user: User, campaign: Campaign
    ) -> int:
        """Retrieve and return the character's campaign experience."""
        # Only users who own a character should be able to upgrade the character with their experience points.  In addition, storyteller characters do not require experience points to upgrade.
        session_user = await fetch_user()
        if int(session_user.id) != int(character.user_owner) or character.type_storyteller:
            return 0

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
        match CharacterViewTab.get_member_by_value(request.args.get("tab", None)):
            case CharacterViewTab.SHEET:
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
            case CharacterViewTab.BIOGRAPHY:
                return catalog.render(
                    "character_view.Biography",
                    character=character,
                    text_type_bio=TextType.BIOGRAPHY,
                    can_edit=session["IS_STORYTELLER"]
                    or session["USER_ID"] == character.user_owner,
                )
            case CharacterViewTab.INFO:
                return catalog.render(
                    "character_view.Info",
                    character=character,
                    CharacterEditableInfo=CharacterEditableInfo,
                    table_type_note=TableType.NOTE,
                    table_type_inventory=TableType.INVENTORYITEM,
                )

            case CharacterViewTab.IMAGES:  # pragma: no cover
                return catalog.render(
                    "character_view.Images",
                    character=character,
                    images=await self._get_character_image_urls(character),
                )
            case CharacterViewTab.STATISTICS:
                stats_engine = Statistics(guild_id=session["GUILD_ID"])

                return catalog.render(
                    "character_view.Statistics",
                    character=character,
                    statistics=await stats_engine.character_statistics(character, as_json=True),
                )
            case _:  # pragma: no cover
                assert_never()

    async def get(self, character_id: str = "") -> str:
        """Handle GET requests."""
        character = await self._get_character_object(character_id)
        character_owner = await User.get(character.user_owner, fetch_links=False)
        campaign = await fetch_active_campaign(campaign_id=character.campaign)

        if request.headers.get("HX-Request") and request.args.get("tab"):
            return await self._handle_tabs(character, character_owner=character_owner)

        sheet_builder = CharacterSheetBuilder(character=character)
        sheet_data = sheet_builder.fetch_sheet_character_traits(show_zeros=False)
        user_is_storyteller = await is_storyteller()
        profile_data = await sheet_builder.fetch_sheet_profile(storyteller_view=user_is_storyteller)

        # We want to link to the user profile from the character view so we add the link here
        if owner_name := profile_data.get("Owner"):
            profile_data["Owner"] = (
                f" <a href='{url_for('user_profile.view', user_id=character_owner.id)}'>{owner_name}</a>"
            )

        return catalog.render(
            "character_view.Main",
            character=character,
            profile_data=profile_data,
            tabs=CharacterViewTab,
            sheet_data=sheet_data,
            character_owner=character_owner,
            campaign_experience=await self._get_campaign_experience(
                character, character_owner, campaign
            ),
            campaign=campaign,
            dice_sizes=[member.value for member in DiceType],
            form=gameplay_form,
            error_msg=request.args.get("error_msg", ""),
            success_msg=request.args.get("success_msg", ""),
            info_msg=request.args.get("info_msg", ""),
            warning_msg=request.args.get("warning_msg", ""),
            CharacterEditableInfo=CharacterEditableInfo,
        )
