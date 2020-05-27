from qiskit.providers.tergite import Tergite
from qiskit import *

provider = Tergite.get_provider()
backend = provider.get_backend("pingu")

qr = QuantumRegister(2)
qc = QuantumCircuit(qr)
qc.cz(qr[0], qr[1])
qc.h(qr[0])

mytr = transpile(qc, backend)
myqobj = assemble(mytr, backend)

job = execute(mytr, backend)
