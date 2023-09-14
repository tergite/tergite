#!/usr/bin/env python
# coding: utf-8

# In[1]:


import qiskit.circuit as circuit
import qiskit.compiler as compiler

from tergite_qiskit_connector.providers.tergite import Tergite

# In[2]:


chalmers = Tergite.get_provider()
backend = chalmers.get_backend("Nov_rain")
backend.set_options(shots=1024)
backend


# In[3]:


#backend.calibration_tables


# In[4]:


qc = circuit.QuantumCircuit(2, 2)
qc.h(1)
qc.measure(1, 1)
qc.draw()


# In[5]:


tc = compiler.transpile(qc, backend=backend)
tc.draw()


# In[6]:


job = backend.run(tc, meas_level=2)
