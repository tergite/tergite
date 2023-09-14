from pprint import pprint

from qiskit.visualization import plot_histogram

from qiskit import *
from tergite_qiskit_connector.providers.tergite import Tergite

provider = Tergite.get_provider()
pingu_backend = provider.get_backend("pingu")


quantum_circuit = QuantumCircuit.from_qasm_file("tests/example.qasm")
print(quantum_circuit)
