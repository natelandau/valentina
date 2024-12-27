"""Form for creating a full character."""

from datetime import UTC, datetime, timedelta
from typing import ClassVar

from beanie import DeleteRules
from flask_discord import requires_authorization
from loguru import logger
from quart import abort, flash, redirect, request, session, url_for
from quart.views import MethodView
from quart_wtf import QuartForm
from werkzeug.wrappers.response import Response

from valentina.constants import BrokerTaskType, HTTPStatus
from valentina.controllers import CharacterSheetBuilder
from valentina.models import BrokerTask, Character, CharacterTrait
from valentina.utils import console
from valentina.webui import catalog
from valentina.webui.constants import CharCreateType
from valentina.webui.utils import fetch_user, update_session
from valentina.webui.utils.discord import post_to_audit_log, post_to_error_log

from .forms.character_create_full import (
    CharacterCreateStep1,
    HunterClassSpecifics,
    VampireClassSpecifics,
    WerewolfClassSpecifics,
)


class FormSessionManager:
    """Manage session data for the character creation forms. Creates a dict of data which can be read from and written to across different forms in the character creation process."""

    def __init__(self) -> None:
        self.key = "CharacterCreateFullData"

    def _clear_if_expired(self) -> None:
        """Clear session data if it has expired.

        Check if the session contains data associated with the key. If the data
        has an expiration time and it is earlier than the current time, clear
        the data from the session.

        """
        if self.key not in session:
            return

        expires = session[self.key].get("expires", None)
        now = datetime.now(UTC)
        if expires and expires < now:
            logger.debug("Form data expired, clearing from session")
            self.clear_data()

    def write_data(self, data: dict) -> None:
        """Write data to the session with an expiration time.

        Clear existing session data if it has expired. Then, write the provided
        data to the session under the specified key. If no expiration time is
        set, add a default expiration of 10 minutes from the current time.

        Args:
            data (dict): The data to be written to the session.
        """
        self._clear_if_expired()

        if self.key not in session:
            session[self.key] = {}

        if not session[self.key].get("expires"):
            now = datetime.now(UTC)
            now_plus_10 = now + timedelta(minutes=10)
            session[self.key]["expires"] = now_plus_10

        session[self.key].update(data)

    def read_data(self) -> dict:
        """Read data from the session.

        Clear session data if it has expired, then return the current data
        associated with the specified key. If no data exists, return an empty
        dictionary.

        Returns:
            dict: The session data associated with the key, or an empty dictionary
        if no data is found.
        """
        self._clear_if_expired()
        return session.get(self.key, {})

    def clear_data(self) -> None:
        """Clear the data associated with the key from the session.

        Remove the session data corresponding to the specified key. If the key
        does not exist in the session, do nothing.

        Returns:
            None
        """
        session.pop(self.key, None)


async def finalize_character_creation(
    character: Character, session_data: FormSessionManager, view: str = ""
) -> None:
    """Save initial traits for a character at level 0."""
    sheet_builder = CharacterSheetBuilder(character=character)
    sheet_traits = sheet_builder.fetch_all_class_traits()

    for section in sheet_traits:
        for category in section.categories:
            if category.traits_for_creation:
                for trait in category.traits_for_creation:
                    trait_obj = CharacterTrait(
                        name=trait.name,
                        value=0,
                        category_name=trait.category.name,
                        character=str(character.id),
                        max_value=int(trait.max_value),
                    )
                    await trait_obj.save()
                    character.traits.append(trait_obj)
                    console.log(f"Saved trait {trait_obj.name}")

    console.log(f"{len(character.traits)=}")
    await character.save()

    user = await fetch_user(fetch_links=True)
    user.characters.append(character)
    await user.save()

    task = BrokerTask(
        guild_id=character.guild,
        author_name=session["USER_NAME"],
        task=BrokerTaskType.CONFIRM_CHARACTER_CHANNEL,
        data={"character_id": character.id},
    )
    await task.insert()

    await post_to_audit_log(
        msg=f"WEBUI: Character {character.full_name} created",
        view=view,
    )

    # Clear temporary creation data and rebuild session with new character
    session_data.clear_data()
    await update_session()


