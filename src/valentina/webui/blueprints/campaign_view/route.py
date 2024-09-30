"""Campaign view."""

from typing import ClassVar

from flask_discord import requires_authorization
from quart import abort, request, session, url_for
from quart.views import MethodView

from valentina.models import Campaign, Statistics
from valentina.webui import catalog
from valentina.webui.utils.helpers import update_session

from .forms import CampaignOverviewForm


class CampaignView(MethodView):
    """View to handle campaign operations."""

    decorators: ClassVar = [requires_authorization]

    def __init__(self) -> None:
        self.is_htmx = bool(request.headers.get("Hx-Request", False))

    async def handle_tabs(self, campaign: Campaign) -> str:
        """Handle rendering of HTMX tab content for the campaign view.

        Determine the requested tab from the "tab" query parameter and render
        the corresponding template for the campaign view. Supported tabs include
        'overview', 'books', 'characters', and 'statistics'.

        Args:
            campaign (Campaign): The campaign object to use for rendering the view.

        Returns:
            str: The rendered HTML content for the selected tab.

        Raises:
            404: If the requested tab is not recognized or supported.

        Note:
            This method is designed to work with HTMX requests for dynamic
            tab content loading in the campaign view.
        """
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
        """Handle GET requests for a specific campaign view.

        Fetch the campaign using the provided campaign ID and render the appropriate view.
        Process the request based on whether it's an HTMX request or a regular GET request.

        For HTMX requests:
        - Delegate rendering to the `handle_tabs` method.
        - Return content specific to the selected tab.

        For regular GET requests:
        - Render the main campaign view.

        Args:
            campaign_id (str): The unique identifier of the campaign to retrieve.

        Returns:
            str: The rendered HTML content for the campaign view. This can be either
                 tab-specific content for HTMX requests or the full campaign view for
                 regular GET requests.

        Raises:
            401: If no campaign is found with the provided ID.
            404: If an invalid tab is requested in an HTMX request (raised by `handle_tabs`).

        Note:
            This method uses the `request` object to determine if it's an HTMX request
            and to access any query parameters for tab selection.
        """
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
        """Handle GET requests for viewing or editing a campaign. Fetch the campaign using the provided campaign ID and render the appropriate view.

        Determine the view mode based on the "view" query parameter:
        - If "view" is set to "edit", render the form for editing the campaign's overview.
        - Otherwise, display the campaign's overview information.

        Args:
            campaign_id (str): The unique identifier of the campaign to retrieve.

        Returns:
            str: Rendered HTML content for either the campaign overview display or
                 the edit form, depending on the request parameters.

        Raises:
            401: If no campaign is found with the provided ID.

        Note:
            This method uses the `request` object to access query parameters for
            determining the view mode.
        """
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
        """Handle POST requests for updating a campaign's overview.

        Fetch the campaign using the provided campaign ID. Validate the submitted
        form data. If valid, update the campaign's name and description. Update
        the session if the campaign's name changes. Render the updated campaign
        overview on success, or re-render the edit form with errors if validation fails.

        Args:
            campaign_id (str): The unique identifier of the campaign to update.

        Returns:
            str: Rendered HTML content for either the updated campaign overview
                 or the edit form with validation errors.

        Raises:
            401: If no campaign is found with the provided ID.

        Note:
            This method uses form validation to ensure data integrity before
            updating the campaign. It also handles session updates to maintain
            consistency across the application.
        """
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
