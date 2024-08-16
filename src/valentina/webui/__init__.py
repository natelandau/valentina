"""Quart application for the Valentina web interface."""

import quart_flask_patch  # isort: skip # noqa: F401
import asyncio
from pathlib import Path

from flask_discord import DiscordOAuth2Session
from hypercorn.asyncio import serve
from hypercorn.config import Config
from loguru import logger
from quart import Quart, redirect, request
from quart_session import Session
from werkzeug.wrappers.response import Response

from valentina.utils import ValentinaConfig
from valentina.webui.utils.errors import register_error_handlers
from valentina.webui.utils.jinja_filters import register_filters
from valentina.webui.utils.jinjax import register_jinjax_catalog

# Allow insecure transport for debugging from localhost
if ValentinaConfig().webui_debug:
    import os

    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"


template_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"
app = Quart(
    __name__, template_folder=str(template_dir), static_url_path="/static", static_folder="static"
)
app.config["SECRET_KEY"] = ValentinaConfig().webui_secret_key
app.config["DISCORD_CLIENT_ID"] = ValentinaConfig().discord_oauth_client_id
app.config["DISCORD_CLIENT_SECRET"] = ValentinaConfig().discord_oauth_secret
app.config["DISCORD_REDIRECT_URI"] = f"{ValentinaConfig().webui_base_url}/callback"
app.config["DISCORD_BOT_TOKEN"] = ValentinaConfig().discord_token
discord_oauth = DiscordOAuth2Session(app)
register_filters(app)
register_error_handlers(app)
catalog = register_jinjax_catalog(app)
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_URI"] = (
    (f"redis://:{ValentinaConfig().redis_password}@{ValentinaConfig().redis_addr}")
    if {ValentinaConfig().redis_addr}
    else f"redis://{ValentinaConfig().redis_addr}"
)
Session(app)


def import_blueprints() -> None:
    """Import routes to avoid circular imports."""
    from .blueprints import campaign_bp, character_bp, gameplay_bp
    from .routes import home, oauth

    app.register_blueprint(campaign_bp)
    app.register_blueprint(character_bp)
    app.register_blueprint(home.bp)
    app.register_blueprint(oauth.bp)
    app.register_blueprint(gameplay_bp)


def create_dev_app() -> Quart:
    """Create a new Quart app with the given configuration. This is used for development only."""
    # Always import blueprints to avoid circular imports
    import_blueprints()

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

    @app.before_request
    def remove_trailing_slash() -> Response:
        """Redirect requests with trailing slashes to the correct URL.

        example.com/url/ -> example.com/url
        """
        request_path: str = request.path
        if request_path != "/" and request_path.endswith("/"):
            return redirect(request_path[:-1], 301)

        return None

    return app


async def run_webserver() -> None:
    """Run the web server in production."""
    # Imnport these here to avoid circular imports
    import_blueprints()

    @app.before_request
    def remove_trailing_slash() -> Response:
        """Redirect requests with trailing slashes to the correct URL.

        example.com/url/ -> example.com/url
        """
        request_path: str = request.path
        if request_path != "/" and request_path.endswith("/"):
            return redirect(request_path[:-1], 301)

        return None

    hypercorn_config = Config()
    hypercorn_config.bind = [f"{ValentinaConfig().webui_host}:{ValentinaConfig().webui_port}"]
    hypercorn_config.loglevel = ValentinaConfig().webui_log_level.upper()
    hypercorn_config.use_reloader = ValentinaConfig().webui_debug
    await serve(app, hypercorn_config, shutdown_trigger=lambda: asyncio.Future())