class CreateFull1(MethodView):
    """Create a character step 1."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self) -> None:
        self.is_htmx = bool(request.headers.get("Hx-Request", False))
        self.session_data = FormSessionManager()
        self.join_label = True

    async def get(self) -> str:
        """Handle initial GET request for step 1 of character creation.

        Create and render a form for entering basic character information like name, class,
        and personality traits. If the user previously entered data and navigated away,
        restore that data from the session to avoid re-entry. This is the entry point for
        creating new characters and guides users through providing essential details before
        proceeding to class-specific traits.

        Returns:
            str: Rendered HTML template containing the character creation form. The template
                includes form validation, field labels, and proper styling.

        Note:
            This method expects certain session variables to be set:
            - USER_ID: The current user's ID for authorization
            - ACTIVE_CAMPAIGN_ID: The campaign context for character creation

            The form data is temporarily stored in the session with a 10 minute expiration
            to enable back navigation during the multi-step creation process.
        """
        form = await CharacterCreateStep1().create_form()

        # Support back navigation in multi-step form by restoring previous entries
        if form_data := self.session_data.read_data():
            form.process(data=form_data)

        return catalog.render(
            "character_create.CreateFull1",
            form=form,
            post_url=url_for(
                "character_create.create_1",
                # Default to player character type if not specified to handle most common case
                character_type=request.args.get("character_type", CharCreateType.PLAYER.value),
                # Fall back to active campaign if none specified to maintain context
                campaign_id=request.args.get("campaign_id", session.get("ACTIVE_CAMPAIGN_ID", "")),
            ),
        )

    async def post(self) -> str | Response:
        """Process form submissions for the first step of character creation.

        Handle form submission for creating a new character, including validation and persistence.
        This method represents the first step in a multi-step character creation workflow where
        basic character information is collected. On successful validation, create a new Character
        instance and determine the next appropriate creation step based on character class.

        Returns:
            Union[str, Response]: Either:
                - str: Rendered HTML with validation errors if form validation fails
                - Response: Redirect to step 2 for vampire/werewolf/hunter characters, or step 3 for other character classes

        Note:
            This method expects certain session variables to be set:
            - GUILD_ID: The Discord guild ID
            - USER_ID: The current user's ID
            - ACTIVE_CAMPAIGN_ID: The active campaign's ID
        """
        form = await CharacterCreateStep1().create_form()

        campaign_id = str(request.args.get("campaign_id", session.get("ACTIVE_CAMPAIGN_ID", None)))

        if form.data.get("cancel"):
            self.session_data.clear_data()
            await flash("Character creation cancelled", "info")
            return redirect(url_for("character_create.start"))

        if await form.validate_on_submit():
            # Conditionally set name fields to None if empty to avoid empty string values in DB
            character = Character(
                campaign=campaign_id,
                guild=session.get("GUILD_ID", None),
                name_first=form.data.get("firstname") if form.data.get("firstname") else None,
                name_last=form.data.get("lastname") if form.data.get("lastname") else None,
                name_nick=form.data.get("nickname") if form.data.get("nickname") else None,
                char_class_name=form.data.get("char_class"),
                type_player=request.args.get("character_type") == CharCreateType.PLAYER.value,
                type_storyteller=request.args.get("character_type")
                == CharCreateType.STORYTELLER.value,
                user_creator=session.get("USER_ID", None),
                user_owner=session.get("USER_ID", None),
                demeanor=form.data.get("demeanor") if form.data.get("demeanor") else None,
                nature=form.data.get("nature") if form.data.get("nature") else None,
                dob=form.data.get("dob") if form.data.get("dob") else None,
            )
            await character.save()
            form.data["char_id"] = str(character.id)

            # Store form data in session to enable back navigation in multi-step form
            self.session_data.write_data(form.data)

            # Only vampire/werewolf/hunter characters need additional class-specific details
            # All other character types can skip directly to trait selection
            char_class = form.data.get("char_class").lower()

            match char_class:
                case "vampire" | "werewolf" | "hunter":
                    return redirect(
                        url_for(
                            "character_create.create_2",
                            character_id=str(character.id),
                            char_class=char_class,
                        )
                    )
                case _:
                    await finalize_character_creation(
                        character=character,
                        session_data=self.session_data,
                        view=self.__class__.__name__,
                    )
                    return redirect(
                        url_for("character_edit.initial_build", character_id=character.id)
                    )

        # Re-render form with validation errors
        return catalog.render(
            "character_create.CreateFull1",
            form=form,
            post_url=url_for("character_create.create_1"),
        )


class CreateFull2(MethodView):
    """Create a character step 2."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self) -> None:
        self.is_htmx = bool(request.headers.get("Hx-Request", False))
        self.session_data = FormSessionManager()
        self.join_label = True

    def _get_class_specific_form(self, char_class: str) -> QuartForm | None:
        """Get the appropriate form class for character class-specific attributes.

        Retrieve the specialized form class needed to collect additional attributes specific
        to a character class during character creation. This is used in step 2 of the
        character creation workflow to gather class-specific details like vampire clans,
        werewolf breeds, or hunter creeds.

        Args:
            char_class (str): The character class identifier to get the form for.
                            Valid values are "vampire", "hunter", "werewolf", or "changeling".

        Returns:
            QuartForm | None: The instantiated form class for the specified character class.
                            Returns VampireClassSpecifics for vampires,
                            HunterClassSpecifics for hunters,
                            WerewolfClassSpecifics for werewolves/changelings,
                            or None if char_class is not recognized.
        """
        if char_class:
            match char_class.lower():
                case "vampire":
                    return VampireClassSpecifics()
                case "hunter":
                    return HunterClassSpecifics()
                case "werewolf" | "changeling":
                    return WerewolfClassSpecifics()

        return None

    async def get(self, character_id: str, char_class: str) -> str:
        """Process GET request for step 2 of character creation to render class-specific forms.

        Handle the GET request for step 2 of the multi-step character creation process. This step
        collects class-specific attributes like clan name for vampires or breed for werewolves.
        The method supports form state persistence via session storage to enable back navigation
        in the form flow.

        Args:
            character_id (str): Unique identifier for the character being created, used to link
                              class-specific attributes to the base character
            char_class (str): Character class type (e.g. "vampire", "werewolf", "hunter") that
                            determines which specialized form to render

        Returns:
            str: Rendered HTML template containing the class-specific form with any previously
                 entered data restored from session storage

        Raises:
            HTTPException: 400 status if character_id or char_class parameters are missing

        Example usage:
            # Route handler for /create/2/<character_id>/<char_class>
            await get("abc123", "vampire")  # Returns vampire-specific form HTML
        """
        if not character_id or not char_class:
            await post_to_error_log(
                msg="No character ID or char_class provided to CreateCharacterStep2",
                view=self.__class__.__name__,
            )
            abort(HTTPStatus.BAD_REQUEST.value)

        class_form = self._get_class_specific_form(char_class)
        form = await class_form.create_form()

        # Restore previous form state to enable back navigation in multi-step form flow
        if form_data := self.session_data.read_data():
            form.process(data=form_data)

        return catalog.render(
            "character_create.CreateFull2",
            form=form,
            post_url=url_for(
                "character_create.create_2", character_id=character_id, char_class=char_class
            ),
        )

    async def post(self, character_id: str, char_class: str) -> str | Response:
        """Process class-specific form data in the multi-step character creation workflow.

        Handle form submission for step 2 of character creation which collects class-specific
        attributes like clan name for vampires or breed for werewolves. This step is crucial
        for building complete character profiles with class-appropriate traits.

        The method supports:
        - Form validation and error handling
        - Storing form data in session for back navigation
        - Character deletion on cancel
        - Automatic redirect to next step on success

        Args:
            character_id (str): Unique identifier for the character being created
            char_class (str): Character class type (e.g. "vampire", "werewolf", "hunter")
                            determining which form fields to process

        Returns:
            Union[str, Response]: Either:
                - str: Rendered HTML with form validation errors
                - Response: Redirect to step 3 on successful validation

        Raises:
            HTTPException:
                - 400: Missing required character_id or char_class parameters
                - 404: Character not found in database

        Note:
            This method expects certain session variables to be pre-populated from step 1.
            Form fields vary based on character class but are handled uniformly through
            the form validation process.
        """
        if not character_id or not char_class:
            await post_to_error_log(
                msg="No character ID or char_class provided to CreateCharacterStep2",
                view=self.__class__.__name__,
            )
            abort(HTTPStatus.BAD_REQUEST.value)

        character = await Character.get(character_id)
        class_form = self._get_class_specific_form(char_class)
        form = await class_form.create_form()

        # Allow users to cancel character creation at any point
        if form.data.get("cancel"):
            self.session_data.clear_data()
            await character.delete(link_rule=DeleteRules.DELETE_LINKS)
            await flash("Character creation cancelled", "info")
            return redirect(url_for("character_create.start"))

        if await form.validate_on_submit():
            # Different character classes have different attributes - set only those that exist
            # Use None for missing attributes to avoid empty strings in database
            character.clan_name = form.data.get("clan_name") if form.data.get("clan_name") else None
            character.sire = form.data.get("sire") if form.data.get("sire") else None
            character.generation = (
                form.data.get("generation") if form.data.get("generation") else None
            )
            character.breed = form.data.get("breed") if form.data.get("breed") else None
            character.auspice = form.data.get("auspice") if form.data.get("auspice") else None
            character.tribe = form.data.get("tribe") if form.data.get("tribe") else None
            character.creed_name = form.data.get("creed") if form.data.get("creed") else None
            await character.save()

            # Store form data in session to support back navigation
            self.session_data.write_data(form.data)

            await finalize_character_creation(
                character=character,
                session_data=self.session_data,
                view=self.__class__.__name__,
            )
            return redirect(url_for("character_edit.initial_build", character_id=character.id))

        # Restore previous form data if user navigated back
        if form_data := self.session_data.read_data():
            form.process(data=form_data)

        # Re-render form with validation errors
        return catalog.render(
            "character_create.CreateFull2",
            form=form,
            post_url=url_for(
                "character_create.create_2", character_id=character_id, char_class=char_class
            ),
        )
