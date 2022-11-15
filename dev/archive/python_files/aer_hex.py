#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import numpy as np
import qiskit.circuit as circuit

from qiskit import Aer

# In[ ]:


backend = Aer.get_backend("aer_simulator")


# In[ ]:


qc = circuit.QuantumCircuit(4, 4)
qc.rx(1.2 * np.pi / 2, 0)
qc.measure(0, 1)
qc.draw()


# In[ ]:


job = backend.run(qc, meas_level=2, meas_return="single")
result = job.result()


# In[ ]:


result
