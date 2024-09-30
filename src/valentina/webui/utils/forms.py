"""Model for HTML forms."""

from dataclasses import dataclass

from bson import ObjectId

from valentina.models import Character


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


async def validate_unique_character_name(
    name_first: str, name_last: str, character_id: str = ""
) -> bool:
    """Check if the first + lastname are unique in the database."""
    if character_id:
        return (
            await Character.find(
                Character.id != ObjectId(character_id),
                Character.name_first == name_first,
                Character.name_last == name_last,
            ).count()
            == 0
        )

    return (
        await Character.find(
            Character.name_first == name_first,
            Character.name_last == name_last,
        ).count()
        == 0
    )
