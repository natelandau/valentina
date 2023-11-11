# type: ignore
"""Tests for the AWS service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from valentina.models import AWSService
from valentina.utils import errors


@pytest.mark.no_db()
def test_get_key_prefix(mock_ctx1):
    """Test get_key_prefix."""
    with pytest.raises(errors.ValidationError):
        AWSService.get_key_prefix(mock_ctx1, "something") == ""

    assert AWSService.get_key_prefix(mock_ctx1, "guild") == "1"
    assert AWSService.get_key_prefix(mock_ctx1, "user") == "1/users/1"
    assert AWSService.get_key_prefix(mock_ctx1, "character", character_id=200) == "1/characters/200"
    assert AWSService.get_key_prefix(mock_ctx1, "campaign", campaign_id=200) == "1/campaigns/200"


@pytest.mark.no_db()
def test_get_url(mocker):
    """Test get_url."""
    # GIVEN a patched boto3 client
    client_mock = MagicMock()
    client_mock.get_bucket_location = MagicMock(return_value="us-east-1")
    mocker.patch("valentina.models.aws.boto3.client", side_effect=client_mock)

    # WHEN the get_url method is called
    # THEN the correct URL is returned
    svc = AWSService()
    assert svc.get_url(key="1/test/1") == "https://bucket.s3.amazonaws.com/1/test/1"
