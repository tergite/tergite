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
"""The ways a circuit measures into its clbits, run on the two-qubit simulator.

tests/integration/test_golden_results.py pins the same cases against a mocked backend; these
show that the real stack puts each qubit's outcome in the clbit the circuit names. They flip
qubits with X alone, and the simulated chip is noisy, so each expects its outcome in most
shots, not all.
"""
from typing import Dict

import numpy as np
from qiskit import QuantumCircuit, transpile

from tergite import Provider
from tests.utils.jobs import wait_for_final_state

SHOTS = 200
# the share of shots the expected outcomes must reach
MAJORITY = 0.8


def test_both_qubits_into_c(backend_provider: Provider):
    """Qubit 0, flipped, and qubit 1 measured into the circuit's own register give 01"""
    qc = QuantumCircuit(2, 2)
    qc.x(0)
    qc.measure([0, 1], [0, 1])

    counts = _run(backend_provider, qc)

    assert _get_share(counts, "01") >= MAJORITY


def test_measure_all(backend_provider: Provider):
    """Qubit 1, flipped, and qubit 0 measured with measure_all() give 10"""
    qc = QuantumCircuit(2)
    qc.x(1)
    qc.measure_all()

    counts = _run(backend_provider, qc)

    assert _get_share(counts, "10") >= MAJORITY


def test_partial_measurement(backend_provider: Provider):
    """Qubit 1, flipped, measured into the one clbit gives 1"""
    qc = QuantumCircuit(2, 1)
    qc.x(1)
    qc.measure(1, 0)

    counts = _run(backend_provider, qc)

    assert _get_share(counts, "1") >= MAJORITY


def test_permuted_clbits(backend_provider: Provider):
    """Qubit 0, flipped, measured into clbit 1, and qubit 1 into clbit 0, gives 10"""
    qc = QuantumCircuit(2, 2)
    qc.x(0)
    qc.measure(0, 1)
    qc.measure(1, 0)

    counts = _run(backend_provider, qc)

    assert _get_share(counts, "10") >= MAJORITY


def test_two_circuits_in_one_job(backend_provider: Provider):
    """Each circuit of a job gets its own counts"""
    flipped = QuantumCircuit(2, 2)
    flipped.x(0)
    flipped.measure([0, 1], [0, 1])
    idle = QuantumCircuit(2, 1)
    idle.measure(1, 0)
    backend = backend_provider.get_backend("qiskit_pulse_2q")
    backend.set_options(shots=SHOTS)

    job = backend.run(transpile([flipped, idle], backend=backend), meas_level=2)
    wait_for_final_state(job)
    result = job.result()

    assert _get_share(result.get_counts(0), "01") >= MAJORITY
    assert _get_share(result.get_counts(1), "0") >= MAJORITY


def test_iq_points_averaged(backend_provider: Provider):
    """meas_level=1 with meas_return=avg gives one IQ point per measured qubit"""
    qc = QuantumCircuit(2, 2)
    qc.measure([0, 1], [0, 1])
    backend = backend_provider.get_backend("qiskit_pulse_2q")
    backend.set_options(shots=SHOTS)

    job = backend.run(transpile(qc, backend=backend), meas_level=1, meas_return="avg")
    wait_for_final_state(job)

    assert np.asarray(job.result().get_memory()).shape == (2,)


def _run(provider: Provider, qc: QuantumCircuit) -> Dict[str, int]:
    """Runs the circuit on the two-qubit simulator, returning its counts"""
    backend = provider.get_backend("qiskit_pulse_2q")
    backend.set_options(shots=SHOTS)
    job = backend.run(transpile(qc, backend=backend), meas_level=2)
    wait_for_final_state(job)
    return job.result().get_counts()


def _get_share(counts: Dict[str, int], *outcomes: str) -> float:
    """The share of the shots that gave one of the outcomes"""
    return sum(counts.get(outcome, 0) for outcome in outcomes) / sum(counts.values())
