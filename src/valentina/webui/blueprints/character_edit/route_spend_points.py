"""Route for spending freebie points."""

from enum import Enum
from typing import ClassVar, assert_never

from flask_discord import requires_authorization
from quart import Response, abort, redirect, request, session, url_for
from quart.views import MethodView

from valentina.constants import HTTPStatus
from valentina.controllers import CharacterSheetBuilder, TraitModifier
from valentina.models import Campaign, Character, CharacterTrait, User
from valentina.utils import errors
from valentina.utils.helpers import get_max_trait_value
from valentina.webui import catalog
from valentina.webui.utils.discord import post_to_audit_log
from valentina.webui.utils.forms import ValentinaForm
from valentina.webui.utils.helpers import fetch_active_character, fetch_user


class SpendPointsType(Enum):
    """The type of point to spend."""

    FREEBIE = "freebie"
    EXPERIENCE = "experience"
    STORYTELLER = "storyteller"


class SpendPoints(MethodView):
    """Manage upgrading/downgrading traits for a character using different point types."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self, spend_type: SpendPointsType) -> None:
        self.form = ValentinaForm(
            hx_validate=False,
            join_labels=True,
            title="Character Traits",
            description="Enter the traits for your character.",
        )
        self.spend_type = spend_type

    async def _get_campaign_experience(
        self, character: "Character", character_owner: User = None
    ) -> int:
        """Retrieve experience points for the character's campaign.

        Args:
            character (Character): The character to check.
            character_owner (User, optional): The character's owner. Defaults to None.

        Returns:
            int: Campaign experience points.
        """
        if not character_owner:
            character_owner = await User.get(character.user_owner, fetch_links=False)

        campaign = await Campaign.get(character.campaign)
        campaign_experience, _, _ = character_owner.fetch_campaign_xp(campaign)
        return campaign_experience

    async def _downgrade_trait(
        self, character: Character, trait: CharacterTrait, new_value: int
    ) -> str:
        """Reduce a trait's value and recoup points.

        Args:
            character (Character): The character to modify.
            trait (CharacterTrait): The trait to downgrade.
            new_value (int): The target value for the trait.

        Returns:
            str: Success message describing the downgrade.
        """
        user = await fetch_user()
        trait_modifier = TraitModifier(character, user)
        difference = trait.value - new_value
        savings = trait_modifier.savings_from_downgrade(trait, difference)

        match self.spend_type:
            case SpendPointsType.FREEBIE:
                downgraded_trait = await trait_modifier.downgrade_with_freebie(trait, difference)
            case SpendPointsType.EXPERIENCE:
                campaign = await Campaign.get(character.campaign)
                downgraded_trait = await trait_modifier.downgrade_with_xp(
                    trait, campaign, difference
                )
            case SpendPointsType.STORYTELLER:
                if trait_modifier.can_trait_be_downgraded(trait, difference):
                    trait.value = new_value
                    downgraded_trait = await character.add_trait(trait)
            case _:
                assert_never()

        player_message = (
            f" recouping {savings} {self.spend_type.value} points"
            if self.spend_type != SpendPointsType.STORYTELLER
            else ""
        )
        await post_to_audit_log(
            msg=f"Downgraded {character.name}'s {trait.name} to {downgraded_trait.value}{player_message}"
        )
        return f"Downgraded {trait.name} to {downgraded_trait.value}{player_message}"

    async def _parse_form_data(
        self, character: Character, form: dict
    ) -> tuple[CharacterTrait, int]:
        """Extract trait and target value from form data.

        Create a new CharacterTrait if it doesn't exist in the database.

        Args:
            character (Character): The character to modify.
            form (dict): The submitted form data.

        Returns:
            tuple[CharacterTrait, int]: The trait to modify and its target value.

        Raises:
            ValueError: If a custom trait name is empty.
        """
        form_key = str(next(iter(form.keys())))

        # Because we have a mix of existing traits and new traits, we need to create new traits if they don't exist
        if form_key.lower().startswith("new_"):
            target_value = int(next(iter(form.values())))
            name, category, max_value = form_key.split("_")[1:]
            trait = CharacterTrait(
                name=name.strip().title(),
                category_name=category.strip().upper(),
                max_value=int(max_value),
                value=0,
                is_custom=False,
                character=str(character.id),
            )

        elif form_key.lower().startswith("custom_"):
            custom_trait_name = next(iter(form.values()))
            target_value = 1
            category = form_key.split("_")[1]
            if not custom_trait_name:
                msg = "Trait name can not be empty"
                raise ValueError(msg)
            trait = CharacterTrait(
                name=custom_trait_name.strip().title(),
                category_name=category.strip().upper(),
                max_value=get_max_trait_value(
                    custom_trait_name.strip().title(), category.strip().upper()
                ),
                value=0,
                is_custom=True,
                character=str(character.id),
            )
        else:
            target_value = int(next(iter(form.values())))
            trait = await CharacterTrait.get(form_key)

        return trait, target_value

    async def _upgrade_trait(
        self, character: Character, trait: CharacterTrait, new_value: int
    ) -> str:
        """Increase a trait's value and spend points.

        Args:
            character (Character): The character to modify.
            trait (CharacterTrait): The trait to upgrade.
            new_value (int): The target value for the trait.

        Returns:
            str: Success message describing the upgrade.
        """
        user = await fetch_user()
        trait_modifier = TraitModifier(character, user)
        difference = new_value - trait.value
        cost = trait_modifier.cost_to_upgrade(trait, difference)

        match self.spend_type:
            case SpendPointsType.FREEBIE:
                upgraded_trait = await trait_modifier.upgrade_with_freebie(trait, difference)
            case SpendPointsType.EXPERIENCE:
                campaign = await Campaign.get(character.campaign)
                upgraded_trait = await trait_modifier.upgrade_with_xp(trait, campaign, difference)
            case SpendPointsType.STORYTELLER:
                if trait_modifier.can_trait_be_upgraded(trait, difference):
                    trait.value = new_value
                    upgraded_trait = await character.add_trait(trait)
            case _:
                assert_never()

        player_message = (
            f" for {cost} {self.spend_type.value} points"
            if self.spend_type != SpendPointsType.STORYTELLER
            else ""
        )
        await post_to_audit_log(
            msg=f"Upgraded {character.name}'s {trait.name} to {upgraded_trait.value}{player_message}"
        )
        return f"Upgraded <strong>{trait.name}</strong> to {upgraded_trait.value}{player_message}"

    async def get(self, character_id: str = "") -> str | Response:
        """Process GET requests for trait modification.

        Args:
            character_id (str, optional): The ID of the character to edit. Defaults to "".

        Returns:
            str | Response: Rendered template or redirect response.

        Raises:
            HTTPException: If the character is not found.
        """
        character = await fetch_active_character(character_id, fetch_links=True)
        if not character:
            abort(HTTPStatus.BAD_REQUEST.value)

        character_owner = await User.get(character.user_owner, fetch_links=False)
        if not session["IS_STORYTELLER"] and character_owner.id != session.get("USER_ID"):
            return redirect(  # type: ignore [return-value]
                url_for(
                    "character_view.view",
                    character_id=character_id,
                    error_msg="You do not have permission to edit this character",
                )
            )
        if not session["IS_STORYTELLER"] and self.spend_type == SpendPointsType.STORYTELLER:
            return redirect(  # type: ignore [return-value]
                url_for(
                    "character_view.view",
                    character_id=character_id,
                    error_msg="Only storytellers can update characters without spending points",
                )
            )

        campaign_experience = (
            await self._get_campaign_experience(character)
            if self.spend_type == SpendPointsType.EXPERIENCE
            else 0
        )

        trait_builder = CharacterSheetBuilder(character)
        all_traits = trait_builder.fetch_character_plus_all_class_traits()

        return catalog.render(
            "character_edit.SpendPoints",
            spend_type=self.spend_type,
            character=character,
            campaign_experience=campaign_experience,
            form=self.form,
            traits=all_traits,
            post_url=url_for(f"character_edit.{self.spend_type.value}", character_id=character_id),
            error_msg=request.args.get("error_msg", ""),
            success_msg=request.args.get("success_msg", ""),
            info_msg=request.args.get("info_msg", ""),
            warning_msg=request.args.get("warning_msg", ""),
        )

    async def post(self, character_id: str = "") -> str:
        """Process POST requests for trait modification.

        Args:
            character_id (str, optional): The ID of the character to edit. Defaults to "".

        Returns:
            Response: Redirect response after processing.

        Raises:
            HTTPException: If the character is not found.
        """
        character = await fetch_active_character(character_id, fetch_links=True)
        if not character:
            abort(HTTPStatus.BAD_REQUEST.value)

        form = await request.form

        try:
            trait, target_value = await self._parse_form_data(character, form)
        except ValueError as e:
            url = url_for(
                f"character_edit.{self.spend_type.value}",
                character_id=str(character.id),
                error_msg=str(e),
            )
            return f'<script>window.location.href="{url}"</script>'

        success_msg = ""
        try:
            if trait.value < target_value:
                success_msg = await self._upgrade_trait(character, trait, target_value)
            elif trait.value > target_value:
                success_msg = await self._downgrade_trait(character, trait, target_value)
        except (
            errors.TraitAtMaxValueError,
            errors.NotEnoughFreebiePointsError,
            errors.TraitExistsError,
            errors.NotEnoughExperienceError,
            errors.TraitAtMinValueError,
        ) as e:
            url = url_for(
                f"character_edit.{self.spend_type.value}",
                character_id=str(character.id),
                error_msg=str(e),
            )
            return f'<script>window.location.href="{url}"</script>'

        url = url_for(
            f"character_edit.{self.spend_type.value}",
            character_id=str(character.id),
            success_msg=success_msg,
        )
        return f'<script>window.location.href="{url}"</script>'
