#!/usr/bin/env python
# coding: utf-8

# # Qubit characterization tests

# In[ ]:


import functools
import pathlib
import re
import time
from inspect import getsource
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
from analysis.spectroscopy_analysis import LorentzianModel
from qiskit.visualization.pulse_v2.stylesheet import IQXDebugging
from quantify_core.analysis import fitting_models as fm
from quantify_core.visualization import mpl_plotting as qpl
from scipy.spatial import distance_matrix

from qiskit.providers.tergite import Tergite


def format_fit_data(model, x, s21, ds, fit_result, /, **kwargs):
    abs_s21 = np.abs(s21)
    return (
        {
            "job_id": ds.attrs["job_id"],
            "tuid": ds.attrs["tuid"],
            "model": model.name,
            "Average |s21|": {"value": float(abs_s21.mean())},
            "Minimum |s21|": {"value": float(abs_s21.min())},
            "Maximum |s21|": {"value": float(abs_s21.max())},
            "Arg Minimum |s21|": {"value": float(x[np.argmin(abs_s21)])},
            "Arg Maximum |s21|": {"value": float(x[np.argmax(abs_s21)])},
        }
        | {
            p: {"value": v.value, "stderr": v.stderr}
            for p, v in fit_result.params.items()
        }
        | kwargs
    )


def plot_fit_resonator(ds):

    fig, axs = plt.subplots(len(ds), 1)
    if len(ds) == 1:
        axs = [axs]

    f = list()

    for i, var in enumerate(ds):
        # plot data
        np.abs(ds[var]).plot(ax=axs[i])
        axs[i].set_title(var)

        # retrieve raw data for model fitting
        x = ds.coords[ds.variables[var].attrs["coords"][0]].data
        s21 = ds[var].data

        # fit resonator model against the data
        model = fm.ResonatorModel()
        guess = model.guess(s21, f=x)
        fit_result = model.fit(s21, params=guess, f=x)

        axs[i].axvline(fit_result.params["fr"].value, ls="--", color="black", alpha=0.2)
        axs[i].axvline(x[np.argmin(np.abs(s21))], ls="-", color="red")

        # plot model fit
        qpl.plot_fit(
            ax=axs[i],
            fit_res=fit_result,
            plot_init=True,
            range_casting="abs",
        )
        f.append(format_fit_data(model, x, s21, ds, fit_result, code="RESONATOR_SPEC"))

    return f


def plot_fit_lorentz(ds):
    fig, axs = plt.subplots(len(ds), 1)
    if len(ds) == 1:
        axs = [axs]

    f = list()
    for i, var in enumerate(ds):
        # plot data
        np.abs(ds[var]).plot(ax=axs[i])
        axs[i].set_title(var)

        # retrieve raw data for model fitting
        x = ds.coords[ds.variables[var].attrs["coords"][0]].data
        s21 = ds[var].data

        # fit resonator model against the data
        model = LorentzianModel()
        guess = model.guess(np.abs(s21), x=x)
        fit_result = model.fit(np.abs(s21), params=guess, x=x)

        model_y = fit_result.eval(x=x)
        axs[i].plot(x, model_y, "r-")
        print()
        print(var, ":", fit_result.params["x0"].value / 1e9, "GHz")
        f.append(format_fit_data(model, x, s21, ds, fit_result, code="QUBIT_SPEC"))

    return f


def plot_fit_cosine(ds):
    fig, axs = plt.subplots(len(ds), 1)
    if len(ds) == 1:
        axs = [axs]

    f = list()
    for i, var in enumerate(ds):
        # plot data
        np.abs(ds[var]).plot(ax=axs[i])
        axs[i].set_title(var)

        # retrieve raw data for model fitting
        x = ds.coords[ds.variables[var].attrs["coords"][0]].data
        s21 = ds[var].data

        # fit resonator model against the data
        model = fm.CosineModel()
        guess = model.guess(np.abs(s21), x=x)
        fit_result = model.fit(np.abs(s21), params=guess, x=x)

        model_y = fit_result.eval(x=x)
        axs[i].plot(x, model_y, "r-")

        idxs = np.argmax(model_y)
        v = x[idxs]
        axs[i].axvline(v, color="red")
        print(var, ":", v * 1000, "mV")
        f.append(
            format_fit_data(model, x, s21, ds, fit_result, code="RABI_OSC", ket1_amp=v)
        )

    return f


