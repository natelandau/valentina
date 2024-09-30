"""Blueprint for character_view."""

from quart import Blueprint

from .route import DiceRollView, GameplayView

blueprint = Blueprint("gameplay", __name__)
blueprint.add_url_rule("/gameplay", view_func=GameplayView.as_view("gameplay"), methods=["GET"])
blueprint.add_url_rule(
    "/gameplay/diceroll",
    view_func=DiceRollView.as_view("diceroll"),
    methods=["GET", "POST"],
)
