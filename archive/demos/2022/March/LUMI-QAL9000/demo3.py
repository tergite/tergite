from qiskit import *
from qiskit.visualization import plot_histogram

from tergite.qiskit.providers import Tergite

IBMQ.load_account()

tergite_provider = Tergite.get_provider()
ibmq_provider = IBMQ.get_provider()
sim_provider = BasicAer

pingu_backend = tergite_provider.get_backend("pingu")
ibmq_backend = ibmq_provider.get_backend("ibmq_burlington")
sim_backend = sim_provider.get_backend("qasm_simulator")

quantum_circuit = QuantumCircuit(3, 3)

quantum_circuit.h(1)
quantum_circuit.x(2)
quantum_circuit.t(2)

quantum_circuit.measure([0, 1, 2], [0, 1, 2])
print(quantum_circuit)

job_pingu = execute(quantum_circuit, pingu_backend)
job_sim = execute(quantum_circuit, sim_backend)
job_ibmq = execute(quantum_circuit, ibmq_backend)

print("Waiting for IBMQ results", flush=True)
job_ibmq.wait_for_final_state()

c_sim = job_sim.result().get_counts()
c_pingu = job_pingu.result().get_counts()
c_ibmq = job_ibmq.result().get_counts()

plot_histogram(c_sim).show()
plot_histogram(c_pingu).show()
plot_histogram(c_ibmq).show()
