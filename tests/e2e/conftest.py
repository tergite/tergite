"""Fixtures for end-to-end tests"""

import os

import pytest

from tergite import Provider, Tergite


@pytest.fixture
def backend_provider() -> Provider:
    """A provider that is authenticated using API token"""
    api_url = os.environ.get("API_URL")
    api_token = os.environ.get("API_TOKEN")
    return Tergite.use_provider_account(
        service_name="test", url=api_url, token=api_token
    )
