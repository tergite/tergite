from .backend import Backend
from datetime import datetime
from qiskit.transpiler import Target
from qiskit.transpiler.coupling import CouplingMap
from itertools import permutations
from typing import Optional, List, Union, Iterable, Tuple

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
        
    @property
    def target(self) -> Target:
        gmap = Target(num_qubits = self.coupling_map.size(), dt = 1e-9)
        
        # TODO: gate calibrations
        
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