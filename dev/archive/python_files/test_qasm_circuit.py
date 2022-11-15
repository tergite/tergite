#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import time

import numpy as np
import qiskit.circuit as circuit
import qiskit.compiler as compiler
from qiskit.providers.jobstatus import JobStatus

from qiskit.providers.tergite import Tergite

# In[ ]:


chalmers = Tergite.get_provider()
backend = chalmers.get_backend(input("Backend name? "))


# In[ ]:


def test_circuit(exc_qbs, msr_qbs) -> circuit.QuantumCircuit:
    qc = circuit.QuantumCircuit(5, 5)
    qc.barrier()
    qc.reset([0, 1, 2, 3, 4])
    # qc.rx(np.pi/2, exc_qbs)
    qc.h(exc_qbs)
    qc.measure(msr_qbs, msr_qbs)
    return qc


qc = test_circuit((2, 3), (2, 3))
qc.draw()


# In[ ]:


job = backend.run(
    compiler.transpile(qc, backend=backend), meas_level=2, meas_return="single"
)


# In[ ]:


while job.status() != JobStatus.DONE:
    time.sleep(1)
result = job.result()
result.get_counts()
