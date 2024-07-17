"""Routes for the home page."""

import random

from flask_discord import requires_authorization
from quart import Blueprint, redirect, request, session, url_for
from quart.views import MethodView
from werkzeug.wrappers import Response

from valentina.constants import BOT_DESCRIPTIONS
from valentina.utils import console
from valentina.webui import catalog, discord_oauth
from valentina.webui.utils.helpers import update_session

bp = Blueprint("homepage", __name__)


homepage_description = f"Valentina, your {random.choice(['honored', 'admired', 'distinguished', 'celebrated', 'hallowed', 'prestigious', 'acclaimed', 'favorite', 'friendly neighborhood', 'prized', 'treasured', 'number one', 'esteemed', 'venerated', 'revered', 'feared'])} {random.choice(BOT_DESCRIPTIONS)}, is ready for you!\n"


class HomepageView(MethodView):
    """View to handle homepage operations."""

    async def get(self) -> str:
        """Handle GET requests."""
        await update_session(session)
        console.rule("Session")
        for key, value in session.items():
            console.log(f"{key}={value}")
        console.rule()

        if not discord_oauth.authorized or not session["USER_ID"]:
            return catalog.render("homepage", homepage_description=homepage_description)

        return catalog.render("homepage", homepage_description=homepage_description)


homepage = HomepageView.as_view("homepage")
bp.add_url_rule("/", view_func=homepage, methods=["GET"])


@bp.route("/select-guild/", methods=["GET", "POST"])
@requires_authorization
async def select_guild() -> str | Response:
    """Select a guild to play in."""
    if request.method == "POST":
        form = await request.form

        session["GUILD_ID"] = int(form["guild_id"])
        del session["matched_guilds"]
        await update_session(session)

        return redirect(url_for("homepage.homepage"))

    user = discord_oauth.fetch_user()

    return catalog.render("guild_select", user=user, matched_guilds=session["matched_guilds"])
