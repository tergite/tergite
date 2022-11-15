import matplotlib.pyplot as plt
import numpy as np
import requests

mss_url = "http://qtl-axean.mc2.chalmers.se:8002"


def plot_hist(ax: object, job_id: str):
    response = requests.get(mss_url + "/rng/" + job_id)
    if not response.ok:
        raise RuntimeError(
            f"Unable to communicate with {mss_url}, response: {response}"
        )

    data = response.json()
    numbers = data["numbers"]
    # N = data["N"]
    return ax.hist(numbers)


# returns 422 if cant find job_id, which is not response.ok
job_ids = [
    "5a00247d-d22b-44ac-a00a-5d21c087f65d",
    "e904e367-b64b-4380-92eb-151f06ed5faf",
    "d044505c-4c92-4a34-8f7a-b880a03d8069",
]

fig, ax = plt.subplots(len(job_ids), 1, figsize=(5, 10))

for idx, j in enumerate(job_ids):
    ax[idx].set_title(f"job_id: {j}")
    plot_hist(ax=ax[idx], job_id=j)

fig.tight_layout()
plt.show()
