# This code is part of Tergite
#
# (C) Copyright Martin Ahindura 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""tests for the get_backend method on tergite backend"""
import pytest

from tergite.qiskit.providers import OpenPulseBackend, Provider, Tergite
from tergite.qiskit.providers.backend import TergiteBackendConfig
from tergite.qiskit.providers.provider_account import ProviderAccount
from tests.conftest import (
    API_TOKEN,
    API_URL,
    BACKENDS_LIST,
    GOOD_BACKEND,
    INVALID_API_TOKENS,
    MALFORMED_BACKEND,
)
from tests.utils.records import get_record


def test_get_backend(api):
    """Retrieves the right backend"""
    provider = _get_test_provider(url=API_URL)
    expected_json = get_record(BACKENDS_LIST, _filter={"name": GOOD_BACKEND})
    expected = OpenPulseBackend(
        data=TergiteBackendConfig(**expected_json), provider=provider, base_url=API_URL
    )
    got = provider.get_backend(GOOD_BACKEND)
    assert got == expected


def test_get_malformed_backend(api):
    """Raises TypeError if a malformed backend is returned"""
    provider = _get_test_provider(url=API_URL)

    with pytest.raises(TypeError, match=f"malformed backend '{MALFORMED_BACKEND}'"):
        provider.get_backend(MALFORMED_BACKEND)


def test_bearer_auth(bearer_auth_api):
    """Retrieves the data if backend is shielded with basic auth"""
    provider = _get_test_provider(url=API_URL, token=API_TOKEN)
    expected_json = get_record(BACKENDS_LIST, _filter={"name": GOOD_BACKEND})
    expected = OpenPulseBackend(
        data=TergiteBackendConfig(**expected_json), provider=provider, base_url=API_URL
    )
    got = provider.get_backend(GOOD_BACKEND)
    assert got == expected


@pytest.mark.parametrize("token", INVALID_API_TOKENS)
def test_invalid_bearer_auth(token, bearer_auth_api):
    """Invalid bearer auth raises RuntimeError if backend is shielded with bearer auth"""
    provider = _get_test_provider(url=API_URL, token=token)
    with pytest.raises(RuntimeError, match="GET request for backends timed out."):
        provider.get_backend(GOOD_BACKEND)


def _get_test_provider(url: str, token: str = None) -> Provider:
    """Retrieves a provider to be used for testing given the optional token"""
    account = ProviderAccount(service_name="test", url=url, token=token)
    return Tergite.use_provider_account(account)
