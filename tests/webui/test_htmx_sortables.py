# type: ignore
"""Test HTMX routes for sortables."""

import pytest

from tests.factories import *
from valentina.models import BrokerTask


@pytest.mark.drop_db
async def test_sortable_book_reorder(
    debug,
    book_factory,
    mocker,
    user_factory,
    guild_factory,
    campaign_factory,
    mock_session,
    test_client,
):
    """Test the sortable book reorder route."""
    mocker.patch(
        "valentina.webui.blueprints.HTMXPartials.sortables.post_to_audit_log",
        return_value=None,
    )

    # Given: A campaign with 5 books in sequential order
    user = await user_factory.build().insert()
    guild = await guild_factory.build().insert()

    parent = await campaign_factory.build(guild=guild.id).insert()
    item1 = await book_factory.build(campaign=str(parent.id), name="Book 1", number=1).insert()
    item2 = await book_factory.build(campaign=str(parent.id), name="Book 2", number=2).insert()
    item3 = await book_factory.build(campaign=str(parent.id), name="Book 3", number=3).insert()
    item4 = await book_factory.build(campaign=str(parent.id), name="Book 4", number=4).insert()
    item5 = await book_factory.build(campaign=str(parent.id), name="Book 5", number=5).insert()

    async with test_client.session_transaction() as session:
        session.update(mock_session(user_id=user.id, guild_id=guild.id))

    # When: Getting the sortable books page
    url = f"/partials/sortbooks/{parent.id}"
    response = await test_client.get(url, follow_redirects=True)
    returned_text = await response.get_data(as_text=True)

    # Then the request succeeds and experience is updated correctly
    assert response.status_code == 200

    # Then: All books are displayed in the sortable list
    assert f"name='{item1.id}'" in returned_text
    assert f"name='{item2.id}'" in returned_text
    assert f"name='{item3.id}'" in returned_text
    assert f"name='{item4.id}'" in returned_text
    assert f"name='{item5.id}'" in returned_text

    # When: Reordering books by swapping positions of books 3 and 4
    form_data = {
        f"{item1.id}": "1",
        f"{item2.id}": "2",
        f"{item4.id}": "4",
        f"{item3.id}": "3",
        f"{item5.id}": "5",
    }

    response2 = await test_client.post(url, form=form_data, follow_redirects=True)
    returned_text = await response2.get_data(as_text=True)

    # Then the request succeeds and experience is updated correctly
    assert response2.status_code == 200

    # Then: The reordered list is displayed successfully
    assert f"name='{item1.id}'" in returned_text
    assert f"name='{item2.id}'" in returned_text
    assert f"name='{item4.id}'" in returned_text
    assert f"name='{item3.id}'" in returned_text
    assert f"name='{item5.id}'" in returned_text

    # And: Broker tasks are created to update Discord channels
    assert await BrokerTask.find().count() == 2

    # And: Book positions are updated in the database
    await item1.sync()
    await item2.sync()
    await item3.sync()
    await item4.sync()
    await item5.sync()

    assert item1.number == 1
    assert item2.number == 2
    assert item3.number == 4
    assert item4.number == 3
    assert item5.number == 5


@pytest.mark.drop_db
async def test_sortable_chapters_reorder(
    debug,
    book_factory,
    book_chapter_factory,
    user_factory,
    guild_factory,
    mocker,
    mock_session,
    test_client,
):
    """Test the sortable chapters reorder route."""
    mocker.patch(
        "valentina.webui.blueprints.HTMXPartials.sortables.post_to_audit_log",
        return_value=None,
    )

    # Given: A campaign with 5 books in sequential order
    user = await user_factory.build().insert()
    guild = await guild_factory.build().insert()

    parent = await book_factory.build().insert()
    item1 = await book_chapter_factory.build(
        book=str(parent.id),
        name="Chapter 1",
        number=1,
    ).insert()
    item2 = await book_chapter_factory.build(
        book=str(parent.id),
        name="Chapter 2",
        number=2,
    ).insert()
    item3 = await book_chapter_factory.build(
        book=str(parent.id),
        name="Chapter 3",
        number=3,
    ).insert()
    item4 = await book_chapter_factory.build(
        book=str(parent.id),
        name="Chapter 4",
        number=4,
    ).insert()
    item5 = await book_chapter_factory.build(
        book=str(parent.id),
        name="Chapter 5",
        number=5,
    ).insert()

    async with test_client.session_transaction() as session:
        session.update(mock_session(user_id=user.id, guild_id=guild.id))

    # When: Getting the sortable books page
    url = f"/partials/sortchapters/{parent.id}"
    response = await test_client.get(url, follow_redirects=True)
    returned_text = await response.get_data(as_text=True)

    # Then the request succeeds and experience is updated correctly
    assert response.status_code == 200

    # Then: All books are displayed in the sortable list
    assert f"name='{item1.id}'" in returned_text
    assert f"name='{item2.id}'" in returned_text
    assert f"name='{item3.id}'" in returned_text
    assert f"name='{item4.id}'" in returned_text
    assert f"name='{item5.id}'" in returned_text

    # When: Reordering books by swapping positions of books 3 and 4
    form_data = {
        f"{item1.id}": "1",
        f"{item2.id}": "2",
        f"{item4.id}": "4",
        f"{item3.id}": "3",
        f"{item5.id}": "5",
    }

    response2 = await test_client.post(url, form=form_data, follow_redirects=True)
    returned_text = await response2.get_data(as_text=True)

    # Then the request succeeds and experience is updated correctly
    assert response2.status_code == 200

    # Then: The reordered list is displayed successfully
    assert f"name='{item1.id}'" in returned_text
    assert f"name='{item2.id}'" in returned_text
    assert f"name='{item4.id}'" in returned_text
    assert f"name='{item3.id}'" in returned_text
    assert f"name='{item5.id}'" in returned_text

    # And: Book positions are updated in the database
    await item1.sync()
    await item2.sync()
    await item3.sync()
    await item4.sync()
    await item5.sync()

    assert item1.number == 1
    assert item2.number == 2
    assert item3.number == 4
    assert item4.number == 3
    assert item5.number == 5
