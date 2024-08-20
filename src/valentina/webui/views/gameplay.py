"""Gameplay views for dicerolling."""

import json
from typing import ClassVar

from flask_discord import requires_authorization
from quart import abort, request, session
from quart.views import MethodView

from valentina.constants import DiceType, RollResultType
from valentina.models import CharacterTrait, DiceRoll
from valentina.webui import catalog
from valentina.webui.utils import fetch_active_campaign, fetch_active_character, fetch_user

from .valentina_forms import ValentinaForm

gameplay_form = ValentinaForm()


class DiceRollView(MethodView):
    """View to handle dice roll operations. POST a diceroll form to this view to return a snippet containing diceroll results."""

    decorators: ClassVar = [requires_authorization]

    def init(self) -> None:
        """Initialize the view."""
        self.session = session

    def get_result_div_classes(self, result_type: RollResultType) -> str:
        """Return CSS classes for the result div based on the roll result type.

        Determine and return the appropriate CSS classes to style the result div
        according to the provided `result_type`. The classes will indicate success,
        failure, or a critical/botch outcome.

        Args:
            result_type (RollResultType): The type of roll result (e.g., critical, success, failure, botch).

        Returns:
            str: A string containing the CSS classes to be applied to the result div.
        """
        if result_type in {RollResultType.CRITICAL, RollResultType.SUCCESS}:
            return "bg-success-subtle border border-success border-2"

        if result_type == RollResultType.FAILURE:
            return "bg-warning-subtle border border-warning border-2"

        if result_type == RollResultType.BOTCH:
            return "bg-danger-subtle border border-danger border-2"

        return "border border-2"

    async def process_traits_form(self, form: dict) -> tuple[int, dict[str, int]]:
        """Process the form data for trait rolling.

        Calculate the total dice pool based on the provided trait values and
        compile a dictionary of the selected traits and their values.

        Args:
            form (dict): The form data containing trait information.

        Returns:
            tuple[int, dict[str, int]]: A tuple containing the total dice pool (sum of trait values) and a dictionary mapping trait names to their respective values.
        """
        trait1 = json.loads(form.get("trait1", {}))
        trait2 = json.loads(form.get("trait2", {}))

        pool = trait1.get("value", 0) + trait2.get("value", 0)
        rolled_traits: dict[str, int] = {}
        if trait1.get("name", None):
            rolled_traits[trait1.get("name")] = trait1.get("value", 0)
        if trait2.get("name", None):
            rolled_traits[trait2.get("name")] = trait2.get("value", 0)

        return pool, rolled_traits

    async def process_macros_form(self, form: dict) -> tuple[int, dict[str, int]]:
        """Process the macro rolling form.

        Retrieve the active character and use the macro data from the form to
        calculate the total dice pool and compile a dictionary of the selected
        traits and their values.

        Args:
            form (dict): The form data containing macro information.

        Returns:
            tuple[int, dict[str, int]]: A tuple containing the total dice pool (sum of trait values) and a dictionary mapping trait names to their respective values.
        """
        character = await fetch_active_character(fetch_links=True)

        macro = json.loads(form.get("macro", {}))

        trait1 = await character.fetch_trait_by_name(macro.get("trait1"))
        trait2 = await character.fetch_trait_by_name(macro.get("trait2"))

        rolled_traits: dict[str, int] = {}
        if trait1:
            rolled_traits[trait1.name] = trait1.value
        if trait2:
            rolled_traits[trait2.name] = trait2.value

        return trait1.value + trait2.value, rolled_traits

    async def post(self) -> str:
        """Process the diceroll form and return the correct snippet."""
        form = await request.form

        # Process forms
        match form.get("tab", None):
            case "traits":
                pool, rolled_traits = await self.process_traits_form(form=form)
            case "macros":
                pool, rolled_traits = await self.process_macros_form(form=form)
            case _:
                pool = int(form.get("pool", 1))
                rolled_traits = {}

        character = await fetch_active_character(fetch_links=True)
        campaign = await fetch_active_campaign()

        roll = DiceRoll(
            difficulty=int(form.get("difficulty", 1)),
            dice_size=int(form.get("dice_size", 10)),
            pool=pool,
            desperation_pool=int(form.get("desperation_dice", 0)),
            guild_id=session["GUILD_ID"],
            author_id=session["USER_ID"],
            author_name=session["USER_NAME"],
            character=character,
            campaign=campaign,
        )

        await roll.log_roll(traits=list(rolled_traits))

        return catalog.render(
            "gameplay.RollResult",
            character=character,
            campaign=campaign,
            roll=roll,
            rolled_traits=rolled_traits,
            result_image_url=await roll.thumbnail_url(),
            result_div_class=self.get_result_div_classes(roll.result_type),
        )


