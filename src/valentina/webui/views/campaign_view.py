"""Campaign view."""

from typing import ClassVar

from flask_discord import requires_authorization
from quart import abort, request, session
from quart.views import MethodView

from valentina.models import Campaign, Statistics
from valentina.webui import catalog


class CampaignView(MethodView):
    """View to handle campaign operations."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self) -> None:
        self.session = session  # Assuming session is defined globally or passed in some way

    async def handle_tabs(self, campaign: Campaign) -> str:
        """Handle HTMX tabs for the campaign view."""
        if request.args.get("tab") == "overview":
            return catalog.render("campaign_view.Overview", campaign=campaign)

        if request.args.get("tab") == "books":
            return catalog.render(
                "campaign_view.Books", campaign=campaign, books=await campaign.fetch_books()
            )

        if request.args.get("tab") == "characters":
            return catalog.render(
                "campaign_view.Characters",
                campaign=campaign,
                characters=await campaign.fetch_characters(),
            )

        if request.args.get("tab") == "statistics":
            stats_engine = Statistics(guild_id=session["GUILD_ID"])
            return catalog.render(
                "campaign_view.Statistics",
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

        return catalog.render("campaign_view.Main", campaign=campaign)
