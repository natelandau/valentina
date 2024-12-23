"""Routes for administration via the web UI."""

from typing import ClassVar

from flask_discord import requires_authorization
from quart import abort, request, url_for
from quart.utils import run_sync
from quart.views import MethodView

from valentina.constants import (
    HTTPStatus,
    PermissionManageCampaign,
    PermissionsGrantXP,
    PermissionsKillCharacter,
    PermissionsManageTraits,
)
from valentina.webui import catalog
from valentina.webui.utils import fetch_guild, is_storyteller
from valentina.webui.utils.discord import post_to_audit_log


class AdminView(MethodView):
    """Route for the admin home page."""

    decorators: ClassVar = [requires_authorization]

    async def get(self) -> str:
        """Return the admin home page view.

        Returns:
            str: Rendered HTML template for the admin page.

        Raises:
            HTTPStatus.FORBIDDEN: If user is not a storyteller.
        """
        if not await is_storyteller():
            return abort(
                HTTPStatus.FORBIDDEN.value, "You are not a storyteller and cannot access this page."
            )

        guild = await fetch_guild()

        return await run_sync(
            lambda: catalog.render(
                "admin.Admin",
                guild=guild,
                PermissionsGrantXP=PermissionsGrantXP,
                PermissionsManageTraits=PermissionsManageTraits,
                PermissionManageCampaign=PermissionManageCampaign,
                PermissionsKillCharacter=PermissionsKillCharacter,
                success_msg=request.args.get("success_msg", ""),
            )
        )()

    async def post(self) -> str:
        """Process permission updates for the admin page.

        Returns:
            str: Rendered admin page template with updated permissions and success message.

        Raises:
            HTTPStatus.FORBIDDEN: If user is not a storyteller.
            HTTPStatus.BAD_REQUEST: If invalid permission values are provided.
        """
        if not await is_storyteller():
            return abort(
                HTTPStatus.FORBIDDEN.value, "You are not a storyteller and cannot access this page."
            )

        guild = await fetch_guild()

        # Map permission names to their corresponding enum classes
        permission_map = {
            "grant_xp": PermissionsGrantXP,
            "manage_traits": PermissionsManageTraits,
            "manage_campaigns": PermissionManageCampaign,
            "kill_character": PermissionsKillCharacter,
        }

        # Find which permission is being updated
        permission_name = next((k for k in permission_map if request.args.get(k)), None)
        if not permission_name:
            abort(HTTPStatus.BAD_REQUEST.value, "No valid action provided.")

        try:
            # Update the permission value
            permission_value = int(request.args.get(permission_name))
            permission_enum = permission_map[permission_name](permission_value)
            setattr(guild.permissions, permission_name, permission_enum)
            await guild.save()

            # Format success message
            msg = f"Set {permission_name} to {permission_enum.name.title().replace('_', ' ')}"
            await post_to_audit_log(msg=msg, view=self.__class__.__name__)

            return (
                f'<script>window.location.href="{url_for("admin.home", success_msg=msg)}"</script>'
            )

        except ValueError:
            abort(HTTPStatus.BAD_REQUEST.value, f"Invalid {permission_name} value.")
