from qiskit import *

from tergite.qiskit.providers import Tergite

provider = Tergite.get_provider()
pingu_backend = provider.get_backend("pingu")


quantum_circuit = QuantumCircuit.from_qasm_file("tests/example.qasm")
print(quantum_circuit)
