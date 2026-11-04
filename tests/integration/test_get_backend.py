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

from tergite import OpenPulseBackend, OpenQASMBackend, Provider, Tergite, TergiteBackend
from tergite.clients.mss.models import Device
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

# a refused token is refused alike on every backend, so one backend is enough
_INVALID_PARAMS = [(token, "loke") for token in INVALID_API_TOKENS]


@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_get_backend(api, backend_name):
    """Retrieves the right backend"""
    provider = _get_test_provider(url=API_URL)
    expected_json = get_record(BACKENDS_LIST, _filter={"name": backend_name})
    expected = TergiteBackend(
        data=Device.model_validate(expected_json), provider=provider, base_url=API_URL
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


@pytest.mark.parametrize("alias", [OpenPulseBackend, OpenQASMBackend])
def test_deprecated_backend_names(api, alias):
    """OpenPulseBackend and OpenQASMBackend still make a TergiteBackend, with a warning"""
    provider = _get_test_provider(url=API_URL)
    device = Device.model_validate(get_record(BACKENDS_LIST, _filter={"name": "loke"}))

    with pytest.warns(DeprecationWarning, match="use TergiteBackend"):
        backend = alias(data=device, provider=provider, base_url=API_URL)

    assert backend == provider.get_backend("loke")


def test_open_pulse_backend_points_to_the_migration_guide(api):
    provider = _get_test_provider(url=API_URL)
    device = Device.model_validate(get_record(BACKENDS_LIST, _filter={"name": "loke"}))

    with pytest.warns(DeprecationWarning, match="#migrating-from-pulse-schedules"):
        OpenPulseBackend(data=device, provider=provider, base_url=API_URL)


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
        call.request.url.path
        for call in api.calls
        if "/calibrations/" in call.request.url.path
    }
    assert calibration_paths == {"/calibrations/loke"}


def test_get_backend_with_uncalibrated_couplers(api, monkeypatch):
    """Pairs whose couplers have no calibration get no CZ, and every backend still loads"""
    calibration = {**TEST_CALIBRATIONS_MAP["loke"], "couplers": []}
    monkeypatch.setitem(TEST_CALIBRATIONS_MAP, "loke", calibration)
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
    api.get(f"{API_URL}/devices/").respond(
        json={"data": devices, "skip": 0, "limit": None}
    )
    provider = _get_test_provider(url=API_URL)

    backend = provider.get_backend("loke")
    with pytest.warns(UserWarning, match="Backend 'loke' has no CZ on"):
        target = backend.target

    assert "cz" not in target.operation_names


def test_backends_sees_a_device_come_online(api):
    """A provider lists the devices MSS lists now, not those it listed first"""
    offline = [device for device in BACKENDS_LIST if device["name"] != "loke"]
    devices_route = api.get(f"{API_URL}/devices/")
    devices_route.respond(json={"data": offline, "skip": 0, "limit": None})
    provider = _get_test_provider(url=API_URL)
    assert provider.backends(name="loke") == []

    devices_route.respond(json={"data": BACKENDS_LIST, "skip": 0, "limit": None})

    assert provider.get_backend("loke").name == "loke"


@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_bearer_auth(bearer_auth_api, backend_name):
    """Retrieves the data if backend is shielded with basic auth"""
    provider = _get_test_provider(url=API_URL, token=API_TOKEN)
    expected_json = get_record(BACKENDS_LIST, _filter={"name": backend_name})
    expected = TergiteBackend(
        data=Device.model_validate(expected_json), provider=provider, base_url=API_URL
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
