import pprint
import pathlib
from qiskit.providers.tergite import Tergite

chalmers = Tergite.get_provider()
backend = chalmers.get_backend("OpenQASM")
#print(backend)








'''
two_tone[q].frequency = qubit:frequency
**** pulse type needs to be specified
duration=round(rabi[q].gauss_dur / backend.dt), = qubit_drive_xy:pi_pulse_duration
amp=rx_theta / (2 * np.pi * rabi[q].frequency), = qubit_drive_xy:qubit_pulse_amplitude
sigma=round(rabi[q].gauss_sig / backend.dt),    = 

rspec[q].frequency = readout:frequency
amp=rspec[q].square_amp, = readout:pulse_amp
**** pulse type needs to be specified
duration=round(rspec[q].square_dur / backend.dt), readout:pulse_duration
duration=round(rspec[q].integration_time / backend.dt),=  readout:acq_integration_time


r0 = Transmon["q0"]["readout_resonator"]
pprint.pprint(r0.get("frequency"))

'''