#!/usr/bin/env python
# coding: utf-8

# # OpenQASM job

# In[ ]:


from time import sleep

import qiskit.circuit as circuit
import requests

from tergite_qiskit_connector.providers.tergite import Tergite

# In[ ]:


chalmers = Tergite.get_provider()
backend = chalmers.get_backend("PinguOpenQASM")
backend.set_options(shots=1024)
backend


# In[ ]:


qc = circuit.QuantumCircuit(2, 2)
qc.h(1)
qc.measure(1, 1)
qc.draw()


# In[ ]:


job = backend.run(qc)


# In[ ]:


sleep(5)
job.result()
