"""tests for the backend module"""
import pytest

from tergite_qiskit_connector.providers.tergite import Tergite, Provider, OpenPulseBackend
from tergite_qiskit_connector.providers.tergite.backend import TergiteBackendConfig
from tergite_qiskit_connector.providers.tergite.provider_account import ProviderAccount
from tests.conftest import API_URL, BACKENDS_LIST
from tests.utils.records import get_record


def test_get_backend(api):
    """Retrieves the right backend"""
    backend_name = "Well-formed"
    provider = _get_test_provider(url=API_URL)
    expected_json = get_record(BACKENDS_LIST, _filter={"name": backend_name})
    expected = OpenPulseBackend(
        data=TergiteBackendConfig(**expected_json), provider=provider, base_url=API_URL
    )
    got = provider.get_backend(backend_name)
    assert got == expected


def test_get_malformed_backend(api):
    """Raises TypeError if a malformed backend is returned"""
    backend_name = "Malformed"
    provider = _get_test_provider(url=API_URL)

    with pytest.raises(TypeError, match="malformed backend "):
        provider.get_backend(backend_name)


def _get_test_provider(url: str, token: str = None, username: str = None, password: str = None) -> Provider:
    """Retrieves a provider to be used for testing given the optional token, username, passwords kwargs"""
    extras = {}
    if username:
        extras = {
            "username": username,
            "password": password
        }

    account = ProviderAccount(
        service_name="test",
        url=url,
        token=token,
        extras=extras
    )
    return Tergite.use_provider_account(account)
