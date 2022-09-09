from qiskit import *
from qiskit.providers.tergite import Tergite
from qiskit.visualization import plot_histogram
from pprint import pprint

provider = Tergite.get_provider()
pingu_backend = provider.get_backend("pingu")


quantum_circuit = QuantumCircuit.from_qasm_file("tests/example.qasm")
print(quantum_circuit)
