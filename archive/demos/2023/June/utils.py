import os
import pickle
import typing
from typing import TYPE_CHECKING

import numpy as np
import qiskit

if TYPE_CHECKING:
    from learning import Net

try:
    from tergite import Tergite
except:
    print("Could not import Tergite!")


class Utils:
    @staticmethod
    def get_backend(name: str, shots: int = 1024):
        if name == "AerSimulator":
            return qiskit.Aer.get_backend("aer_simulator")
        elif name is None:
            raise RuntimeError("Calling backend without providing name")
        else:
            tergite_provider = Tergite.get_provider()
            backend = tergite_provider.get_backend(name)
            backend.set_options(shots=shots)
            return backend

    @staticmethod
    def change_backend_layer(
        model: "Net", backend, qubits: typing.List[int], shots: int = 1024
    ) -> "Net":
        model.hybrid.quantum_circuit.backend = backend
        model.hybrid.quantum_circuit.shots = shots
        model.hybrid.quantum_circuit.qubits = qubits
        return model

    @staticmethod
    def append_thetas(run_id: str, thetas: np.ndarray):
        if not os.path.exists("temp"):
            os.makedirs("temp")
        filename = f"temp/{run_id}.thetas"
        stored_thetas = np.array([])
        if f"{run_id}.thetas" in os.listdir("temp"):
            stored_thetas = pickle.load(open(filename, "rb"))
        stored_thetas = np.concatenate((stored_thetas, np.array(thetas)))
        pickle.dump(stored_thetas, open(filename, "wb"))

    @staticmethod
    def load_thetas(run_id: str):
        filename = f"temp/{run_id}.thetas"
        return pickle.load(open(filename, "rb"))
