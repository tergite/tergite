import contextlib
import time

import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
import qiskit.circuit as circuit
import qiskit.compiler as compiler
from qiskit.ignis.verification.tomography import (
    StateTomographyFitter,
    state_tomography_circuits,
)
from qiskit.providers.jobstatus import JobStatus
from qiskit.providers.tergite import Tergite
from qiskit.visualization import plot_bloch_multivector
from tqdm.auto import tqdm

chalmers = Tergite.get_provider()
backend = chalmers.get_backend("Nov7")
backend.set_options(shots=2000)

print(f"Loaded backend {backend.name}")

fig, ax = plt.subplots()

# show first frame
im = ax.imshow(plt.imread("ground_state.jpg"))
ax.axis("off")

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


# function to update figure
def updatefig(j):
    if not j:
        return [im]

    print()
    job = backend.run(precomputed_tomog_circs[j], meas_level=2, meas_return="single")
    print("Computing frame...")
    while job.status() != JobStatus.DONE:
        print("#", end="")
        time.sleep(1)  # blocking wait
    print("  Complete")

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
    fig, updatefig, frames=range(len(thetadef)), interval=50, blit=True, repeat=False
)
# figManager = plt.get_current_fig_manager()
# figManager.window.showMaximized()
plt.show()
