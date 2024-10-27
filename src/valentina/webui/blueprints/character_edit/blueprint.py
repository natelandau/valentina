"""Blueprint for editing characters."""

from quart import Blueprint

from valentina.webui.constants import CharacterEditableInfo

from .route_info import EditCharacterInfo
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
    f"/character/<string:character_id>/edit/{CharacterEditableInfo.CUSTOM_SECTION.value}",
    view_func=EditCharacterInfo.as_view(
        CharacterEditableInfo.CUSTOM_SECTION.value, edit_type=CharacterEditableInfo.CUSTOM_SECTION
    ),
    methods=["GET", "POST", "DELETE"],
)
blueprint.add_url_rule(
    f"/character/<string:character_id>/edit/{CharacterEditableInfo.NOTE.value}",
    view_func=EditCharacterInfo.as_view(
        CharacterEditableInfo.NOTE.value, edit_type=CharacterEditableInfo.NOTE
    ),
    methods=["GET", "POST", "DELETE"],
)
blueprint.add_url_rule(
    f"/character/<string:character_id>/edit/{CharacterEditableInfo.INVENTORY.value}",
    view_func=EditCharacterInfo.as_view(
        CharacterEditableInfo.INVENTORY.value, edit_type=CharacterEditableInfo.INVENTORY
    ),
    methods=["GET", "POST", "DELETE"],
)
