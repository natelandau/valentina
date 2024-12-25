# type: ignore
"""Test assorted forms using HTMXPartials."""

import pytest

from tests.factories import *


@pytest.mark.drop_db
async def test_set_desperation_or_danger(debug, mocker, test_client, campaign_factory):
    """Test the set desperation or danger form."""
    # Given: A campaign with desperation and danger set to 0
    mocker.patch(
        "valentina.webui.blueprints.HTMXPartials.others.post_to_audit_log", return_value=None
    )
    campaign = await campaign_factory.build(desperation=0, danger=0).insert()

    url = f"/partials/setdesperation/{campaign.id}"

    # When: Getting the desperation form
    response = await test_client.get(url, follow_redirects=True)
    # Then: The form loads successfully
    assert response.status_code == 200

    # When: Submitting the form with updated values
    response = await test_client.post(
        url, form={"desperation": 1, "danger": 1, "submit": True}, follow_redirects=True
    )
    # Then: The form submission is successful
    assert response.status_code == 200

    # And: The campaign values are updated in the database
    await campaign.sync()
    assert campaign.desperation == 1
    assert campaign.danger == 1
