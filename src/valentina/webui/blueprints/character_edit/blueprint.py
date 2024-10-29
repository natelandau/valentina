"""Blueprint for editing characters."""

from quart import Blueprint

from valentina.webui.constants import CharacterEditableInfo

from .route_info import EditCharacterInfo
from .route_profile import EditProfile
from .route_spend_points import SpendPoints, SpendPointsType

blueprint = Blueprint("character_edit", __name__)

blueprint.add_url_rule(
    "/character/<string:character_id>/edit/profile",
    view_func=EditProfile.as_view("profile"),
    methods=["GET", "POST"],
)

for spend_type in SpendPointsType:
    blueprint.add_url_rule(
        f"/character/<string:character_id>/spend/{spend_type.value}",
        view_func=SpendPoints.as_view(spend_type.value, spend_type=spend_type),
        methods=["GET", "POST"],
    )

for item in CharacterEditableInfo:
    blueprint.add_url_rule(
        f"/character/<string:character_id>/edit/{item.value.name}",
        view_func=EditCharacterInfo.as_view(item.value.route_suffix, edit_type=item),
        methods=["GET", "POST", "DELETE"],
    )
