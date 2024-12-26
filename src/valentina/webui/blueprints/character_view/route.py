"""View character."""

from typing import ClassVar, assert_never

from flask_discord import requires_authorization
from quart import abort, redirect, request, session, url_for
from quart.utils import run_sync
from quart.views import MethodView
from werkzeug.wrappers.response import Response

from valentina.constants import DiceType, HTTPStatus
from valentina.controllers import CharacterSheetBuilder
from valentina.models import Campaign, Character, Statistics, User
from valentina.webui import catalog
from valentina.webui.constants import CharacterEditableInfo, CharacterViewTab, TableType, TextType
from valentina.webui.utils import fetch_active_campaign, fetch_user, is_storyteller, link_terms
from valentina.webui.utils.forms import ValentinaForm

gameplay_form = ValentinaForm()


class CharacterView(MethodView):
    """Handle character viewing and modification operations.

    Provides endpoints for viewing and modifying character details including:
        - Basic character information
        - Experience points and leveling
        - Character sheet data
        - Character images
        - Character notes and inventory

    Returns:
        MethodView: Flask view class handling character-related HTTP endpoints

    Raises:
        HTTPException: If character not found or user lacks permissions
    """

    decorators: ClassVar = [requires_authorization]

    async def _get_character_object(self, character_id: str) -> Character:
        """Fetch and return a character object from the database by its ID.

        Retrieve a character from the database using the provided ID and fetch all linked
        relationships. Validate the ID format and character existence.

        Args:
            character_id (str): Unique identifier of the character to fetch

        Returns:
            Character: Character object with all relationships loaded

        Raises:
            HTTPException: If character_id is invalid (400)
            HTTPException: If character not found (400)
        """
        try:
            character = await Character.get(character_id, fetch_links=True)
        except ValueError:
            abort(HTTPStatus.BAD_REQUEST.value)

        if not character:
            abort(HTTPStatus.BAD_REQUEST.value)

        return character

    async def _get_campaign_experience(
        self, character: Character, user: User, campaign: Campaign
    ) -> int:
        """Get campaign experience points for a character.

        Calculate and return the experience points available to a character in a specific campaign.
        Only return points if the session user owns the character and the character is not a
        storyteller character.

        Args:
            character (Character): Character to get experience for
            user (User): User who owns the character
            campaign (Campaign): Campaign to get experience from

        Returns:
            int: Experience points available to the character in the campaign. Returns 0 if:
                - Session user does not own the character
                - Character is a storyteller character
        """
        # Only users who own a character should be able to upgrade the character with their experience points.  In addition, storyteller characters do not require experience points to upgrade.
        session_user = await fetch_user()
        if int(session_user.id) != int(character.user_owner) or character.type_storyteller:
            return 0

        campaign_experience, _, _ = user.fetch_campaign_xp(campaign)
        return campaign_experience

    async def _handle_tabs(self, character: Character, character_owner: User) -> str | Response:
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

                result = await run_sync(
                    lambda: catalog.render(
                        "character_view.Sheet",
                        character=character,
                        sheet_data=sheet_data,
                        profile_data=profile_data,
                        character_owner=character_owner,
                    )
                )()

                return await link_terms(result, link_type="html")

            case CharacterViewTab.BIOGRAPHY:
                result = await run_sync(
                    lambda: catalog.render(
                        "character_view.Biography",
                        character=character,
                        text_type_bio=TextType.BIOGRAPHY,
                        can_edit=session["IS_STORYTELLER"]
                        or session["USER_ID"] == character.user_owner,
                    )
                )()

                return await link_terms(result, link_type="html")

            case CharacterViewTab.INFO:
                result = await run_sync(
                    lambda: catalog.render(
                        "character_view.Info",
                        character=character,
                        CharacterEditableInfo=CharacterEditableInfo,
                        table_type_note=TableType.NOTE,
                        table_type_inventory=TableType.INVENTORYITEM,
                    )
                )()

                return await link_terms(result, link_type="html")

            case CharacterViewTab.IMAGES:  # pragma: no cover
                return redirect(url_for("partials.characterimages", character_id=character.id))

            case CharacterViewTab.STATISTICS:
                stats_engine = Statistics(guild_id=session["GUILD_ID"])

                return catalog.render(
                    "character_view.Statistics",
                    character=character,
                    statistics=await stats_engine.character_statistics(character, as_json=True),
                )
            case _:  # pragma: no cover
                assert_never()

    async def get(self, character_id: str = "") -> str | Response:
        """Process GET requests for character view.

        Handle GET requests for character view, either returning the full character page or
        a specific tab's content if requested via HTMX.

        Args:
            character_id (str): ID of the character to display

        Returns:
            Union[str, Response]: Either rendered HTML string or redirect Response

        Raises:
            HTTPException: If character not found (404)
            HTTPException: If user lacks permission to view character (403)
        """
        character = await self._get_character_object(character_id)
        character_owner = await User.get(character.user_owner, fetch_links=False)
        campaign = await fetch_active_campaign(campaign_id=character.campaign)

        if request.headers.get("HX-Request") and request.args.get("tab"):
            return await self._handle_tabs(character, character_owner=character_owner)

        sheet_builder = CharacterSheetBuilder(character=character)
        sheet_data = sheet_builder.fetch_sheet_character_traits(show_zeros=False)
        user_is_storyteller = await is_storyteller()
        profile_data = await sheet_builder.fetch_sheet_profile(
            storyteller_view=user_is_storyteller, is_web_ui=True
        )

        # We want to link to the user profile from the character view so we add the link here
        if owner_name := profile_data.get("Owner"):
            profile_data["Owner"] = (
                f" <a href='{url_for('user_profile.view', user_id=character_owner.id)}'>{owner_name}</a>"
            )

        campaign_experience = await self._get_campaign_experience(
            character, character_owner, campaign
        )

        result = await run_sync(
            lambda: catalog.render(
                "character_view.Main",
                character=character,
                profile_data=profile_data,
                tabs=CharacterViewTab,
                sheet_data=sheet_data,
                character_owner=character_owner,
                campaign_experience=campaign_experience,
                campaign=campaign,
                dice_sizes=[member.value for member in DiceType],
                form=gameplay_form,
                error_msg=request.args.get("error_msg", ""),
                success_msg=request.args.get("success_msg", ""),
                info_msg=request.args.get("info_msg", ""),
                warning_msg=request.args.get("warning_msg", ""),
                CharacterEditableInfo=CharacterEditableInfo,
            )
        )()

        return await link_terms(result, link_type="html")
