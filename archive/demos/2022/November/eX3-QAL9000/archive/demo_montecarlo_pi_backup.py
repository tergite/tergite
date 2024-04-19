import time

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import requests
from qiskit.providers.jobstatus import JobStatus
from qiskit.providers.tergite import Tergite

# Task: Estimate Pi numerically
# Area of circle = pi*r**2
#
# If we compute the area of a quarter of a circle and multiply it by 4, we should get Pi = 3.14159...
# The size of the circle doesn't matter, so let's take the top right quadrant of the unit circle.


def f(x):
    return np.sqrt(1 - x**2)


xdef = np.linspace(0, 1)

# ---------- Riemann estimate
riemann_est = sum(f(xdef) * np.diff(xdef)[0])
riemann_est_pi = riemann_est * 4


# ---------- Monte Carlo estimate, from pseudo random numbers
def mc_hitmiss(fn: callable, *, M: int) -> tuple:
    np.random.seed(0)
    U = np.random.rand(M, 2)
    estimate = np.mean(
        U[:, 1] <= fn(U[:, 0])
    )  # <- This is the estimator for integral value
    return estimate, U


mc_est, mc_samples = mc_hitmiss(f, M=400)
mc_est_pi = mc_est * 4

# ---------- Monte Carlo estimate, from Quantum Computer

mss_url = "http://qtl-axean.mc2.chalmers.se:8002"
chalmers = Tergite.get_provider()
backend = chalmers.get_backend("Nov7")


# dummy class for testing, implement this before the demo
class _test:
    def job_id(self: object) -> str:
        # return "7ef2ab6d-d33a-4849-82ca-2e183fc457ce" # test data
        # return "d044505c-4c92-4a34-8f7a-b880a03d8069"
        return "e904e367-b64b-4380-92eb-151f06ed5faf"

    def status(self: object) -> JobStatus:
        if np.random.rand() < 0.2:
            return JobStatus.DONE
        else:
            return JobStatus.QUEUED


def qmc_hitmiss(fn: callable, *, M: int) -> tuple:
    job = _test()  # <- REPLACE THIS WITH SOMETHING THATS WAITABLE
    while job.status() != JobStatus.DONE:
        time.sleep(1)

    response = requests.get(mss_url + "/rng/" + str(job.job_id()))
    if response.ok:
        data = response.json()
        X = np.asarray(data["numbers"][:M])  # first M are X coordinate
        Y = np.asarray(data["numbers"][M : (M + M)])  # second M are Y coordinate

        # these numbers are random 32-bit integers in the range [-2**31, 2**31 - 1]
        # so we need to convert them to floats in the range [0,1]
        U = np.zeros((M, 2))
        U[:, 0] = (X + 2**31) / (2**32)
        U[:, 1] = (Y + 2**31) / (2**32)
    else:
        raise RuntimeError(
            f"Unable to fetch random numbers from MSS, response: {response}"
        )

    estimate = np.mean(
        U[:, 1] <= fn(U[:, 0])
    )  # <- This is the estimator for integral value
    return estimate, U


qmc_est, qmc_samples = qmc_hitmiss(f, M=313 // 2)
qmc_est_pi = qmc_est * 4

# ---------- Plotting
text_settings = {"fontsize": 20}
fig, axs = plt.subplots(1, 3, figsize=(17, 6.5), sharex=True, sharey=True)


def plot_estimate(ax: object, estimate: float):
    textstr = "$\hat\pi = {}$".format(estimate)
    props = dict(boxstyle="round", facecolor="wheat", alpha=0.95)
    # place a text box in upper left in axes coords
    ax.text(
        0.15,
        0.15,
        textstr,
        transform=ax.transAxes,
        verticalalignment="top",
        bbox=props,
        fontsize=25,
    )


# plot riemann rectangles
riemann_rects = [
    mpl.patches.Rectangle(
        xy=(x, 0),
        width=np.diff(xdef)[0],
        height=f(x),
        ec="black",
        fc="none",
        alpha=0.75,
    )
    for x in xdef
]
for r in riemann_rects:
    axs[0].add_patch(r)
plot_estimate(axs[0], riemann_est_pi)


# plot monte carlo samples for the MC and QMC methods
def plot_samples(ax: object, samples: np.array):
    inside = np.sqrt(samples[:, 0] ** 2 + samples[:, 1] ** 2) < 1
    ax.scatter(samples[inside, 0], samples[inside, 1], color="C1")
    ax.scatter(samples[~inside, 0], samples[~inside, 1], color="C2")


plot_samples(axs[1], mc_samples)
plot_estimate(axs[1], mc_est_pi)

plot_samples(axs[2], qmc_samples)
plot_estimate(axs[2], qmc_est_pi)

axs[0].set_title("Riemann", **text_settings)
axs[1].set_title("Monte Carlo", **text_settings)
axs[2].set_title("Quantum Monte Carlo", **text_settings)

for ax in axs:
    ax.plot(np.linspace(0, 1, 1000), f(np.linspace(0, 1, 1000)), lw=3.5, zorder=99)
    ax.set_ylabel("f(x)", **text_settings)
    ax.set_xlabel("x", **text_settings)
    ax.grid(zorder=-99, alpha=0.3)
    ax.tick_params(axis="both", which="minor", labelsize=text_settings["fontsize"])
    ax.tick_params(axis="both", which="major", labelsize=text_settings["fontsize"])
fig.suptitle("$f(x) = (1-x^2)^{1/2}$", **text_settings)

# print(f"Riemann approximation of Pi {np.pi} from f(x) over [0,1] :", f"4*{riemann_qtr_pi} = ", 4*riemann_qtr_pi)

fig.tight_layout()
plt.show()
