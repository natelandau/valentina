"""Define and configure the Quart application for the Valentina web interface.

This module initializes the Quart application, sets up Discord OAuth2 integration,
configures session management with Redis, and registers custom filters, error handlers,
and JinjaX templates. It serves as the main entry point for the Valentina web UI.
"""

import quart_flask_patch  # isort: skip # noqa: F401
import asyncio
import os
from typing import assert_never

from flask_discord import DiscordOAuth2Session
from hypercorn.asyncio import serve
from hypercorn.config import Config as HypercornConfig
from hypercorn.middleware import ProxyFixMiddleware
from quart import Quart, redirect, request
from quart_session import Session
from werkzeug.wrappers.response import Response

from valentina.constants import WEBUI_ROOT_PATH, WebUIEnvironment
from valentina.utils import ValentinaConfig
from valentina.webui.utils.blueprints import import_all_bps
from valentina.webui.utils.errors import register_error_handlers
from valentina.webui.utils.jinjax import register_jinjax_catalog

# Allow insecure transport for OAuth2. This is used for development or when running behind a reverse proxy.
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

discord_oauth = DiscordOAuth2Session()
catalog = register_jinjax_catalog()


def configure_app(environment: WebUIEnvironment) -> Quart:
    """Configure the Quart application."""
    app = Quart(
        __name__,
        template_folder=str(WEBUI_ROOT_PATH / "shared"),
        static_url_path="/static",
        static_folder="static",
    )
    app.config.from_object(f"valentina.webui.config.{environment}")

    register_error_handlers(app)
    discord_oauth.init_app(app)
    import_all_bps(app)
    app.jinja_env.globals["catalog"] = catalog

    catalog.jinja_env.globals.update(app.jinja_env.globals)
    catalog.jinja_env.filters.update(app.jinja_env.filters)
    catalog.jinja_env.tests.update(app.jinja_env.tests)
    catalog.jinja_env.extensions.update(app.jinja_env.extensions)

    if app.config.get("SESSION_TYPE", "").lower() == "redis":  # pragma: no cover
        Session(app)

    # Don't require REDIS for session storage in development mode
    if environment == WebUIEnvironment.DEVELOPMENT:
        app.config["SESSION_COOKIE_SECURE"] = False

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


async def create_app(environment: WebUIEnvironment) -> Quart | None:
    """Create and configure a Quart application for the Valentina web interface.

    Args:
        environment (WebUIEnvironment): The environment in which the application will run to determine the configuration settings.

    Returns:
        Quart: A configured Quart application instance ready for use.
    """
    app = configure_app(environment)

    match environment:
        case WebUIEnvironment.DEVELOPMENT:
            await app.run_task(
                host=ValentinaConfig().webui_host,
                port=int(ValentinaConfig().webui_port),
                debug=True,
                shutdown_trigger=lambda: asyncio.Future(),
                # use_reloader=True, # Commented out because it's not compatible with run_task, only with run()  # noqa: ERA001
            )
        case WebUIEnvironment.PRODUCTION:
            await run_production_server(app)

        case WebUIEnvironment.TESTING:
            # Only return the app in testing mode so that the test suite can handle it with a test_client()
            return app
        case _:
            assert_never(environment)

    return app


async def run_production_server(app: Quart) -> None:  # pragma: no cover
    """Run the Quart web server in a production environment.

    Call this function to initiate the server in production mode. The server will run
    indefinitely until manually stopped or an unhandled exception occurs.

    Note: Ensure all required configurations are properly set in ValentinaConfig
    before calling this function.

    Args:
        app (Quart): The Quart application to run.
    """
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
