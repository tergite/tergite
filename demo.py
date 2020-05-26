from qiskit.providers.tergite import Tergite
from qiskit import *

provider=Tergite.get_provider()
backend=provider.get_backend('pingu')

qr = QuantumRegister(3)
qc = QuantumCircuit(qr)
qc.cry(3.14, qr[0], qr[1])

mytr = transpile(qc,backend)
myqobj = assemble(qc,backend)

job = execute(mytr,backend)

