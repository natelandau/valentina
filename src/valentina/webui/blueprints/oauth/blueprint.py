"""Route for Discord OAuth2 authentication."""

from typing import Any

from loguru import logger
from quart import Blueprint, abort, redirect, session, url_for

from valentina.models import User
from valentina.webui import discord_oauth
from valentina.webui.utils import update_session

blueprint = Blueprint("oauth", __name__)


@blueprint.route("/login")
async def login() -> Any:  # pragma: no cover
    """Login route."""
    return discord_oauth.create_session()


@blueprint.route("/logout")
async def logout() -> Any:  # pragma: no cover
    """Login route."""
    session.clear()
    discord_oauth.revoke()
    return redirect(url_for("homepage.homepage"))


@blueprint.route("/callback")
async def callback() -> Any:  # pragma: no cover
    """Callback route.  Sets initial session variables.

    session["USER_ID"] = user.id

    # if one guild, set GUILD_ID
    session["GUILD_ID"] = guiid.id
    # if multiple guilds, set matched_guilds
    session["matched_guilds"] = matched_guilds
    """
    discord_oauth.callback()

    user = discord_oauth.fetch_user()
    session["USER_ID"] = user.id

    db_user = await User.get(user.id)

    # Deny access to users who aren't playing in a guild
    # TODO: Add a custom page for this
    if not db_user:
        logger.error(f"User {user.id} is not in the database.")
        abort(403)

    matched_guilds = [
        {"id": x.id, "name": x.name} for x in user.fetch_guilds() if int(x.id) in db_user.guilds
    ]

    if not matched_guilds:
        abort(403)

    if len(matched_guilds) == 1:
        session["GUILD_ID"] = matched_guilds[0]["id"]
        await update_session()
        return redirect(url_for("homepage.homepage"))

    session["matched_guilds"] = matched_guilds
    return redirect(url_for("homepage.select_guild"))
