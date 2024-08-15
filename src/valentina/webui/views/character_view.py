"""View character."""

from typing import ClassVar

from flask_discord import requires_authorization
from loguru import logger
from markupsafe import escape
from quart import abort, render_template, request, session, url_for
from quart.views import MethodView
from quart_wtf import QuartForm
from werkzeug.wrappers.response import Response

from valentina.constants import CharSheetSection, InventoryItemType, TraitCategory
from valentina.models import AWSService, Character, CharacterTrait, InventoryItem, Statistics
from valentina.webui import catalog
from valentina.webui.utils.discord import post_to_audit_log
from valentina.webui.utils.helpers import update_session
from valentina.webui.WTForms import fields
from valentina.webui.WTForms.character_edit import EmptyForm


class CharacterView(MethodView):
    """View to handle character operations."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self) -> None:
        self.session = session  # Assuming session is defined globally or passed in some way

    async def get_character_object(self, character_id: str) -> Character:
        """Get a character db object by ID.

        Args:
            character_id (str): The character ID to fetch.

        Returns:
            Character: The character object.
        """
        try:
            character = await Character.get(character_id, fetch_links=True)
        except ValueError:
            abort(406)

        if not character:
            abort(404)

        return character

    async def get_character_sheet_traits(
        self, character: Character
    ) -> dict[str, dict[str, list[CharacterTrait]]]:
        """Returns all character traits grouped by character sheet section and category."""
        character_traits = await CharacterTrait.find(
            CharacterTrait.character == str(character.id)
        ).to_list()

        sheet_traits: dict[str, dict[str, list[CharacterTrait]]] = {}

        for section in sorted(CharSheetSection, key=lambda x: x.value["order"]):
            if section != CharSheetSection.NONE:
                sheet_traits[section.name] = {}

            # Sort by trait category
            for cat in sorted(
                [x for x in TraitCategory if x.value.section == section],
                key=lambda x: x.value.order,
            ):
                for x in character_traits:
                    if x.category_name == cat.name and not (
                        x.value == 0 and not cat.value.show_zero
                    ):
                        try:
                            sheet_traits[section.name][x.category_name].append(x)
                        except KeyError:
                            sheet_traits[section.name][x.category_name] = [x]

        return sheet_traits

    async def get_character_inventory(self, character: Character) -> dict:
        """Get the character's inventory."""
        inventory: dict[str, list[InventoryItem]] = {}
        for x in InventoryItemType:
            inventory[x.name] = []

        for item in await InventoryItem.find(
            InventoryItem.character == str(character.id)
        ).to_list():
            inventory[item.type].append(item)

        # remove all empty dictionary entries
        return {k: v for k, v in inventory.items() if v}

    async def process_form_data(self, character: Character) -> None:
        """Process form data and update character attributes."""
        form = await request.form

        # Iterate over all form fields and update character attributes if they exist and are not "None"
        for key, value in form.items():
            if hasattr(character, key):
                v = value if value != "" else None
                if getattr(character, key) != v:
                    setattr(character, key, escape(v) if v else None)

            if not hasattr(character, key):
                logger.warning(f"Character attribute {key} not found.")

            # TODO: Implement channel renaming

        await character.save()

    async def get_character_image_urls(self, character: Character) -> list[str]:
        """Get image URLs for a character."""
        aws_svc = AWSService()

        return [aws_svc.get_url(x) for x in character.images]

    async def handle_tabs(self, character: Character) -> str:
        """Handle htmx tab requests."""
        if request.args.get("tab") == "sheet":
            return catalog.render(
                "character.Sheet",
                character=character,
                traits=await self.get_character_sheet_traits(character),
            )

        if request.args.get("tab") == "inventory":
            return catalog.render(
                "character.Inventory",
                character=character,
                inventory=await self.get_character_inventory(character),
            )

        if request.args.get("tab") == "profile":
            return catalog.render("character.profile", character=character)

        if request.args.get("tab") == "images":
            return catalog.render(
                "character.Images",
                character=character,
                images=await self.get_character_image_urls(character),
            )

        if request.args.get("tab") == "statistics":
            stats_engine = Statistics(guild_id=session["GUILD_ID"])

            return catalog.render(
                "character.Statistics",
                character=character,
                statistics=await stats_engine.character_statistics(character, as_json=True),
            )

        return abort(404)

    async def get(self, character_id: str = "") -> str:
        """Handle GET requests."""
        success_msg = request.args.get("success_msg")
        character = await self.get_character_object(character_id)

        if request.headers.get("HX-Request"):
            return await self.handle_tabs(character)

        return catalog.render(
            "character",
            character=character,
            traits=await self.get_character_sheet_traits(character),
            success_msg=success_msg,
        )

    async def post(self, character_id: str = "") -> str:
        """Handle POST requests."""
        character = await self.get_character_object(character_id)
        traits = await self.get_character_sheet_traits(character)
        inventory = await self.get_character_inventory(character)
        stats_engine = Statistics(guild_id=session["GUILD_ID"])
        statistics = await stats_engine.character_statistics(character, as_json=True)

        await self.process_form_data(character)

        return await render_template(
            "character.html",
            character=character,
            traits=traits,
            inventory_item_types=inventory,
            args=request.args,
            statistics=statistics,
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

        EmptyForm.character_id = fields.character_id
        EmptyForm.name_first = fields.name_first
        EmptyForm.name_last = fields.name_last
        EmptyForm.name_nick = fields.name_nick
        EmptyForm.demeanor = fields.demeanor
        EmptyForm.nature = fields.nature
        EmptyForm.dob = fields.dob

        if character.char_class_name.lower() == "vampire":
            EmptyForm.sire = fields.sire
            EmptyForm.generation = fields.generation

        if character.char_class_name.lower() == "werewolf":
            EmptyForm.tribe = fields.tribe
            EmptyForm.auspice = fields.auspice
            EmptyForm.breed = fields.breed

        return await EmptyForm().create_form(data=data_from_db)

    async def get(self, character_id: str) -> str:
        """Handle GET requests."""
        character = await Character.get(character_id)
        if not character:
            abort(404)

        form = await self._build_form(character)

        return catalog.render(
            "character_edit",
            character=character,
            form=form,
            join_label=self.join_label,
            floating_label=self.floating_label,
        )

    async def post(self, character_id: str) -> str | Response:
        """Handle POST requests."""
        character = await Character.get(character_id)
        if not character:
            abort(404)

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
                "character.character_view",
                character_id=character_id,
                success_msg="Character updated!" if has_updates else "No changes made.",
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
