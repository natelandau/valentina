# type: ignore
"""Test the DictionaryTerm model."""

import pytest

from valentina.models import DictionaryTerm


@pytest.mark.drop_db
async def test_event_based_actions():
    """Test the DictionaryTerm model."""
    # Given: A dictionary term with whitespace and mixed case
    test_name = " TEST TERM "
    test_synonyms = ["TEST SYNONYM 1", "TEST SYNONYM 2 ", " "]

    # When: Creating and inserting a new dictionary term
    new_term = DictionaryTerm(term=test_name, synonyms=test_synonyms, guild_id=1234567890)
    await new_term.insert()

    # Then: The term and synonyms are normalized to lowercase with whitespace trimmed
    assert new_term.term == "test term"
    assert new_term.synonyms == ["test synonym 1", "test synonym 2"]
