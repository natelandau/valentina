"""Blueprint for character views."""

from flask_discord import requires_authorization
from loguru import logger
from markupsafe import escape
from quart import Blueprint, abort, render_template, request, session
from quart.views import MethodView

from valentina.constants import CharSheetSection, InventoryItemType, TraitCategory
from valentina.models import AWSService, Character, CharacterTrait, InventoryItem, Statistics
from valentina.utils import console
from valentina.webui import catalog

bp = Blueprint("character", __name__)


class CharacterView(MethodView):
    """View to handle character operations."""

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
        console.log(f"{form=}")

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

    @requires_authorization
    async def get(self, character_id: str = "") -> str:
        """Handle GET requests."""
        character = await self.get_character_object(character_id)

        if request.headers.get("HX-Request"):
            return await self.handle_tabs(character)

        return catalog.render(
            "character",
            character=character,
            traits=await self.get_character_sheet_traits(character),
        )

    @requires_authorization
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


# Register the view with the Blueprint
character_view = CharacterView.as_view("character_view")
bp.add_url_rule(
    "/character/<string:character_id>", view_func=character_view, methods=["GET", "POST"]
)


class CharacterEditView(MethodView):
    """View to handle editing an individual character."""

    def __init__(self) -> None:
        self.session = session  # Assuming session is defined globally or passed in some way

    @requires_authorization
    async def get(self, character_id: str) -> str:
        """Edit an individual character."""
        character = await Character.get(character_id, fetch_links=True)
        if not character:
            abort(404)

        return await render_template(
            "snippets/character_edit.html", character=character, view="sheet"
        )


# Register the view with the Blueprint
edit_character = CharacterEditView.as_view("edit_character")
bp.add_url_rule("/character/<string:character_id>/edit", view_func=edit_character, methods=["GET"])
