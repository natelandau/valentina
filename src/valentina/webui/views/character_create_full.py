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

from valentina.constants import CharSheetSection, TraitCategory
from valentina.models import Character, CharacterTrait
from valentina.utils.helpers import get_max_trait_value
from valentina.webui import catalog
from valentina.webui.utils.discord import post_to_audit_log, post_to_error_log
from valentina.webui.utils.helpers import update_session
from valentina.webui.WTForms.forms import (
    CharacterCreateFullStep1,
    HunterClassSpecifics,
    VampireClassSpecifics,
    WerewolfClassSpecifics,
)

from .valentina_forms import ValentinaForm


class FormSessionManager:
    """Manage session data for the character creation forms. Creates a dict of data which can be read from and written to across different forms in the character creation process."""

    def __init__(self) -> None:
        self.key = "CharacterCreateFullData"

    def _clear_if_expired(self) -> None:
        """Clear the session data if it has expired."""
        if self.key not in session:
            return

        expires = session[self.key].get("expires", None)
        now = datetime.now(UTC)
        if expires and expires < now:
            logger.debug("Form data expired, clearing from session")
            self.clear_data()

    def write_data(self, data: dict) -> None:
        """Write data to the session."""
        self._clear_if_expired()

        if self.key not in session:
            session[self.key] = {}

        if not session[self.key].get("expires"):
            now = datetime.now(UTC)
            now_plus_10 = now + timedelta(minutes=10)
            session[self.key]["expires"] = now_plus_10

        session[self.key].update(data)

    def read_data(self) -> dict:
        """Read data from the session."""
        self._clear_if_expired()
        return session.get(self.key, {})

    def clear_data(self) -> None:
        """Clear the data from the session."""
        session.pop(self.key, None)


class CreateCharacterStart(MethodView):
    """Create a character step 1."""

    decorators: ClassVar = [requires_authorization]

    async def get(self) -> str:
        """Process initial page load."""
        return catalog.render("character_create_full")


