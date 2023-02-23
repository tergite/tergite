# This code is part of Tergite
#
# (C) Copyright Miroslav Dobsicek 2020, 2021
# (C) Copyright Axel Andersson 2022
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
import functools
from abc import abstractmethod

import qiskit.circuit as circuit
import qiskit.compiler as compiler
import qiskit.pulse as pulse
import requests
from numpy import inf as infinity
from qiskit.circuit import QuantumCircuit
from qiskit.providers.models import BackendConfiguration
from qiskit.pulse.channels import (
    AcquireChannel,
    ControlChannel,
    DriveChannel,
    MeasureChannel,
    MemorySlot,
)
from qiskit.qobj import PulseQobj, QasmQobj
from qiskit.transpiler import Target
from qiskit.transpiler.coupling import CouplingMap

from qiskit.providers import BackendV2, Options

from . import calibrations
from .config import REST_API_MAP
from .job import Job


class TergiteBackend(BackendV2):

    max_shots = infinity
    max_circuits = infinity

    @classmethod
    def _default_options(cls, /) -> Options:
        """This defines the default user configurable settings of this backend. See: help(backend.set_options)"""
        options = Options(shots=2000)
        options.set_validator("shots", (1, TergiteBackend.max_shots))
        return options

    def __init__(self, /, *, data: dict, provider: object, base_url: str):
        super().__init__(
            provider=provider,
            name=data["name"],
            backend_version=data["version"],
        )
        self.base_url = base_url
        self.data = data

    def __repr__(self: object) -> str:
        repr_list = [f"TergiteBackend object @ {hex(id(self))}:"]
        config = self.configuration().to_dict()
        config["characterized"] = self.data["characterized"]
        for attr, value in config.items():
            repr_list.append(f"  {attr}:\t{value}".expandtabs(30))
        return "\n".join(repr_list)

    def register_job(self: object) -> Job:
        """Registers a new job at the Tergite MSS."""
        jobs_url = self.base_url + REST_API_MAP["jobs"]
        response = requests.post(jobs_url)
        if response.ok:
            job_registration = response.json()
        else:
            raise RuntimeError(
                f"Unable to register job at the Tergite MSS, response: {response}"
            )
        job_id = job_registration["job_id"]
        job_upload_url = job_registration["upload_url"]
        return Job(backend=self, job_id=job_id, upload_url=job_upload_url)

    @abstractmethod
    def make_qobj(self: object, experiments: list, /, **kwargs) -> object:
        """Constructs a Qobj from a list of user OpenPulse schedules or OpenQASM circuits and
        returns a PulseQobj or a QasmQobj respectively (in dictionary format)."""
        ...

    def run(self, experiments, /, **kwargs) -> Job:
        job = self.register_job()
        qobj = self.make_qobj(experiments, **kwargs)
        response = job.submit(qobj)
        if response.ok:
            print("Tergite: Job has been successfully submitted")
            return job
        else:
            raise RuntimeError(
                f"Unable to transmit job to the Tergite BCC, response: {response}"
            )

    @property
    def meas_map(self: object) -> list:
        return self.data["meas_map"]

    @functools.cached_property
    def coupling_map(self: object) -> CouplingMap:
        # It is required that nodes are contiguously indexed starting at 0.
        # Missed nodes will be added as isolated nodes in the coupling map.
        #
        # Also for some reason the graph has to be connected in Qiskit? Not sure why that is..
        edges = sorted(
            sorted(self.data["coupling_map"], key=lambda i: i[1]), key=lambda i: i[0]
        )
        return CouplingMap(couplinglist=list(edges))


