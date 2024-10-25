"""Configure Jinjax for Valentina."""

import re

import jinjax
from loguru import logger
from markdown2 import markdown
from markupsafe import escape

from valentina.constants import BLUEPRINT_FOLDER_PATH, WEBUI_ROOT_PATH


def from_markdown(value: str) -> str:
    """Convert a Markdown string to HTML.

    Escape the provided Markdown string to prevent HTML injection,
    then convert the escaped Markdown content to HTML.

    Args:
        value (str): The Markdown string to be converted.

    Returns:
        str: The HTML representation of the provided Markdown string.
    """
    value = escape(value)
    return markdown(value)


def from_markdown_no_p(value: str) -> str:
    """Strip enclosing paragraph marks, <p> ... </p>, which markdown() forces, and which interfere with some jinja2 layout."""
    value = escape(value)
    return re.sub("(^<P>|</P>$)", "", markdown(value), flags=re.IGNORECASE)


def register_jinjax_catalog() -> jinjax.Catalog:
    """Register the JinJax catalog with the Quart application.

    Initialize a JinJax catalog, add component and template folders to it, and configure custom filters and settings. The catalog is then made available globally in the application's Jinja2 environment.

    Returns:
        jinjax.Catalog: The configured JinJax catalog.
    """
    catalog = jinjax.Catalog()
    catalog.add_folder(WEBUI_ROOT_PATH / "shared")

    # Attempt to register templates from each blueprint folder
    for template_folder in BLUEPRINT_FOLDER_PATH.glob("*/templates"):
        if not template_folder.is_dir() or not any(template_folder.iterdir()):
            continue

        logger.debug(f"Register template folder: {template_folder.parent.stem}")
        catalog.add_folder(template_folder)

    catalog.jinja_env.filters.update({"from_markdown": from_markdown})
    catalog.jinja_env.filters.update({"from_markdown_no_p": from_markdown_no_p})
    catalog.jinja_env.trim_blocks = True
    catalog.jinja_env.lstrip_blocks = True

    return catalog
