#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import json

import numpy as np
import qiskit.circuit as circuit
import qiskit.compiler as compiler
import qiskit.pulse as pulse
import retworkx.visualization as rxv
from qiskit.ignis.verification import StateTomographyFitter
from qiskit.result import Result
from qiskit.visualization.pulse_v2.stylesheet import IQXDebugging, IQXSimple
from qiskit_experiments.framework import ExperimentData
from qiskit_experiments.library.tomography import (
    StateTomography,
    StateTomographyAnalysis,
)

from tergite_qiskit_connector.providers.tergite import Tergite

# In[ ]:


# In[ ]:


with open("tomog.result.json", mode="r") as fp:
    result = Result.from_dict(json.load(fp))


# In[ ]:


len(result.results)
