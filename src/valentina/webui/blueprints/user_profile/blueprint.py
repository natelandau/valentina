"""Blueprint for the user profile."""

from quart import Blueprint

from .route import UserProfile

blueprint = Blueprint("user_profile", __name__)

blueprint.add_url_rule(
    "/user/<int:user_id>",
    view_func=UserProfile.as_view("view"),
    methods=["GET"],
)
