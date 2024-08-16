"""Custom errors for the webui."""

from flask_discord import Unauthorized
from quart import Quart, redirect, render_template, url_for
from werkzeug.exceptions import HTTPException
from werkzeug.wrappers.response import Response


def register_error_handlers(app: Quart) -> None:
    """Register error handlers for the app."""

    @app.errorhandler(Unauthorized)
    async def redirect_unauthorized(e: type[Exception] | int) -> Response:  # noqa: ARG001
        """Redirect unauthorized users to the login page."""
        return redirect(url_for("oauth.login"))

    @app.errorhandler(HTTPException)
    async def error_handler(exc: HTTPException) -> str:
        """Use a custom error handler for HTTP exceptions."""
        return await render_template(
            "error.html",
            detail=exc.description,
            status_code=exc.code,
            page_title=f"{exc.code} Error",
        )
