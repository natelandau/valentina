"""Automatically register all blueprints in the blueprints directory."""

from importlib import import_module

from loguru import logger
from quart import Quart

from valentina.constants import BLUEPRINT_FOLDER_PATH


def import_all_bps(app: Quart) -> Quart:
    """Register all the blueprints with the Quart application.

    Scan the specified blueprint folder for subdirectories,
    attempt to import a blueprint module from each subdirectory, and register
    the blueprint with the provided Quart application.

    Args:
        app (Quart): The Quart application instance to register blueprints with.
        blueprint_folder (Path): The path to the folder containing blueprint subdirectories.

    Returns:
        Quart: The Quart application instance with registered blueprints.
    """
    for bp_folder in BLUEPRINT_FOLDER_PATH.glob("*"):
        if not bp_folder.is_dir() or bp_folder.stem == "__pycache__":
            continue

        try:
            bp = import_module(f"valentina.webui.blueprints.{bp_folder.stem}.blueprint")
        except ModuleNotFoundError as e:
            logger.error(f"Failed to import blueprint from: {bp_folder}\n{e}")
            continue
        else:
            app.register_blueprint(bp.blueprint)
            logger.debug(f"Import blueprint: {bp_folder.stem}")

    return app