def plot_fit_decay(ds):
    fig, axs = plt.subplots(len(ds), 1)
    if len(ds) == 1:
        axs = [axs]

    f = list()
    for i, var in enumerate(ds):
        # plot data
        np.abs(ds[var]).plot(ax=axs[i])
        axs[i].set_title(var)

        # retrieve raw data for model fitting
        x = ds.coords[ds.variables[var].attrs["coords"][0]].data
        s21 = ds[var].data

        # fit resonator model against the data
        model = fm.ExpDecayModel()
        guess = model.guess(np.abs(s21), delay=x)
        fit_result = model.fit(np.abs(s21), params=guess, t=x)

        model_y = fit_result.eval(delay=x)
        axs[i].plot(x, model_y, "r-")
        print(var, ":", fit_result.params["tau"].value, "ns")
        f.append(format_fit_data(model, x, s21, ds, fit_result, code="T1_DECOHERENCE"))

    return f


# In[ ]:


chalmers = Tergite.get_provider()
backend = chalmers.get_backend("PinguOpenPulse")
backend.set_options(shots=1500)
templates.backend = backend


# In[ ]:


QUBIT = "q4"
QUBIT_IDX = int(QUBIT[1]) - 1


# In[ ]:


resonator_freqs = {
    "q1": 6.884461765134884e9,
    "q2": 6.745482508417368e9,
    "q3": 7.029379073099976e9,
    "q4": 7.187505069855161e9,
    "q5": 6.660153814436366e9,
}
VNA_qub_freqs = {
    "q1": 5.8977e9,
    "q2": 6.109e9,  # I think this is the wrong peak
    "q3": 6.0940e9,
    "q4": 5.9500e9,
    "q3c4": 7.3632e9,
    "q5": 5.0341e9,  # has weird discontinuities?
}


# # Resonator spec

# In[ ]:


frequencies = np.linspace(
    resonator_freqs[QUBIT] - 6e6, resonator_freqs[QUBIT] + 6e6, 160
)


# In[ ]:


param_sched = pulse.ScheduleBlock(name=f"res spec {QUBIT}")

freq0 = circuit.Parameter(f"f readout 0")
param_sched += pulse.SetFrequency(freq0, backend.measure_channel(QUBIT_IDX))

ro_dur = 3000
ro_amp = 14e-3

param_sched += templates.measure(QUBIT_IDX, ro_amp=ro_amp, ro_dur=ro_dur)


# In[ ]:


sweep = [
    param_sched.assign_parameters(
        {
            freq0: f,
        },
        inplace=False,
    )
    for f in frequencies
]
print("Total schedule count in sweep:", len(sweep))


# In[ ]:


sweep[10].draw(style=IQXDebugging())


# In[ ]:


# compile metadata about the sweep
qobj_header = {
    "sweep": {
        "serial_order": ("frequencies",),
        "parameters": {
            "frequencies": {
                "long_name": "Frequency of readout pulse",
                "unit": "Hz",
                "slots": {QUBIT_IDX: frequencies},
            }
        },
    }
}
job = backend.run(sweep, qobj_header=qobj_header)


# In[ ]:


while job.status != "DONE":
    time.sleep(5)
sf = tqcsf.file.StorageFile(job.logfile, mode="r")
ds = sf.as_xarray()
ds


# In[ ]:


get_ipython().run_line_magic("matplotlib", "inline")
data = plot_fit_resonator(ds)
data[0]["ro_amp"] = ro_amp
data[0]["ro_dur"] = ro_dur * 1e-9
data[0]["qubit"] = QUBIT
rich.print(data)


# In[ ]:


job.store_data(data)


# # Qubit spectroscopy

# In[ ]:


param_sched = pulse.ScheduleBlock(name=f"tt spec {QUBIT}")

