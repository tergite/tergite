"""Fixtures for end-to-end tests"""
import os

import pytest

from tergite.qiskit.providers import Tergite, Provider
from tergite.qiskit.providers.provider_account import ProviderAccount
from tests.utils.env import is_end_to_end


@pytest.mark.skipif(not is_end_to_end(), reason="is end-to-end test")
def backend_provider() -> Provider:
    """A provider that is authenticated using API token"""
    api_url = os.environ.get("API_URL")
    api_token = os.environ.get("API_TOKEN")
    account = ProviderAccount(service_name="test", url=api_url, token=api_token)
    return Tergite.use_provider_account(account)
