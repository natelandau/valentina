"""Start webui without Discord bot for debugging and development."""

import asyncio

import pymongo
from loguru import logger

from valentina.utils import ValentinaConfig
from valentina.utils.database import init_database
from valentina.webui import create_dev_app

# async def run_webserver() -> None:
#     pass


async def create_db_pool() -> None:
    """Initialize the database connection pool."""
    while True:
        try:
            await init_database()
        except pymongo.errors.ServerSelectionTimeoutError as e:
            logger.error(f"DB: Failed to initialize database: {e}")
            await asyncio.sleep(60)
        else:
            break


def dev() -> None:
    """Run the web server for development."""
    app = create_dev_app()
    app.run(
        host=ValentinaConfig().webui_host,
        port=ValentinaConfig().webui_port,
        debug=True,
        use_reloader=True,
    )
