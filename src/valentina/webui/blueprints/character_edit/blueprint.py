"""Blueprint for editing characters."""

from quart import Blueprint

from .route_finalize import SpendFreeiePoints

blueprint = Blueprint("character_edit", __name__)

blueprint.add_url_rule(
    "/character/<string:character_id>/finalize",
    view_func=SpendFreeiePoints.as_view("finalize"),
    methods=["GET", "POST"],
)
