"""Route for editing the character profile."""

import uuid
from typing import ClassVar

from flask_discord import requires_authorization
from quart import Response, abort, url_for
from quart.views import MethodView
from quart_wtf import QuartForm
from wtforms import (
    DateField,
    HiddenField,
    SelectField,
    StringField,
    SubmitField,
    ValidationError,
)
from wtforms.validators import DataRequired, Length, Optional

from valentina.constants import (
    HTTPStatus,
    HunterCreed,
    VampireClan,
    WerewolfAuspice,
    WerewolfBreed,
    WerewolfTribe,
)
from valentina.models import Character
from valentina.webui import catalog
from valentina.webui.utils import sync_channel_to_discord, update_session
from valentina.webui.utils.discord import post_to_audit_log
from valentina.webui.utils.forms import validate_unique_character_name


class ProfileForm(QuartForm):
    """A form for editing the character profile."""

    prefix = str(uuid.uuid4())[:8]

    name_first = StringField(
        "First Name",
        default="",
        validators=[DataRequired(), Length(min=3, message="Must be at least 3 characters")],
        filters=[str.strip, str.title],
    )
    name_last = StringField(
        "Last Name",
        default="",
        validators=[DataRequired(), Length(min=3, message="Must be at least 3 characters")],
        filters=[str.strip, str.title],
    )
    name_nick = StringField(
        "Nickname",
        default="",
        validators=[Optional()],
        filters=[str.strip, str.title],
    )
    clan_name = SelectField(
        "Vampire Clan",
        choices=[("", "-- Select --")] + [(x.name, x.value.name) for x in VampireClan],
        validators=[DataRequired()],
    )
    breed = SelectField(
        "Breed",
        choices=[("", "-- Select --")] + [(x.name, x.value.name) for x in WerewolfBreed],
        validators=[DataRequired()],
    )

    auspice = SelectField(
        "Auspice",
        choices=[("", "-- Select --")] + [(x.name, x.value.name) for x in WerewolfAuspice],
        validators=[DataRequired()],
    )

    tribe = SelectField(
        "Tribe",
        choices=[("", "-- Select --")] + [(x.name, x.value.name) for x in WerewolfTribe],
        validators=[DataRequired()],
    )

    creed_name = SelectField(
        "Creed",
        choices=[("", "-- Select --")] + [(x.name, x.value.name) for x in HunterCreed],
        validators=[DataRequired()],
    )
    demeanor = StringField(
        default="",
        validators=[Optional(), Length(min=3, message="Must be at least 3 characters")],
        filters=[str.strip, str.title],
    )
    nature = StringField(
        "Nature",
        default="",
        validators=[Optional(), Length(min=3, message="Must be at least 3 characters")],
        filters=[str.strip, str.title],
    )
    dob = DateField(
        "Date of Birth", description="Used to calculate age", validators=[Optional()], default=""
    )
    sire = StringField(
        "Sire",
        default="",
        validators=[Optional(), Length(min=3, message="Must be at least 3 characters")],
        filters=[str.strip, str.title],
    )
    generation = StringField(
        "Generation",
        default="",
        validators=[Optional()],
        filters=[str.strip, str.title],
    )

    submit = SubmitField("Submit")
    character_id = HiddenField()

    async def async_validators_name_last(self, name_last: StringField) -> None:
        """Check if the first + lastname are unique in the database."""
        if not await validate_unique_character_name(
            name_first=self.name_first.data,
            name_last=name_last.data,
            character_id=self.character_id.data,
        ):
            msg = "Character name must not already exist."
            raise ValidationError(msg)

    async def async_validators_name_first(self, name_first: StringField) -> None:
        """Check if the first + lastname are unique in the database."""
        if not await validate_unique_character_name(
            name_first=name_first.data,
            name_last=self.name_last.data,
            character_id=self.character_id.data,
        ):
            msg = "Character name must not already exist."
            raise ValidationError(msg)


class EditProfile(MethodView):
    """Edit the character's profile, aka, the top of a character sheet."""

    decorators: ClassVar = [requires_authorization]

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
            "creed_name": character.creed_name if character.creed_name else "",
            "tribe": character.tribe if character.tribe else "",
            "auspice": character.auspice if character.auspice else "",
            "breed": character.breed if character.breed else "",
            "clan_name": character.clan_name if character.clan_name else "",
        }

        form = await ProfileForm().create_form(data=data_from_db)
        if character.char_class_name != "HUNTER":
            del form.creed_name
        if character.char_class_name != "VAMPIRE":
            del form.clan_name
            del form.sire
            del form.generation
        if character.char_class_name not in ("WEREWOLF", "CHANGELING"):
            del form.breed
            del form.tribe
            del form.auspice

        return form

    async def get(self, character_id: str) -> str:
        """Handle GET requests."""
        character = await Character.get(character_id)
        if not character:
            abort(HTTPStatus.BAD_REQUEST.value)

        return catalog.render(
            "character_edit.EditProfile",
            character=character,
            form=await self._build_form(character),
            join_label=False,
            floating_label=True,
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
                await sync_channel_to_discord(obj=character, update_type="update")

                await character.save()
                await post_to_audit_log(
                    msg=f"Character {character.name} edited",
                    view=self.__class__.__name__,
                )

                # Rebuild the session with the new character data
                await update_session()

            url = url_for(
                "character_view.view",
                character_id=character_id,
                success_msg="<strong>Character updated!</strong>"
                if has_updates
                else "No changes made.",
            )
            return f'<script>window.location.href="{url}"</script>'

        # If POST request does not validate, return errors
        return catalog.render(
            "character_edit.ProfileForm",
            form=form,
            join_label=False,
            floating_label=True,
            character=character,
        )
