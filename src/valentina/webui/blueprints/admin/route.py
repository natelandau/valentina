"""Routes for administration via the web UI."""

from typing import ClassVar

from flask_discord import requires_authorization
from quart import abort, flash, request, session, url_for
from quart.utils import run_sync
from quart.views import MethodView

from valentina.constants import (
    BrokerTaskType,
    HTTPStatus,
    LogLevel,
    PermissionManageCampaign,
    PermissionsGrantXP,
    PermissionsKillCharacter,
    PermissionsManageTraits,
)
from valentina.models import BrokerTask
from valentina.utils import instantiate_logger
from valentina.webui import catalog
from valentina.webui.utils import fetch_guild, is_storyteller
from valentina.webui.utils.discord import post_to_audit_log


class AdminView(MethodView):
    """Route for the admin home page."""

    decorators: ClassVar = [requires_authorization]

    async def _update_permissions(self) -> str:
        """Update guild permission settings based on request arguments.

        Returns:
            str: Success message indicating the permission that was updated and its new value.

        Raises:
            HTTPStatus.BAD_REQUEST: If no valid permission is provided in request args or if
                permission value is invalid.
        """
        guild = await fetch_guild()

        # Map permission names to their corresponding enum classes
        permission_map = {
            "grant_xp": PermissionsGrantXP,
            "manage_traits": PermissionsManageTraits,
            "manage_campaigns": PermissionManageCampaign,
            "kill_character": PermissionsKillCharacter,
        }

        permission_name = next((k for k in permission_map if request.args.get(k)), None)
        if not permission_name:
            abort(HTTPStatus.BAD_REQUEST.value, "No valid action provided.")

        try:
            # Update the permission value
            permission_value = int(request.args.get(permission_name))
            permission_enum = permission_map[permission_name](permission_value)
            setattr(guild.permissions, permission_name, permission_enum)
            await guild.save()
        except ValueError:
            abort(HTTPStatus.BAD_REQUEST.value, f"Invalid {permission_name} value.")

        # Format success message
        return f"Set {permission_name.title().replace('_', ' ')} to <span class='font-monospace'>{permission_enum.name.title().replace('_', ' ')}</span>"

    async def _rebuild_channels(self) -> str:
        """Delete and recreate all campaign channels in Discord.

        Create a broker task to rebuild all campaign channels in the guild. The task will delete
        existing Discord channels and recreate them with proper permissions and categories.
        This is executed asynchronously by the task broker.

        Returns:
            str: Status message indicating channel rebuild has been initiated.

        Warning:
            This is a destructive operation that will delete and recreate all campaign-related
            channels, including their message history. Use with caution.
        """
        task = BrokerTask(
            task=BrokerTaskType.REBUILD_CHANNELS,
            guild_id=session["GUILD_ID"],
            author_name=session["USER_NAME"],
        )
        await task.insert()

        return "Rebuilding Discord channels..."

    async def _update_log_level(self) -> str:
        """Update the log level for the bot."""
        log_level = LogLevel(request.args.get("log_level"))
        instantiate_logger(log_level)

        return f"Set log level to <span class='font-monospace'>{log_level.name}</span>"

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
                LogLevel=LogLevel,
            )
        )()

    async def post(self) -> str:
        """Process permission updates and maintenance tasks for the admin page.

        Process POST requests to update guild permissions or perform maintenance tasks like
        rebuilding Discord channels. Only storytellers can access this endpoint.

        Args:
            None

        Returns:
            str: Rendered HTML template with updated permissions and success message, or
                 JavaScript redirect with success message.

        Raises:
            HTTPStatus.FORBIDDEN: If requesting user is not a storyteller.
            HTTPStatus.BAD_REQUEST: If request arguments do not match any valid actions.
        """
        if not await is_storyteller():
            return abort(
                HTTPStatus.FORBIDDEN.value, "You are not a storyteller and cannot access this page."
            )

        # Map request parameters to handler functions to avoid a long if/elif chain
        # and make it easier to add new admin actions in the future
        request_map = {
            "rebuild_channels": self._rebuild_channels,
            "log_level": self._update_log_level,
            "grant_xp": self._update_permissions,
            "manage_traits": self._update_permissions,
            "manage_campaigns": self._update_permissions,
            "kill_character": self._update_permissions,
        }

        request_name = next((k for k in request_map if request.args.get(k)), None)
        if not request_name:
            abort(HTTPStatus.BAD_REQUEST.value, "No valid action provided.")

        msg = await request_map[request_name]()

        await post_to_audit_log(msg=msg, view=self.__class__.__name__)

        await flash(msg, "success")
        return f'<script>window.location.href="{url_for("admin.home")}"</script>'
