"""Custom Jinja2 filters for Valentina web UI."""

from markdown2 import markdown
from markupsafe import escape
from quart import Quart


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


def register_filters(app: Quart) -> Quart:
    """Register custom Jinja2 filters for the Quart application.

    Add custom filters to the Jinja2 environment, such as converting Markdown
    to HTML using the `from_markdown` function.

    Args:
        app (Quart): The Quart application instance to which the filters will be registered.

    Returns:
        Quart: The updated Quart application instance with the registered filters.
    """
    app.jinja_env.filters["from_markdown"] = from_markdown

    return app
