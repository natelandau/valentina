"""Blueprint for admin and storyteller specific routes."""

from quart import Blueprint

from .route import AdminView

blueprint = Blueprint("admin", __name__)

blueprint.add_url_rule(
    "/admin",
    view_func=AdminView.as_view("home"),
    methods=["GET", "POST"],
)
