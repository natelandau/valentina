"""Quart application for the Valentina web interface."""

import quart_flask_patch  # isort: skip # noqa: F401
import asyncio
from pathlib import Path
from typing import Any

import jinjax
from flask_discord import DiscordOAuth2Session, Unauthorized
from flask_discord.models import User as FlaskDiscordUser
from hypercorn.asyncio import serve
from hypercorn.config import Config
from loguru import logger
from quart import Quart, redirect, render_template, url_for
from werkzeug.exceptions import HTTPException

from valentina.utils import ValentinaConfig
from valentina.webui.utils.jinja_filters import from_markdown

# Allow insecure transport for debugging from localhost
if ValentinaConfig().webui_debug:
    import os

    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


template_dir = Path(__file__).parent / "templates"
app = Quart(
    __name__, template_folder=str(template_dir), static_url_path="/static", static_folder="static"
)
app.config["SECRET_KEY"] = ValentinaConfig().webui_secret_key
app.config["DISCORD_CLIENT_ID"] = ValentinaConfig().discord_oauth_client_id
app.config["DISCORD_CLIENT_SECRET"] = ValentinaConfig().discord_oauth_secret
app.config["DISCORD_REDIRECT_URI"] = f"{ValentinaConfig().webui_base_url}/callback/"
app.config["DISCORD_BOT_TOKEN"] = ValentinaConfig().discord_token

discord_oauth = DiscordOAuth2Session(app)
catalog = jinjax.Catalog(jinja_env=app.jinja_env)
catalog.add_folder(Path(__file__).parent / "components")
catalog.add_folder(Path(__file__).parent / "templates")
app.jinja_env.globals["catalog"] = catalog
catalog.jinja_env.filters.update({"from_markdown": from_markdown})


async def error_handler(exc: HTTPException) -> str:
    """Use a custom error handler for HTTP exceptions."""
    return await render_template(
        "error.html",
        detail=exc.description,
        status_code=exc.code,
        page_title=f"{exc.code} Error",
    )


app.register_error_handler(HTTPException, error_handler)


@app.errorhandler(Unauthorized)
async def redirect_unauthorized(e: Any) -> Any:  # noqa: ARG001
    """Redirect unauthorized users to the login page."""
    return redirect(url_for("oauth.login"))


def import_routes() -> None:
    """Import routes to avoid circular imports."""
    from .routes import campaigns, characters, gameplay, home, oauth

    app.register_blueprint(campaigns.bp)
    app.register_blueprint(characters.bp)
    app.register_blueprint(home.bp)
    app.register_blueprint(oauth.bp)
    app.register_blueprint(gameplay.bp)


def create_dev_app() -> Quart:
    """Create a new Quart app with the given configuration. This is used for development only."""
    import_routes()

    @app.before_serving
    async def create_db_pool() -> None:
        """Initialize the database connection pool."""
        import pymongo

        from valentina.utils.database import init_database

        while True:
            try:
                await init_database()
            except pymongo.errors.ServerSelectionTimeoutError as e:
                logger.error(f"DB: Failed to initialize database: {e}")
                await asyncio.sleep(60)
            else:
                break

    return app


async def run_webserver() -> None:
    """Run the web server in production."""
    # Imnport these here to avoid circular imports
    import_routes()

    hypercorn_config = Config()
    hypercorn_config.bind = [f"{ValentinaConfig().webui_host}:{ValentinaConfig().webui_port}"]
    hypercorn_config.loglevel = ValentinaConfig().webui_log_level.upper()
    hypercorn_config.use_reloader = ValentinaConfig().webui_debug
    await serve(app, hypercorn_config, shutdown_trigger=lambda: asyncio.Future())


async def send_user_dm(user: FlaskDiscordUser, message: str) -> dict | str:
    """Send private message message in Discord to a user.

    Args:
        user (FlaskDiscordUser): The user to send the message to.
        message (str): The message to send.
    """
    dm_channel = discord_oauth.bot_request(
        "/users/@me/channels", "POST", json={"recipient_id": user.id}
    )
    return discord_oauth.bot_request(
        f"/channels/{dm_channel['id']}/messages",
        "POST",
        json={"content": message},
    )
