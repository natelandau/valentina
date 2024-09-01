"""Configure Jinjax for Valentina."""

from pathlib import Path

import jinjax
from quart import Quart

from .jinja_filters import from_markdown


def register_jinjax_catalog(app: Quart) -> jinjax.Catalog:
    """Register the JinJax catalog with the Quart application.

    Initialize a JinJax catalog, add component and template folders to it,
    and configure the Jinja2 environment with custom filters and settings.
    The catalog is then made available globally in the application's Jinja2 environment.

    Args:
        app (Quart): The Quart application instance to which the JinJax catalog
        and Jinja2 environment settings will be registered.

    Returns:
        jinjax.Catalog: The configured JinJax catalog.
    """
    catalog = jinjax.Catalog(jinja_env=app.jinja_env)
    catalog.add_folder(Path(__file__).parent.parent / "components")
    catalog.add_folder(Path(__file__).parent.parent / "templates")
    catalog.jinja_env.filters.update({"from_markdown": from_markdown})
    catalog.jinja_env.trim_blocks = True
    catalog.jinja_env.lstrip_blocks = True
    app.jinja_env.globals["catalog"] = catalog

    return catalog
