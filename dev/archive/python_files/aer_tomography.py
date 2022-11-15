#!/usr/bin/env python
# coding: utf-8

# In[ ]:


get_ipython().run_line_magic("matplotlib", "inline")
import json
from pprint import pprint

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
import qiskit.circuit as circuit
import qiskit.compiler as compiler
import qiskit.pulse as pulse
import qiskit.quantum_info as qi
import retworkx.visualization as rxv
import rich

# from qiskit import *
from qiskit.ignis.verification.tomography import (
    StateTomographyFitter,
    state_tomography_circuits,
)
from qiskit.visualization import (
    plot_bloch_multivector,
    plot_histogram,
    plot_state_city,
    plot_state_hinton,
    plot_state_paulivec,
    plot_state_qsphere,
)
from qiskit.visualization.pulse_v2.stylesheet import IQXDebugging, IQXSimple
from qiskit_experiments.library.tomography import StateTomography
from tqdm.auto import tqdm

from qiskit import Aer
from qiskit.providers.tergite import Tergite

# In[ ]:


# In[ ]:


backend = Aer.get_backend("aer_simulator")


# In[ ]:


q = circuit.QuantumRegister(5)
circ = circuit.QuantumCircuit(q)
circ.barrier()
circ.reset([q[0]])

print("Input circuit")
print(circ)


# In[ ]:


target_state = qi.Statevector.from_instruction(circ)


# In[ ]:


tomography_circuits = state_tomography_circuits(circ, [q[0]])


# In[ ]:


job = backend.run(tomography_circuits, meas_level=2)


# In[ ]:


rich.print(job.qobj())


# In[ ]:


rich.print(job.result().to_dict())


# In[ ]:


fitter = StateTomographyFitter(job.result(), tomography_circuits)


# In[ ]:


fitter.data


# In[ ]:


density_matrix = fitter.fit(method="lstsq")


# In[ ]:


fig = plot_bloch_multivector(
    density_matrix, reverse_bits=True, filename="bg_bloch_multivector.jpg"
)


# In[ ]:


fig


# In[ ]:


def frame_bloch(j):
    J = np.linspace(0, 1.2 * np.pi / 2, 10)
    q = circuit.QuantumRegister(5)
    circ = circuit.QuantumCircuit(q)
    [circ.reset(qb) for qb in q]  # reset qubits

    circ.ry(J[j], q[4])  # ry <-

    circ.rx(np.pi / 4, q[3]), circ.rz(J[j], q[3])  # rz <-

    circ.rx(J[j], q[2])  # rx

    circ.rx(-np.pi / 4, q[1]), circ.rz(-J[j], q[1])  # rz ->

    circ.ry(-J[j], q[0])  # ry ->

    tomography_circuits = state_tomography_circuits(circ, q)
    job = backend.run(tomography_circuits, meas_level=2)
    fitter = StateTomographyFitter(job.result(), tomography_circuits)
    density_matrix = fitter.fit(method="lstsq")
    plot_bloch_multivector(
        density_matrix, reverse_bits=True, filename=f"frames/frame{j}.jpg"
    )


[frame_bloch(j) for j in tqdm(range(10))]
