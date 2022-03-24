from .backend import Backend
from datetime import datetime
from qiskit.transpiler import Target
from qiskit.transpiler.coupling import CouplingMap
from qiskit.pulse import Schedule, ScheduleBlock, InstructionScheduleMap
from qiskit.pulse.instructions import Play, Delay, SetFrequency, SetPhase, ShiftFrequency, ShiftPhase, Acquire
#from qiskit.pulse.channels import DriveChannel, MeasureChannel, AcquireChannel, ControlChannel
from qiskit.pulse.library import Gaussian, Constant, cos, GaussianSquare
from qiskit.circuit import Parameter, Instruction
from itertools import permutations
from typing import Optional, List, Union, Iterable, Tuple

import functools

class Thor(Backend):
    def __init__(self, provider, base_url):
        super().__init__(
            provider        = provider,
            base_url        = base_url,
            name            = "Thor",
            description     = "Connected to the Chalmers intranet.",
            online_date     = datetime.now(),
            backend_version = "0.5.4", # QBLOX firmware driver version
        )
    
    @property
    def target(self) -> Target:
        gmap = Target(num_qubits = self.coupling_map.size(), dt = 1e-9)
        
        # TODO: gate calibrations
        
        return gmap 
    
    @property
    def qubit_lo_freq(self) -> List[float]:
        return [f*1e9 for f in (4.1,4.2,4.3,4.4,4.5)]
    
    @property
    def meas_lo_freq(self) -> List[float]:
        return [f*1e9 for f in (6.1,6.2,6.3,6.4,6.5)]
    
    @property
    def meas_map(self) -> List[List[int]]:
        return [[i for i in range( self.num_qubits )]]
    
    @property
    def coupling_map(self) -> CouplingMap:
        cl = [
            [0,1], [1,0],
            [0,2], [2,0],
            [0,3], [3,0],
            [0,4], [4,0]
        ]
        return CouplingMap(couplinglist = cl)

#------------------------------------------------------------------------------------------------------

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
        
    @functools.cached_property
    def target(self) -> Target:
        num_qubits = self.coupling_map.size()
        gmap = Target(num_qubits = num_qubits, dt = 1e-9)
        ismap = InstructionScheduleMap()
        """
            How to add a new gate definition:
                - Experimentally find numerical parameters for the pulse.
                - Create a minimal ScheduleBlock which implements the instruction on this backend.
                - Use InstructionScheduleMap.add to add that ScheduleBlock to the 'ismap'.
                - Create an Instruction object which lets the compiler know how to use it.
        """
        params = {
            k : Parameter(k) for k in (
                "qubit",
                "x_dur",
                "x_amp",
                "x_sig",
            )
        }
        gates = dict()
        
        # temp solution to assign parameters
        calibrations = {
            0: dict(
                qubit = 0,
                x_dur =0, #FIXME
                x_amp =0, #FIXME
                x_sig =1, #FIXME
            ),
            1 : dict(
                qubit = 1,
                x_dur = 120,
                x_amp = 0.0904,
                x_sig = 40,
            )
        }
        
        gate_defs = list()
        
        # ================== DEFINE OPERATIONS ================= #
        # ------------------------- x -------------------------- #
        x_gate = ScheduleBlock(name = "x")
        x_gate += Play(
            Gaussian(
                params["x_dur"],
                amp = params["x_amp"],
                sigma = params["x_sig"]
            ),
            self.drive_channel(params["qubit"]),
            name = "x gate"
        )
        
        for qubit_idx in range(num_qubits):
            ismap.add("x", qubit_idx, x_gate.assign_parameters({
                    params[k] : calibrations[qubit_idx][k] for k in params
                },
                inplace = False
            ))
            
        gates["x"] = Instruction(
            name = "x",
            num_qubits = num_qubits,
            num_clbits = 0,
            params = [],
            duration = 200,
            unit = "dt",
            label = "x gate"
        )
        # ------------------------ /x -------------------------- #
        
        # ================= /DEFINED OPERATIONS ================ #
        gmap.update_from_instruction_schedule_map(ismap, inst_name_map = gates)
        return gmap
    
    @property
    def qubit_lo_freq(self) -> List[float]:
        return [f*1e9 for f in (4.1395428, 4.773580)]
    
    @property
    def meas_lo_freq(self) -> List[float]:
        return [f*1e9 for f in (6.21445, 6.379170)]
    
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

class Test(Backend):
    def __init__(self, provider, base_url):
        super().__init__(
            provider        = provider,
            base_url        = base_url,
            name            = "Test",
            description     = "Test object for debugging. Five fake qubits.",
            online_date     = datetime.now(),
            backend_version = "0.0.0"
        )
    
    @property
    def target(self) -> Target:
        gmap = Target(num_qubits = self.coupling_map.size(), dt = 1e-9)
        
        # TODO: gate calibrations
        
        return gmap 
    
    @property
    def qubit_lo_freq(self) -> List[float]:
        return [f for f in range(self.num_qubits)]
    
    @property
    def meas_lo_freq(self) -> List[float]:
        return [(f+1)*10 for f in range(self.num_qubits)]
    
    @property
    def meas_map(self) -> List[List[int]]:
        return [[i for i in range( self.num_qubits )]]
    
    @property
    def coupling_map(self) -> CouplingMap:
        cl = list(permutations([i for i in range(5)], 2))
        return CouplingMap(couplinglist = cl)

#------------------------------------------------------------------------------------------------------

hardcoded_backends = [ Thor, Pingu, Test ]