class GameplayView(MethodView):
    """View to handle character operations."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self) -> None:
        self.session = session  # Assuming session is defined globally or passed in some way
        self.dice_size_values = [member.value for member in DiceType]

    async def handle_form_tabs(self) -> str:
        """Switch tabs for the gameplay template based on the selected tab.

        Fetch the active campaign and character, displaying an error message if either is missing.
        Depending on the tab specified in the request, render the appropriate tab content
        (e.g., "throw", "traits", "macros"). If an unrecognized tab is requested, return a 404 error.

        Returns:
            str: The rendered HTML content for the selected tab or an error message if applicable.

        Raises:
            404: If the requested tab is not recognized.
        """
        campaign = await fetch_active_campaign(fetch_links=True)
        character = await fetch_active_character(fetch_links=True)
        error_msg = None

        if not character and not campaign:
            error_msg = "Select a character and a campaign"
        elif not character:
            error_msg = "Select a character"
        elif not campaign:
            error_msg = "Select a campaign"

        if error_msg:
            return f'<div class="alert alert-danger" role="alert">{error_msg}</div>'

        if request.args.get("tab") == "throw":
            return catalog.render(
                "gameplay.FormTabThrow",
                character=character,
                campaign=campaign,
                dice_sizes=self.dice_size_values,
                form=gameplay_form,
            )

        if request.args.get("tab") == "traits":
            traits = (
                await CharacterTrait.find(CharacterTrait.character == str(character.id))
                .sort(+CharacterTrait.name)
                .to_list()
            )

            return catalog.render(
                "gameplay.FormTabTraits",
                traits=traits,
                campaign=campaign,
                form=gameplay_form,
            )

        if request.args.get("tab") == "macros":
            user = await fetch_user()
            return catalog.render(
                "gameplay.FormTabMacros",
                macros=user.macros,
                campaign=campaign,
                form=gameplay_form,
            )

        return abort(404)

    async def get(self) -> str:
        """Handle GET requests. Changes to the form made prior to dice-rolling are handled as GET requests.

        The gameplay template is split into three jinjax partials for usage with HTMX for form processing.

            FormWrapper - The outside wrapper containing all elements of the left column of the page
            FormHeader  - The controller for selecting characters and campaigns
            FormTab...  -  The diceroll tabs, each with their own name corresponding to the tab name
        """
        # Handle changes from the form header where character and campaign are selected
        if request.headers.get("HX-Request") and (
            request.args.get("character_id", None) or request.args.get("campaign_id", None)
        ):
            return catalog.render(
                "gameplay.FormWrapper",
                character=await fetch_active_character(
                    character_id=request.args.get("character_id", None)
                ),
                campaign=await fetch_active_campaign(
                    campaign_id=request.args.get("campaign_id", None)
                ),
                dice_sizes=self.dice_size_values,
                form=gameplay_form,
            )

        # Handle tab switches
        if request.headers.get("HX-Request") and request.args.get("tab", None):
            return await self.handle_form_tabs()

        # If not an HTMX request, return the entire page
        return catalog.render(
            "gameplay.Main",
            character=await fetch_active_character(),
            campaign=await fetch_active_campaign(),
            dice_sizes=self.dice_size_values,
            form=gameplay_form,
        )
