"""Route for the character creation start page."""

from typing import ClassVar

from flask_discord import requires_authorization
from quart import request, session, url_for
from quart.views import MethodView
from werkzeug.wrappers.response import Response

from valentina.constants import CharClass
from valentina.webui import catalog
from valentina.webui.constants import CharCreateType
from valentina.webui.utils import fetch_active_campaign, fetch_user, update_session


class StartCharacterCreate(MethodView):
    """Route for the character creation start page."""

    decorators: ClassVar = [requires_authorization]

    async def _serve_page(self) -> str:
        """Render the character creation start page for both GET and POST requests.

        This helper method consolidates the page rendering logic used by both GET and POST
        handlers. It fetches campaign data, calculates available experience points, and
        generates class description snippets for display.

        Returns:
            str: The rendered HTML template containing the character creation form,
                campaign details, and class descriptions.

        Note:
            This method is used internally to avoid duplicating rendering logic between
            request handlers. It expects request context to be available for accessing
            query parameters.
        """
        # Generate class description snippet
        rng_class_list = "".join(
            [
                f"<li><strong><code>{c.value.percentile_range[1] - c.value.percentile_range[0]}%</code> {c.value.name}</strong> {c.value.description}</li>"
                for c in CharClass.playable_classes()
            ]
        )

        rng_class_snippet = f"<ul>{rng_class_list}</ul>"

        # Get the selected campaign and available experience
        available_experience = None

        if campaign_id := request.args.get("campaign_id"):
            selected_campaign = await fetch_active_campaign(campaign_id)
        else:
            selected_campaign = await fetch_active_campaign()

        if selected_campaign:
            user = await fetch_user()
            available_experience = user.fetch_campaign_xp(selected_campaign)[0]

        # Render the page
        return catalog.render(
            "character_create.Start",
            selected_campaign=selected_campaign,
            available_experience=available_experience,
            rng_class_snippet=rng_class_snippet,
            CharCreateType=CharCreateType,
        )

    async def get(self) -> str:
        """Serve the initial character creation page.

        Fetch the active campaign and user's available experience to display the character
        creation form. This route requires authorization and updates the session before
        rendering.

        Returns:
            str: The rendered HTML template for the character creation start page.
        """
        await update_session()
        return await self._serve_page()

    async def post(self) -> str | Response:
        """Process POST requests for campaign selection and management on character creation start page.

        Handle form submissions for selecting or resetting the active campaign. When a campaign
        is selected, store it in the session. When reset is requested, clear the campaign from
        session and redirect to refresh the page.

        Returns:
            Union[str, Response]: Either HTML content for HTMX to update the page, or a
                JavaScript redirect response when resetting the campaign.

        Note:
            This endpoint is designed to work with HTMX partial page updates. The campaign
            selection affects the entire character creation flow, so proper session management
            here is critical.
        """
        form = await request.form

        if "reset_campaign" in form:
            del session["ACTIVE_CAMPAIGN_ID"]

            url = url_for("character_create.start")
            return f'<script>window.location.href="{url}"</script>'

        if new_campaign := form.get("campaign", None):
            session["ACTIVE_CAMPAIGN_ID"] = new_campaign

        # Send the updated response to HTMX which will repaint the page
        return await self._serve_page()
