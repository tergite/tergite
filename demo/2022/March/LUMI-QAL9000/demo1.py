from pprint import pprint

from qiskit.visualization import plot_histogram

from qiskit import *
from tergite_qiskit_connector.providers.tergite import Tergite

provider = Tergite.get_provider()
pingu_backend = provider.get_backend("pingu")

quantum_register = QuantumRegister(3)  # 3 qubits
quantum_circuit = QuantumCircuit(quantum_register)

quantum_circuit.x(quantum_register[1])
quantum_circuit.h(quantum_register[2])

print(quantum_circuit)
