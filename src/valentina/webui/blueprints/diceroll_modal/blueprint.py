"""Blueprint for the dice roll modal."""

from flask import Blueprint

from .route import RollResults, RollSelector

blueprint = Blueprint("diceroll_modal", __name__)

blueprint.add_url_rule(
    "/diceroll_modal/<string:character_id>/<string:campaign_id>",
    view_func=RollSelector.as_view("roll_selector"),
)
blueprint.add_url_rule(
    "/diceroll_modal/<string:character_id>/<string:campaign_id>/results",
    view_func=RollResults.as_view("roll_results"),
    methods=["GET", "POST"],
)
