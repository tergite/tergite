#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import retworkx.visualization as rxv
from qiskit.providers.fake_provider import FakeHanoi
from qiskit.transpiler import CouplingMap

from qiskit.providers.tergite import Tergite

# In[ ]:


chalmers = Tergite.get_provider()
backend = chalmers.get_backend(input("Backend name? "))
backend.set_options(shots=1500)
print(f"Loaded Tergite backend {backend.name}")


# In[ ]:


dfq, dfr, dfc = backend.calibration_tables
dfq
