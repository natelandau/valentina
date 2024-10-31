"""Route for storyteller RNG character creation.

Unlike players, Storytellers get to select the class, level, and other options for a character to allow them to quickly build a character for use in a campaign.
"""

import random
from enum import Enum
from typing import ClassVar

from flask_discord import requires_authorization
from quart import Response, abort, request, session, url_for
from quart.views import MethodView
from quart_wtf import QuartForm
from wtforms import HiddenField, SelectField, SubmitField
from wtforms.validators import DataRequired

from valentina.constants import (
    CharacterConcept,
    CharClass,
    DBSyncUpdateType,
    HTTPStatus,
    NameNationality,
    RNGCharLevel,
)
from valentina.controllers import RNGCharGen
from valentina.webui import catalog
from valentina.webui.utils import (
    fetch_active_campaign,
    fetch_user,
    sync_char_to_discord,
    update_session,
)
from valentina.webui.utils.discord import post_to_audit_log


class Gender(Enum):
    """Gender options."""

    MALE = "male"
    FEMALE = "female"

    @classmethod
    def random_member(cls) -> "Gender":
        """Return a random gender."""
        return random.choice(list(cls))

    @classmethod
    def random_member_value(cls) -> str:
        """Return a random gender value."""
        return cls.random_member().value


class StorytellerRNGStartForm(QuartForm):
    """Form for the storyteller to start RNG character creation."""

    gender = SelectField(
        "Gender",
        choices=[("", "-- Select --")] + [(x.value, x.name.capitalize()) for x in Gender],
        description="Used to generate a name",
        validators=[],
    )

    nationality = SelectField(
        "Nationality",
        choices=[("", "-- Select --")] + [(x.name, x.name.capitalize()) for x in NameNationality],
        description="Used to generate a name",
        validators=[],
    )

    level = SelectField(
        "Level",
        choices=[("", "-- Select --")] + [(x.name, x.name.capitalize()) for x in RNGCharLevel],
        description="How powerful the character is",
        validators=[DataRequired()],
    )

    char_class = SelectField(
        "Character Class",
        choices=[("", "-- Select --")]
        + [(x.name, x.name.capitalize()) for x in CharClass.playable_classes()],
        validators=[DataRequired()],
    )

    concept = SelectField(
        "Concept",
        choices=[("", "-- Select --")] + [(x.name, x.name.capitalize()) for x in CharacterConcept],
        validators=[DataRequired()],
    )

    campaign_id = HiddenField()
    submit = SubmitField("Build Character")
    cancel = SubmitField("Cancel")


class CreateStorytellerRNGCharacter(MethodView):
    """Create a storyteller RNG character."""

    decorators: ClassVar = [requires_authorization]

    async def _build_form(self) -> StorytellerRNGStartForm:
        """Build the form."""
        data = {}
        if campaign_id := request.args.get("campaign_id"):
            data["campaign_id"] = campaign_id

        return await StorytellerRNGStartForm().create_form(data=data)

    async def get(self) -> str:
        """Render the form."""
        campaign_id = request.args.get("campaign_id")
        if not campaign_id:
            abort(HTTPStatus.BAD_REQUEST.value)

        form = await self._build_form()

        return catalog.render(
            "character_create/StorytellerRNGForm",
            form=form,
            join_label=False,
            floating_label=True,
            post_url=url_for("character_create.rng_storyteller"),
        )

    async def post(self) -> str | Response:
        """Process the form."""
        form = await self._build_form()

        if not form.validate_on_submit():
            return catalog.render(
                "character_create/StorytellerRNGForm",
                form=form,
                join_label=False,
                floating_label=True,
                post_url=url_for("character_create.rng_storyteller"),
            )

        from valentina.utils import console

        console.rule("PROCESS FORM")
        console.log(f"{form.data=}")

        if form.cancel.data:
            return Response(
                headers={
                    "HX-Redirect": url_for(
                        "character_create.start", campaign_id=form.campaign_id.data
                    )
                }
            )

        # Create the character
        user = await fetch_user()
        campaign = await fetch_active_campaign(form.campaign_id.data)

        if form.level.data:
            experience_level = RNGCharLevel[form.level.data]
        else:
            experience_level = RNGCharLevel.random_member()

        chargen = RNGCharGen(
            guild_id=session["GUILD_ID"],
            user=user,
            experience_level=experience_level,
            campaign=campaign,
        )

        generated_character = await chargen.generate_full_character(
            char_class=CharClass[form.char_class.data] if form.char_class.data else None,
            storyteller_character=True,
            player_character=False,
            nationality=form.nationality.data if form.nationality.data else None,
            gender=form.gender.data if form.gender.data else None,
            concept=CharacterConcept[form.concept.data] if form.concept.data else None,
        )

        await post_to_audit_log(
            f"{user.name} created storyteller character {generated_character.full_name}"
        )
        await sync_char_to_discord(generated_character, DBSyncUpdateType.CREATE)
        await update_session()

        return Response(
            headers={
                "HX-Redirect": url_for(
                    "character_view.view",
                    character_id=str(generated_character.id),
                    success_msg="<strong>Character created successfully.</strong>",
                )
            }
        )
