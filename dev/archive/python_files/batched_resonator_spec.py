#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import functools
import pathlib
import time
from tempfile import gettempdir

import matplotlib.pyplot as plt
import matplotlib.ticker as plticker
import numpy as np
import qiskit.circuit as circuit
import qiskit.pulse as pulse
import requests
import rich
import template_schedules as templates
import tqcsf.file
from qiskit.visualization.pulse_v2.stylesheet import IQXDebugging
from quantify_core.analysis import fitting_models as fm
from quantify_core.visualization import mpl_plotting as qpl
from scipy.spatial import distance_matrix

from tergite_qiskit_connector.providers.tergite import Tergite

# In[ ]:


chalmers = Tergite.get_provider()
backend = chalmers.get_backend("PinguOpenPulse")
backend.set_options(shots=1000)
templates.backend = backend


# In[ ]:


qubits = (0, 1, 2, 3)  # qubits to characterize

# 8d70a7f1-41f9-4bd6-a68f-abd6ae9fdf18 @ 17mV:
resonator_freqs = [
    6.884461765134884e9,
    6.745482508417368e9,
    7.029379073099976e9,
    7.187505069855161e9,
    6.66309e9,
]


# In[ ]:


param_sched = pulse.ScheduleBlock()

freq0 = circuit.Parameter(f"f drive 0")
freq1 = circuit.Parameter(f"f drive 1")
freq2 = circuit.Parameter(f"f drive 2")
freq3 = circuit.Parameter(f"f drive 3")

param_sched += pulse.SetFrequency(freq0, backend.measure_channel(0))
param_sched += pulse.SetFrequency(freq1, backend.measure_channel(1))
param_sched += pulse.SetFrequency(freq2, backend.measure_channel(2))
param_sched += pulse.SetFrequency(freq3, backend.measure_channel(3))

ro_dur = 3500
ro_amp = 17e-3

param_sched += templates.measure(0, ro_amp=ro_amp, ro_dur=ro_dur)
param_sched += templates.measure(1, ro_amp=ro_amp, ro_dur=ro_dur)
param_sched += templates.measure(2, ro_amp=ro_amp, ro_dur=ro_dur)
param_sched += templates.measure(3, ro_amp=ro_amp, ro_dur=ro_dur)
