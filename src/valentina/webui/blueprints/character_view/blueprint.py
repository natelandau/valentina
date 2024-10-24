"""Blueprint for character_view."""

from quart import Blueprint

from .route import CharacterView

blueprint = Blueprint("character_view", __name__)
blueprint.add_url_rule(
    "/character/<string:character_id>",
    view_func=CharacterView.as_view("view"),
    methods=["GET", "POST"],
)