param_sched += pulse.SetFrequency(
    res_fr := 7187391862.307991, backend.measure_channel(QUBIT_IDX)
)

freq = circuit.Parameter(f"f drive")
stim_dur = 5000

param_sched += pulse.SetFrequency(freq, backend.drive_channel(QUBIT_IDX))

param_sched += pulse.Play(
    pulse.Constant(
        stim_dur,
        amp=(stim_amp := 14e-3),
    ),
    backend.drive_channel(QUBIT_IDX),
)
# don't measure during excitation
param_sched += pulse.Delay(
    stim_dur, backend.measure_channel(QUBIT_IDX), name="Wait excite"
)
param_sched += pulse.Delay(
    stim_dur, backend.acquire_channel(QUBIT_IDX), name="Wait excite"
)

param_sched += templates.measure(QUBIT_IDX, ro_amp=ro_amp, ro_dur=ro_dur)
param_sched.draw()


# In[ ]:


GHz = 1e9
MHz = 1e6

center = VNA_qub_freqs[QUBIT]
freq_span = 60 * MHz
freq_step = 0.36 * MHz

frequencies = np.arange(center - freq_span / 2, center + freq_span / 2, freq_step)
print("That will be:", frequencies.shape[0], "schedules")


# In[ ]:


sweep = [
    param_sched.assign_parameters(
        {
            freq: f,
        },
        inplace=False,
    )
    for f in frequencies
]
print("Total schedule count in sweep:", len(sweep))


# In[ ]:


sweep[20].draw(style=IQXDebugging())


# In[ ]:


# compile metadata about the sweep
qobj_header = {
    "sweep": {
        "serial_order": ("frequencies",),
        "parameters": {
            "frequencies": {
                "long_name": "Frequency of drive pulse",
                "unit": "Hz",
                "slots": {QUBIT_IDX: frequencies},
            }
        },
    }
}
job = backend.run(sweep, qobj_header=qobj_header)


# In[ ]:


while job.status != "DONE":
    time.sleep(5)
sf = tqcsf.file.StorageFile(job.logfile, mode="r")
print("File location: ", pathlib.Path(gettempdir()) / sf.job_id)
ds = sf.as_xarray()
ds


# In[ ]:


data = plot_fit_lorentz(ds)
data[0]["ro_amp"] = ro_amp
data[0]["ro_dur"] = ro_dur * 1e-9
data[0]["stim_dur"] = stim_dur * 1e-9
data[0]["stim_amp"] = stim_amp
data[0]["qubit"] = QUBIT
data[0]["res_fr"] = res_fr
rich.print(data)


# In[ ]:


job.store_data(data)


# # Rabi oscillation

# In[ ]:


param_sched = pulse.ScheduleBlock(name=f"RABI {QUBIT}")

param_sched += pulse.SetFrequency(res_fr, backend.measure_channel(QUBIT_IDX))
param_sched += pulse.SetFrequency(
    stim_fr := 5950369506.889604, backend.drive_channel(QUBIT_IDX)
)

amp = circuit.Parameter(f"amp drive")
stim_dur = 240

param_sched += pulse.Play(
    pulse.Gaussian(stim_dur, amp=amp, sigma=round(stim_dur / 5)),
    backend.drive_channel(QUBIT_IDX),
)
# don't measure during excitation
param_sched += pulse.Delay(
    stim_dur, backend.measure_channel(QUBIT_IDX), name="Wait excite"
)
param_sched += pulse.Delay(
    stim_dur, backend.acquire_channel(QUBIT_IDX), name="Wait excite"
)

param_sched += templates.measure(QUBIT_IDX, ro_amp=ro_amp, ro_dur=ro_dur)
param_sched.draw()


# In[ ]:


amplitudes = np.linspace(0.01e-3, 20e-3, 100)
print("That will be:", amplitudes.shape[0], "schedules")


# In[ ]:


get_ipython().run_line_magic("matplotlib", "inline")
sweep = [param_sched.assign_parameters({amp: a}, inplace=False) for a in amplitudes]
print("Total schedule count in sweep:", len(sweep))


# In[ ]:


sweep[15].draw(style=IQXDebugging())


