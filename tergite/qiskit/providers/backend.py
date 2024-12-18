# This code is part of Tergite
#
# (C) Copyright Miroslav Dobsicek 2020, 2021
# (C) Copyright Axel Andersson 2022
# (C) Copyright Martin Ahindura 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
#
# This code was refactored from the original on 22nd September, 2023 by Martin Ahindura
"""Defines the backend types provided by Tergite."""

from __future__ import annotations

import dataclasses
import functools
import warnings
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

import qiskit.circuit as circuit
import qiskit.compiler as compiler
import qiskit.pulse as pulse
import requests
from numpy import inf as infinity
from pydantic import BaseModel, Extra
from qiskit.circuit import QuantumCircuit
from qiskit.providers import BackendV2, Options
from qiskit.pulse.channels import (
    AcquireChannel,
    DriveChannel,
    MeasureChannel,
    MemorySlot,
)
from qiskit.transpiler import Target
from qiskit.transpiler.coupling import CouplingMap
from qiskit_ibm_runtime.models import BackendConfiguration

from tergite.qiskit.deprecated.compiler.assembler import assemble
from tergite.qiskit.deprecated.qobj import PulseQobj, QasmQobj
from tergite.qiskit.providers import calibrations

from .config import REST_API_MAP
from .job import Job

if TYPE_CHECKING:
    from .provider import Provider as TergiteProvider


