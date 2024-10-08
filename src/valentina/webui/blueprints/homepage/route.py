"""Homepage views."""

import random

from quart import session
from quart.views import MethodView

from valentina.constants import BOT_DESCRIPTIONS
from valentina.webui import catalog, discord_oauth
from valentina.webui.utils import update_session

homepage_description = f"Valentina, your {random.choice(['honored', 'admired', 'distinguished', 'celebrated', 'hallowed', 'prestigious', 'acclaimed', 'favorite', 'friendly neighborhood', 'prized', 'treasured', 'number one', 'esteemed', 'venerated', 'revered', 'feared'])} {random.choice(BOT_DESCRIPTIONS)}, is ready for you!\n"


class HomepageView(MethodView):
    """View to handle homepage operations."""

    async def get(self) -> str:
        """Handle GET requests."""
        await update_session()

        if not discord_oauth.authorized or not session["USER_ID"]:
            return catalog.render(
                "homepage.Anonymous",
                homepage_description=homepage_description,
            )

        return catalog.render("homepage.Loggedin")
