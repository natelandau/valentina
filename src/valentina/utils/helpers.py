"""Helper functions for Valentina."""
from valentina.models.database import Character


def normalize_row(row: str) -> str:
    """Takes a string and returns a normalized version of it for use as a row in the database."""
    return row.replace("-", "_").replace(" ", "_").lower()


def num_to_circles(num: int = 0, maximum: int = 5) -> str:
    """Return the emoji corresponding to the number. When `num` is greater than `maximum`, the `maximum` is increased to `num`.

    Args:
        num (int, optional): The number to convert. Defaults to 0.
        maximum (int, optional): The maximum number of circles. Defaults to 5.

    Returns:
        str: A string of circles and empty circles. i.e. `●●●○○`
    """
    if num is None:
        num = 0
    if maximum is None:
        maximum = 5
    if num > maximum:
        maximum = num

    return "●" * num + "○" * (maximum - num)


def get_max_trait_value(trait: str) -> int:
    """Return the maximum value for a trait."""
    match normalize_row(trait):
        case "willpower" | "humanity" | "rage" | "gnosis" | "arete":
            return 10
        case "blood_pool" | "quintessence":
            return 20
        case _:
            return 5


def format_traits(character: Character, traits: list[str], show_zeros: bool = True) -> str:
    """Return a string of traits to be added as the value of an embed field.

    Args:
        character (Character): The character to get the traits from.
        traits (list[str]): The traits to get from the character.
        show_zeros (bool, optional): Whether to show traits with a value of 0. Defaults to True.

    Returns:
        str: A string of traits to be added as the value of an embed field. In the format of:
            `trait_name: ●●●○○`
    """
    trait_list = []

    for t in traits:
        trait = normalize_row(t)
        max_value = get_max_trait_value(trait)

        if hasattr(character, trait):
            value = getattr(character, trait)
            if not show_zeros and (value == 0 or value is None):
                continue

            value = num_to_circles(value, max_value)
            trait_list.append(f"`{trait:13}: {value}`")

    return "\n".join(trait_list)
