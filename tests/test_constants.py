# type: ignore
"""Test Constants."""

from valentina import constants


def test_CharClassType():  # noqa: N802
    """Test CharClassType."""
    for _ in range(100):
        # WHEN a random member of CharClassType is selected
        result = constants.CharClassType.random_member()

        # THEN return a CharClassType
        assert isinstance(result, constants.CharClassType)
        assert result != constants.CharClassType.NONE
        assert result != constants.CharClassType.OTHER

        # GIVEN a CharClassType member
        value_map: dict[int, constants.CharClassType] = {
            1: constants.CharClassType.MORTAL,
            32: constants.CharClassType.MORTAL,
            62: constants.CharClassType.VAMPIRE,
            71: constants.CharClassType.WEREWOLF,
            75: constants.CharClassType.MAGE,
            80: constants.CharClassType.GHOUL,
            85: constants.CharClassType.CHANGELING,
            93: constants.CharClassType.HUNTER,
            98: constants.CharClassType.SPECIAL,
        }

        # WHEN member is selected by a number between 1-100
        for value, member in value_map.items():
            result = constants.CharClassType.get_member_by_value(value)

            # THEN return the correct member
            assert isinstance(result, constants.CharClassType)
            assert result == member
