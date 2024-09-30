"""Blueprint for character_view."""

from quart import Blueprint

from .route import CharacterEdit, CharacterView

blueprint = Blueprint("character_view", __name__)
blueprint.add_url_rule(
    "/character/<string:character_id>",
    view_func=CharacterView.as_view("view"),
    methods=["GET", "POST"],
)
blueprint.add_url_rule(
    "/character/<string:character_id>/edit",
    view_func=CharacterEdit.as_view("edit"),
    methods=["GET", "POST"],
)