# In[ ]:


# compile metadata about the sweep
qobj_header = {
    "sweep": {
        "serial_order": ("amplitudes",),
        "parameters": {
            "amplitudes": {
                "long_name": "amplitude of drive pulse",
                "unit": "V",
                "slots": {QUBIT_IDX: amplitudes},
            }
        },
    }
}
job = backend.run(sweep, qobj_header=qobj_header)


# In[ ]:


while job.status != "DONE":
    time.sleep(5)
sf = tqcsf.file.StorageFile(job.logfile, mode="r")
print("File location: ", pathlib.Path(gettempdir()) / sf.job_id)
ds = sf.as_xarray()
ds


# In[ ]:


data = plot_fit_cosine(ds)
data[0]["ro_amp"] = ro_amp
data[0]["ro_dur"] = ro_dur * 1e-9
data[0]["stim_dur"] = stim_dur * 1e-9
data[0]["qubit"] = QUBIT
data[0]["res_fr"] = res_fr
data[0]["stim_fr"] = stim_fr
data[0]["stim_sigma"] = round(stim_dur / 5) * 1e-9
rich.print(data)


# In[ ]:


job.store_data(data)


# # Decoherence measurement (T1)

# In[ ]:


param_sched = pulse.ScheduleBlock(name=f"T1 {QUBIT}")

param_sched += pulse.SetFrequency(res_fr, backend.measure_channel(QUBIT_IDX))
param_sched += pulse.SetFrequency(stim_fr, backend.drive_channel(QUBIT_IDX))

t1_wait = circuit.Parameter(f"t1 wait")
stim_amp = 0.015759696969696972

param_sched += pulse.Play(
    pulse.Gaussian(stim_dur, amp=stim_amp, sigma=round(stim_dur / 5)),
    backend.drive_channel(QUBIT_IDX),
)
# don't measure during excitation
param_sched += pulse.Delay(
    stim_dur, backend.measure_channel(QUBIT_IDX), name="Wait excite"
)
param_sched += pulse.Delay(
    stim_dur, backend.acquire_channel(QUBIT_IDX), name="Wait excite"
)

param_sched += pulse.Delay(t1_wait, backend.measure_channel(QUBIT_IDX), name="T1 Wait")
param_sched += pulse.Delay(t1_wait, backend.acquire_channel(QUBIT_IDX), name="T1 Wait")

param_sched += templates.measure(QUBIT_IDX, ro_amp=ro_amp, ro_dur=ro_dur)


# In[ ]:


durations = np.arange(4, 65000, 412)
print("That will be:", durations.shape[0], "schedules")


# In[ ]:


get_ipython().run_line_magic("matplotlib", "inline")
sweep = [param_sched.assign_parameters({t1_wait: d}, inplace=False) for d in durations]
print("Total schedule count in sweep:", len(sweep))


# In[ ]:


sweep[19].draw(style=IQXDebugging())


# In[ ]:


# compile metadata about the sweep
qobj_header = {
    "sweep": {
        "serial_order": ("durations",),
        "parameters": {
            "durations": {
                "long_name": "t1 wait duration",
                "unit": "ns",
                "slots": {QUBIT_IDX: durations},
            }
        },
    }
}
job = backend.run(sweep, qobj_header=qobj_header)


# In[ ]:


while job.status != "DONE":
    time.sleep(5)
sf = tqcsf.file.StorageFile(job.logfile, mode="r")
print("File location: ", pathlib.Path(gettempdir()) / sf.job_id)
ds = sf.as_xarray()
ds


# In[ ]:


data = plot_fit_decay(ds)
data[0]["ro_amp"] = ro_amp
data[0]["ro_dur"] = ro_dur * 1e-9
data[0]["stim_dur"] = stim_dur * 1e-9
data[0]["qubit"] = QUBIT
data[0]["res_fr"] = res_fr
data[0]["stim_fr"] = stim_fr
data[0]["stim_sigma"] = round(stim_dur / 5) * 1e-9
data[0]["stim_amp"] = stim_amp
rich.print(data)


# In[ ]:


job.store_data(data)
