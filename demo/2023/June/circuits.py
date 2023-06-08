# 2023-05-22 following:
# https://learn.qiskit.org/course/ch-applications/hybrid-quantum-classical-neural-networks-with-pytorch-and-qiskit
import typing
from time import sleep

import numpy as np

# working with qiskit-aer 0.8.2
import qiskit
from qiskit import transpile
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

    def __init__(self,
                 backend: qiskit.providers.Backend = qiskit.Aer.get_backend('aer_simulator'),
                 shots: int = 100,
                 run_id: str = 'default'):
        self.backend = backend
        self.shots = shots
        self.run_id = run_id

    def run(self, thetas: typing.List[float]) -> np.ndarray:
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
        n_qubits = len(thetas)

        Utils.append_thetas(self.run_id, thetas)

        circuit = qiskit.QuantumCircuit(n_qubits)
        circuit.h([i for i in range(n_qubits)])
        for theta, i in list(zip(thetas, range(n_qubits))):
            circuit.ry(theta, i)
        circuit.measure_all()
        circuit.delay(100_000)
        t_qc = transpile(circuit, self.backend)

        if isinstance(self.backend, AerSimulator):
            job = self.backend.run(t_qc, shots=self.shots)
        else:
            job = self.backend.run(t_qc, meas_level=2, meas_return="single")

        waiting = True
        while waiting:
            try:
                job.result().get_counts()
                waiting = False
            except:
                print("Waiting for a response")
                sleep(4)

        expectations = []
        for i in range(n_qubits):
            marginalised_result = marginal_counts(job.result(), indices=[i])
            result = marginalised_result.get_counts()

            counts = np.array(list(result.values()))
            states = np.array(list(result.keys())).astype(np.float32)

            probabilities = counts / self.shots
            expectations.append(np.sum(states * probabilities))

        return np.array(expectations, dtype=np.float32)
