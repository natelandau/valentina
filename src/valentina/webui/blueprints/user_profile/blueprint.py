"""Blueprint for the user profile."""

from quart import Blueprint

from valentina.webui.constants import UserEditableInfo

from .route import UserEditItem, UserProfile

blueprint = Blueprint("user_profile", __name__)

blueprint.add_url_rule(
    "/user/<int:user_id>",
    view_func=UserProfile.as_view("view"),
    methods=["GET"],
)

for item in UserEditableInfo:
    blueprint.add_url_rule(
        f"/user/<int:user_id>/edit/{item.value.name}",
        view_func=UserEditItem.as_view(item.value.route_suffix, edit_type=item),
        methods=["GET", "POST", "DELETE"],
    )
