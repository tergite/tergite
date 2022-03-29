from .backend import Backend
from datetime import datetime
from qiskit.transpiler import Target, InstructionProperties
from qiskit.transpiler.coupling import CouplingMap
from qiskit.pulse import Schedule, ScheduleBlock, InstructionScheduleMap
from qiskit.pulse.instructions import Play, Delay, SetFrequency, SetPhase, ShiftFrequency, ShiftPhase, Acquire
#from qiskit.pulse.channels import DriveChannel, MeasureChannel, AcquireChannel, ControlChannel
from qiskit.pulse.library import Gaussian, Constant, cos, GaussianSquare

#from qiskit.circuit import QuantumCircuit
from qiskit.circuit import Delay as circuitDelay

from qiskit.circuit.measure import Measure
from qiskit.circuit.library.standard_gates import (
    CXGate,
    UGate,
    ECRGate,
    RXGate,
    SXGate,
    XGate,
    RZGate,
)
from qiskit.circuit import Parameter, Instruction
from itertools import permutations
from typing import Optional, List, Union, Iterable, Tuple
from numpy import sin
import pandas as pd

import functools

class Pingu(Backend):
    def __init__(self, provider, base_url):
        super().__init__(
            provider        = provider,
            base_url        = base_url,
            name            = "Pingu",
            description     = "This is only Pingu B (TODO: add Pingu A)",
            online_date     = datetime.now(),
            backend_version = "0.5.4", # QBLOX firmware driver version
        )
        self._dt = 1e-9
        
    @functools.cached_property
    def calibration_table(self: object):
        # This should be returned from a database, but right now this suffices
        # all values should be in SI units
        df = pd.DataFrame()
        df["qubit"] = [0, 1]
        df.set_index("qubit")
        
        df["rabi_amp_gauss"]           = [0.1    , 0.0660]
        df["rabi_dur_gauss"]           = [58e-9  , 200e-9]
        
        df["readout_amp_square"]       = [14e-3  , 14e-3 ]
        df["readout_dur_square"]       = [3.5e-6 , 3.5e-6]
        df["readout_integration_time"] = [3e-6   , 3e-6  ]
        df["readout_tof"]              = [300e-9 , 300e-9]
        return df
        
    def __getitem__(
        self: object,
        args: tuple
    ):        
        gate_name = args[0]
        qubits = args[1]
        params = args[2:]
        get_param = lambda name: next(filter(lambda param: param.name == name, params))
        
        sched = ScheduleBlock(gate_name)
            
        if gate_name == "rx":
            θ = get_param("theta")
            for qubit in qubits:
                stim_pulse_width = self.calibration_table["rabi_dur_gauss"][qubit]
                ampl_qubit = self.calibration_table["rabi_amp_gauss"][qubit]
                sched += Play(
                    Gaussian(
                        duration = round(stim_pulse_width/self._dt),
                        amp = sin(θ/2) * ampl_qubit,
                        sigma = stim_pulse_width/5e-9
                    ),
                    self.drive_channel(qubit)
                )
        
        elif gate_name == "rz":
            λ = get_param("lambda")
            for qubit in qubits:
                sched += ShiftPhase(λ, self.drive_channel(qubit))
            
        elif gate_name == "measure":
            for qubit in qubits:

                sched += Play(Constant(
                    amp = self.calibration_table["readout_amp_square"][qubit],
                    duration = round(
                        self.calibration_table["readout_dur_square"][qubit] / self._dt
                    )
                ), self.measure_channel(qubit))
                
                sched += Delay(
                    duration = round(
                        self.calibration_table["readout_tof"][qubit] / self._dt
                    ),
                    channel = self.acquire_channel(qubit)
                )
                
                sched += Acquire(
                    duration = round(
                        self.calibration_table["readout_integration_time"][qubit] / self._dt
                    ),
                    channel = self.acquire_channel(qubit),
                    mem_slot = self.memory_slot(qubit) # FIXME: deranged c-map is broken
                )
        
        elif gate_name == "delay":
            τ = get_param("tau")
            for qubit in qubits:
                sched += Delay(
                    duration = τ,
                    channel = self.drive_channel(qubit)
                )
        
        else:
            raise NotImplementedError(f"Calibration for gate {gate_name} has not yet been added to {self.name}.")

        return sched
        
    @functools.cached_property
    def target(self) -> Target:

        gmap = Target(num_qubits = self.coupling_map.size(), dt = self._dt)
        
        θ = Parameter("theta")  # rotation around x axis
        φ = Parameter("phi")    # rotation around y axis
        λ = Parameter("lambda") # rotation around z axis
        τ = Parameter("tau")    # duration
        
        rx_props = {
            (0,): InstructionProperties(error=0.0, calibration = self["rx", (0,), θ]),
            (1,): InstructionProperties(error=0.0, calibration = self["rx", (1,), θ]),
        }
        gmap.add_instruction(RXGate(θ), rx_props)
        
        rz_props = {
            (0,): InstructionProperties(error=0.0, calibration = self["rz", (0,), λ]),
            (1,): InstructionProperties(error=0.0, calibration = self["rz", (1,), λ]),
        }
        gmap.add_instruction(RZGate(λ), rz_props)
        
        delay_props = {
            (0,): InstructionProperties(error=0.0, calibration = self["delay", (0,), τ]),
            (1,): InstructionProperties(error=0.0, calibration = self["delay", (1,), τ]),
        }
        gmap.add_instruction(circuitDelay(τ, unit = "dt"), delay_props)
        
        measure_props = {
            (0,1): InstructionProperties(error=0.0, calibration = self["measure", (0,1)]),
        }
        gmap.add_instruction(Measure(), measure_props)
        
        return gmap
    
    @property
    def qubit_lo_freq(self) -> List[float]:
        return [4.1395428e9, 4.773580e9 + 1.3e6]
    
    @property
    def meas_lo_freq(self) -> List[float]:
        return [6.21445e9, 6.379170e9]
    
    @property
    def meas_map(self) -> List[List[int]]:
        return [[i for i in range( self.num_qubits )]]
    
    @property
    def coupling_map(self) -> CouplingMap:
        cl = [
            [0,1], [1,0]
        ]
        return CouplingMap(couplinglist = cl)

#------------------------------------------------------------------------------------------------------

hardcoded_backends = [ Pingu ]