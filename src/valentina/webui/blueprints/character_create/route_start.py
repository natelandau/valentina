"""Route for the character creation start page."""

from typing import ClassVar

from flask_discord import requires_authorization
from quart import request, session, url_for
from quart.views import MethodView
from werkzeug.wrappers.response import Response

from valentina.constants import CharClass
from valentina.webui import catalog
from valentina.webui.utils import fetch_active_campaign, fetch_user, update_session


class StartCharacterCreate(MethodView):
    """Route for the character creation start page."""

    decorators: ClassVar = [requires_authorization]

    async def _serve_page(self) -> str:
        """Render the page for both get and post requests."""
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
        )

    async def post(self) -> str | Response:
        """Handle POST requests to the character creation start page."""
        form = await request.form

        if "reset_campaign" in form:
            del session["ACTIVE_CAMPAIGN_ID"]
            # Send redirect header to HTMX to repaint the entire page, thus allowing tooltips to function
            return Response(headers={"HX-Redirect": url_for("character_create.start")})

        if new_campaign := form.get("campaign", None):
            session["ACTIVE_CAMPAIGN_ID"] = new_campaign

        # Send the updated response to HTMX which will repaint the page
        return await self._serve_page()

    async def get(self) -> str:
        """Get the character creation start page."""
        await update_session()
        return await self._serve_page()