class CreateCharacterStep1(MethodView):
    """Create a character step 1. Loads HTMX partials for the first form."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self) -> None:
        self.is_htmx = bool(request.headers.get("Hx-Request", False))
        self.session_data = FormSessionManager()
        self.join_label = True

    async def get(self) -> str:
        """Process initial page load."""
        form = await CharacterCreateFullStep1().create_form()

        # If form data for this step is already in the session, populate the form with it. Usefed for going "back" in the form process.
        if form_data := self.session_data.read_data():
            form.process(data=form_data)

        return catalog.render(
            "character_create_full.Step1",
            form=form,
            join_label=self.join_label,
            post_url=url_for("character.create_full_1"),
        )

    async def post(self) -> str | Response:
        """Process form responses."""
        form = await CharacterCreateFullStep1().create_form()
        if await form.validate_on_submit():
            character = Character(
                campaign=session.get("ACTIVE_CAMPAIGN_ID", None),
                guild=session.get("GUILD_ID", None),
                name_first=form.data.get("firstname") if form.data.get("firstname") else None,
                name_last=form.data.get("lastname") if form.data.get("lastname") else None,
                name_nick=form.data.get("nickname") if form.data.get("nickname") else None,
                char_class_name=form.data.get("char_class"),
                type_player=True,
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
                    route = "character.create_full_2"
                case _:
                    route = "character.create_full_3"

            return redirect(url_for(route, character_id=str(new_char.id), char_class=char_class))

        # If POST request does not validate, return errors
        return catalog.render(
            "character_create_full.Step1",
            form=form,
            join_label=self.join_label,
            post_url=url_for("character.create_full_1"),
        )


class CreateCharacterStep2(MethodView):
    """Create a character step 2. Loads HTMX partials for class specific items."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self) -> None:
        self.is_htmx = bool(request.headers.get("Hx-Request", False))
        self.session_data = FormSessionManager()
        self.join_label = True

    def _get_class_specific_form(self, char_class: str) -> QuartForm | None:
        """Return the form for the selected class specific items."""
        if char_class:
            match char_class.lower():
                case "vampire":
                    return VampireClassSpecifics()
                case "hunter":
                    return HunterClassSpecifics()
                case "werewolf":
                    return WerewolfClassSpecifics()

        return None

    async def get(self, character_id: str, char_class: str) -> str:
        """Process initial page load."""
        if not character_id or not char_class:
            await post_to_error_log(
                msg="No character ID or char_class provided to CreateCharacterStep2",
                view=self.__class__.__name__,
            )
            abort(400)

        class_form = self._get_class_specific_form(char_class)
        form = await class_form.create_form()

        # If form data for this step is already in the session, populate the form with it. Used for going "back" in the form process.
        if form_data := self.session_data.read_data():
            form.process(data=form_data)

        return catalog.render(
            "character_create_full.Step2",
            form=form,
            join_label=self.join_label,
            post_url=url_for(
                "character.create_full_2", character_id=character_id, char_class=char_class
            ),
        )

    async def post(self, character_id: str, char_class: str) -> str | Response:
        """Process form responses."""
        if not character_id or not char_class:
            await post_to_error_log(
                msg="No character ID or char_class provided to CreateCharacterStep2",
                view=self.__class__.__name__,
            )
            abort(400)

        class_form = self._get_class_specific_form(char_class)
        form = await class_form.create_form()

        if await form.validate_on_submit():
            if not character_id:
                await post_to_error_log(
                    msg="No character ID  provided to CreateCharacterStep2",
                    view=self.__class__.__name__,
                )
                abort(401)

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

            # Write the form data to the session
            self.session_data.write_data(form.data)

            # Redirect to next step
            return redirect(url_for("character.create_full_3", character_id=character_id))

        # If form data for this step is already in the session, populate the form with it. Used for going "back" in the form process.
        if form_data := self.session_data.read_data():
            form.process(data=form_data)

        # If POST request does not validate, return errors
        return catalog.render(
            "character_create_full.Step2",
            form=form,
            join_label=self.join_label,
            post_url=url_for(
                "character.create_full_2", character_id=character_id, char_class=char_class
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

    async def _fetch_trait_names(self, category: TraitCategory, character: Character) -> list[str]:
        """Fetch the trait names for the selected category."""
        return list(category.value.COMMON) + list(
            getattr(category.value, character.char_class_name)
        )

    async def _fetch_sheet_traits(
        self, character: Character
    ) -> dict[str, dict[str, dict[str, int]]]:
        """Fetch the traits for the character sheet."""
        sheet_traits: dict[str, dict[str, dict[str, int]]] = {}
        for sheet_section in sorted(CharSheetSection, key=lambda x: x.value["order"]):
            sheet_traits[sheet_section.name] = {}

            trait_categories = sorted(
                [x for x in TraitCategory if x.value.section == sheet_section],
                key=lambda x: x.value.order,
            )
            for category in trait_categories:
                if not sheet_traits[sheet_section.name].get(category.name):
                    sheet_traits[sheet_section.name][category.name] = {}

                traits = await self._fetch_trait_names(category=category, character=character)
                for trait_name in traits:
                    sheet_traits[sheet_section.name][category.name][trait_name] = (
                        get_max_trait_value(trait_name, category.name)
                    )

        return sheet_traits

    async def get(self, character_id: str) -> str:
        """Process initial page load."""
        if not character_id:
            await post_to_error_log(
                msg="No character ID provided to CreateCharacterStep3",
                view=self.__class__.__name__,
            )
            abort(400)

        character = await Character.get(character_id, fetch_links=True)
        sheet_traits = await self._fetch_sheet_traits(character)

        return catalog.render(
            "character_create_full.Step3",
            form=self.form,
            sheet_traits=sheet_traits,
            post_url=url_for("character.create_full_3", character_id=character_id),
        )

    async def post(self, character_id: str) -> str | Response:
        """Process form responses."""
        if not character_id:
            await post_to_error_log(
                msg="No character ID provided to CreateCharacterStep3",
                view=self.__class__.__name__,
            )
            abort(400)

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

        # Log the result
        await post_to_audit_log(
            msg=f"New character created: {character.full_name}",
            view=self.__class__.__name__,
        )

        # Rebuild the session with the new character data
        await update_session()
        return redirect(
            url_for(
                "character.character_view",
                character_id=character_id,
                success_msg="Character created successfully!",
            )
        )
