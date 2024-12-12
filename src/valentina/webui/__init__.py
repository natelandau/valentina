"""Define and configure the Quart application for the Valentina web interface.

This module initializes the Quart application, sets up Discord OAuth2 integration,
configures session management with Redis, and registers custom filters, error handlers,
and JinjaX templates. It serves as the main entry point for the Valentina web UI.
"""

from .web_app import catalog, configure_app, create_app, discord_oauth

__all__ = ["catalog", "configure_app", "create_app", "discord_oauth"]
