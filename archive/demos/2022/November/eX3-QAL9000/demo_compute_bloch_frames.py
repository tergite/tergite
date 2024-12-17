#!/usr/bin/env python3.9
# coding: utf-8

import contextlib
import time

import matplotlib.pyplot as plt
import numpy as np
import qiskit.circuit as circuit
import qiskit.compiler as compiler

with contextlib.redirect_stderr(None):
    from qiskit.ignis.verification.tomography import StateTomographyFitter
    from qiskit.ignis.verification.tomography import state_tomography_circuits

from datetime import datetime
from os import listdir, makedirs
from pathlib import Path
from shutil import move

from qiskit.providers.jobstatus import JobStatus
from qiskit.visualization import plot_bloch_multivector
from tqdm.auto import tqdm

from tergite.qiskit.providers import Tergite

folder = Path("demo_bloch_frames").resolve()


def save_old_frames():
    global folder
    saved_folder = folder / "saved_animations"
    makedirs(saved_folder, exist_ok=True)

    old_frames = [f for f in listdir(folder) if f.endswith(".jpg")]

    if len(old_frames):
        now_time = datetime.now()
        mstr = now_time.strftime("%Y%m%d%H%M%S")
        new_dir = saved_folder / mstr
        makedirs(new_dir, exist_ok=True)
        for f in old_frames:
            move(folder / f, new_dir / f)


save_old_frames()

# ----------------------------------------------------------------------------

chalmers = Tergite.get_provider()
backend = chalmers.get_backend("Nov7")
backend.set_options(shots=2000)

print(f"Loaded backend {backend.name} (QAL 9000)")

thetadef = -1 * np.asarray([0, np.pi / 2, np.pi])


def tomog_circs(theta):
    q = circuit.QuantumRegister(1)
    circ = circuit.QuantumCircuit(q)
    circ.barrier([0])
    circ.reset([0])

    circ.rx(theta, q[0])

    return state_tomography_circuits(circ, [q[0]])


print("Transpiling...")
with contextlib.redirect_stderr(None):
    precomputed_tomog_circs = [
        compiler.transpile(tomog_circs(theta), backend=backend) for theta in thetadef
    ]


def compute_new_frame(j: int):
    job = backend.run(precomputed_tomog_circs[j], meas_level=2, meas_return="single")
    while job.status() != JobStatus.DONE:
        time.sleep(1)  # blocking wait

    # fit state vector when result is ready
    fitter = StateTomographyFitter(job.result(), precomputed_tomog_circs[j])

    density_matrix = fitter.fit(method="lstsq")

    # compute frame and save to main memory
    _tmp = plot_bloch_multivector(
        density_matrix, reverse_bits=True, filename=folder / f"frame{j}.jpg"
    )
    plt.close(_tmp)  # close returned figure


# progress bar
for j in tqdm(range(len(thetadef)), desc="Reconstructing qubit state"):
    compute_new_frame(j)
