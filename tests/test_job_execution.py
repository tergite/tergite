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
"""tests for the running of qiskit circuits on the tergite backend"""
import numpy as np
from qiskit import circuit, compiler

from tergite_qiskit_connector.providers.tergite import OpenPulseBackend, Tergite
from tergite_qiskit_connector.providers.tergite.backend import TergiteBackendConfig
from tergite_qiskit_connector.providers.tergite.provider_account import ProviderAccount
from tests.conftest import API_URL, BACKENDS_LIST, GOOD_BACKEND
from tests.utils.records import get_record


def test_transpile(api):
    """compiler.transpile(qc, backend=backend) returns backend-specific QuantumCircuits"""
    backend = _get_backend()
    qc = _get_test_qiskit_circuit()
    expected = _get_expected_transpiled_circuit()
    got = compiler.transpile(qc, backend=backend)
    assert got == expected


def _get_test_qiskit_circuit():
    """Returns a qiskit quantum circuit for testing"""
    qc = circuit.QuantumCircuit(2, 2)
    qc.h(1)
    qc.measure(1, 1)
    return qc


def _get_expected_transpiled_circuit():
    """Returns a quantum circuit specific to the TEST_BACKEND"""
    phase = np.pi / 2
    qc = circuit.QuantumCircuit(2, 2, global_phase=phase)
    qc.rz(np.pi / 2, 1)
    qc.rx(np.pi / 2, 1)
    qc.rz(np.pi / 2, 1)
    qc.measure(1, 1)
    return qc


def _get_backend():
    """Retrieves the right backend"""
    account = ProviderAccount(service_name="test", url=API_URL)
    provider = Tergite.use_provider_account(account)
    expected_json = get_record(BACKENDS_LIST, _filter={"name": GOOD_BACKEND})
    return OpenPulseBackend(
        data=TergiteBackendConfig(**expected_json), provider=provider, base_url=API_URL
    )