class OpenPulseBackend(TergiteBackend):

    open_pulse = True

    parametric_pulses = [
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
    ]

    def configuration(self: object) -> BackendConfiguration:
        return BackendConfiguration(
            backend_name=self.name,  # From BackendV2.
            backend_version=self.backend_version,  # From BackendV2.
            n_qubits=self.target.num_qubits,  # Number of qubits, obtained from self.target.
            basis_gates=[],  # Don't need.
            gates=[],  # Don't need.
            simulator=False,  # This is a real quantum computer.
            conditional=False,  # We cannot do conditional gate application yet.
            local=False,  # Jobs are sent over the internet.
            open_pulse=True,  # This backend converts all quantum experiment input to schedules.
            meas_levels=(0, 1, 2),  # 0: RAW, 1: INTEGRATED, 2: DISCRIMINATED
            memory=False,  # Unsure what this is for. (?)
            max_shots=TergiteBackend.max_shots,  # From TergiteBackend.
            coupling_map=self.coupling_map,  # From TergiteBackend.
            supported_instructions= self.target.instructions,  # Supported instructions, obtained from self.target.
            dt=self.dt,  # From self
            dtm=self.dtm,  # From self
            description=self.description,  # From BackendV2.
            parametric_pulses=OpenPulseBackend.parametric_pulses,  # From type of self
        )

    @property
    def dt(self: object) -> float:
        # hardware sample resolution for drive
        return self.data["dt"]

    @property
    def dtm(self: object) -> bool:
        # hardware sample resolution for readout
        return self.data["dtm"]

    @functools.cached_property
    def target(self: object) -> Target:
        print("target is created ... ...")
        gmap = Target(num_qubits=self.data["num_qubits"], dt=self.data["dt"])
        if self.data["characterized"]:
            calibrations.add_instructions(
                backend=self,
                qubits=tuple(q for q in range(self.data["num_qubits"])),
                target=gmap,
            )
        return gmap

    @functools.cached_property
    def calibration_tables(self: object) -> tuple:
        """Returns dataframes with empirical calibration values specific to this backend."""
        # cache and return dataframes to caller
        print("loading calibratoin tables ... ...")
        return calibrations.load_tables(backend=self)

    @property
    def qubit_lo_freq(self: object) -> list:
        # return list(map(float, self.data["qubit_lo_freq"]))
        return [0.0] * self.data["num_qubits"]

    @property
    def meas_lo_freq(self: object) -> list:
        # return list(map(float, self.data["meas_lo_freq"]))
        return [0.0] * self.data["num_resonators"]

    def drive_channel(self: object, qubit_idx: int) -> DriveChannel:
        return DriveChannel(qubit_idx)

    def measure_channel(self: object, qubit_idx: int) -> MeasureChannel:
        return MeasureChannel(qubit_idx)

    def acquire_channel(self: object, qubit_idx: int) -> AcquireChannel:
        return AcquireChannel(qubit_idx)

    def memory_slot(self: object, qubit_idx: int) -> MemorySlot:
        return MemorySlot(qubit_idx)

    def control_channel(self: object, qubits: list) -> list:
        if qubits not in self.coupling_map.get_edges():
            raise ValueError(f"Coupling {qubits} not in coupling map.")

        return list(map(ControlChannel, qubits))

    def make_qobj(self: object, experiments: object, /, **kwargs) -> PulseQobj:
        if type(experiments) is not list:
            experiments = [experiments]

        # convert all non-schedules to schedules
        experiments = [
            compiler.schedule(experiment, backend=self)
            if (type(experiment) is not pulse.ScheduleBlock)
            and (type(experiment) is not pulse.Schedule)
            else experiment  # already a schedule, so don't convert
            for experiment in experiments
        ]

        # assemble schedules to PulseQobj
        return compiler.assemble(
            experiments=experiments,
            backend=self,
            shots=self.options.shots,
            qubit_lo_freq=self.qubit_lo_freq,
            meas_lo_freq=self.meas_lo_freq,
            **kwargs,
        )


class OpenQASMBackend(TergiteBackend):

    open_pulse = False

    @functools.cached_property
    def target(self: object) -> Target:
        gmap = Target(num_qubits=self.data["num_qubits"])

        # add rx, rz, delay, measure gate set
        gmap.add_instruction(circuit.library.Reset())
        gmap.add_instruction(
            circuit.library.standard_gates.RXGate(circuit.Parameter("theta"))
        )
        gmap.add_instruction(
            circuit.library.standard_gates.RZGate(circuit.Parameter("lambda"))
        )
        gmap.add_instruction(circuit.Delay(circuit.Parameter("tau")))
        gmap.add_instruction(circuit.measure.Measure())

        return gmap

    def make_qobj(self: object, experiments: object, /, **kwargs) -> QasmQobj:
        if type(experiments) is not list:
            experiments = [experiments]
        for e in experiments:
            if not isinstance(e, QuantumCircuit):
                raise TypeError(f"Experiment {e} is not an instance of QuantumCircuit.")
        circuits = compiler.transpile(circuits=experiments, backend=self)
        return compiler.assemble(
            experiments=circuits, shots=self.options.shots, **kwargs
        )

    def configuration(self: object) -> BackendConfiguration:
        return BackendConfiguration(
            backend_name=self.name,  # From BackendV2.
            backend_version=self.backend_version,  # From BackendV2.
            n_qubits=self.target.num_qubits,  # Number of qubits, obtained from self.target.
            basis_gates=[],  # Don't need.
            gates=[],  # Don't need.
            simulator=False,  # This is a real quantum computer.
            conditional=False,  # We cannot do conditional gate application yet.
            local=False,  # Jobs are sent over the internet.
            open_pulse=False,  # This backend just transpiles circuits.
            meas_levels=(2,),  # 0: RAW, 1: INTEGRATED, 2: DISCRIMINATED
            memory=True,  # Meas level 2 results are stored in MongoDB (?).
            max_shots=TergiteBackend.max_shots,  # From TergiteBackend.
            coupling_map=self.coupling_map,  # From TergiteBackend.
        )
