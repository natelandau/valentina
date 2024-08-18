"""Campaign view."""

from typing import ClassVar

from flask_discord import requires_authorization
from quart import abort, request, session, url_for
from quart.views import MethodView

from valentina.models import Campaign, Statistics
from valentina.webui import catalog
from valentina.webui.utils.helpers import update_session
from valentina.webui.WTForms.campaign import CampaignOverviewForm


class CampaignView(MethodView):
    """View to handle campaign operations."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self) -> None:
        self.is_htmx = bool(request.headers.get("Hx-Request", False))

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

    async def get(self, campaign_id: str = "") -> str:
        """Handle GET requests."""
        campaign = await Campaign.get(campaign_id, fetch_links=True)
        if not campaign:
            abort(401)

        if request.headers.get("HX-Request"):
            return await self.handle_tabs(campaign)

        return catalog.render("campaign_view.Main", campaign=campaign)


class CampaignOverviewSnippet(MethodView):
    """View to handle campaign overview snippets."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self) -> None:
        self.is_htmx = bool(request.headers.get("Hx-Request", False))

    async def get(self, campaign_id: str = "") -> str:
        """Handle GET requests."""
        campaign = await Campaign.get(campaign_id, fetch_links=True)
        if not campaign:
            abort(401)

        if request.args.get("view") == "edit":
            form = await CampaignOverviewForm().create_form(
                data={"name": campaign.name, "description": campaign.description}
            )
            return catalog.render(
                "campaign_view.partials.OverviewEdit",
                form=form,
                campaign=campaign,
                post_url=url_for("campaign.campaign_overview", campaign_id=campaign_id),
                join_label=True,
            )

        return catalog.render("campaign_view.partials.OverviewDisplay", campaign=campaign)

    async def post(self, campaign_id: str = "") -> str:
        """Handle POST requests."""
        campaign = await Campaign.get(campaign_id, fetch_links=True)
        if not campaign:
            abort(401)

        form = await CampaignOverviewForm().create_form(
            data={"name": campaign.name, "description": campaign.description}
        )
        if await form.validate_on_submit():
            do_update_session = campaign.name != form.name.data

            campaign.name = form.name.data
            campaign.description = form.description.data
            await campaign.save()

            if do_update_session:
                await update_session()

            return catalog.render("campaign_view.partials.OverviewDisplay", campaign=campaign)

        return catalog.render(
            "campaign_view.partials.OverviewEdit",
            form=form,
            campaign=campaign,
            post_url=url_for("campaign.campaign_overview", campaign_id=campaign_id),
        )
