"""Views for the homepage."""

from flask_discord import requires_authorization
from quart import Blueprint, redirect, request, session, url_for
from werkzeug.wrappers.response import Response

from valentina.webui import catalog, discord_oauth
from valentina.webui.utils.helpers import update_session

from .route import HomepageView

blueprint = Blueprint("homepage", __name__)
blueprint.add_url_rule("/", view_func=HomepageView.as_view("homepage"), methods=["GET"])


@blueprint.route("/select-guild", methods=["GET", "POST"])
@requires_authorization
async def select_guild() -> str | Response:
    """Select a guild to play in."""
    if request.method == "POST":
        form = await request.form

        session["GUILD_ID"] = int(form["guild_id"])
        del session["matched_guilds"]
        await update_session()

        return redirect(url_for("homepage.homepage"))

    user = discord_oauth.fetch_user()

    return catalog.render("guild_select", user=user, matched_guilds=session["matched_guilds"])
