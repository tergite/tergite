import numpy as np
from quantify_core.analysis import base_analysis as ba
from quantify_core.visualization import mpl_plotting as qpl
import matplotlib.pyplot as plt
import lmfit
from quantify_core.visualization.SI_utilities import format_value_string

def sinc_function( x: float, x0: float, width: float, A: float, c: float,) -> float:
    # return A * np.abs(np.sin(width*(x-x0))/(width*(x-x0))) + c + 1e-10
    return A * width / ( (x-x0)**2 + width**2 ) + c

class SincModel(lmfit.model.Model):
    def __init__(self, *args, **kwargs):
        # pass in the defining equation so the user doesn't have to later.

        super().__init__(sinc_function, *args, **kwargs)

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
        A_guess = (np.max(data) - c_guess)
        self.set_param_hint("A", value=A_guess)

        params = self.make_params()
        print( params)
        return lmfit.models.update_param_vals(params, self.prefix, **kws)

class QubitSpectroscopyAnalysis():
    def  __init__(self,qubit_dataset):
        self.dataset = qubit_dataset
        self.LO = 0

    def spec_fit(self):
        model = SincModel()
#         real = self.dataset.y0.values
#         imag = self.dataset.y1.values
#         self.magnitudes = np.sqrt(real**2 + imag**2)
        self.magnitudes = self.dataset.y0.values
        frequency = np.array(self.dataset.x0)
        self.fit_freqs = np.linspace( frequency[0], frequency[-1], 2000)

        guess = model.guess(self.magnitudes, x=frequency)
        fit_result = model.fit(self.magnitudes, params=guess, x=frequency)

        fit_y = model.eval(fit_result.params, **{model.independent_vars[0]: self.fit_freqs})
        self.dataset['fit_freqs'] = self.fit_freqs
        self.dataset['fit_y'] = ('fit_freqs',fit_y)
        return fit_result.params['x0'].value


    def plotter(self):
        plt.figure(figsize=(6,2.5))
        plt.plot( self.dataset['fit_freqs'].values +  self.LO, self.dataset['fit_y'].values,'r-',lw=3.0)
        print('self_LO',self.LO)
        plt.plot( self.dataset.x0 +  self.LO, self.magnitudes,'bo-',ms=3.0)
        plt.title('Qubit Spectroscopy')
        plt.xlabel('frequency (Hz)')
        plt.ylabel('|S21| (V)')
        plt.grid()
        plt.tight_layout()
        plt.show()
