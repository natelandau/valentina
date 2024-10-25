"""Blueprint for editing characters."""

from quart import Blueprint

from .route_info import EditCharacterCustomSection, EditCharacterNote
from .route_profile import EditProfile
from .route_spend_points import SpendPoints, SpendPointsType

blueprint = Blueprint("character_edit", __name__)

blueprint.add_url_rule(
    "/character/<string:character_id>/spend/freebie",
    view_func=SpendPoints.as_view(
        SpendPointsType.FREEBIE.value, spend_type=SpendPointsType.FREEBIE
    ),
    methods=["GET", "POST"],
)
blueprint.add_url_rule(
    "/character/<string:character_id>/spend/experience",
    view_func=SpendPoints.as_view(
        SpendPointsType.EXPERIENCE.value, spend_type=SpendPointsType.EXPERIENCE
    ),
    methods=["GET", "POST"],
)
blueprint.add_url_rule(
    "/character/<string:character_id>/spend/storyteller",
    view_func=SpendPoints.as_view(
        SpendPointsType.STORYTELLER.value, spend_type=SpendPointsType.STORYTELLER
    ),
    methods=["GET", "POST"],
)
blueprint.add_url_rule(
    "/character/<string:character_id>/edit/profile",
    view_func=EditProfile.as_view("profile"),
    methods=["GET", "POST"],
)
blueprint.add_url_rule(
    "/character/<string:character_id>/edit/customsection",
    view_func=EditCharacterCustomSection.as_view("customsection"),
    methods=["GET", "POST", "DELETE"],
)
blueprint.add_url_rule(
    "/character/<string:character_id>/edit/note",
    view_func=EditCharacterNote.as_view("note"),
    methods=["GET", "POST", "DELETE"],
)
