"""Configure Jinjax for Valentina."""

from pathlib import Path

import jinjax
from loguru import logger
from quart import Quart

from valentina.constants import WEBUI_ROOT_PATH

from .jinja_filters import from_markdown


def register_jinjax_catalog(app: Quart, blueprint_folder: Path) -> jinjax.Catalog:
    """Register the JinJax catalog with the Quart application.

    Initialize a JinJax catalog, add component and template folders to it,
    and configure the Jinja2 environment with custom filters and settings.
    The catalog is then made available globally in the application's Jinja2 environment.

    Args:
        app (Quart): The Quart application instance to which the JinJax catalog
                     and Jinja2 environment settings will be registered.
        blueprint_folder (Path): The path to the folder containing blueprint templates.

    Returns:
        jinjax.Catalog: The configured JinJax catalog.
    """
    catalog = jinjax.Catalog(jinja_env=app.jinja_env)
    catalog.add_folder(WEBUI_ROOT_PATH / "shared")

    # Attempt to register templates from each blueprint folder
    for template_folder in blueprint_folder.glob("*/templates"):
        if not template_folder.is_dir() or not any(template_folder.iterdir()):
            continue

        logger.debug(f"Register template folder: {template_folder.parent.stem}")
        catalog.add_folder(template_folder)

    catalog.jinja_env.filters.update({"from_markdown": from_markdown})
    catalog.jinja_env.trim_blocks = True
    catalog.jinja_env.lstrip_blocks = True
    app.jinja_env.globals["catalog"] = catalog

    return catalog
