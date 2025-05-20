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
from qiskit.providers import QiskitBackendNotFoundError

from tergite import OpenPulseBackend, Provider, Tergite
from tergite.services.api_client.dtos import TergiteBackendConfig
from tests.utils.records import get_record

from ..utils.env import is_end_to_end
from .conftest import (
    API_TOKEN,
    API_URL,
    BACKENDS_LIST,
    GOOD_BACKENDS,
    INVALID_API_TOKENS,
    MALFORMED_BACKEND,
)

_INVALID_PARAMS = [
    (token, backend) for backend in GOOD_BACKENDS for token in INVALID_API_TOKENS
]


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_get_backend(api, backend_name):
    """Retrieves the right backend"""
    provider = _get_test_provider(url=API_URL)
    expected_json = get_record(BACKENDS_LIST, _filter={"name": backend_name})
    expected = OpenPulseBackend(
        data=TergiteBackendConfig(**expected_json), provider=provider, base_url=API_URL
    )
    got = provider.get_backend(backend_name)
    assert got == expected


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
def test_get_malformed_backend(api):
    """Raises TypeError if a malformed backend is returned"""
    provider = _get_test_provider(url=API_URL)

    with pytest.raises(
        QiskitBackendNotFoundError, match="No backend matches the criteria"
    ):
        provider.get_backend(MALFORMED_BACKEND)


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_bearer_auth(bearer_auth_api, backend_name):
    """Retrieves the data if backend is shielded with basic auth"""
    provider = _get_test_provider(url=API_URL, token=API_TOKEN)
    expected_json = get_record(BACKENDS_LIST, _filter={"name": backend_name})
    expected = OpenPulseBackend(
        data=TergiteBackendConfig(**expected_json), provider=provider, base_url=API_URL
    )
    got = provider.get_backend(backend_name)
    assert got == expected


@pytest.mark.skipif(is_end_to_end(), reason="is not end-to-end test")
@pytest.mark.parametrize("token, backend", _INVALID_PARAMS)
def test_invalid_bearer_auth(token, backend, bearer_auth_api):
    """Invalid bearer auth raises RuntimeError if backend is shielded with bearer auth"""
    provider = _get_test_provider(url=API_URL, token=token)
    with pytest.raises(RuntimeError, match="Error retrieving backends: Unauthorized"):
        provider.get_backend(backend)


def _get_test_provider(url: str, token: str = None) -> Provider:
    """Retrieves a provider to be used for testing given the optional token"""
    return Tergite.use_provider_account(service_name="test", url=url, token=token)
