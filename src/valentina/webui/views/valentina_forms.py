"""Model for HTML forms."""

from dataclasses import dataclass


@dataclass()
class ValentinaForm:
    """Form class to contain custom form elements."""

    title: str = ""
    description: str = ""
    hx_validate: bool = False
    hx_url: str = ""
    join_labels: bool = False
    floating_labels: bool = False

    def hx_command_outer(self, name: str = "") -> str:
        """The parent element HTMX command to be placed within the <div> tag surrounding the form item.

        Args:
            name (str): The element name

        Returns:
            str: The HTMX command
        """
        if self.hx_validate:
            return f'hx-target="this" hx-swap="outerHTML" hx-indicator="#indicator-{name}"'

        return ""

    def hx_command_input(self, name: str = "") -> str:
        """The HTMX command for the input element to be placed within the <input> tag.

        Args:
            name (str): The element name

        Returns:
            str: The HTMX command
        """
        if self.hx_validate:
            return f'hx-post="{self.hx_url}" hx-indicator="#indicator-{name}" hx-headers=\'{{"HX-form-field": "{name}"}}\''

        return ""
