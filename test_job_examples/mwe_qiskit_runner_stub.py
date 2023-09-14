#!/usr/bin/env python
# coding: utf-8

# In[1]:


from time import sleep

import qiskit.circuit as circuit

from tergite_qiskit_connector.providers.tergite import Tergite

# In[2]:


chalmers = Tergite.get_provider()
backend = chalmers.get_backend("OpenQASM")
backend.set_options(shots=1024)
backend


# In[3]:


qc = circuit.QuantumCircuit(2, 2)
qc.h(1)
qc.measure(1, 1)
qc.draw()


# In[4]:


job = backend.run(qc)


# In[5]:


sleep(10)
job.result()
