"""Validators for WTF forms."""

from bson import ObjectId

from valentina.models import Character
from valentina.utils import console


async def validate_unique_character_name(
    name_first: str, name_last: str, character_id: str = ""
) -> bool:
    """Check if the first + lastname are unique in the database."""
    if character_id:
        result = await Character.find(
            Character.id != ObjectId(character_id),
            Character.name_first == name_first,
            Character.name_last == name_last,
        ).count()
        console.log(f"{result=}")

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
