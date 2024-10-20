"""View character."""

from typing import ClassVar

from flask_discord import requires_authorization
from quart import abort, request, session, url_for
from quart.views import MethodView
from quart_wtf import QuartForm
from werkzeug.wrappers.response import Response

from valentina.constants import (
    DBSyncUpdateType,
    HTTPStatus,
    InventoryItemType,
)
from valentina.controllers import CharacterSheetBuilder
from valentina.models import (
    AWSService,
    Character,
    InventoryItem,
    Statistics,
    User,
)
from valentina.webui import catalog
from valentina.webui.utils import is_storyteller, sync_char_to_discord, update_session
from valentina.webui.utils.discord import post_to_audit_log

from . import form_fields
from .forms import EmptyForm


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
        success_msg = request.args.get("success_msg")
        character = await self._get_character_object(character_id)
        character_owner = await User.get(character.user_owner, fetch_links=False)

        if request.headers.get("HX-Request"):
            return await self._handle_tabs(character, character_owner=character_owner)

        sheet_builder = CharacterSheetBuilder(character=character)
        sheet_data = sheet_builder.fetch_sheet_character_traits(show_zeros=False)
        storyteller_data = await is_storyteller()
        profile_data = await sheet_builder.fetch_sheet_profile(storyteller_view=storyteller_data)

        return catalog.render(
            "character_view.Main",
            character=character,
            profile_data=profile_data,
            sheet_data=sheet_data,
            success_msg=success_msg,
            character_owner=character_owner,
        )


class CharacterEdit(MethodView):
    """View to handle character field edits.  Serves individual field forms for editing character attributes."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self) -> None:
        self.join_label = True
        self.floating_label = False

    async def _build_form(self, character: Character) -> QuartForm:
        """Build the character edit form."""
        data_from_db = {
            "character_id": character.id,
            "name_first": character.name_first if character.name_first else "",
            "name_last": character.name_last if character.name_last else "",
            "name_nick": character.name_nick if character.name_nick else "",
            "demeanor": character.demeanor if character.demeanor else "",
            "nature": character.nature if character.nature else "",
            "dob": character.dob if character.dob else "",
            "sire": character.sire if character.sire else "",
            "generation": character.generation if character.generation else "",
            "tribe": character.tribe if character.tribe else "",
            "auspice": character.auspice if character.auspice else "",
            "breed": character.breed if character.breed else "",
        }

        EmptyForm.character_id = form_fields.character_id
        EmptyForm.name_first = form_fields.name_first
        EmptyForm.name_last = form_fields.name_last
        EmptyForm.name_nick = form_fields.name_nick
        EmptyForm.demeanor = form_fields.demeanor
        EmptyForm.nature = form_fields.nature
        EmptyForm.dob = form_fields.dob

        if character.char_class_name.lower() == "vampire":
            EmptyForm.sire = form_fields.sire
            EmptyForm.generation = form_fields.generation

        if character.char_class_name.lower() == "werewolf":
            EmptyForm.tribe = form_fields.tribe
            EmptyForm.auspice = form_fields.auspice
            EmptyForm.breed = form_fields.breed

        return await EmptyForm().create_form(data=data_from_db)

    async def get(self, character_id: str) -> str:
        """Handle GET requests."""
        character = await Character.get(character_id)
        if not character:
            abort(HTTPStatus.BAD_REQUEST.value)

        form = await self._build_form(character)

        return catalog.render(
            "character_edit.Main",
            character=character,
            form=form,
            join_label=self.join_label,
            floating_label=self.floating_label,
        )

    async def post(self, character_id: str) -> str | Response:
        """Handle POST requests."""
        character = await Character.get(character_id)
        if not character:
            abort(HTTPStatus.BAD_REQUEST.value)

        form = await self._build_form(character)
        if await form.validate_on_submit():
            form_data = {
                k: v if v else None
                for k, v in form.data.items()
                if k not in {"submit", "character_id", "csrf_token"}
            }

            # Iterate over all form fields and update character attributes if they exist and are not "None"
            has_updates = False
            for key in form_data:
                if (not form_data[key] and getattr(character, key)) or (
                    form_data[key] and form_data[key] != getattr(character, key)
                ):
                    # dob field from form is datetime.date, but dob field from character is datetime.datetime. convert the character dob to date() for comparison
                    if (
                        key == "dob"
                        and getattr(character, key)
                        and form_data[key] == getattr(character, key).date()
                    ):
                        continue

                    has_updates = True
                    setattr(character, key, form_data[key])

            if has_updates:
                await sync_char_to_discord(character, DBSyncUpdateType.UPDATE)

                await character.save()
                await post_to_audit_log(
                    msg=f"Character {character.name} edited",
                    view=self.__class__.__name__,
                )

                # Rebuild the session with the new character data
                await update_session()

            # Redirect to the character view via htmx-redirect
            response = Response()
            response.headers["hx-redirect"] = url_for(
                "character_view.view",
                character_id=character_id,
                success_msg="<strong>Character updated!</strong><br><small>Changes will be reflected in Discord within ten minutes.</small>"
                if has_updates
                else "No changes made.",
            )
            return response

        # If POST request does not validate, return errors
        return catalog.render(
            "character_edit.WTForm",
            form=form,
            join_label=self.join_label,
            floating_label=self.floating_label,
            character=character,
        )
