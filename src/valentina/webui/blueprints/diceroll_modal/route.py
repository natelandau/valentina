"""Routes for the dice roll modal.

None of the routes in this blueprint load full pages. They are all partials that are loaded via HTMX.
Start by calling RollType. This will return the outer partial which contains the roll type selector alloing a user to select between rolling dice, traits, or macros.  Each of those forms makes a POST request to RollResults which will return the result partial in a div#roll-results.
"""

import json
from enum import Enum
from typing import TYPE_CHECKING, ClassVar, assert_never

from flask_discord import requires_authorization
from quart import request, session
from quart.views import MethodView

from valentina.constants import DiceType, RollResultType
from valentina.models import CharacterTrait, DiceRoll
from valentina.webui import catalog
from valentina.webui.utils import fetch_active_campaign, fetch_active_character, fetch_user
from valentina.webui.utils.forms import ValentinaForm

if TYPE_CHECKING:
    from valentina.models import Campaign, Character


gameplay_form = ValentinaForm()


class RollType(Enum):
    """Enum for the types of dice rolls which each have their own tab."""

    THROW = "throw"
    TRAITS = "traits"
    MACROS = "macros"

    @classmethod
    def get_member_by_value(cls, value: str) -> "RollType":
        """Get the member of the enum by its value."""
        return next((member for member in cls if member.value == value), None)


class RollSelector(MethodView):
    """Route for the dice roll modal."""

    decorators: ClassVar = [requires_authorization]

    async def handle_form_tabs(self, character: "Character", campaign: "Campaign") -> str:
        """Switch tabs for the gameplay template based on the selected tab.

        Fetch the active campaign and character, displaying an error message if either is missing.
        Depending on the tab specified in the request, render the appropriate tab content
        (e.g., "throw", "traits", "macros"). If an unrecognized tab is requested, return a 404 error.

        Returns:
            str: The rendered HTML content for the selected tab or an error message if applicable.
        """
        match RollType.get_member_by_value(request.args.get("tab", None)):
            case RollType.THROW:
                return catalog.render(
                    "diceroll_modal.TabThrow",
                    character=character,
                    campaign=campaign,
                    dice_sizes=[member.value for member in DiceType],
                    form=gameplay_form,
                    roll_types=RollType,
                )
            case RollType.TRAITS:
                traits = (
                    await CharacterTrait.find(CharacterTrait.character == str(character.id))
                    .sort(+CharacterTrait.name)
                    .to_list()
                )
                return catalog.render(
                    "diceroll_modal.TabTraits",
                    traits=traits,
                    campaign=campaign,
                    character=character,
                    form=gameplay_form,
                    roll_types=RollType,
                )
            case RollType.MACROS:
                user = await fetch_user()
                return catalog.render(
                    "diceroll_modal.TabMacros",
                    macros=user.macros,
                    campaign=campaign,
                    character=character,
                    form=gameplay_form,
                    roll_types=RollType,
                )
            case _:
                assert_never()

    async def get(self, character_id: str, campaign_id: str) -> str:
        """Handle GET requests. Changes to the form made prior to dice-rolling are handled as GET requests.

        The gameplay template is split into three jinjax partials for usage with HTMX for form processing.

            FormWrapper - The outside wrapper containing all elements of the left column of the page
            FormHeader  - The controller for selecting characters and campaigns
            FormTab...  -  The diceroll tabs, each with their own name corresponding to the tab name
        """
        character = await fetch_active_character(character_id=character_id)
        campaign = await fetch_active_campaign(campaign_id=campaign_id)

        # Handle tab switches
        if request.headers.get("HX-Request") and request.args.get("tab", None):
            return await self.handle_form_tabs(character=character, campaign=campaign)

        # If not an HTMX request, return the entire page
        return catalog.render(
            "diceroll_modal.RollTypeOuter",
            character=character,
            campaign=campaign,
            dice_sizes=[member.value for member in DiceType],
            form=gameplay_form,
            roll_types=RollType,
        )


class RollResults(MethodView):
    """Route for the dice roll results."""

    decorators: ClassVar = [requires_authorization]

    def _get_result_div_classes(self, result_type: RollResultType) -> str:
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

    async def _process_traits_form(self, form: dict) -> tuple[int, dict[str, int]]:
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

    async def _process_macros_form(
        self, form: dict, character: "Character"
    ) -> tuple[int, dict[str, int]]:
        """Process the macro rolling form.

        Retrieve the active character and use the macro data from the form to
        calculate the total dice pool and compile a dictionary of the selected
        traits and their values.

        Args:
            form (dict): The form data containing macro information.
            character (Character): The active character.

        Returns:
            tuple[int, dict[str, int]]: A tuple containing the total dice pool (sum of trait values) and a dictionary mapping trait names to their respective values.
        """
        macro = json.loads(form.get("macro", {}))

        trait1 = await character.fetch_trait_by_name(macro.get("trait1"))
        trait2 = await character.fetch_trait_by_name(macro.get("trait2"))

        rolled_traits: dict[str, int] = {}
        num_dice = 0
        if trait1:
            rolled_traits[trait1.name] = trait1.value
            num_dice += trait1.value
        if trait2:
            rolled_traits[trait2.name] = trait2.value
            num_dice += trait2.value

        return num_dice, rolled_traits

    async def post(self, character_id: str, campaign_id: str) -> str:
        """Process the diceroll form and return the correct partial."""
        character = await fetch_active_character(character_id=character_id, fetch_links=True)
        campaign = await fetch_active_campaign(campaign_id=campaign_id)

        form = await request.form

        match RollType.get_member_by_value(form.get("roll_type", None)):
            case RollType.TRAITS:
                pool, rolled_traits = await self._process_traits_form(form=form)
            case RollType.MACROS:
                pool, rolled_traits = await self._process_macros_form(
                    form=form, character=character
                )
            case RollType.THROW:
                pool = int(form.get("pool", 1))
                rolled_traits = {}
            case _:
                assert_never(RollType)

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
            "diceroll_modal.RollResult",
            roll=roll,
            rolled_traits=rolled_traits,
            result_image_url=await roll.thumbnail_url(),
            result_div_class=self._get_result_div_classes(roll.result_type),
        )
