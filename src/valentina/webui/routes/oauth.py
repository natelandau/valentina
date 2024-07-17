"""Route for Discord OAuth2 authentication."""

from typing import Any

from quart import Blueprint, abort, redirect, session, url_for

from valentina.models import User
from valentina.webui import discord_oauth
from valentina.webui.utils import update_session

bp = Blueprint("oauth", __name__)


@bp.route("/login/")
async def login() -> Any:
    """Login route."""
    return discord_oauth.create_session()


@bp.route("/logout/")
async def logout() -> Any:
    """Login route."""
    session.clear()
    discord_oauth.revoke()
    return redirect(url_for("homepage.homepage"))


@bp.route("/callback/")
async def callback() -> Any:
    """Callback route."""
    discord_oauth.callback()

    user = discord_oauth.fetch_user()
    session["USER_ID"] = user.id

    db_user = await User.get(user.id)

    # Deny access to users who aren't playing in a guild
    # TODO: Add a custom page for this
    if not db_user:
        abort(403)

    matched_guilds = [
        {"id": x.id, "name": x.name} for x in user.fetch_guilds() if int(x.id) in db_user.guilds
    ]

    if not matched_guilds:
        abort(403)

    if len(matched_guilds) == 1:
        session["GUILD_ID"] = matched_guilds[0]["id"]
        await update_session(session)
        return redirect(url_for("index"))

    session["matched_guilds"] = matched_guilds
    return redirect(url_for("homepage.select_guild"))
