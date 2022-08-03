# This code is part of Tergite
#
# (C) Copyright Andreas Bengtsson, Miroslav Dobsicek 2020, 2021
# (C) Copyright Axel Andersson 2022
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
from .backend import Backend
from datetime import datetime
from qiskit.transpiler import Target, InstructionProperties
from qiskit.transpiler.coupling import CouplingMap
from qiskit.pulse import (
    #   Schedule,
    ScheduleBlock,
    #  InstructionScheduleMap
)
from qiskit.pulse.instructions import (
    Play,
    Delay,
    #   SetFrequency,
    #  SetPhase,
    #  ShiftFrequency,
    ShiftPhase,
    Acquire,
)

# from qiskit.pulse.channels import DriveChannel, MeasureChannel, AcquireChannel, ControlChannel
from qiskit.pulse.library import (
    Gaussian,
    Constant,
    #   cos,
    #  GaussianSquare
)

# from qiskit.circuit import QuantumCircuit
from qiskit.circuit import Delay as circuitDelay

from qiskit.circuit.measure import Measure
from qiskit.circuit.library.standard_gates import (
    # CXGate,
    # UGate,
    # ECRGate,
    RXGate,
    # SXGate,
    # XGate,
    RZGate,
)
from qiskit.circuit import Parameter  # , Instruction

# from itertools import permutations
from typing import (
    #   Optional,
    List,
    #   Union,
    #  Iterable,
    # Tuple
)
from numpy import sin
import pandas as pd

import functools

from qiskit.providers import BackendV2
from qiskit.providers.models import BackendConfiguration
from qiskit.providers import Options
from qiskit.pulse.channels import (
    DriveChannel,
    MeasureChannel,
    AcquireChannel,
    ControlChannel,
)
from qiskit.pulse.channels import MemorySlot
from qiskit.qobj import PulseQobj, QasmQobj

import qiskit.compiler as compiler

# typing
from qiskit.transpiler import Target
from qiskit.pulse import Schedule, ScheduleBlock
from qiskit.transpiler.coupling import CouplingMap
from numpy import inf as infinity
from abc import abstractmethod
from typing import (
    #   Optional,
    List,
    Union,
    Iterable,
    #   Tuple
)

# job transmission and result retrieval
# from qiskit.result import Result
import pathlib
import json
import requests
from tempfile import gettempdir
from uuid import uuid4
from .job import Job
from .json_encoder import IQXJsonEncoder
from .config import REST_API_MAP
from .serialization import iqx_rle

