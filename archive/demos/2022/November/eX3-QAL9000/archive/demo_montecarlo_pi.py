import time
from uuid import uuid4 as uuid

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import requests
from qiskit.providers.jobstatus import JobStatus
from qiskit.providers.tergite import Tergite
from tqdm.auto import tqdm

# Task: Estimate Pi numerically
# Area of circle = pi*r**2
#
# If we compute the area of a quarter of a circle and multiply it by 4, we should get Pi = 3.14159...
# The size of the circle doesn't matter, so let's take the top right quadrant of the unit circle.

# ---------------------- settings
vm_url = "http://qtl-axean.mc2.chalmers.se"
mss_url = vm_url + ":8002"
bcc_url = vm_url + ":8000"
chalmers = Tergite.get_provider()
backend = chalmers.get_backend("Nov7")
print(f"Connected to backend: {backend.name}")

text_settings = {"fontsize": 20}
plt.ion()  # enable interactive mode
fig, axs = plt.subplots(1, 2, figsize=(14, 6.5), sharex=True, sharey=True)
# ---------------------- settings


def f(x):
    return np.sqrt(1 - x**2)


def mc_hitmiss(fn: callable, *, M: int) -> tuple:
    np.random.seed(0)
    U = np.random.rand(M, 2)
    estimate = np.mean(
        U[:, 1] <= fn(U[:, 0])
    )  # <- This is the estimator for integral value
    return estimate, U


def plot_estimate(ax: object, estimate: float):
    textstr = "$\hat\pi = {:10.5f}$".format(estimate)
    props = dict(boxstyle="round", facecolor="wheat", alpha=1)
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


def plot_samples(ax: object, samples: np.array, marker: str = "o"):
    inside = np.sqrt(samples[:, 0] ** 2 + samples[:, 1] ** 2) < 1
    ax.scatter(samples[inside, 0], samples[inside, 1], color="C1", marker=marker)
    ax.scatter(samples[~inside, 0], samples[~inside, 1], color="C2", marker=marker)


def api_error(url, response):
    return f"Failed to communicate with {url}, response: {response}"


def wait_for_job(job_id: str, timeout: int = 20) -> object:
    mss_response = requests.get(mss_url + "/rng/" + job_id)
    return mss_response


def qmc_estimate(fn: callable, U: np.ndarray) -> float:
    estimate = np.mean(
        U[:, 1] <= fn(U[:, 0])
    )  # <- This is the estimator for integral value
    return estimate


def qmc_hitmiss_parts(fn: callable, num_jobs: int = 3) -> tuple:
    job_ids = list(str(uuid()) for _ in range(num_jobs))

    estimates = list()  # should be monotonic increasing
    points = np.asarray([[], []]).T
    points_by_job = dict()

    for job_id in tqdm(job_ids):
        # queue job on backend directly
        bcc_response = requests.get(bcc_url + "/rng/" + job_id)
        if not bcc_response.ok:
            raise RuntimeError(api_error(bcc_url, bcc_response))

        # wait for job to complete
        mss_response = wait_for_job(job_id)
        data = mss_response.json()

        # split obtained numbers into two disjoint subsets
        N = data["N"] // 2
        X = np.asarray(data["numbers"][:N]).astype(float)  # first M are X coordinate
        Y = np.asarray(data["numbers"][N : (N + N)]).astype(
            float
        )  # second M are Y coordinate

        # these numbers are random 32-bit integers in the range [-2**31, 2**31 - 1]
        # so we want to convert them to floats in the range [0,1]
        X += 2**31
        Y += 2**31
        X *= 2**-32
        Y *= 2**-32

        # concatenate points obtained
        U = np.zeros((N, 2))
        U[:, 0] = X
        U[:, 1] = Y
        points = np.concatenate((points, U))
        points_by_job[job_id] = U
        est = qmc_estimate(fn, points)

        plot_samples(axs[1], U)
        plot_estimate(axs[1], est * 4)
        fig.canvas.draw()
        fig.canvas.flush_events()

        # compute estimator on all the points, up until now
        estimates.append(est)

    return estimates, points_by_job, job_ids


xdef = np.linspace(0, 1)

# ---------- Riemann estimate
riemann_est = sum(f(xdef) * np.diff(xdef)[0])
riemann_est_pi = riemann_est * 4

# ---------- Monte Carlo estimate, from pseudo random numbers
mc_est, mc_samples = mc_hitmiss(f, M=400)
mc_est_pi = mc_est * 4

# ---------- Plotting non quantum stuff
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

axs[0].set_title("Riemann", **text_settings)
axs[1].set_title("Quantum Monte Carlo", **text_settings)

for ax in axs:
    ax.plot(np.linspace(0, 1, 1000), f(np.linspace(0, 1, 1000)), lw=3.5, zorder=99)
    ax.set_ylabel("f(x)", **text_settings)
    ax.set_xlabel("x", **text_settings)
    ax.grid(zorder=-99, alpha=0.5)
    ax.tick_params(axis="both", which="minor", labelsize=text_settings["fontsize"])
    ax.tick_params(axis="both", which="major", labelsize=text_settings["fontsize"])
fig.suptitle("$f(x) = (1-x^2)^{1/2}$", **text_settings)

# plot_samples(axs[1], mc_samples)
# plot_estimate(axs[1], mc_est_pi)

fig.canvas.draw()
fig.canvas.flush_events()

# ---------- Plotting quantum stuff
qmc_hitmiss_parts(f, num_jobs=5)

fig.tight_layout()
