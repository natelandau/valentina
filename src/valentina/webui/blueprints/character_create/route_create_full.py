"""Form for creating a full character."""

from datetime import UTC, datetime, timedelta
from typing import ClassVar

from beanie import WriteRules
from flask_discord import requires_authorization
from loguru import logger
from quart import abort, redirect, request, session, url_for
from quart.views import MethodView
from quart_wtf import QuartForm
from werkzeug.wrappers.response import Response

from valentina.constants import DBSyncUpdateType, HTTPStatus
from valentina.controllers import CharacterSheetBuilder
from valentina.models import Character, CharacterTrait
from valentina.webui import catalog
from valentina.webui.utils.discord import post_to_audit_log, post_to_error_log
from valentina.webui.utils.forms import ValentinaForm
from valentina.webui.utils.helpers import sync_char_to_discord, update_session

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


class CreateCharacterStep1(MethodView):
    """Create a character step 1. Loads HTMX partials for the first form."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self) -> None:
        self.is_htmx = bool(request.headers.get("Hx-Request", False))
        self.session_data = FormSessionManager()
        self.join_label = True

    async def get(self) -> str:
        """Process the initial page load for the first step of character creation.

        Create and return a form for the first step of character creation. If
        there is existing form data stored in the session, prepopulate the form
        fields with this data, which is useful when navigating back to this step.

        Returns:
            str: The rendered HTML content for the first step of the character creation process.
        """
        form = await CharacterCreateStep1().create_form()

        # If form data for this step is already in the session, populate the form with it. Usefed for going "back" in the form process.
        if form_data := self.session_data.read_data():
            form.process(data=form_data)

        return catalog.render(
            "character_create.Step1",
            form=form,
            join_label=self.join_label,
            post_url=url_for(
                "character_create.create_1",
                character_type=request.args.get("character_type", "player"),
                campaign_id=request.args.get("campaign_id", session.get("ACTIVE_CAMPAIGN_ID", "")),
            ),
            error_msg=request.args.get("error_msg", ""),
            success_msg=request.args.get("success_msg", ""),
            info_msg=request.args.get("info_msg", ""),
            warning_msg=request.args.get("warning_msg", ""),
        )

    async def post(self) -> str | Response:
        """Process form submissions for the first step of character creation.

        Validate the submitted form data. If valid, create a new character object
        with the provided data and save it to the database. Store the form data
        in the session and redirect to the next step in the character creation
        process based on the selected character class. If the form validation
        fails, re-render the form with validation errors.

        Returns:
            str: The rendered HTML content for the first step of the character
                    creation process if validation fails.
            Response: A redirect to the appropriate next step in the character
                        creation process if the form is successfully validated and the
                        character is created.
        """
        form = await CharacterCreateStep1().create_form()

        campaign_id = str(request.args.get("campaign_id", session.get("ACTIVE_CAMPAIGN_ID", None)))

        if await form.validate_on_submit():
            character = Character(
                campaign=campaign_id,
                guild=session.get("GUILD_ID", None),
                name_first=form.data.get("firstname") if form.data.get("firstname") else None,
                name_last=form.data.get("lastname") if form.data.get("lastname") else None,
                name_nick=form.data.get("nickname") if form.data.get("nickname") else None,
                char_class_name=form.data.get("char_class"),
                type_player=request.args.get("character_type", "player") == "player",
                type_storyteller=request.args.get("character_type", "player") == "storyteller",
                user_creator=session.get("USER_ID", None),
                user_owner=session.get("USER_ID", None),
                demeanor=form.data.get("demeanor") if form.data.get("demeanor") else None,
                nature=form.data.get("nature") if form.data.get("nature") else None,
                dob=form.data.get("dob") if form.data.get("dob") else None,
            )
            new_char = await character.save()
            form.data["char_id"] = str(new_char.id)

            # Write the form data to the session
            self.session_data.write_data(form.data)

            # Redirect to next step
            char_class = form.data.get("char_class").lower()
            match char_class:
                case "vampire" | "werewolf" | "hunter":
                    route = "character_create.create_2"
                case _:
                    route = "character_create.create_3"

            return redirect(url_for(route, character_id=str(new_char.id), char_class=char_class))

        # If POST request does not validate, return errors
        return catalog.render(
            "character_create.Step1",
            form=form,
            join_label=self.join_label,
            post_url=url_for("character_create.create_1"),
        )


class CreateCharacterStep2(MethodView):
    """Create a character step 2. Loads HTMX partials for class specific items."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self) -> None:
        self.is_htmx = bool(request.headers.get("Hx-Request", False))
        self.session_data = FormSessionManager()
        self.join_label = True

    def _get_class_specific_form(self, char_class: str) -> QuartForm | None:
        """Return the form for the selected character class.

        Based on the provided character class, return the corresponding form
        for class-specific items. If the class is not recognized, return None.

        Args:
            char_class (str): The character class for which to retrieve the form
                                (e.g., "vampire", "hunter", "werewolf").

        Returns:
            QuartForm | None: The form corresponding to the selected character
                                class, or None if the class is not recognized.
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
        """Process the initial page load for the second step of character creation.

        Validate that both a character ID and character class are provided. If valid,
        retrieve and create the form corresponding to the character class. If form data
        is already stored in the session (useful for navigating back), prepopulate the
        form fields with this data. Render and return the form for this step.

        Args:
            character_id (str): The unique identifier of the character being created.
            char_class (str): The character class to determine which form to render.

        Returns:
            str: The rendered HTML content for the second step of the character creation process.

        Raises:
            400: If either the character ID or character class is not provided.
        """
        if not character_id or not char_class:
            await post_to_error_log(
                msg="No character ID or char_class provided to CreateCharacterStep2",
                view=self.__class__.__name__,
            )
            abort(HTTPStatus.BAD_REQUEST.value)

        class_form = self._get_class_specific_form(char_class)
        form = await class_form.create_form()

        # If form data for this step is already in the session, populate the form with it. Used for going "back" in the form process.
        if form_data := self.session_data.read_data():
            form.process(data=form_data)

        return catalog.render(
            "character_create.Step2",
            form=form,
            join_label=self.join_label,
            post_url=url_for(
                "character_create.create_2", character_id=character_id, char_class=char_class
            ),
        )

    async def post(self, character_id: str, char_class: str) -> str | Response:
        """Process form submissions for the second step of character creation.

        Validate that both a character ID and character class are provided. Retrieve
        and validate the form data specific to the character class. If valid, update
        the character with the provided data and save it to the database. Store the
        form data in the session and redirect to the next step in the character
        creation process. If validation fails, re-render the form with errors.

        Args:
            character_id (str): The unique identifier of the character being created.
            char_class (str): The character class to determine which form to process.

        Returns:
            str: The rendered HTML content for the second step of the character creation process if validation fails.
            Response: A redirect to the next step in the character creation process if the form is successfully validated and the character is updated.

        Raises:
            400: If either the character ID or character class is not provided.
            401: If the character ID is not found during the form processing.
        """
        if not character_id or not char_class:
            await post_to_error_log(
                msg="No character ID or char_class provided to CreateCharacterStep2",
                view=self.__class__.__name__,
            )
            abort(HTTPStatus.BAD_REQUEST.value)

        class_form = self._get_class_specific_form(char_class)
        form = await class_form.create_form()

        if await form.validate_on_submit():
            if not character_id:
                await post_to_error_log(
                    msg="No character ID  provided to CreateCharacterStep2",
                    view=self.__class__.__name__,
                )
                abort(HTTPStatus.UNAUTHORIZED.value)

            character = await Character.get(character_id)

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

            await sync_char_to_discord(character, DBSyncUpdateType.CREATE)
            await post_to_audit_log(
                msg=f"WEBUI: Character {character.full_name} created",
                view=self.__class__.__name__,
            )

            # Write the form data to the session
            self.session_data.write_data(form.data)

            # Redirect to next step
            return redirect(url_for("character_create.create_3", character_id=character_id))

        # If form data for this step is already in the session, populate the form with it. Used for going "back" in the form process.
        if form_data := self.session_data.read_data():
            form.process(data=form_data)

        # If POST request does not validate, return errors
        return catalog.render(
            "character_create.Step2",
            form=form,
            join_label=self.join_label,
            post_url=url_for(
                "character_create.create_2", character_id=character_id, char_class=char_class
            ),
        )


class CreateCharacterStep3(MethodView):
    """Create a character step 3. Loads HTMX partials for the third form - traits."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self) -> None:
        self.is_htmx = bool(request.headers.get("Hx-Request", False))
        self.session_data = FormSessionManager()
        self.join_label = True
        self.char_class = request.args.get("char_class", None)
        self.form = ValentinaForm(
            hx_validate=False,
            join_labels=True,
            title="Character Traits",
            description="Enter the traits for your character.",
        )

    async def get(self, character_id: str) -> str:
        """Process the initial page load for the third step of character creation.

        Validate the presence of a character ID, then fetch the character and
        its associated traits to render the character sheet. If no character ID
        is provided, log the error and abort the request with a 400 status.

        Args:
            character_id (str): The unique identifier of the character being created.

        Returns:
            str: The rendered HTML content for the third step of the character creation process.

        Raises:
            400: If the character ID is not provided.
        """
        if not character_id:
            await post_to_error_log(
                msg="No character ID provided to CreateCharacterStep3",
                view=self.__class__.__name__,
            )
            abort(HTTPStatus.BAD_REQUEST.value)

        character = await Character.get(character_id, fetch_links=True)
        sheet_builder = CharacterSheetBuilder(character=character)
        sheet_traits = sheet_builder.fetch_all_class_traits()

        return catalog.render(
            "character_create.Step3",
            form=self.form,
            sheet_traits=sheet_traits,
            post_url=url_for("character_create.create_3", character_id=character_id),
        )

    async def post(self, character_id: str) -> str | Response:
        """Process form submissions for the third step of character creation.

        Validate the presence of a character ID, then retrieve the character and
        process the submitted form data. Extract traits from the form, create
        `CharacterTrait` objects, and save them to the character. Clear session
        data, log the creation, update the session, and redirect to the character
        view with a success message.

        Args:
            character_id (str): The unique identifier of the character being created.

        Returns:
            str: The rendered HTML content if an error occurs.
            Response: A redirect to the character view page upon successful creation.

        Raises:
            400: If the character ID is not provided.
        """
        if not character_id:
            await post_to_error_log(
                msg="No character ID provided to CreateCharacterStep3",
                view=self.__class__.__name__,
            )
            abort(HTTPStatus.BAD_REQUEST.value)

        character = await Character.get(character_id, fetch_links=True)
        form = await request.form

        traits_to_add = []
        for k, value in form.items():
            category, name, max_value = k.split("_")
            traits_to_add.append(
                CharacterTrait(
                    name=name,
                    value=int(value),
                    category_name=category,
                    character=str(character_id),
                    max_value=int(max_value),
                )
            )

        character.traits = traits_to_add
        await character.save(link_rule=WriteRules.WRITE)
        self.session_data.clear_data()

        # Rebuild the session with the new character data
        await update_session()
        return redirect(
            url_for(
                "character_view.view",
                character_id=character_id,
                error_msg=request.args.get("error_msg", ""),
                success_msg=request.args.get("success_msg", ""),
                info_msg=request.args.get("info_msg", ""),
                warning_msg=request.args.get("warning_msg", ""),
            )
        )
