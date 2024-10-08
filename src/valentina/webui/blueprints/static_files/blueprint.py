"""Routes for serving static files."""

from flask_discord import requires_authorization
from quart import Blueprint, request, send_from_directory
from quart.wrappers.response import Response as QuartResponse

from valentina.constants import USER_GUIDE_PATH, WEBUI_STATIC_DIR_PATH
from valentina.webui import catalog

blueprint = Blueprint("static_files", __name__)


@blueprint.route("/robots.txt")
async def static_from_root() -> QuartResponse:
    """Serve a static file from the root directory."""
    return await send_from_directory(WEBUI_STATIC_DIR_PATH, request.path[1:])


@requires_authorization
@blueprint.route("/user-guide")
async def user_guide() -> str:
    """Serve the user guide."""
    guide_content = USER_GUIDE_PATH.read_text()

    return catalog.render("static_files.UserGuide", guide=guide_content)
