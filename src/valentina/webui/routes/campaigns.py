"""Blueprint for character views."""

from flask_discord import requires_authorization
from quart import Blueprint, abort, request, session
from quart.views import MethodView

from valentina.models import Campaign, Statistics
from valentina.webui import catalog

bp = Blueprint("campaign", __name__)


class CampaignView(MethodView):
    """View to handle campaign operations."""

    def __init__(self) -> None:
        self.session = session  # Assuming session is defined globally or passed in some way

    async def handle_tabs(self, campaign: Campaign) -> str:
        """Handle HTMX tabs for the campaign view."""
        if request.args.get("tab") == "overview":
            return catalog.render("campaign.Overview", campaign=campaign)

        if request.args.get("tab") == "books":
            return catalog.render(
                "campaign.Books", campaign=campaign, books=await campaign.fetch_books()
            )

        if request.args.get("tab") == "characters":
            return catalog.render(
                "campaign.Characters",
                campaign=campaign,
                characters=await campaign.fetch_characters(),
            )

        if request.args.get("tab") == "statistics":
            stats_engine = Statistics(guild_id=session["GUILD_ID"])
            return catalog.render(
                "campaign.Statistics",
                campaign=campaign,
                statistics=await stats_engine.campaign_statistics(campaign, as_json=True),
            )

        return abort(404)

    @requires_authorization
    async def get(self, campaign_id: str = "") -> str:
        """Handle GET requests."""
        campaign = await Campaign.get(campaign_id, fetch_links=True)
        if not campaign:
            abort(401)

        if request.headers.get("HX-Request"):
            return await self.handle_tabs(campaign)

        return catalog.render("campaign", campaign=campaign)


# Register the view with the Blueprint
view_campaign = CampaignView.as_view("view_campaign")
bp.add_url_rule("/campaign/<string:campaign_id>", view_func=view_campaign, methods=["GET", "POST"])