class TergiteBackend(BackendV2):
    """Abstract class for Tergite Backends"""

    max_shots = infinity
    max_circuits = infinity

    def __init__(
        self,
        /,
        *,
        data: "TergiteBackendConfig",
        provider: "TergiteProvider",
        base_url: str,
    ):
        """Initialize a TergiteBackend based backend

        Args:
            provider: An optional backwards reference to the
                :class:`~qiskit.providers.Provider` object that the backend
                is from
            data: An optional config of type :class:`TergiteBackendConfig`
                from which to construct this backend
            base_url: An optional URL to Tergite API through which
                jobs are to be run

        Raises:
            AttributeError: If a field is specified that's outside the backend's
                options
            TypeError: If ``data`` is not a :class:`TergiteBackendConfig` object
        """
        super().__init__(
            provider=provider,
            name=data.name,
            backend_version=data.version,
        )
        self.base_url = base_url
        self.data = dataclasses.asdict(data)

    def register_job(self) -> Job:
        """Registers a new asynchronous job with the Tergite API.

        Returns:
             tergite.qiskit.providers.job.Job: An asynchronous
                 job registered in the Tergite API to be executed
        """
        jobs_url = self.base_url + REST_API_MAP["jobs"]
        provider: "TergiteProvider" = self.provider
        auth_headers = provider.get_auth_headers()
        response = requests.post(
            jobs_url,
            headers=auth_headers,
            params=dict(backend=self.name),
        )
        if response.ok:
            job_registration = response.json()
        else:
            raise RuntimeError(
                f"Unable to register job at the Tergite MSS, response: {response}"
            )
        job_id = job_registration["job_id"]
        job_upload_url = job_registration["upload_url"]
        return Job(backend=self, job_id=job_id, upload_url=job_upload_url)

    def run(self, experiments, /, **kwargs) -> Job:
        """Run on the Tergite backend.

        This method returns a :class:`~qiskit.providers.Job` object
        that runs circuits. Depending on the backend this may be either an async
        or sync call. It is at the discretion of the provider to decide whether
        running should block until the execution is finished or not: the Job
        class can handle either situation.

        Args:
            experiments (QuantumCircuit or Schedule or ScheduleBlock or list): An
                individual or a list of
                :class:`~qiskit.circuits.QuantumCircuit,
                :class:`~qiskit.pulse.ScheduleBlock`, or
                :class:`~qiskit.pulse.Schedule` objects to run on the backend.
            kwargs: Any kwarg options to pass to the backend for running the
                config. If a key is also present in the options
                attribute/object then the expectation is that the value
                specified will be used instead of what's set in the options
                object.

        Returns:
            tergite.qiskit.providers.job.Job: The job object for the run
        """
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

    @abstractmethod
    def configuration(self) -> BackendConfiguration:
        """Retrieves this backend's configuration

        Returns:
            qiskit.providers.models.backendconfiguration.BackendConfiguration:
                this backend's configuration
        """
        ...

    @abstractmethod
    def make_qobj(self, experiments: list, /, **kwargs) -> object:
        """Constructs a Qobj from a list of user OpenPulse schedules or OpenQASM circuits

        Args:
            experiments (QuantumCircuit or Schedule or ScheduleBlock or list): An
                individual or a list of
                :class:`~qiskit.circuits.QuantumCircuit,
                :class:`~qiskit.pulse.ScheduleBlock`, or
                :class:`~qiskit.pulse.Schedule` objects to run on the backend.

        Returns:
             qiskit.qobj.pulse_qobj.PulseQobj or qiskit.qobj.pulse_qobj.QasmQobj
                transpiled from the experiments.
        """
        ...

    @property
    def meas_map(self) -> list:
        return self.data["meas_map"]

    @functools.cached_property
    def coupling_map(self) -> CouplingMap:
        # It is required that nodes are contiguously indexed starting at 0.
        # Missed nodes will be added as isolated nodes in the coupling map.
        #
        # Also for some reason the graph has to be connected in Qiskit? Not sure why that is..
        edges = sorted(
            sorted(self.data["coupling_map"], key=lambda i: i[1]), key=lambda i: i[0]
        )
        return CouplingMap(couplinglist=list(edges))

    @classmethod
    def _default_options(cls, /) -> Options:
        """This defines the default user configurable settings of this backend.

        See: help(backend.set_options)

         Returns:
            qiskit.providers.Options: A options object with
                default values set
        """
        options = Options(shots=2000)
        options.set_validator("shots", (1, TergiteBackend.max_shots))
        return options

    def _as_dict(self):
        """Converts this backend into a dictionary representation

        Returns:
            dict: a dictionary representation of this backend
        """
        obj = self.configuration().to_dict()
        obj["characterized"] = self.data["characterized"]
        return obj

    def __repr__(self) -> str:
        repr_list = [f"TergiteBackend object @ {hex(id(self))}:"]
        config = self._as_dict()
        for attr, value in config.items():
            repr_list.append(f"  {attr}:\t{value}".expandtabs(30))
        return "\n".join(repr_list)

    def __eq__(self, other: Any):
        if not isinstance(other, TergiteBackend):
            return False

        self_dict = self._as_dict().copy()
        other_dict = other._as_dict().copy()

        # serialize a few items that are hard to serialize
        self_dict["coupling_map"] = f"{self_dict['coupling_map']}"
        other_dict["coupling_map"] = f"{other_dict['coupling_map']}"

        self_dict["supported_instructions"] = f"{self_dict['supported_instructions']}"
        other_dict["supported_instructions"] = f"{other_dict['supported_instructions']}"

        return self_dict == other_dict


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
        "wacqt_cz_gate_pulse",
    ]

    def configuration(self) -> BackendConfiguration:
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
            supported_instructions=self.target.instructions,  # Supported instructions, obtained from self.target.
            dt=self.dt,  # From self
            dtm=self.dtm,  # From self
            description=self.description,  # From BackendV2.
            parametric_pulses=OpenPulseBackend.parametric_pulses,  # From type of self
        )

    @property
    def dt(self) -> float:
        return self.data["dt"]

    @property
    def dtm(self) -> float:
        return self.data["dtm"]

    @property
    def target(self) -> Target:
        provider: "TergiteProvider" = self.provider
        device_properties = provider.get_latest_calibration(backend_name=self.name)
        gmap = Target(num_qubits=self.data["num_qubits"], dt=self.data["dt"])
        if self.data["characterized"]:
            calibrations.add_instructions(
                backend=self,
                qubits=tuple(q for q in range(self.data["num_qubits"])),
                coupled_qubit_idxs=self.data["coupled_qubit_idxs"],
                target=gmap,
                device_properties=device_properties,
            )
        return gmap

    @property
    def qubit_lo_freq(self) -> list:
        return [0.0] * self.data["num_qubits"]

    @property
    def meas_lo_freq(self) -> list:
        return [0.0] * self.data["num_resonators"]

    def drive_channel(self, qubit_idx: int) -> DriveChannel:
        return DriveChannel(qubit_idx)

    def measure_channel(self, qubit_idx: int) -> MeasureChannel:
        return MeasureChannel(qubit_idx)

    def acquire_channel(self, qubit_idx: int) -> AcquireChannel:
        return AcquireChannel(qubit_idx)

    def memory_slot(self, qubit_idx: int) -> MemorySlot:
        return MemorySlot(qubit_idx)

    def control_channel(self, qubits):
        """Return the control channel for the given qubits."""
        try:
            pulse_channel = self.data["qubit_ids_coupler_dict"][qubits]
            return [pulse.ControlChannel(pulse_channel)]
        except KeyError:
            raise ValueError(f"Coupling {qubits} not in coupling map.")

    def make_qobj(self, experiments: object, /, **kwargs) -> PulseQobj:
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
        with warnings.catch_warnings():
            # The method assemble is deprecated
            warnings.filterwarnings(
                "ignore", category=DeprecationWarning, module="qiskit"
            )
            return assemble(
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
    def target(self) -> Target:
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
        gmap.add_instruction(circuit.library.CZGate())

        return gmap

    def make_qobj(
        self, experiments: Union[List[QuantumCircuit], QuantumCircuit], /, **kwargs
    ) -> QasmQobj:
        """Constructs a QasmQobj from an OpenQASM circuit, or a list of them

        Raises:
            TypeError: If any of the experiments passed in not an instance
                of :class:`~qiskit.qobj.qasm_qobj.QasmQobj`

        Returns:
            qiskit.qobj.qasm_qobj.QasmQobj: A QasmQobj object transpiled from the circuits
        """
        if type(experiments) is not list:
            experiments = [experiments]
        for e in experiments:
            if not isinstance(e, QuantumCircuit):
                raise TypeError(f"Experiment {e} is not an instance of QuantumCircuit.")

        circuits = compiler.transpile(circuits=experiments, backend=self)
        with warnings.catch_warnings():
            # The class QobjExperimentHeader is deprecated
            warnings.filterwarnings(
                "ignore", category=DeprecationWarning, module="qiskit"
            )
            return assemble(experiments=circuits, shots=self.options.shots, **kwargs)

    def configuration(self) -> BackendConfiguration:
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


@dataclasses.dataclass
class TergiteBackendConfig:
    """Version 2 of the TergiteBackendConfig dataclass"""

    # Fields without default values
    name: str
    version: str
    number_of_qubits: int
    is_online: bool
    basis_gates: List[str]
    coupling_map: List[Tuple[int, int]]
    coordinates: List[Tuple[int, int]]
    is_simulator: bool
    characterized: bool
    open_pulse: bool
    meas_map: List[List[int]]

    # Fields with default values
    _id: Optional[str] = None
    last_online: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    simulator: bool = False
    num_qubits: int = 0
    num_couplers: int = 0
    num_resonators: int = 0
    online_date: Optional[str] = None
    dt: Optional[float] = None
    dtm: Optional[float] = None
    timelog: Dict[str, Any] = dataclasses.field(default_factory=dict)
    coupling_dict: Dict[str, Tuple[str, str]] = dataclasses.field(default_factory=dict)
    coupled_qubit_idxs: Tuple[Tuple[int, int], ...] = ()
    qubit_ids_coupler_dict: Dict[Tuple[int, int], int] = dataclasses.field(
        default_factory=dict
    )
    qubit_ids_coupler_map: List[Tuple[Tuple[int, int], int]] = dataclasses.field(
        default_factory=list
    )
    qubit_ids: List[str] = dataclasses.field(default_factory=list)
    meas_lo_freq: Optional[List[int]] = None
    qubit_lo_freq: Optional[List[int]] = None
    gates: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    properties: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Run after initialization of the dataclass"""
        # qubits_coupler_map is a list of key,value tuples for the qubit_ids_coupler_dict
        # It is so because a dict with tuples as keys is not JSON serializable
        self.qubit_ids_coupler_dict = {
            tuple(k): v for (k, v) in self.qubit_ids_coupler_map
        }

        # the coupling_map sometimes has qubits connected to themselves e.g. [0, 0] when there are
        # no couplers so we need to filter these out to get the qubits that are actually coupled
        self.coupled_qubit_idxs = tuple(
            [pair for pair in self.coupling_map if pair[0] != pair[1]]
        )


class CalibrationValue(BaseModel, extra=Extra.allow):
    """A calibration value"""

    value: Union[float, str, int]
    date: Optional[str] = None
    unit: str = ""


class QubitCalibration(BaseModel, extra=Extra.allow):
    """Schema for the calibration data of the qubit"""

    t1_decoherence: Optional[CalibrationValue] = None
    t2_decoherence: Optional[CalibrationValue] = None
    frequency: Optional[CalibrationValue] = None
    anharmonicity: Optional[CalibrationValue] = None
    readout_assignment_error: Optional[CalibrationValue] = None
    # parameters for x gate
    pi_pulse_amplitude: Optional[CalibrationValue] = None
    pi_pulse_duration: Optional[CalibrationValue] = None
    pulse_type: Optional[CalibrationValue] = None
    pulse_sigma: Optional[CalibrationValue] = None
    id: Optional[int] = None
    index: Optional[CalibrationValue] = None
    x_position: Optional[CalibrationValue] = None
    y_position: Optional[CalibrationValue] = None
    xy_drive_line: Optional[CalibrationValue] = None
    z_drive_line: Optional[CalibrationValue] = None


class ResonatorCalibration(BaseModel, extra=Extra.allow):
    """Schema for the calibration data of the resonator"""

    acq_delay: Optional[CalibrationValue] = None
    acq_integration_time: Optional[CalibrationValue] = None
    frequency: Optional[CalibrationValue] = None
    pulse_amplitude: Optional[CalibrationValue] = None
    pulse_delay: Optional[CalibrationValue] = None
    pulse_duration: Optional[CalibrationValue] = None
    pulse_type: Optional[CalibrationValue] = None
    id: Optional[int] = None
    index: Optional[CalibrationValue] = None
    x_position: Optional[CalibrationValue] = None
    y_position: Optional[CalibrationValue] = None
    readout_line: Optional[CalibrationValue] = None


class CouplersCalibration(BaseModel, extra=Extra.allow):
    """Schema for the calibration data of the coupler"""

    frequency: Optional[CalibrationValue] = None
    frequency_detuning: Optional[CalibrationValue] = None
    anharmonicity: Optional[CalibrationValue] = None
    coupling_strength_02: Optional[CalibrationValue] = None
    coupling_strength_12: Optional[CalibrationValue] = None
    cz_pulse_amplitude: Optional[CalibrationValue] = None
    cz_pulse_dc_bias: Optional[CalibrationValue] = None
    cz_pulse_phase_offset: Optional[CalibrationValue] = None
    cz_pulse_duration_before: Optional[CalibrationValue] = None
    cz_pulse_duration_rise: Optional[CalibrationValue] = None
    cz_pulse_duration_constant: Optional[CalibrationValue] = None
    pulse_type: Optional[CalibrationValue] = None
    id: Optional[int] = None


class DeviceCalibrationV2(BaseModel):
    """Schema for the calibration data of a given device"""

    name: str
    version: str
    qubits: List[QubitCalibration]
    resonators: Optional[List[ResonatorCalibration]] = None
    couplers: Optional[List[CouplersCalibration]] = None
    discriminators: Optional[Dict[str, Any]] = None
    last_calibrated: str