class PinguOpenPulse(Backend):
    def __init__(self, provider, base_url):
        super().__init__(
            provider=provider,
            base_url=base_url,
            name="PinguOpenPulse",
            description="OpenPulse compatible backend for Chalmers quantum computer Pingu B",
            online_date=datetime.now(),
            backend_version="0.5.4",  # QBLOX firmware driver version
        )
        self._dt = 1e-9
        self.open_pulse = True

    @functools.cached_property
    def calibration_table(self: object):
        µs = 1e-6
        ns = 1e-9
        MHz = 1e6
        GHz = 1e9
        mV = 1e-3

        # This should be returned from a database, but right now this suffices
        # all values should be in SI units
        df = pd.DataFrame()
        df["qubit"] = [0, 1]
        df.set_index("qubit")

        df["rabi_amp_gauss"] = [130 * mV] * 2
        df["rabi_dur_gauss"] = [100 * ns] * 2

        df["readout_amp_square"] = [14 * mV] * 2
        df["readout_dur_square"] = [3.5 * µs] * 2
        df["readout_integration_time"] = [3.0 * µs] * 2
        df["readout_tof"] = [300 * ns] * 2
        return df

    def __getitem__(self: object, args: tuple):
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
                        duration=round(stim_pulse_width / self._dt),
                        amp=sin(θ / 2) * ampl_qubit,
                        sigma=stim_pulse_width / (5 * self._dt),
                    ),
                    self.drive_channel(qubit),
                )

        elif gate_name == "rz":
            λ = get_param("lambda")
            for qubit in qubits:
                sched += ShiftPhase(λ, self.drive_channel(qubit))

        elif gate_name == "measure":
            for qubit in qubits:

                sched += Play(
                    Constant(
                        amp=self.calibration_table["readout_amp_square"][qubit],
                        duration=round(
                            self.calibration_table["readout_dur_square"][qubit]
                            / self._dt
                        ),
                    ),
                    self.measure_channel(qubit),
                )

                sched += Delay(
                    duration=round(
                        self.calibration_table["readout_tof"][qubit] / self._dt
                    ),
                    channel=self.acquire_channel(qubit),
                )

                sched += Acquire(
                    duration=round(
                        self.calibration_table["readout_integration_time"][qubit]
                        / self._dt
                    ),
                    channel=self.acquire_channel(qubit),
                    mem_slot=self.memory_slot(qubit),  # FIXME: deranged c-map is broken
                )

        elif gate_name == "delay":
            τ = get_param("tau")
            for qubit in qubits:
                sched += Delay(duration=τ, channel=self.drive_channel(qubit))

        else:
            raise NotImplementedError(
                f"Calibration for gate {gate_name} has not yet been added to {self.name}."
            )

        return sched

    @functools.cached_property
    def target(self) -> Target:

        gmap = Target(num_qubits=self.coupling_map.size(), dt=self._dt)

        θ = Parameter("theta")  # rotation around x axis
        φ = Parameter("phi")  # rotation around y axis
        λ = Parameter("lambda")  # rotation around z axis
        τ = Parameter("tau")  # duration

        rx_props = {
            (0,): InstructionProperties(error=0.0, calibration=self["rx", (0,), θ]),
            (1,): InstructionProperties(error=0.0, calibration=self["rx", (1,), θ]),
        }
        gmap.add_instruction(RXGate(θ), rx_props)

        rz_props = {
            (0,): InstructionProperties(error=0.0, calibration=self["rz", (0,), λ]),
            (1,): InstructionProperties(error=0.0, calibration=self["rz", (1,), λ]),
        }
        gmap.add_instruction(RZGate(λ), rz_props)

        delay_props = {
            (0,): InstructionProperties(error=0.0, calibration=self["delay", (0,), τ]),
            (1,): InstructionProperties(error=0.0, calibration=self["delay", (1,), τ]),
        }
        gmap.add_instruction(circuitDelay(τ, unit="dt"), delay_props)

        measure_props = {
            (0, 1): InstructionProperties(
                error=0.0, calibration=self["measure", (0, 1)]
            ),
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
        return [[i for i in range(self.num_qubits)]]

    @property
    def coupling_map(self) -> CouplingMap:
        cl = [[0, 1], [1, 0]]
        return CouplingMap(couplinglist=cl)
    
    def run(self, circuits: Union[object, List[object]], /, **kwargs) -> Job:
        # --------- Register job
        JOBS_URL = self.base_url + REST_API_MAP["jobs"]
        job_registration = requests.post(JOBS_URL).json()
        job_id = job_registration["job_id"]
        job_upload_url = job_registration["upload_url"]

        # --------- Convert any circuits to pulse schedules
        if not isinstance(circuits, list):
            circuits = [circuits]

        schedules = list()
        for circ in circuits:
            if isinstance(circ, Schedule) or isinstance(circ, ScheduleBlock):
                schedules.append(circ)
            else:
                schedules.append(
                    compiler.schedule(
                        compiler.transpile(circ, backend=self), backend=self
                    )
                )

        # --------- Try to make a nice human readable tag (for all experiments)
        qobj_header = (
            dict() if "qobj_header" not in kwargs else kwargs.pop("qobj_header")
        )
        if "tag" not in qobj_header:
            qobj_header["tag"] = (
                circuits[0].name if type(circuits) == list else circuits.name
            )
            if type(circuits) == list:
                for circ in circuits:
                    if circ.name != qobj_header["tag"]:
                        qobj_header["tag"] = ""
                        break
            qobj_header["tag"] = qobj_header["tag"].replace(" ", "_")

        qobj_header["dt"] = self.dt  # for some reason this is not in the config
        qobj_header["dtm"] = self.dtm  # for some reason this is not in the config

        # --------- Assemble the PulseQobj
        qobj = compiler.assemble(
            experiments=schedules,
            backend=self,
            shots=self.options.shots,
            meas_map=self.meas_map,
            qubit_lo_range=[[0, 10e9]] * self.num_qubits,
            meas_lo_range=[[0, 10e9]] * self.num_qubits,
            meas_level=1 if "meas_level" not in kwargs else kwargs.pop("meas_level"),
            meas_return="avg"
            if "meas_return" not in kwargs
            else kwargs.pop("meas_return"),
            qubit_lo_freq=self.qubit_lo_freq,  # qubit frequencies (base + if)
            meas_lo_freq=self.meas_lo_freq,  # resonator frequencies (base + if)
            qobj_header=qobj_header,
            parametric_pulses=[
                "constant",
                "zero",
                "square",
                "sawtooth",
                "triangle",
                "cos",
                "sin",
                "gaussian",
                "gaussian_deriv",
                "sech",
                "sech_deriv",
                "gaussian_square",
                "drag",
            ],
            **kwargs,
        )

        qobj = PulseQobj.to_dict(qobj)

        # --------- RLE pulse library (for compression)
        for pulse in qobj["config"]["pulse_library"]:
            pulse["samples"] = iqx_rle(pulse["samples"])

        # --------- Transmit job
        job_entry = {
            "job_id": job_id,
            "type": "script",
            "name": "pulse_schedule",
            "params": {"qobj": qobj},
        }

        # create a temporary file for transmission
        # job_file = pathlib.Path("/tmp") / str(uuid4())
        job_file = pathlib.Path(gettempdir()) / str(uuid4())
        with job_file.open("w") as dest:
            json.dump(job_entry, dest, cls=IQXJsonEncoder, indent="\t")

        with job_file.open("r") as src:
            files = {"upload_file": src}
            response = requests.post(job_upload_url, files=files)

            if response:
                print("Tergite: Job has been successfully submitted")

        # delete temporary transmission file
        job_file.unlink()

        job = Job(backend=self, job_id=job_id, qobj=qobj)
        return job


# ------------------------------------------------------------------------------------------------------

class PinguOpenQASM(Backend):
    def __init__(self, provider, base_url):
        super().__init__(
            provider=provider,
            base_url=base_url,
            name="PinguOpenQASM",
            description="OpenQASM compatible backend for Chalmers quantum computer Pingu B",
            online_date=datetime.now(),
            backend_version="0.0.0",  # ? so many versions of everything
        )
        self._dt = 1e-9
        self.open_pulse = False

    @functools.cached_property
    def calibration_table(self: object):
        µs = 1e-6
        ns = 1e-9
        MHz = 1e6
        GHz = 1e9
        mV = 1e-3

        # This should be returned from a database, but right now this suffices
        # all values should be in SI units
        df = pd.DataFrame()
        df["qubit"] = [0, 1]
        df.set_index("qubit")

        df["rabi_amp_gauss"] = [130 * mV] * 2
        df["rabi_dur_gauss"] = [100 * ns] * 2

        df["readout_amp_square"] = [14 * mV] * 2
        df["readout_dur_square"] = [3.5 * µs] * 2
        df["readout_integration_time"] = [3.0 * µs] * 2
        df["readout_tof"] = [300 * ns] * 2
        return df

    def __getitem__(self: object, args: tuple):
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
                        duration=round(stim_pulse_width / self._dt),
                        amp=sin(θ / 2) * ampl_qubit,
                        sigma=stim_pulse_width / (5 * self._dt),
                    ),
                    self.drive_channel(qubit),
                )

        elif gate_name == "rz":
            λ = get_param("lambda")
            for qubit in qubits:
                sched += ShiftPhase(λ, self.drive_channel(qubit))

        elif gate_name == "measure":
            for qubit in qubits:

                sched += Play(
                    Constant(
                        amp=self.calibration_table["readout_amp_square"][qubit],
                        duration=round(
                            self.calibration_table["readout_dur_square"][qubit]
                            / self._dt
                        ),
                    ),
                    self.measure_channel(qubit),
                )

                sched += Delay(
                    duration=round(
                        self.calibration_table["readout_tof"][qubit] / self._dt
                    ),
                    channel=self.acquire_channel(qubit),
                )

                sched += Acquire(
                    duration=round(
                        self.calibration_table["readout_integration_time"][qubit]
                        / self._dt
                    ),
                    channel=self.acquire_channel(qubit),
                    mem_slot=self.memory_slot(qubit),  # FIXME: deranged c-map is broken
                )

        elif gate_name == "delay":
            τ = get_param("tau")
            for qubit in qubits:
                sched += Delay(duration=τ, channel=self.drive_channel(qubit))

        else:
            raise NotImplementedError(
                f"Calibration for gate {gate_name} has not yet been added to {self.name}."
            )

        return sched

    @functools.cached_property
    def target(self) -> Target:

        gmap = Target(num_qubits=self.coupling_map.size(), dt=self._dt)

        θ = Parameter("theta")  # rotation around x axis
        φ = Parameter("phi")  # rotation around y axis
        λ = Parameter("lambda")  # rotation around z axis
        τ = Parameter("tau")  # duration

        rx_props = {
            (0,): InstructionProperties(error=0.0, calibration=self["rx", (0,), θ]),
            (1,): InstructionProperties(error=0.0, calibration=self["rx", (1,), θ]),
        }
        gmap.add_instruction(RXGate(θ), rx_props)

        rz_props = {
            (0,): InstructionProperties(error=0.0, calibration=self["rz", (0,), λ]),
            (1,): InstructionProperties(error=0.0, calibration=self["rz", (1,), λ]),
        }
        gmap.add_instruction(RZGate(λ), rz_props)

        delay_props = {
            (0,): InstructionProperties(error=0.0, calibration=self["delay", (0,), τ]),
            (1,): InstructionProperties(error=0.0, calibration=self["delay", (1,), τ]),
        }
        gmap.add_instruction(circuitDelay(τ, unit="dt"), delay_props)

        measure_props = {
            (0, 1): InstructionProperties(
                error=0.0, calibration=self["measure", (0, 1)]
            ),
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
        return [[i for i in range(self.num_qubits)]]

    @property
    def coupling_map(self) -> CouplingMap:
        cl = [[0, 1], [1, 0]]
        return CouplingMap(couplinglist=cl)
    
    def run(self, circuits: Union[object, List[object]], /, **kwargs) -> Job:
        # --------- Register job
        JOBS_URL = self.base_url + REST_API_MAP["jobs"]
        job_registration = requests.post(JOBS_URL).json()
        job_id = job_registration["job_id"]
        job_upload_url = job_registration["upload_url"]

        # --------- Convert any circuits to pulse schedules
        if not isinstance(circuits, list):
            circuits = [circuits]

        transpiled_circuits = list()
        for circ in circuits:
            transpiled_circuits.append(compiler.transpile(circ, backend=self))

        # --------- Try to make a nice human readable tag (for all experiments)
        qobj_header = (
            dict() if "qobj_header" not in kwargs else kwargs.pop("qobj_header")
        )
        if "tag" not in qobj_header:
            qobj_header["tag"] = (
                circuits[0].name if type(circuits) == list else circuits.name
            )
            if type(circuits) == list:
                for circ in circuits:
                    if circ.name != qobj_header["tag"]:
                        qobj_header["tag"] = ""
                        break
            qobj_header["tag"] = qobj_header["tag"].replace(" ", "_")

        qobj_header["dt"] = self.dt  # for some reason this is not in the config
        qobj_header["dtm"] = self.dtm  # for some reason this is not in the config

        # --------- Assemble the QasmQobj
        qobj = compiler.assemble(
            experiments=transpiled_circuits,
            backend=self,
            shots=self.options.shots,
            meas_map=self.meas_map,
            qubit_lo_range=[[0, 10e9]] * self.num_qubits,
            meas_lo_range=[[0, 10e9]] * self.num_qubits,
            meas_level=1 if "meas_level" not in kwargs else kwargs.pop("meas_level"),
            meas_return="avg"
            if "meas_return" not in kwargs
            else kwargs.pop("meas_return"),
            qubit_lo_freq=self.qubit_lo_freq,  # qubit frequencies (base + if)
            meas_lo_freq=self.meas_lo_freq,  # resonator frequencies (base + if)
            qobj_header=qobj_header,
            **kwargs,
        )

        qobj = QasmQobj.to_dict(qobj)

        # --------- Transmit job
        job_entry = {
            "job_id": job_id,
            "type": "script",
            "name": "qasm_dummy_job",
            "params": {"qobj": qobj},
        }

        # create a temporary file for transmission
        # job_file = pathlib.Path("/tmp") / str(uuid4())
        job_file = pathlib.Path(gettempdir()) / str(uuid4())
        with job_file.open("w") as dest:
            json.dump(job_entry, dest, cls=IQXJsonEncoder, indent="\t")
#             json.dump(job_entry, dest, indent="\t")

        with job_file.open("r") as src:
            files = {"upload_file": src}
            response = requests.post(job_upload_url, files=files)

            if response:
                print("Tergite: Job has been successfully submitted")

        # delete temporary transmission file
        job_file.unlink()

        job = Job(backend=self, job_id=job_id, qobj=qobj)
        return job


# ------------------------------------------------------------------------------------------------------

# these are the backends which Tergite supports
hardcoded_backends = [PinguOpenQASM, PinguOpenPulse]
