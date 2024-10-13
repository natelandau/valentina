"""Blueprints for character_create."""

from flask_discord import requires_authorization
from loguru import logger
from quart import Blueprint, request

from valentina.webui import catalog
from valentina.webui.utils import fetch_active_campaign, fetch_user, update_session

from .route_create_full import (
    CreateCharacterStep1,
    CreateCharacterStep2,
    CreateCharacterStep3,
)

blueprint = Blueprint("character_create", __name__)


@requires_authorization
@blueprint.route("/create_character", methods=["GET", "POST"])
async def start() -> str:
    """Load the starting page for character creation."""
    await update_session()

    if request.method == "POST":
        logger.warning("POST request to /create_character, but no logic implemented.")
        form = await request.form
        selected_campaign = await fetch_active_campaign(form["campaign"])

    available_experience = None
    selected_campaign = await fetch_active_campaign()
    if selected_campaign:
        user = await fetch_user()
        available_experience = user.fetch_campaign_xp(selected_campaign)[0]

    return catalog.render(
        "character_create.Main",
        selected_campaign=selected_campaign,
        available_experience=available_experience,
    )


blueprint.add_url_rule(
    "/create_character/1",
    view_func=CreateCharacterStep1.as_view("create_1"),
    methods=["GET", "POST"],
)
blueprint.add_url_rule(
    "/create_character/2/<string:character_id>/<string:char_class>",
    view_func=CreateCharacterStep2.as_view("create_2"),
    methods=["GET", "POST"],
)
blueprint.add_url_rule(
    "/create_character/3/<string:character_id>",
    view_func=CreateCharacterStep3.as_view("create_3"),
    methods=["GET", "POST"],
)
