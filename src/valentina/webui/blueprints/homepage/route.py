"""Homepage views."""

import random

from quart import request, session
from quart.views import MethodView

from valentina.constants import BOT_DESCRIPTIONS
from valentina.webui import catalog, discord_oauth
from valentina.webui.utils import update_session

homepage_description = f"Valentina, your {random.choice(['honored', 'admired', 'distinguished', 'celebrated', 'hallowed', 'prestigious', 'acclaimed', 'favorite', 'friendly neighborhood', 'prized', 'treasured', 'number one', 'esteemed', 'venerated', 'revered', 'feared'])} {random.choice(BOT_DESCRIPTIONS)}, is ready for you!\n"


class HomepageView(MethodView):
    """View to handle homepage operations."""

    async def get(self) -> str:
        """Handle GET requests."""
        if not discord_oauth.authorized or not session.get("USER_ID", None):
            return catalog.render(
                "homepage.Anonymous",
                homepage_description=homepage_description,
            )

        await update_session()
        return catalog.render(
            "homepage.Loggedin",
            error_msg=request.args.get("error_msg", ""),
            success_msg=request.args.get("success_msg", ""),
            info_msg=request.args.get("info_msg", ""),
            warning_msg=request.args.get("warning_msg", ""),
        )
