# type: ignore
"""Test HTMX routes for sortables."""

import pytest

from tests.factories import *
from valentina.models import BrokerTask


@pytest.mark.drop_db
async def test_sortable_book_reorder(
    debug, book_factory, user_factory, guild_factory, campaign_factory, mock_session, test_client
):
    """Test the sortable book reorder route."""
    # Given: A campaign with 5 books in sequential order
    user = await user_factory.build().insert()
    guild = await guild_factory.build().insert()
    campaign = await campaign_factory.build(guild=guild.id).insert()
    book1 = await book_factory.build(campaign=str(campaign.id), name="Book 1", number=1).insert()
    book2 = await book_factory.build(campaign=str(campaign.id), name="Book 2", number=2).insert()
    book3 = await book_factory.build(campaign=str(campaign.id), name="Book 3", number=3).insert()
    book4 = await book_factory.build(campaign=str(campaign.id), name="Book 4", number=4).insert()
    book5 = await book_factory.build(campaign=str(campaign.id), name="Book 5", number=5).insert()

    async with test_client.session_transaction() as session:
        session.update(mock_session(user_id=user.id, guild_id=guild.id))

    # When: Getting the sortable books page
    url = f"/partials/sortbooks/{campaign.id}"
    response = await test_client.get(url, follow_redirects=True)
    returned_text = await response.get_data(as_text=True)

    # Then: All books are displayed in the sortable list
    assert response.status_code == 200
    assert f"name='{book1.id}'" in returned_text
    assert f"name='{book2.id}'" in returned_text
    assert f"name='{book3.id}'" in returned_text
    assert f"name='{book4.id}'" in returned_text
    assert f"name='{book5.id}'" in returned_text

    # When: Reordering books by swapping positions of books 3 and 4
    form_data = {
        f"{book1.id}": "1",
        f"{book2.id}": "2",
        f"{book4.id}": "4",
        f"{book3.id}": "3",
        f"{book5.id}": "5",
    }

    response2 = await test_client.post(url, form=form_data, follow_redirects=True)
    returned_text = await response2.get_data(as_text=True)

    # Then: The reordered list is displayed successfully
    assert response2.status_code == 200
    assert f"name='{book1.id}'" in returned_text
    assert f"name='{book1.id}'" in returned_text
    assert f"name='{book2.id}'" in returned_text
    assert f"name='{book3.id}'" in returned_text
    assert f"name='{book4.id}'" in returned_text
    assert f"name='{book5.id}'" in returned_text

    # And: Broker tasks are created to update Discord channels
    assert await BrokerTask.find().count() == 2

    # And: Book positions are updated in the database
    await book1.sync()
    await book2.sync()
    await book3.sync()
    await book4.sync()
    await book5.sync()

    assert book1.number == 1
    assert book2.number == 2
    assert book3.number == 4
    assert book4.number == 3
    assert book5.number == 5
