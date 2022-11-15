#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import functools
import pathlib
import time
from tempfile import gettempdir

import matplotlib.pyplot as plt

# from quantify_core.visualization import mpl_plotting as qpl
import matplotlib.ticker as plticker
import numpy as np
import qiskit.circuit as circuit
import qiskit.pulse as pulse
import requests
import rich
import tqcsf.file

# from quantify_core.analysis import fitting_models as fm
from qiskit.visualization.pulse_v2.stylesheet import IQXDebugging
from scipy.spatial import distance_matrix

from qiskit.providers.tergite import Tergite

# In[ ]:


chalmers = Tergite.get_provider()
backend = chalmers.get_backend("PinguOpenPulse_Anuj")
backend.set_options(shots=1000)
backend.calibration_table
