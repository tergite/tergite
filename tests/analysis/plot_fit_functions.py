import matplotlib.pyplot as plt
import numpy as np
from quantify_core.analysis import fitting_models as fm
from .spectroscopy_analysis import LorentzianModel
from quantify_core.visualization import mpl_plotting as qpl

def format_fit_data(model, x, s21, ds, fit_result, /, **kwargs):
    abs_s21 = np.abs(s21)
    return {
        "job_id" : ds.attrs["job_id"],
        "tuid" : ds.attrs["tuid"],
        "model": model.name,
        "Average |s21|" : {"value": float(abs_s21.mean()) },
        "Minimum |s21|" : {"value": float(abs_s21.min()) },
        "Maximum |s21|" : {"value": float(abs_s21.max()) },
        "Arg Minimum |s21|" : {"value": float(x[np.argmin(abs_s21)]) },
        "Arg Maximum |s21|" : {"value": float(x[np.argmax(abs_s21)]) },
    } | {
        p : {
            "value" : v.value,
            "stderr" : v.stderr
        } for p, v in fit_result.params.items()
    } | kwargs

def plot_fit_resonator(ds):
    
    fig, axs = plt.subplots(len(ds), 1)
    if len(ds) == 1:
        axs = [axs]

    f = list()
        
    for i,var in enumerate(ds):
        # plot data
        np.abs(ds[var]).plot(ax = axs[i])
        axs[i].set_title(var)

        # retrieve raw data for model fitting
        x = ds.coords[ds.variables[var].attrs["coords"][0]].data
        s21 = ds[var].data

        # fit resonator model against the data
        model = fm.ResonatorModel()
        guess = model.guess(s21, f = x)
        fit_result = model.fit(s21, params = guess, f = x)
        
        axs[i].axvline(fit_result.params["fr"].value, ls="--", color = "black", alpha = 0.2)
        axs[i].axvline(x[np.argmin(np.abs(s21))], ls="-", color = "red")

        # plot model fit
        qpl.plot_fit(
            ax=axs[i],
            fit_res=fit_result,
            plot_init=True,
            range_casting="abs",
        )
        f.append(format_fit_data(model, x, s21, ds, fit_result, code = "RESONATOR_SPEC"))
    
    return f

def plot_fit_lorentz(ds):
    fig, axs = plt.subplots(len(ds), 1)
    if len(ds) == 1:
        axs = [axs]
    
    f = list()
    for i,var in enumerate(ds):
        # plot data
        np.abs(ds[var]).plot(ax = axs[i])
        axs[i].set_title(var)

        # retrieve raw data for model fitting
        x = ds.coords[ds.variables[var].attrs["coords"][0]].data
        s21 = ds[var].data

        # fit resonator model against the data
        model = LorentzianModel()
        guess = model.guess(np.abs(s21), x = x)
        fit_result = model.fit(np.abs(s21), params = guess, x = x)

        model_y = fit_result.eval(x = x)
        axs[i].plot(x, model_y,'r-')
        print()
        print(var,":", fit_result.params["x0"].value/1e9, "GHz")
        f.append(format_fit_data(model, x, s21, ds, fit_result, code = "QUBIT_SPEC"))
        
    return f

def plot_fit_cosine(ds):
    fig, axs = plt.subplots(len(ds), 1)
    if len(ds) == 1:
        axs = [axs]
    
    f = list()
    for i,var in enumerate(ds):
        # plot data
        np.abs(ds[var]).plot(ax = axs[i])
        axs[i].set_title(var)

        # retrieve raw data for model fitting
        x = ds.coords[ds.variables[var].attrs["coords"][0]].data
        s21 = ds[var].data

        # fit resonator model against the data
        model = fm.CosineModel()
        guess = model.guess(np.abs(s21), x = x)
        fit_result = model.fit(np.abs(s21), params = guess, x = x)

        model_y = fit_result.eval(x = x)
        axs[i].plot(x, model_y,'r-')
        
        idxs = np.argmax(model_y)
        v = x[idxs]
        axs[i].axvline(v, color = "red")
        print(var,":", v*1000, "mV")
        f.append(format_fit_data(model, x, s21, ds, fit_result, code = "RABI_OSC", ket1_amp = v))
        
    return f

def plot_fit_decay(ds):
    fig, axs = plt.subplots(len(ds), 1)
    if len(ds) == 1:
        axs = [axs]
    
    f = list()
    for i,var in enumerate(ds):
        # plot data
        np.abs(ds[var]).plot(ax = axs[i])
        axs[i].set_title(var)

        # retrieve raw data for model fitting
        x = ds.coords[ds.variables[var].attrs["coords"][0]].data
        s21 = ds[var].data

        # fit resonator model against the data
        model = fm.ExpDecayModel()
        guess = model.guess(np.abs(s21), delay = x)
        fit_result = model.fit(np.abs(s21), params = guess, t = x)

        model_y = fit_result.eval(delay = x)
        axs[i].plot(x, model_y,'r-')
        print(var,":", fit_result.params["tau"].value, "ns")
        f.append(format_fit_data(model, x, s21, ds, fit_result, code = "T1_DECOHERENCE"))
        
    return f