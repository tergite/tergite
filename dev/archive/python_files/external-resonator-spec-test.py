#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import numpy as np
import qiskit.compiler as compiler
from qiskit.circuit import Parameter
from qiskit.pulse import Schedule, ScheduleBlock
from qiskit.pulse.channels import (
    AcquireChannel,
    DriveChannel,
    MeasureChannel,
    MemorySlot,
)
from qiskit.pulse.instructions import (
    Acquire,
    Delay,
    Play,
    SetFrequency,
    SetPhase,
    ShiftFrequency,
    ShiftPhase,
)
from qiskit.pulse.library import Constant, Gaussian, cos
from qiskit.pulse.transforms.alignments import AlignEquispaced, AlignLeft, AlignRight
from qiskit.visualization.pulse_v2.stylesheet import IQXDebugging

# In[ ]:


µs = 1e-6
ns = 1e-9
MHz = 1e6
GHz = 1e9
mV = 1e-3


# In[ ]:


freq_qubit = Parameter("freq")
qubit = 0

spec_pulse_width = 3.5 * µs
spec_pulse_amp = 14 * mV


# In[ ]:


center = 6.21445 * GHz
span = 35 * MHz
step = 1.5 * MHz
start = center - span / 2
end = center + span / 2
frequencies = np.arange(start, end, step)

print(
    f"Sweeping from {start/GHz} GHz to {end/GHz} GHz around {center/GHz} GHz with stepsize {step/MHz} MHz."
)
# ----------------------------------------------

sched = ScheduleBlock(f"resonator spectroscopy - stepsize {step/MHz} MHz")
sched += SetFrequency(freq_qubit, MeasureChannel(qubit))
sched += SetFrequency(freq_qubit, MeasureChannel(qubit))
sched += Play(
    Constant(int(spec_pulse_width / ns), amp=spec_pulse_amp), MeasureChannel(qubit)
)
sched += Delay(300, AcquireChannel(qubit), "Time of flight")
sched += Acquire(int(3 * µs / ns), AcquireChannel(qubit), MemorySlot(qubit))

# ----------------------------------------------
sweep = [sched.assign_parameters({freq_qubit: f}, inplace=False) for f in frequencies]
print(f"Thats {len(sweep)} schedules")


# In[ ]:


sweep[0].draw(style=IQXDebugging())


# # Loading Tergite and the backend

# In[ ]:


from tergite_qiskit_connector.providers.tergite import Tergite

chalmers = Tergite.get_provider()
backend = chalmers.get_backend("Pingu")
backend.set_options(shots=1024)
backend.options.shots


# In[ ]:


import tempfile
from pathlib import Path

Path(tempfile.gettempdir())


# In[ ]:


backend.run(
    sweep,
    meas_level=1,
    meas_return="avg",
    qobj_header={
        "frequencies": frequencies,
        # "amplitudes"  : amplitudes
    },
)
