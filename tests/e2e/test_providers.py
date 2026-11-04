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
"""End-to-end tests for providers and backends"""

import pytest
from qiskit.providers import QiskitBackendNotFoundError

from tergite import Provider

RUNNING_BACKENDS = ("sim_1q", "sim_2q", "Loke")


def test_backends_lists_the_running_devices(backend_provider: Provider):
    """backends() lists every device whose backend is running"""
    names = {backend.name for backend in backend_provider.backends()}

    assert set(RUNNING_BACKENDS) <= names


def test_get_unknown_backend(backend_provider: Provider):
    """get_backend() of a name MSS does not know raises"""
    with pytest.raises(QiskitBackendNotFoundError):
        backend_provider.get_backend("no-such-device")


def test_target_follows_the_calibration(backend_provider: Provider):
    """A backend's target holds its calibrated gates on each qubit and coupled pair"""
    backend = backend_provider.get_backend("sim_2q")
    target = backend.target

    assert target.num_qubits == 2
    for name in ("rx", "rz", "delay", "reset", "measure"):
        assert set(target.qargs_for_operation_name(name)) == {(0,), (1,)}
    assert set(target.qargs_for_operation_name("cz")) == set(
        {tuple(p) for p in backend.data.coupling_map if p[0] != p[1]}
    )
    assert backend.last_calibrated is not None
