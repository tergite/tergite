import numpy as np
from quantify_core.analysis import base_analysis as ba
from quantify_core.visualization import mpl_plotting as qpl
import matplotlib.pyplot as plt
import lmfit
from quantify_core.visualization.SI_utilities import format_value_string


class QubitSpectroscopyAnalysis(ba.BaseAnalysis):
    """
    Fits a Lorentzian function to qubit spectroscopy data and finds the
    0-1 transistion frequency of the qubit
    """

    def process_data(self):
        """
        Populates the :code:`.dataset_processed`.
        """
        # y0 = amplitude, no check for the amplitude unit as the name/label is
        # often different.

        self.dataset_processed["Magnitude"] = self.dataset.y0[:]
        self.dataset_processed.Magnitude.attrs["name"] = "Magnitude"
        self.dataset_processed.Magnitude.attrs["units"] = self.dataset.y0.units
        self.dataset_processed.Magnitude.attrs["long_name"] = "Magnitude, $|S_{21}|$"

        self.dataset_processed["x0"] = self.dataset.x0[:]
        self.dataset_processed = self.dataset_processed.set_coords("x0")
        # replace the default dim_0 with x0
        self.dataset_processed = self.dataset_processed.swap_dims({"dim_0": "x0"})

    def run_fitting(self):
        """
        Fits a Lorentzian function to the data.
        """
        mod = LorentzianModel()

        magnitude = np.array(self.dataset_processed["Magnitude"])
        frequency = np.array(self.dataset_processed.x0)
        guess = mod.guess(magnitude, x=frequency)
        fit_result = mod.fit(magnitude, params=guess, x=frequency)

        self.fit_results.update({"Lorentzian_peak": fit_result})

    def analyze_fit_results(self):
        """
        Checks fit success and populates :code:`.quantities_of_interest`.
        """
        fit_result = self.fit_results["Lorentzian_peak"]
        fit_warning = ba.wrap_text(ba.check_lmfit(fit_result))

        # If there is a problem with the fit, display an error message in the text box.
        # Otherwise, display the parameters as normal.
        if fit_warning is None:
            self.quantities_of_interest["fit_success"] = True

            text_msg = "Summary\n"
            text_msg += format_value_string(
                "Frequency 0-1",
                fit_result.params["x0"],
                unit="Hz",
                end_char="\n",
            )
            text_msg += format_value_string(
                "Peak width",
                fit_result.params["width"],
                unit="Hz",
                end_char="\n",
            )
        else:
            text_msg = ba.wrap_text(fit_warning)
            self.quantities_of_interest["fit_success"] = False

            self.quantities_of_interest["frequency_01"] = ba.lmfit_par_to_ufloat(
                fit_result.params["x0"]
            )
        self.quantities_of_interest["fit_msg"] = text_msg

    def create_figures(self):
        """Creates qubit spectroscopy figure"""

        fig_id = "qubit_spectroscopy"
        fig, ax = plt.subplots(figsize = (9,4.5))
        self.figs_mpl[fig_id] = fig
        self.axs_mpl[fig_id] = ax

        # Add a textbox with the fit_message
        #qpl.plot_textbox(ax, self.quantities_of_interest["fit_msg"])
        fig.text(
            .56, 0.8, # bottom left in ax coords
            self.quantities_of_interest["fit_msg"],
            transform=ax.transAxes,
        #     fontsize=14,
            verticalalignment='top',
            color = "black",
            bbox=dict(boxstyle='round', facecolor="white", edgecolor = "black", alpha=1.0)
        )

        self.dataset_processed.Magnitude.plot(ax=ax, marker=".", linestyle="")

        qpl.plot_fit(
            ax=ax,
            fit_res=self.fit_results["Lorentzian_peak"],
            plot_init=not self.quantities_of_interest["fit_success"],
            range_casting="real",
        )

        qpl.set_ylabel(ax, r"Output voltage", self.dataset_processed.Magnitude.units)
        qpl.set_xlabel(
            ax, self.dataset_processed.x0.long_name, self.dataset_processed.x0.units
        )

        qpl.set_suptitle_from_dataset(fig, self.dataset, "S21")
def lorentzian(
    x: float,
    x0: float,
    width: float,
    A: float,
    c: float,
) -> float:
    r"""
    A Lorentzian function.

    Parameters
    ----------
    x:
    independent variable
    x0:
    horizontal offset
    width:
    Lorenztian linewidth
    A:
    amplitude
    c:
    vertical offset

    Returns
    -------
    :
    Lorentzian function


    .. math::

    y = \frac{A*\mathrm{width}}{\pi(\mathrm{width}^2 + (x - x_0)^2)} + c

    """

    return A * width / (np.pi * ((x - x0) ** 2) + width ** 2) + c
class LorentzianModel(lmfit.model.Model):
    """
    Model for data which follows a Lorentzian function.
    """

        # pylint: disable=empty-docstring
        # pylint: disable=abstract-method
        # pylint: disable=too-few-public-methods

    def __init__(self, *args, **kwargs):
        # pass in the defining equation so the user doesn't have to later.

        super().__init__(lorentzian, *args, **kwargs)

        self.set_param_hint("x0", vary=True)
        self.set_param_hint("A", vary=True)
        self.set_param_hint("c", vary=True)
        self.set_param_hint("width", vary=True)

        # pylint: disable=missing-function-docstring
    def guess(self, data, **kws) -> lmfit.parameter.Parameters:
        x = kws.get("x", None)

        if x is None:
            return None

        # Guess that the resonance is where the function takes its maximal
        # value
        x0_guess = x[np.argmax(data)]
        self.set_param_hint("x0", value=x0_guess)

        # assume the user isn't trying to fit just a small part of a resonance curve.
        xmin = x.min()
        xmax = x.max()
        width_max = xmax - xmin

        delta_x = np.diff(x)  # assume f is sorted
        min_delta_x = delta_x[delta_x > 0].min()
        # assume data actually samples the resonance reasonably
        width_min = min_delta_x
        width_guess = np.sqrt(width_min * width_max)  # geometric mean, why not?
        self.set_param_hint("width", value=width_guess)

        # The guess for the vertical offset is the mean absolute value of the data
        c_guess = np.mean(data)
        self.set_param_hint("c", value=c_guess)

        # Calculate A_guess from difference between the peak and the backround level
        A_guess = np.pi * width_guess * (np.max(data) - c_guess)
        self.set_param_hint("A", value=A_guess)

        params = self.make_params()
        return lmfit.models.update_param_vals(params, self.prefix, **kws)
