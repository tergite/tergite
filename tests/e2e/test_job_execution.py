"""End-to-end tests for job execution"""

import numpy as np
from qiskit import circuit, compiler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from tergite import Job, Provider
from tests.utils.jobs import wait_for_final_state


def test_simulator_1_qubit_gate(backend_provider: Provider):
    """Can run a single qubit gate operation on simulator when auth on MSS and backend is ON"""
    backend = backend_provider.get_backend("qiskit_pulse_1q")
    backend.set_options(shots=1024)

    qc = circuit.QuantumCircuit(1)
    qc.x(0)
    qc.h(0)
    qc.measure_all()

    tc = compiler.transpile(qc, backend=backend)
    job: Job = backend.run(tc, meas_level=2, meas_return="single")
    wait_for_final_state(job)
    result = job.result().get_counts()

    assert (
        420 <= result["0"] <= 640
    ), f"Expected {result['00']} to be between 450 and 640"
    assert (
        420 <= result["1"] <= 640
    ), f"Expected {result['01']} to be between 450 and 640"


def test_simulator_2_qubit_gate(backend_provider: Provider):
    """A Bell pair on the 2-qubit simulator reads 00 and 11 about half the time each"""
    backend = backend_provider.get_backend("qiskit_pulse_2q")
    backend.set_options(shots=1024)

    qc = circuit.QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()

    tc = compiler.transpile(qc, backend=backend)
    job: Job = backend.run(tc, meas_level=2, meas_return="single")
    wait_for_final_state(job)
    result = job.result().get_counts()

    for bits in ("00", "11"):
        assert 420 <= result[bits] <= 640, f"{bits}: {result[bits]} not in 420 to 640"


def test_simulator_2_qubit_gate_iq_points(backend_provider: Provider):
    """Can return well-seperated clusters of raw iq points for a two-qubit gate operation
    on simulator when auth on MSS and backend is ON"""
    backend = backend_provider.get_backend("qiskit_pulse_2q")
    backend.set_options(shots=1024)

    qc = circuit.QuantumCircuit(2)
    qc.h(0)
    qc.h(1)
    qc.cx(0, 1)
    qc.measure_all()

    tc = compiler.transpile(qc, backend=backend)
    job: Job = backend.run(tc, meas_level=1, meas_return="single")
    wait_for_final_state(job)
    memory = job.result().get_memory()  # shape = (shots, n_qubits)

    assert (
        memory.ndim == 2 and memory.shape[1] == 2
    ), f"Expected (shots, 2) IQ array, got {memory.shape}"

    for qubit in range(2):
        # I-Q coordinates for this qubit
        xy = np.column_stack((memory[:, qubit].real, memory[:, qubit].imag))

        # Run unsupervised 2-means clustering
        kmeans = KMeans(n_clusters=2, n_init="auto", random_state=0).fit(xy)
        labels = kmeans.labels_

        # ensure both clusters are populated
        counts = np.bincount(labels, minlength=2)
        assert counts.min() > 0, f"One of the clusters for qubit {qubit} is empty"

        # ensure clusters are well-separated
        sil = silhouette_score(xy, labels)
        assert sil > 0.25, (
            f"Clusters for qubit {qubit} are not distinct enough "
            f"(silhouette ={sil:.2f} ≤ 0.25)"
        )


def test_dummy_quantify_device(backend_provider: Provider):
    """Can run summy jobs on the dummy device"""
    backend = backend_provider.get_backend("Loke")
    backend.set_options(shots=1024)

    qc = circuit.QuantumCircuit(1)
    qc.x(0)
    qc.h(0)
    qc.measure_all()

    tc = compiler.transpile(qc, backend=backend)
    job: Job = backend.run(tc, meas_level=2, meas_return="single")
    wait_for_final_state(job)
    result = job.result().get_counts()

    assert result["0"] == 1024, f"Expected {result['00']} to be 1024"
