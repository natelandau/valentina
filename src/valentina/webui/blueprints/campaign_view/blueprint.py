"""Blueprints for campaign_view."""

from quart import Blueprint

from .route import CampaignOverviewSnippet, CampaignView

blueprint = Blueprint("campaign", __name__)
blueprint.add_url_rule(
    "/campaign/<string:campaign_id>",
    view_func=CampaignView.as_view("campaign_view"),
    methods=["GET", "POST"],
)
blueprint.add_url_rule(
    "/campaign/<string:campaign_id>/overview",
    view_func=CampaignOverviewSnippet.as_view("campaign_overview"),
    methods=["GET", "POST"],
)
