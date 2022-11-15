#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import functools
import shutil
from itertools import product

import helpers
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import qiskit.circuit as circuit
import qiskit.pulse as pulse
import tqcsf.file
from more_itertools import powerset
from qiskit.visualization.pulse_v2.stylesheet import IQXDebugging

from qiskit.providers.tergite import Tergite

# In[ ]:


chalmers = Tergite.get_provider()
backend = chalmers.get_backend(
    input("Please enter backend name (default: LokiOpenPulse)") or "LokiOpenPulse"
)
backend.set_options(shots=1500)
helpers.backend = backend
print(f"Loaded Tergite backend {backend.name}")


# # Resonator spectroscopy (Qubit 1)

# In[ ]:


header = helpers.gen_header((0,))


# In[ ]:


sweep = helpers.sweep_rs2d((0,), qobj_header=header)
sweep[2].draw(style=IQXDebugging())


# In[ ]:


job = backend.run(sweep, qobj_header=header, meas_level=1)


# In[ ]:


save_name = input("Please provide logfile name (saves in CWD): ") or str(job.job_id())
save_name = save_name + ".hdf5"
shutil.copyfile(job.logfile, save_name)
sf = tqcsf.file.StorageFile(save_name, mode="r")
ds = sf.as_xarray()
ds


# In[ ]:


fig, ax = plt.subplots(1, figsize=(10, 4))
np.abs(ds["slot~0/acq~0"]).plot(ax=ax, ls="-.")
ax.axvline(6.74159e9, c="red")
fig.tight_layout()


# # Qubit spectroscopy (Qubit 1)

# In[ ]:


headerB = helpers.gen_header((0,))


# In[ ]:


sweepB = helpers.sweep_qs2d(
    (0,), qobj_header=headerB, ro_freq_Hz=(6.74159e9,), ro_amp_V=(5e-3,)
)
sweepB[2].draw(style=IQXDebugging())


# In[ ]:


job = backend.run(sweepB, qobj_header=headerB, meas_level=1)


# In[ ]:


save_name = input("Please provide logfile name (saves in CWD): ") or str(job.job_id())
save_name = save_name + ".hdf5"
shutil.copyfile(job.logfile, save_name)
sf = tqcsf.file.StorageFile(save_name, mode="r")
ds = sf.as_xarray()
ds


# In[ ]:


fig, ax = plt.subplots(1, figsize=(10, 4))
np.abs(ds["slot~0/acq~0"]).plot(ax=ax, ls="-.")
ax.axvline(3.74806e9, c="red")
fig.tight_layout()


# In[ ]:


np.abs(ds["slot~0/acq~0"])[:, -1].plot()


# # Rabi oscillations (Qubit 1)
