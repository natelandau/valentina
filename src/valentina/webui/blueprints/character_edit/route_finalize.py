"""Route for spending freebie points."""

from typing import ClassVar

from flask_discord import requires_authorization
from loguru import logger
from quart import Response, abort, request, session, url_for
from quart.views import MethodView

from valentina.constants import CharSheetSection, HTTPStatus, TraitCategory
from valentina.controllers import TraitModifier
from valentina.models import Character, CharacterTrait, User
from valentina.utils import errors
from valentina.webui import catalog
from valentina.webui.utils.discord import post_to_audit_log
from valentina.webui.utils.forms import ValentinaForm
from valentina.webui.utils.helpers import fetch_active_character, fetch_user, is_storyteller


class SpendFreeiePoints(MethodView):
    """View to manage freebie point spending. This page uses HTMX to validate each trait as it is changed."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self) -> None:
        self.form = ValentinaForm(
            hx_validate=False,
            join_labels=True,
            title="Character Traits",
            description="Enter the traits for your character.",
        )

    async def _get_character_sheet_traits(
        self, character: Character, show_zero_values: bool = False
    ) -> dict[str, dict[str, list[CharacterTrait]]]:
        """Return all character traits grouped by character sheet section and category.

        Retrieve the character's traits from the database and organize them into a
        dictionary grouped by character sheet sections and categories. Only include
        traits with non-zero values, unless the category is configured to show zero values.

        Args:
            character (Character): The character whose traits are to be retrieved and grouped.
            show_zero_values (bool): Include traits with a value of zero. Defaults to False.

        Returns:
            dict[str, dict[str, list[CharacterTrait]]]: A nested dictionary where the top-level
                keys are section names, the second-level keys are category names, and the values
                are lists of `CharacterTrait` objects associated with each category.
        """
        character_traits = await CharacterTrait.find(
            CharacterTrait.character == str(character.id)
        ).to_list()

        sheet_traits: dict[str, dict[str, list[CharacterTrait]]] = {}

        for section in sorted(CharSheetSection, key=lambda x: x.value.order):
            if section != CharSheetSection.NONE:
                sheet_traits[section.name] = {}

            # Sort by trait category
            for cat in sorted(
                [x for x in TraitCategory if x.value.section == section],
                key=lambda x: x.value.order,
            ):
                for x in character_traits:
                    if x.category_name == cat.name:
                        if not show_zero_values and x.value == 0 and not cat.value.show_zero:
                            continue
                        try:
                            sheet_traits[section.name][x.category_name].append(x)
                        except KeyError:
                            sheet_traits[section.name][x.category_name] = [x]

        return sheet_traits

    async def get(self, character_id: str = "") -> str:
        """Manage GET requests."""
        character = await fetch_active_character(character_id, fetch_links=True)
        if not character:
            abort(HTTPStatus.BAD_REQUEST.value)

        character_owner = await User.get(character.user_owner, fetch_links=False)
        if not is_storyteller and character_owner.id != session.get("USER_ID"):
            # TODO: Return custom error page when user can not edit character
            abort(HTTPStatus.BAD_REQUEST.value)

        traits = await self._get_character_sheet_traits(character, show_zero_values=True)
        return catalog.render(
            "character_edit.Finalize",
            character=character,
            form=self.form,
            traits=traits,
            post_url=url_for("character_edit.finalize", character_id=character_id),
            error_msg=request.args.get("error_msg", ""),
        )

    async def post(self, character_id: str = "") -> Response:
        """Manage POST requests."""
        character = await fetch_active_character(character_id, fetch_links=False)
        user = await fetch_user()
        if not character:
            abort(HTTPStatus.BAD_REQUEST.value)

        form = await request.form
        trait_id = next(iter(form.keys()))
        target_value = int(next(iter(form.values())))

        trait = await CharacterTrait.get(trait_id)

        if trait.value < target_value:
            trait_modifier = TraitModifier(character, user)
            difference = target_value - trait.value
            cost = trait_modifier.cost_to_upgrade(trait, difference)

            try:
                updated_trait = await trait_modifier.upgrade_with_freebie(trait, difference)
                await post_to_audit_log(
                    msg=f"Upgraded {character.name}'s {trait.name} to {updated_trait.value} costing {cost} freebie points"
                )
            except errors.TraitAtMaxValueError:
                logger.warning("Trait at max value")
            except errors.NotEnoughFreebiePointsError:
                logger.warning("Not enough freebie points to upgrade trait")
                return Response(
                    headers={
                        "HX-Redirect": url_for(
                            "character_edit.finalize",
                            character_id=character_id,
                            error_msg=f"Not enough freebie points to upgrade {trait.name} to {trait.value + difference}",
                        )
                    }
                )

        elif trait.value > target_value:
            trait_modifier = TraitModifier(character, user)
            difference = trait.value - target_value
            savings = trait_modifier.savings_from_downgrade(trait, difference)
            try:
                updated_trait = await trait_modifier.downgrade_with_freebie(trait, difference)
                await post_to_audit_log(
                    msg=f"Downgraded {character.name}'s {trait.name} to {updated_trait.value} recouping {savings} freebie points"
                )
            except errors.TraitAtMinValueError:
                logger.warning("Trait at min value")

        # Redirect to the finalize page after updating the trait
        return Response(
            headers={
                "HX-Redirect": url_for(
                    "character_edit.finalize",
                    character_id=character_id,
                )
            }
        )
