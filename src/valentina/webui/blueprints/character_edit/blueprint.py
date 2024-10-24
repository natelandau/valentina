"""Blueprint for editing characters."""

from quart import Blueprint

from .route_profile import EditProfile
from .route_spend_points import SpendPoints, SpendPointsType

blueprint = Blueprint("character_edit", __name__)

blueprint.add_url_rule(
    "/character/<string:character_id>/spendfreebie",
    view_func=SpendPoints.as_view(
        SpendPointsType.FREEBIE.value, spend_type=SpendPointsType.FREEBIE
    ),
    methods=["GET", "POST"],
)
blueprint.add_url_rule(
    "/character/<string:character_id>/spendexperience",
    view_func=SpendPoints.as_view(
        SpendPointsType.EXPERIENCE.value, spend_type=SpendPointsType.EXPERIENCE
    ),
    methods=["GET", "POST"],
)
blueprint.add_url_rule(
    "/character/<string:character_id>/spendstoryteller",
    view_func=SpendPoints.as_view(
        SpendPointsType.STORYTELLER.value, spend_type=SpendPointsType.STORYTELLER
    ),
    methods=["GET", "POST"],
)
blueprint.add_url_rule(
    "/character/<string:character_id>/editprofile",
    view_func=EditProfile.as_view("profile"),
    methods=["GET", "POST"],
)
