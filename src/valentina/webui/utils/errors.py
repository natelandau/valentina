"""Custom errors for the webui."""

from flask_discord import Unauthorized
from quart import Quart, redirect, render_template, url_for
from werkzeug.exceptions import HTTPException
from werkzeug.wrappers.response import Response


def register_error_handlers(app: Quart) -> None:
    """Register custom error handlers for the Quart application.

    Set up error handlers for unauthorized access and general HTTP exceptions.
    Unauthorized users are redirected to the login page, and other HTTP
    exceptions are handled by rendering a custom error page.

    Args:
        app (Quart): The Quart application instance to which the error handlers
        will be registered.

    Returns:
        None
    """

    @app.errorhandler(Unauthorized)
    async def redirect_unauthorized(e: type[Exception] | int) -> Response:  # noqa: ARG001 # pragma: no cover
        """Redirect unauthorized users to the login page.

        Args:
            e (type[Exception] | int): The exception or error code that triggered the handler.

        Returns:
            Response: A redirect response to the login page.
        """
        return redirect(url_for("oauth.login"))

    @app.errorhandler(HTTPException)
    async def error_handler(exc: HTTPException) -> tuple[str, int]:
        """Handle HTTP exceptions by rendering a custom error page.

        Args:
            exc (HTTPException): The HTTP exception to be handled.

        Returns:
            str: The rendered HTML content of the custom error page.
        """
        return await render_template(
            "error.html",
            detail=exc.description,
            status_code=exc.code,
            page_title=f"{exc.code} Error",
        ), exc.code
