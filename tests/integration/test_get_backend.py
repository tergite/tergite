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
from qiskit import QuantumCircuit
from qiskit.providers import QiskitBackendNotFoundError

from tergite import OpenPulseBackend, OpenQASMBackend, Provider, Tergite
from tergite.exc import TergiteError
from tergite.services.api_client.dtos import TergiteBackendConfig
from tests.utils.records import get_record

from .conftest import (
    API_TOKEN,
    API_URL,
    BACKENDS_LIST,
    GOOD_BACKENDS,
    INVALID_API_TOKENS,
    MALFORMED_BACKEND,
    NON_PULSE_BACKEND,
    TEST_CALIBRATIONS_MAP,
)

_INVALID_PARAMS = [
    (token, backend) for backend in GOOD_BACKENDS for token in INVALID_API_TOKENS
]


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


def test_get_malformed_backend(api):
    """Raises TypeError if a malformed backend is returned"""
    provider = _get_test_provider(url=API_URL)

    with pytest.raises(
        QiskitBackendNotFoundError, match="No backend matches the criteria"
    ):
        provider.get_backend(MALFORMED_BACKEND)


def test_malformed_backend_warns(api):
    """Listing backends skips a malformed device with a warning naming its invalid fields"""
    provider = _get_test_provider(url=API_URL)

    with pytest.warns(
        UserWarning, match=f"Skipping malformed device '{MALFORMED_BACKEND}': version"
    ):
        provider.backends()


@pytest.mark.parametrize("backend_name", [*GOOD_BACKENDS, NON_PULSE_BACKEND])
def test_backend_hash(api, backend_name):
    """Equal backends hash alike, so backends can be set members and dict keys"""
    first = _get_test_provider(url=API_URL).get_backend(backend_name)
    second = _get_test_provider(url=API_URL).get_backend(backend_name)

    assert first == second
    assert hash(first) == hash(second)
    assert len({first, second}) == 1


def test_get_backend_fetches_only_its_own_calibration(api):
    """get_backend(name) fetches the calibration of that backend alone"""
    provider = _get_test_provider(url=API_URL)

    provider.get_backend("loke").target

    calibration_paths = {
        req.path for req in api.request_history if "/calibrations/" in req.path
    }
    assert calibration_paths == {"/calibrations/loke"}


def test_get_backend_with_uncalibrated_couplers(api):
    """Pairs whose couplers have no calibration get no CZ, and every backend still loads"""
    calibration = {**TEST_CALIBRATIONS_MAP["loke"], "couplers": []}
    api.get(f"{API_URL}/calibrations/loke", json=calibration)
    provider = _get_test_provider(url=API_URL)

    backend = provider.get_backend("loke")
    with pytest.warns(UserWarning, match="Backend 'loke' has no CZ on"):
        target = backend.target

    assert "cz" not in target.operation_names
    assert provider.get_backend("qiskit_pulse_2q").target.instruction_supported("cz")


def test_get_backend_with_pairs_without_couplers(api):
    """Coupled pairs that have no coupler get no CZ, and every backend still loads"""
    devices = [
        {**device, "qubit_ids_coupler_map": []} if device["name"] == "loke" else device
        for device in BACKENDS_LIST
    ]
    api.get(f"{API_URL}/devices/", json={"data": devices, "skip": 0, "limit": None})
    provider = _get_test_provider(url=API_URL)

    backend = provider.get_backend("loke")
    with pytest.warns(UserWarning, match="Backend 'loke' has no CZ on"):
        target = backend.target

    assert "cz" not in target.operation_names


def test_get_non_pulse_backend(api):
    """Retrieves a backend whose device takes no pulse jobs"""
    provider = _get_test_provider(url=API_URL)
    got = provider.get_backend(NON_PULSE_BACKEND)
    assert isinstance(got, OpenQASMBackend)


def test_run_on_non_pulse_backend(api):
    """run() on a backend whose device takes no pulse jobs raises before registering a job"""
    provider = _get_test_provider(url=API_URL)
    backend = provider.get_backend(NON_PULSE_BACKEND)
    qc = QuantumCircuit(1, 1)
    qc.x(0)
    qc.measure(0, 0)

    with pytest.raises(TergiteError, match="accept pulse jobs only"):
        backend.run(qc)

    assert [req for req in api.request_history if req.method == "POST"] == []


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


@pytest.mark.parametrize("token, backend", _INVALID_PARAMS)
def test_invalid_bearer_auth(token, backend, bearer_auth_api):
    """Invalid bearer auth raises RuntimeError if backend is shielded with bearer auth"""
    provider = _get_test_provider(url=API_URL, token=token)
    with pytest.raises(RuntimeError, match="Error retrieving backends: Unauthorized"):
        provider.get_backend(backend)


def _get_test_provider(url: str, token: str = None) -> Provider:
    """Retrieves a provider to be used for testing given the optional token"""
    return Tergite.use_provider_account(service_name="test", url=url, token=token)
