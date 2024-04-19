import json
import time
from pprint import pprint

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
import qiskit.circuit as circuit
import qiskit.compiler as compiler
import qiskit.pulse as pulse
import qiskit.quantum_info as qi
import retworkx.visualization as rxv
from matplotlib import pyplot as plt
from qiskit import Aer
from qiskit.ignis.verification.tomography import (
    StateTomographyFitter,
    state_tomography_circuits,
)
from qiskit.providers.jobstatus import JobStatus
from qiskit.providers.tergite import Tergite
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

backend = Aer.get_backend("aer_simulator")

fig, ax = plt.subplots()

im = ax.imshow(np.zeros((320, 1600)))
ax.axis("off")

thetadef = np.linspace(0, 1.09 * np.pi / 2, 20)  # overshoot by 9%


def tomog_circs(theta):
    q = circuit.QuantumRegister(5)
    circ = circuit.QuantumCircuit(q)
    circ.barrier()
    [circ.reset(qb) for qb in q]  # reset qubits

    # Rotate qubit 4 around the y-axis
    circ.ry(theta, q[4])

    # Rotate qubit 3 around the z-axis, spinning at np.pi/4 around x
    circ.rx(np.pi / 4, q[3])
    circ.rz(theta, q[3])

    # Rotate qubit 2 around the x-axis
    circ.rx(theta, q[2])

    # Rotate qubit 3 around the z-axis in the other direction, spinning at np.pi/4 around x
    circ.rx(-np.pi / 4, q[1])
    circ.rz(-theta, q[1])

    # Rotate qubit 0 around the y-axis in the other direction
    circ.ry(-theta, q[0])

    return state_tomography_circuits(circ, q)


precomputed_tomog_circs = [tomog_circs(theta) for theta in thetadef]


# function to update figure
def updatefig(j):
    job = backend.run(precomputed_tomog_circs[j], meas_level=2)
    while job.status() != JobStatus.DONE:
        time.sleep(0.1)  # blocking wait

    # fit state vector
    fitter = StateTomographyFitter(job.result(), precomputed_tomog_circs[j])
    density_matrix = fitter.fit(method="lstsq")

    # plot and save to main memory
    _tmp = plot_bloch_multivector(
        density_matrix, reverse_bits=True, filename=f"frames/frame{j}.jpg"
    )
    plt.close(_tmp)

    # load file (workaround, because cannot access the axis directly)
    image_j = plt.imread(f"frames/frame{j}.jpg")

    # show next frame
    im.set_array(image_j)
    return [im]


# start animation
ani = animation.FuncAnimation(
    fig, updatefig, frames=range(20), interval=50, blit=True, repeat=False
)
figManager = plt.get_current_fig_manager()
figManager.window.showMaximized()
plt.show()
