"""Blueprint for editing characters."""

from quart import Blueprint

from .route_spend_points import SpendPoints, SpendPointsType

blueprint = Blueprint("character_edit", __name__)

blueprint.add_url_rule(
    "/character/<string:character_id>/spendfreebie",
    view_func=SpendPoints.as_view("freebie", spend_type=SpendPointsType.FREEBIE),
    methods=["GET", "POST"],
)
blueprint.add_url_rule(
    "/character/<string:character_id>/spendexperience",
    view_func=SpendPoints.as_view("experience", spend_type=SpendPointsType.EXPERIENCE),
    methods=["GET", "POST"],
)
