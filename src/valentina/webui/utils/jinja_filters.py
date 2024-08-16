"""Custom Jinja2 filters for Valentina web UI."""

from markdown2 import markdown
from markupsafe import escape
from quart import Quart


def from_markdown(value: str) -> str:
    """Convert a Markdown string to HTML."""
    value = escape(value)
    return markdown(value)


def register_filters(app: Quart) -> Quart:
    """Register custom Jinja2 filters for the app."""
    app.jinja_env.filters["from_markdown"] = from_markdown

    return app
