"""Custom Jinja2 filters for Valentina web UI."""

from markdown2 import markdown
from markupsafe import escape


def from_markdown(value: str) -> str:
    """Convert a Markdown string to HTML."""
    value = escape(value)
    return markdown(value)
