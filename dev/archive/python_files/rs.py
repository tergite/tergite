#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import time

import numpy as np
import qiskit.circuit as circuit
import qiskit.compiler as compiler
import qiskit.pulse as pulse
import retworkx.visualization as rxv
import tqcsf.file
from qiskit.providers.jobstatus import JobStatus
from qiskit.visualization.pulse_v2.stylesheet import IQXDebugging, IQXSimple

from tergite_qiskit_connector.providers.tergite import Tergite

# In[ ]:


chalmers = Tergite.get_provider()
backend = chalmers.get_backend(input("Backend name? "))


# In[ ]:


qubit_idx = 0


# In[ ]:


qc0 = circuit.QuantumCircuit(5, 5, name="KET0")
qc0
