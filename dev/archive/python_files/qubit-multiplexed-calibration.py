#!/usr/bin/env python
# coding: utf-8

# # Qubit characterization tests

# In[ ]:


import functools
import time

import numpy as np
import qiskit.circuit as circuit
import qiskit.pulse as pulse
import tqcsf.file
from qiskit.visualization.pulse_v2.stylesheet import IQXDebugging

import tergite_qiskit_connector.providers.tergite.template_schedules as templates
from tergite_qiskit_connector.providers.tergite import Tergite

# In[ ]:


chalmers = Tergite.get_provider()
backend = chalmers.get_backend("PinguOpenPulse")
backend.set_options(shots=1500)
backend


# In[ ]:


backend.calibration_table


# In[ ]:


QUBITS = ("q1", "q2", "q3", "q4", "q5")
# QUBITS = ("q5",)
QUBIT_IDXS = list(map(lambda QUBIT: int(QUBIT[1]) - 1, QUBITS))


# In[ ]:


resonator_freqs = {
    "q1": 6883895727.3990345,
    "q2": 6744891313.448814,
    "q3": 7029316180.018214,
    "q4": 7187190604.446356,
    "q5": 6660015449.656492,
}

VNA_qub_freqs = {
    "q1": 5.8977e9,
    "q2": 6.109e9,  # I think this is the wrong peak
    "q3": 6.0940e9,
    "q4": 5.9500e9,
    "q3c4": 7.3632e9,
    "q5": 5.0341e9,  # has weird discontinuities?
}


# # Resonator spec

# In[ ]:


frequencies = np.asarray(
    [
        np.linspace(resonator_freqs[q] - 2e6, resonator_freqs[q] + 2e6, 260)
        for q in QUBITS
    ]
).transpose()


# In[ ]:


param_sched = pulse.ScheduleBlock(name=f"res spec {QUBITS}")
freqs = [circuit.Parameter(f"ro freq q{q}") for q in QUBIT_IDXS]
for k, q in enumerate(QUBIT_IDXS):
    param_sched += pulse.SetFrequency(freqs[k], backend.measure_channel(q))

param_sched += templates.measure(backend, set(QUBIT_IDXS))


# In[ ]:


sweep = [
    param_sched.assign_parameters(
        functools.reduce(
            lambda a, b: {**a, **b}, [{p: f[i]} for i, p in enumerate(freqs)]
        ),
        inplace=False,
    )
    for f in frequencies
]

print("Total schedule count in sweep:", len(sweep))


# In[ ]:


# compile metadata about the sweep
qobj_header = {
    "tag": f"Resonator spectroscopy {QUBITS}",
    "sweep": {
        "serial_order": ("frequencies",),
        "parameters": {
            "frequencies": {
                "long_name": "Frequency of readout pulse",
                "unit": "Hz",
                "slots": {q: frequencies[:, k] for k, q in enumerate(QUBIT_IDXS)},
            }
        },
    },
}
job = backend.run(sweep, qobj_header=qobj_header, meas_level=1)


# In[ ]:


while job.status != "DONE":
    time.sleep(5)
sf = tqcsf.file.StorageFile(job.logfile, mode="r")


# In[ ]:


ds = sf.as_xarray()
ds


# In[ ]:


from analysis import plot_fit_functions as pff

# In[ ]:


get_ipython().run_line_magic("matplotlib", "inline")
data = pff.plot_fit_resonator(ds)


# # Two tone

# In[ ]:


param_sched = pulse.ScheduleBlock(name=f"tt spec {QUBITS}")

stim_dur = 5000

freqs = [circuit.Parameter(f"stim freq q{q}") for q in QUBIT_IDXS]
amps = [circuit.Parameter(f"stim amp q{q}") for q in QUBIT_IDXS]

for k, (q, Q) in enumerate(zip(QUBIT_IDXS, QUBITS)):
    param_sched += pulse.SetFrequency(resonator_freqs[Q], backend.measure_channel(q))
    param_sched += pulse.SetFrequency(freqs[k], backend.drive_channel(q))
    param_sched += pulse.Play(
        pulse.Gaussian(stim_dur, amp=amps[k], sigma=stim_dur / 5),
        backend.drive_channel(q),
    )
    # don't measure during excitation
    param_sched += pulse.Delay(stim_dur, backend.measure_channel(q), name="Wait excite")
    param_sched += pulse.Delay(stim_dur, backend.acquire_channel(q), name="Wait excite")

param_sched += templates.measure(backend, set(QUBIT_IDXS))


# In[ ]:


frequencies = np.asarray(
    [np.linspace(VNA_qub_freqs[Q] - 5e6, VNA_qub_freqs[Q] + 5e6, 120) for Q in QUBITS]
).transpose()
amplitudes = np.asarray([np.linspace(0, 1e-3, 10) for Q in QUBITS]).transpose()


# In[ ]:


sweep = [
    param_sched.assign_parameters(
        functools.reduce(
            lambda a, b: {**a, **b},
            [({p: f[i]} | {q: a[i]}) for i, p in enumerate(freqs) for q in amps],
        ),
        inplace=False,
    )
    for f in frequencies
    for a in amplitudes
]

print("Total schedule count in sweep:", len(sweep))


# In[ ]:


# compile metadata about the sweep
qobj_header = {
    "tag": f"Qubit spectroscopy {QUBITS}",
    "sweep": {
        "serial_order": ("frequencies", "amplitudes"),
        "parameters": {
            "frequencies": {
                "long_name": "Frequency of excitation pulse",
                "unit": "Hz",
                "slots": {q: frequencies[:, k] for k, q in enumerate(QUBIT_IDXS)},
            },
            "amplitudes": {
                "long_name": "Amplitude of excitation pulse",
                "unit": "V",
                "slots": {q: amplitudes[:, k] for k, q in enumerate(QUBIT_IDXS)},
            },
        },
    },
}
job = backend.run(sweep, qobj_header=qobj_header, meas_level=1)


# In[ ]:


while job.status != "DONE":
    time.sleep(5)
sf = tqcsf.file.StorageFile(job.logfile, mode="r")


# In[ ]:


ds = sf.as_xarray()
ds


# In[ ]:


get_ipython().run_line_magic("matplotlib", "notebook")
import matplotlib.pyplot as plt

fig, axs = plt.subplots(len(QUBITS), 1)
if len(QUBITS) == 1:
    axs = [axs]

for i, var in enumerate(ds):
    np.abs(ds[var]).plot(ax=axs[i])
    axs[i].set_title(var)
