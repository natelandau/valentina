"""Logic for RNG character creation."""

from typing import ClassVar

from beanie import DeleteRules
from flask_discord import requires_authorization
from loguru import logger
from quart import abort, request, session, url_for
from quart.views import MethodView
from werkzeug.wrappers.response import Response

from valentina.constants import STARTING_FREEBIE_POINTS, DBSyncUpdateType, HTTPStatus, RNGCharLevel
from valentina.controllers import RNGCharGen
from valentina.models import Character
from valentina.webui import catalog
from valentina.webui.utils import (
    fetch_active_campaign,
    fetch_user,
    sync_char_to_discord,
    update_session,
)
from valentina.webui.utils.discord import post_to_audit_log


class CreateRNGCharacter(MethodView):
    """Create an RNG character."""

    decorators: ClassVar = [requires_authorization]

    async def get(self) -> str:
        """Create a page for a user to select one of three RNG characters or re-roll the choices."""
        # Because there are a few edge cases (such as a page reload) where previous chargen characters may not have been deleted, we delete them here.
        async for char in Character.find(
            Character.type_chargen == True,  # noqa: E712
            Character.user_owner == session["USER_ID"],
        ):
            logger.debug(f"Draft RNG characters out of state, deleting invalid character {char.id}")
            await char.delete(link_rule=DeleteRules.DELETE_LINKS)

        # Create three new RNG characters for the user to choose from
        user = await fetch_user()
        chargen = RNGCharGen(
            guild_id=session["GUILD_ID"], user=user, experience_level=RNGCharLevel.NEW
        )

        # Create three characters for the user to choose from
        characters = [
            await chargen.generate_full_character(chargen_character=True) for _ in range(3)
        ]

        # Add the created characters to the session so they can be acted upon in the next step
        # use a dictionary with the index as the key
        session["RNG_DRAFT_CHARACTERS"] = {
            i: str(char.id) for i, char in enumerate(characters, start=1)
        }

        selected_campaign = await fetch_active_campaign(request.args.get("campaign_id", None))

        remaining_xp = None
        if not session["IS_STORYTELLER"]:
            user = await fetch_user()
            remaining_xp = await user.spend_campaign_xp(selected_campaign, 10)

        return catalog.render(
            "character_create.RNG",
            selected_campaign=selected_campaign,
            remaining_xp=remaining_xp,
            rng_characters=characters,
            character_type=request.args.get("character_type", "player"),
            error_msg=request.args.get("error_msg", ""),
            success_msg=request.args.get("success_msg", ""),
            info_msg=request.args.get("info_msg", ""),
            warning_msg=request.args.get("warning_msg", ""),
        )

    async def post(self) -> str | Response:
        """Handle POST requests to the RNG character creation page."""
        form = await request.form

        if form.get("reroll", None) == "true":
            return Response(
                headers={
                    "HX-Redirect": url_for(
                        "character_create.rng",
                        character_type=request.args["character_type"],
                        campaign_id=request.args["campaign_id"],
                    )
                }
            )

        if selected_character_num := form.get("char_select", None):
            for num, character_id in session["RNG_DRAFT_CHARACTERS"].items():
                character = await Character.get(character_id)

                # Delete characters that were not selected
                if num != selected_character_num:
                    logger.debug(f"CHARGEN: Deleting unselected character {character_id}")
                    await character.delete(link_rule=DeleteRules.DELETE_LINKS)
                    continue

                # Add the selected character to the campaign and the player or storyteller
                character.freebie_points = STARTING_FREEBIE_POINTS
                character.type_player = bool(request.args["character_type"] == "player")
                character.type_storyteller = bool(request.args["character_type"] == "storyteller")
                character.type_chargen = False
                character.campaign = request.args["campaign_id"]
                await character.save()

                await sync_char_to_discord(character, DBSyncUpdateType.CREATE)
                await post_to_audit_log(
                    msg=f"Character {character.full_name} created",
                    view=self.__class__.__name__,
                )
                logger.info(f"WEBUI: Character {character_id} created")
                redirect_char_id = str(character.id)

            del session["RNG_DRAFT_CHARACTERS"]
            await update_session()

            return Response(
                headers={
                    "HX-Redirect": url_for(
                        "character_view.view",
                        character_id=redirect_char_id,
                        success_msg="<strong>Character created successfully.</strong><br>You have 24 hours to spend freebie points and edit the character before it is locked.",
                    )
                }
            )

        return abort(HTTPStatus.INTERNAL_SERVER_ERROR.value)
