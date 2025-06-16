# 2023-05-22 following:
# https://learn.qiskit.org/course/ch-applications/hybrid-quantum-classical-neural-networks-with-pytorch-and-qiskit
import threading
import typing
from time import sleep

import numpy as np

# working with qiskit-aer 0.8.2
import qiskit
from qiskit import transpile

try:
    from tergite import Provider
    from tergite.types.backend import TergiteBackend
except:
    print("Could not import Tergite!")
from qiskit.result import marginal_counts
from qiskit_aer import AerSimulator
from utils import Utils

# Import Tergite
# from qiskit.providers.tergite import Tergite


class HybridLayerCircuit:
    """
    This class provides a simple interface for interaction
    with the quantum circuit
    """

    def __init__(
        self,
        backend: qiskit.providers.Backend = qiskit.Aer.get_backend("aer_simulator"),
        shots: int = 100,
        qubits: typing.List[int] = None,
        run_id: str = "default",
    ):
        self.backend = backend
        self.shots = shots
        self.qubits = qubits
        self.run_id = run_id

    def run(self, thetas: typing.Union[typing.List[float], np.ndarray]) -> np.ndarray:
        """
        Runs a circuit that looks like this:
        |0> ---|H|---|RY(theta_0)|---|M|
        |0> ---|H|---|RY(theta_1)|---|M|
        ...
        |0> ---|H|---|RY(theta_n)|---|M|

        Args:
            thetas: List of thetas for the RY gates

        Returns:
            The expectation value for the standard measurement in the computational basis

        """
        # TODO: here one could add more qubit bucketing options
        # n_qubits = 1 if self.qubits is None else len(self.qubits)
        qubits = [0] if self.qubits is None else self.qubits

        min_circuit_size = max(qubits) + 1

        Utils.append_thetas(self.run_id, thetas)

        circuit = qiskit.QuantumCircuit(min_circuit_size)
        circuit.h(qubits)
        for theta, i in list(zip(thetas, qubits)):
            circuit.ry(theta, i)
        circuit.measure_all()
        circuit.delay(100_000)
        t_qc = transpile(circuit, self.backend)

        job_args = tuple([t_qc])

        if isinstance(self.backend, AerSimulator):
            job_kwargs = {"shots": self.shots}
        elif isinstance(self.backend, TergiteBackend):
            job_kwargs = {"meas_level": 2, "meas_return": "single"}
        else:
            raise NotImplementedError("Cannot resolve backend!")

        job = self.backend.run(*job_args, **job_kwargs)

        waiting = True
        while waiting:
            try:
                job.result().get_counts()
                waiting = False
            except:
                sleep(0.25)

        expectations = []
        for i in qubits:
            marginalised_result = marginal_counts(job.result(), indices=[i])
            result = marginalised_result.get_counts()

            counts = np.array(list(result.values()))
            states = np.array(list(result.keys())).astype(np.float32)

            probabilities = counts / self.shots
            expectations.append(np.sum(states * probabilities))

        # TODO: here, one must as well think of how to average the expectation values by then later
        averaged_expectations = np.mean(np.array(expectations))
        return np.array([averaged_expectations], dtype=np.float32)
