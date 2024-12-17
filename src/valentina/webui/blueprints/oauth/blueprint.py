"""Route for Discord OAuth2 authentication."""

from typing import Any

from loguru import logger
from quart import Blueprint, abort, redirect, session, url_for

from valentina.constants import HTTPStatus
from valentina.models import User
from valentina.utils import console
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

    oauth_user = discord_oauth.fetch_user()
    session["USER_ID"] = oauth_user.id
    db_user = await User.get(oauth_user.id)

    # Deny access to users who aren't playing in a guild
    # TODO: Add a custom page for this
    if not db_user:
        logger.error(f"User {oauth_user.name} with ID {oauth_user.id} is not in the database.")
        abort(HTTPStatus.BAD_REQUEST.value, f"User {oauth_user.name} is not in the database.")

    matched_guilds = [
        {"id": x.id, "name": x.name}
        for x in oauth_user.fetch_guilds()
        if int(x.id) in db_user.guilds
    ]

    if not matched_guilds:
        logger.error(f"User {oauth_user.name} is not in any known guilds.")
        console.print(
            f"In the DB, user {oauth_user.name} is associated with the following guilds: {db_user.guilds}"
        )
        console.print(
            f"In Discord, user {oauth_user.id} is associated with the following guilds: {[x.id for x in oauth_user.fetch_guilds()]}"
        )
        abort(HTTPStatus.BAD_REQUEST.value, f"User {oauth_user.name} is not in any known guilds.")

    if len(matched_guilds) == 1:
        logger.info(
            f"User {oauth_user.name} is known to one guild: {matched_guilds[0]["id"]}. Logging in."
        )
        session["GUILD_ID"] = matched_guilds[0]["id"]
        await update_session()
        return redirect(url_for("homepage.homepage"))

    session["matched_guilds"] = matched_guilds
    logger.info(
        f"User {oauth_user.name} is known to multiple guilds. Redirecting to guild selection before log in."
    )
    return redirect(url_for("homepage.select_guild"))
