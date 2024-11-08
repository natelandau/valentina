"""Blueprints for campaign."""

from quart import Blueprint

from valentina.webui.constants import CampaignEditableInfo

from .route import CampaignEditItem, CampaignView

blueprint = Blueprint("campaign", __name__)

blueprint.add_url_rule(
    "/campaign/<string:campaign_id>",
    view_func=CampaignView.as_view("view"),
    methods=["GET"],
)

for item in CampaignEditableInfo:
    blueprint.add_url_rule(
        f"/campaign/<string:campaign_id>/edit/{item.value.name}",
        view_func=CampaignEditItem.as_view(item.value.route_suffix, edit_type=item),
        methods=["GET", "POST", "DELETE"],
    )
