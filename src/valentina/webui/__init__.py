"""Define and configure the Quart application for the Valentina web interface.

This module initializes the Quart application, sets up Discord OAuth2 integration,
configures session management with Redis, and registers custom filters, error handlers,
and JinjaX templates. It serves as the main entry point for the Valentina web UI.
"""

import quart_flask_patch  # isort: skip # noqa: F401
import asyncio
import os
from typing import Literal

from flask_discord import DiscordOAuth2Session
from hypercorn.asyncio import serve
from hypercorn.config import Config as HypercornConfig
from hypercorn.middleware import ProxyFixMiddleware
from loguru import logger
from quart import Quart, redirect, request
from quart_session import Session
from werkzeug.wrappers.response import Response

from valentina.constants import WEBUI_ROOT_PATH
from valentina.utils import ValentinaConfig, console
from valentina.webui.utils.blueprints import import_all_bps
from valentina.webui.utils.errors import register_error_handlers
from valentina.webui.utils.jinjax import register_jinjax_catalog

# Allow insecure transport for OAuth2. This is used for development or when running behind a reverse proxy.
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

discord_oauth = DiscordOAuth2Session()
catalog = register_jinjax_catalog()


def create_app(environment: Literal["Production", "Development", "Testing"]) -> Quart:
    """Create and configure a Quart application for the Valentina web interface.

    Args:
        environment (Literal["Production", "Development", "Testing"]): The environment in which the application will run to determine the configuration settings.


    Returns:
        Quart: A configured Quart application instance ready for use.
    """
    app = Quart(
        __name__,
        template_folder=str(WEBUI_ROOT_PATH / "shared"),
        static_url_path="/static",
        static_folder="static",
    )
    app.config.from_object(f"valentina.webui.config.{environment}")

    register_error_handlers(app)
    discord_oauth.init_app(app)
    console.log("importing blueprints")
    import_all_bps(app)
    app.jinja_env.globals["catalog"] = catalog

    catalog.jinja_env.globals.update(app.jinja_env.globals)
    catalog.jinja_env.filters.update(app.jinja_env.filters)
    catalog.jinja_env.tests.update(app.jinja_env.tests)
    catalog.jinja_env.extensions.update(app.jinja_env.extensions)

    if app.config.get("SESSION_TYPE", "").lower() == "redis":
        Session(app)

    if environment == "Development":
        app.config["SESSION_COOKIE_SECURE"] = False

        @app.before_serving
        async def create_db_pool() -> None:
            """Initialize the database connection pool before the Quart application starts serving.

            Attempt to establish a connection to the database. If the initial connection fails:
            1. Log the error encountered during the connection attempt.
            2. Wait for 60 seconds before retrying.
            3. Repeat the process until a successful connection is established.

            This ensures that the application will eventually connect to the database, even if it's
            temporarily unavailable during startup. The function will not return until a successful
            connection is made, preventing the application from serving requests without a valid
            database connection.
            """
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

        Redirect URLs that end with a trailing slash (e.g., example.com/url/)
        to their non-slash counterparts (e.g., example.com/url) using a 301
        permanent redirect. If the URL does not end with a slash, allow the
        request to proceed as normal.
        """
        request_path: str = request.path
        if request_path != "/" and request_path.endswith("/"):
            return redirect(request_path[:-1], 301)

        return None

    return app


async def run_webserver() -> None:
    """Run the Quart web server in a production environment.

    Configure and start the Hypercorn server with settings derived from the application's configuration. This function performs the following tasks:

    1. Import necessary blueprints to avoid circular imports.
    2. Set up a request handler to remove trailing slashes from URLs.
    3. Create a Hypercorn configuration object with settings from ValentinaConfig.
    4. Start the server using the configured Hypercorn instance.

    Call this function to initiate the server in production mode. The server will run
    indefinitely until manually stopped or an unhandled exception occurs.

    Note: Ensure all required configurations are properly set in ValentinaConfig
    before calling this function.
    """
    app = create_app(environment="Production")

    hypercorn_config = HypercornConfig()
    hypercorn_config.bind = [f"{ValentinaConfig().webui_host}:{ValentinaConfig().webui_port}"]
    hypercorn_config.loglevel = ValentinaConfig().webui_log_level.upper()
    hypercorn_config.use_reloader = ValentinaConfig().webui_debug
    hypercorn_config.accesslog = ValentinaConfig().webui_access_log
    hypercorn_config.access_log_format = (
        '%(h)s %(l)s %(l)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s'
    )

    # Pass x-forwarded-for header if behind a reverse proxy
    # https://hypercorn.readthedocs.io/en/latest/how_to_guides/proxy_fix.html
    if ValentinaConfig().webui_behind_reverse_proxy:
        proxied_app = ProxyFixMiddleware(app, mode="legacy", trusted_hops=1)
        await serve(proxied_app, hypercorn_config, shutdown_trigger=lambda: asyncio.Future())
    else:
        await serve(app, hypercorn_config, shutdown_trigger=lambda: asyncio.Future())
