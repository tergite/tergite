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
from .job import Job
from .config import REST_API_MAP
from . import template_schedules as templates
from numpy import inf as infinity
from qiskit.providers import BackendV2
from abc import abstractmethod
from qiskit.providers import Options
from qiskit.providers.models import BackendConfiguration
from qiskit.pulse.channels import AcquireChannel, ControlChannel
from qiskit.pulse.channels import DriveChannel, MeasureChannel
from qiskit.pulse.channels import MemorySlot
from qiskit.transpiler import Target, InstructionProperties
from qiskit.transpiler.coupling import CouplingMap
#from qiskit.circuit import Delay as circuitDelay
from qiskit.circuit import QuantumCircuit
import qiskit.circuit as circuit
from qiskit.circuit.measure import Measure
#from qiskit.circuit.library.standard_gates import RXGate, RZGate
import pandas as pd
import functools
from qiskit.qobj import PulseQobj, QasmQobj
import qiskit.compiler as compiler
import requests


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
            n_qubits=self.target.num_qubits,
            basis_gates=[],
            gates=[],
            simulator=False,  # This is a real quantum computer.
            conditional=False,  # We cannot do conditional gate application yet.
            local=False,  # Jobs are sent over the internet.
            open_pulse=True,
            meas_levels=(0, 1),  # 0: RAW, 1: INTEGRATED, 2: DISCRIMINATED
            memory=False,
            max_shots=TergiteBackend.max_shots,  # From TergiteBackend.
            coupling_map=self.coupling_map,
            supported_instructions=self.target.instructions,
            dt=self.dt,
            dtm=self.dtm,
            description=self.description,  # From BackendV2.
            parametric_pulses=OpenPulseBackend.parametric_pulses,
        )

    @property
    def dt(self: object) -> float:
        return self.data["dt"]

    @property
    def dtm(self: object) -> bool:
        return self.data["dtm"]

    @functools.cached_property
    def target(self: object) -> Target:
        gmap = Target(num_qubits=self.data["qubits"], dt=self.data["dt"])
        qubits = tuple(q for q in range(self.data["qubits"]))

        if self.data["characterized"]:

            rx_theta = circuit.Parameter("theta")
            rz_lambda = circuit.Parameter("lambda")
            delay_tau = circuit.Parameter("tau")

            # Reset qubits to ground state
            # do this by simply waiting 200 µs
            reset_props = {
                (q,) : InstructionProperties(
                    error = 0.0,
                    calibration = templates.delay(self, (q,), 200*1000, delay_str = "Reset")
                )
                for q in qubits
            }
            gmap.add_instruction(circuit.library.Reset(), reset_props)

            # Rotation around X-axis on Bloch sphere
            rx_props = {
                (q,) : InstructionProperties(
                    error = 0.0, 
                    calibration = templates.rx(self, (q,), rx_theta)
                )
                for q in qubits
            }
            gmap.add_instruction(circuit.library.standard_gates.RXGate(rx_theta), rx_props)

            # Rotation around Z-axis on Bloch sphere
            rz_props = {
                (q,) : InstructionProperties(
                    error = 0.0,
                    calibration = templates.rz(self, (q,), rz_lambda)
                )
                for q in qubits
            }
            gmap.add_instruction(circuit.library.standard_gates.RZGate(rz_lambda), rz_props)

            # Delay instruction
            delay_props = {
                (q,) : InstructionProperties(
                    error = 0.0,
                    calibration = templates.delay(self, (q,), delay_tau)
                )
                for q in qubits
            }
            gmap.add_instruction(circuit.Delay(delay_tau), delay_props)

            # Measurement
            measure_props = {
                qubits: InstructionProperties(
                    error=0.0, calibration=templates.measure(self, qubits)
                )
            }
            gmap.add_instruction(Measure(), measure_props)

        return gmap

    @property
    def meas_map(self: object) -> list:
        return self.data["meas_map"]

    @functools.cached_property
    def calibration_table(self: object) -> pd.DataFrame:
        """Returns a pandas dataframe with empirical calibration values specific to this backend."""
        df = pd.DataFrame(data=self.data["calibrations"])
        df["qubit"] = list(range(1, self.data["qubits"] + 1))
        df.set_index("qubit", inplace = True)
        return df

    @functools.cached_property
    def coupling_map(self: object) -> CouplingMap:
        return CouplingMap(couplinglist=self.data["coupling_map"])

    @property
    def qubit_lo_freq(self: object) -> list:
        return self.data["qubit_lo_freq"]

    @property
    def meas_lo_freq(self: object) -> list:
        return self.data["meas_lo_freq"]

    def drive_channel(self: object, qubit_idx: int) -> DriveChannel:
        return DriveChannel(self.data["drive_mapping"][f"d{qubit_idx}"])

    def measure_channel(self: object, qubit_idx: int) -> MeasureChannel:
        return MeasureChannel(self.data["acq_mapping"][f"m{qubit_idx}"])

    def acquire_channel(self: object, qubit_idx: int) -> AcquireChannel:
        return AcquireChannel(self.data["acq_mapping"][f"m{qubit_idx}"])

    def memory_slot(self: object, qubit_idx: int) -> MemorySlot:
        return MemorySlot(qubit_idx)

    def control_channel(self: object, qubits: list) -> list:
        if qubits not in self.coupling_map.get_edges():
            raise ValueError(f"Coupling {qubits} not in coupling map.")

        arr = [self.data["control_mapping"][qubits] for idx in qubits]
        return list(map(ControlChannel, arr))

    def make_qobj(self: object, experiments: object, /, **kwargs) -> PulseQobj:
        if type(experiments) is not list:
            experiments = [experiments]
        return compiler.assemble(
            experiments=experiments,
            backend=self,
            qubit_lo_freq=self.qubit_lo_freq,
            meas_lo_freq=self.meas_lo_freq,
            **kwargs,
        )


class OpenQASMBackend(OpenPulseBackend):

    open_pulse = False

    def make_qobj(self: object, experiments: object, /, **kwargs) -> QasmQobj:
        if type(experiments) is not list:
            experiments = [experiments]
        for e in experiments:
            if not isinstance(e, QuantumCircuit):
                raise TypeError(f"Experiment {e} is not an instance of QuantumCircuit.")
        circuits = compiler.transpile(
            circuits=experiments,
            basis_gates=self.data["basis_gates"],
        )
        return compiler.assemble(experiments=circuits, **kwargs)

    def configuration(self: object) -> BackendConfiguration:
        return BackendConfiguration(
            backend_name=self.name,  # From BackendV2.
            backend_version=self.backend_version,  # From BackendV2.
            n_qubits=self.target.num_qubits,
            basis_gates=self.data["basis_gates"],
            gates=[],
            simulator=False,  # This is a real quantum computer.
            conditional=False,  # We cannot do conditional gate application yet.
            local=False,  # Jobs are sent over the internet.
            open_pulse=False,
            meas_levels=(2,),  # 0: RAW, 1: INTEGRATED, 2: DISCRIMINATED
            memory=True,  # Meas level 2 results are stored in MongoDB.
            max_shots=TergiteBackend.max_shots,  # From TergiteBackend.
            coupling_map=self.coupling_map,
        )
