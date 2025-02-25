"""End-to-end tests for job execution"""
import pytest
from qiskit import circuit, compiler

from tergite.qiskit.providers import Provider, Job
from tests.utils.env import is_end_to_end


@pytest.mark.skipif(not is_end_to_end(), reason="is end-to-end test")
def test_simulator_1_qubit_gate(backend_provider: Provider):
    """Can run a single qubit gate operation on simulator when auth on MSS and backend is ON"""
    backend = backend_provider.get_backend("qiskit_pulse_1q")
    backend.set_options(shots=1024)

    qc = circuit.QuantumCircuit(1, 1)
    qc.x(0)
    qc.h(0)
    qc.measure_all()

    tc = compiler.transpile(qc, backend=backend)
    job: Job = backend.run(tc, meas_level=2, meas_return="single")
    job.wait_for_final_state(timeout=100)
    result = job.result()

    assert 490 >= result[0] <= 600
    assert 490 >= result[1] <= 600


@pytest.mark.skipif(not is_end_to_end(), reason="is end-to-end test")
def test_simulator_2_qubit_gate(backend_provider: Provider):
    """Can run a two-qubit gate operation on simulator when auth on MSS and backend is ON"""
    backend = backend_provider.get_backend("qiskit_pulse_2q")
    backend.set_options(shots=1024)

    qc = circuit.QuantumCircuit(2, 2)
    qc.h(0)
    qc.h(1)
    qc.cx(0, 1)
    qc.measure_all()

    tc = compiler.transpile(qc, backend=backend)
    job: Job = backend.run(tc, meas_level=2, meas_return="single")
    job.wait_for_final_state(timeout=300)
    result = job.result()

    assert 490 >= result[0] <= 600
    assert 490 >= result[1] <= 600
