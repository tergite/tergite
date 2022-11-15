#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import matplotlib.pyplot as plt
import numpy as np
import qiskit.circuit as circuit
import qiskit.compiler as compiler
import qiskit.pulse as pulse
import retworkx.visualization as rxv
import tqcsf.file
from qiskit.visualization.pulse_v2.stylesheet import IQXDebugging, IQXSimple

from qiskit.providers.tergite import Tergite

# In[ ]:


chalmers = Tergite.get_provider()
backend = chalmers.get_backend(input("Backend name? "))
backend.set_options(shots=2000)


# In[ ]:


qc = circuit.QuantumCircuit(5, 5)
qc.barrier([0, 1, 2, 3, 4])
[qc.reset(i) for i in range(5)]  # reset qubits
[qc.rx(np.pi, i) for i in range(5)]  # rotate qubits
qc.measure([i for i in range(5)], [i for i in range(5)])  # measure qubits
qc.draw()


# In[ ]:


job = backend.run(qc, meas_level=1, meas_return="single")
