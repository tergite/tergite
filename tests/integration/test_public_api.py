# This code is part of Tergite
#
# (C) Copyright Chalmers Next Labs 2026
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""The public API users program against, which REFACTOR.md's convention 14 keeps.

Its behaviour is covered beside the code it exercises (test_provider.py, test_get_backend.py,
test_job_execution.py); this file pins the signatures, and what those files leave out.
"""
import inspect
from typing import Callable

import pytest

from tergite import Job, Provider, ProviderFactory, Tergite, TergiteBackend

from .conftest import API_URL, GOOD_BACKENDS

SIGNATURES = [
    (
        ProviderFactory.use_provider_account,
        "(self, service_name, url, token=None, save=False)",
    ),
    (ProviderFactory.get_provider, "(self, service_name=None)"),
    (ProviderFactory.providers, "(self)"),
    (Provider.backends, "(self, /, name=None, filters=None, **kwargs)"),
    (Provider.get_backend, "(self, name=None, **kwargs)"),
    (Provider.job, "(self, job_id)"),
    (TergiteBackend.run, "(self, run_input, /, calibrations=(), **options)"),
    (TergiteBackend.set_options, "(self, **fields)"),
    (Job.status, "(self)"),
    (Job.result, "(self)"),
    (Job.cancel, "(self)"),
]
PROPERTIES = [
    (TergiteBackend, "target"),
    (TergiteBackend, "options"),
    (Job, "download_url"),
    (Job, "logfile"),
]


@pytest.mark.parametrize("function, expected", SIGNATURES)
def test_signatures(function: Callable, expected: str):
    """The public functions keep their parameters, defaults included"""
    signature = inspect.signature(function).replace(
        return_annotation=inspect.Signature.empty
    )
    parameters = [
        p.replace(annotation=inspect.Parameter.empty)
        for p in signature.parameters.values()
    ]

    assert str(signature.replace(parameters=parameters)) == expected


@pytest.mark.parametrize("cls, name", PROPERTIES)
def test_properties(cls: type, name: str):
    """The public properties stay properties"""
    assert isinstance(inspect.getattr_static(cls, name), property)


def test_providers_lists_service_names(mock_tergiterc):
    """providers() lists the service names of the accounts in use"""
    factory = ProviderFactory(rc_file=mock_tergiterc)
    factory.use_provider_account("foo", url=API_URL)
    factory.use_provider_account("bar", url=API_URL)

    assert factory.providers() == ["foo", "bar"]


def test_backends_filters_by_name(api):
    """backends(name=…) returns only the backend of that name"""
    provider = Tergite.use_provider_account(service_name="test", url=API_URL)

    assert [backend.name for backend in provider.backends(name="loke")] == ["loke"]


def test_backends_filters_with_a_callable(api):
    """backends(filters=…) returns the backends the callable accepts"""
    provider = Tergite.use_provider_account(service_name="test", url=API_URL)

    got = provider.backends(filters=lambda backend: backend.name.startswith("qiskit"))

    assert sorted(backend.name for backend in got) == [
        "qiskit_pulse_1q",
        "qiskit_pulse_2q",
    ]


def test_set_options_sets_shots(api):
    """set_options(shots=…) sets the shots of the jobs the backend runs"""
    backend = _get_backend("loke")
    backend.set_options(shots=123)

    assert backend.options.shots == 123


def test_set_options_refuses_zero_shots(api):
    """set_options refuses shots below 1"""
    backend = _get_backend("loke")

    with pytest.raises(ValueError):
        backend.set_options(shots=0)


@pytest.mark.parametrize("backend_name", GOOD_BACKENDS)
def test_target_has_the_calibrated_gates(api, backend_name):
    """target holds rx, rz, delay, reset and measure on every qubit, and cz on each coupled pair"""
    backend = _get_backend(backend_name)
    target = backend.target
    qubits = {(q,) for q in range(backend.data.number_of_qubits)}
    pairs = {tuple(p) for p in backend.data.coupling_map if p[0] != p[1]}

    assert target.num_qubits == backend.data.number_of_qubits
    for name in ("rx", "rz", "delay", "reset", "measure"):
        assert set(target.qargs_for_operation_name(name)) == qubits
    if pairs:
        assert set(target.qargs_for_operation_name("cz")) == pairs


def _get_backend(name: str) -> TergiteBackend:
    """Retrieves the backend of the given name through a test provider"""
    provider = Tergite.use_provider_account(service_name="test", url=API_URL)
    return provider.get_backend(name)
