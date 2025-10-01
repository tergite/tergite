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
# Alteration Notice
# -----------------
# This code was refactored from the original by:
#
# Martin Ahindura, 2023, 2025
"""Defines the backend types provided by Tergite."""

from __future__ import annotations

import functools
import logging
import warnings
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union

import qiskit.circuit as circuit
import qiskit.compiler as compiler
import qiskit.pulse as pulse
from numpy import inf as infinity
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

from ..compat.qiskit.compiler.assembler import assemble
from ..compat.qiskit.qobj import PulseQobj, QasmQobj
from ..services import api_client, device_compiler
from ..utils.quantum_circuit import as_circuit_list, normalise_classical_registers
from .job import Job

if TYPE_CHECKING:
    from ..services.api_client import DeviceCalibration, TergiteBackendConfig
    from .provider import Provider as TergiteProvider


class TergiteBackend(BackendV2):
    """Abstract class for Tergite Backends"""

    max_shots = infinity
    max_circuits = infinity
    provider: "TergiteProvider"

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
        self.data = data

    @property
    @abstractmethod
    def device_properties(self) -> Optional["DeviceCalibration"]:
        """The calibrated data for the given device"""

    def register_job(self, payload: Union[PulseQobj, QasmQobj], **metadata) -> Job:
        """Registers a new asynchronous job with the Tergite API.

        Args:
            payload: the experiments to attach to the given job
            metadata: the extra properties to add to the metadata of the object

        Returns:
             tergite.qiskit.providers.job.Job: An asynchronous
                 job registered in the Tergite API to be executed
        """
        calibration_date = metadata.get("calibration_date", None)
        resp = api_client.register_job(
            self.provider.account,
            backend_name=self.name,
            calibration_date=calibration_date,
        )
        return Job(
            backend=self,
            job_id=resp.job_id,
            payload=payload,
            upload_url=resp.upload_url,
            access_token=resp.access_token,
            **metadata,
        )

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
        experiments = as_circuit_list(experiments)

        # only normalize if that's a circuit
        if all(isinstance(exp, QuantumCircuit) for exp in experiments):
            # measure_all creates an additional classical register with a different name
            # remove unsused classical register if any present
            experiments = [
                normalise_classical_registers(exp, prefer_c=True) for exp in experiments
            ]

        qobj = self.make_qobj(experiments, **kwargs)
        job = self.register_job(
            payload=qobj,
            shots=qobj.config.shots,
            qobj_id=qobj.qobj_id,
            num_experiments=len(qobj.experiments),
            calibration_date=self.last_calibrated,
        )
        response = job.submit()
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
    def make_qobj(self, experiments: list, /, **kwargs) -> Union[PulseQobj, QasmQobj]:
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
        return self.data.meas_map

    @property
    def last_calibrated(self) -> Optional[str]:
        """The timestamp for when this backed was last calibrated"""
        try:
            return self.device_properties.last_calibrated
        except AttributeError:
            pass

    @functools.cached_property
    def coupling_map(self) -> CouplingMap:
        # It is required that nodes are contiguously indexed starting at 0.
        # Missed nodes will be added as isolated nodes in the coupling map.
        #
        # Also for some reason the graph has to be connected in Qiskit? Not sure why that is..
        edges = sorted(
            sorted(self.data.coupling_map, key=lambda i: i[1]), key=lambda i: i[0]
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
        obj["characterized"] = self.data.characterized
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
    provider: "TergiteProvider"
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

    def __init__(
        self,
        /,
        *,
        data: "TergiteBackendConfig",
        provider: "TergiteProvider",
        base_url: str,
    ):
        self._target: Optional[Target] = None
        self._device_properties: Optional[DeviceCalibration] = None
        super().__init__(data=data, provider=provider, base_url=base_url)

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
    def device_properties(self) -> DeviceCalibration:
        """The calibrated data for the given device"""
        if self._device_properties is None:
            self._refresh_device_properties()
        return self._device_properties

    @property
    def dt(self) -> float:
        return self.data.dt

    @property
    def dtm(self) -> float:
        return self.data.dtm

    @property
    def target(self) -> Target:
        """A qiskit. transpiler. Target object for the backend.

        This internally makes a call to the calibrations endpoint
        to get the latest calibration data and compiles a new Target
        for it.
        """
        if self._target is None:
            self._refresh_target()

        return self._target

    @property
    def qubit_lo_freq(self) -> list:
        # FIXME: I think self.data might have a 'qubit_lo_freq' value.
        return [0.0] * self.data.number_of_qubits

    @property
    def meas_lo_freq(self) -> list:
        # FIXME: I think self.data might have a 'meas_lo_freq' value.
        return [0.0] * self.data.number_of_resonators

    def drive_channel(self, qubit_idx: int) -> DriveChannel:
        return DriveChannel(qubit_idx)

    def measure_channel(self, qubit_idx: int) -> MeasureChannel:
        return MeasureChannel(qubit_idx)

    def acquire_channel(self, qubit_idx: int) -> AcquireChannel:
        return AcquireChannel(qubit_idx)

    def memory_slot(self, qubit_idx: int) -> MemorySlot:
        return MemorySlot(qubit_idx)

    def control_channel(self, qubits: Tuple[int, int]):
        """Return the control channel for the given qubits."""
        try:
            pulse_channel = self.data.qubit_ids_coupler_dict[qubits]
            return [pulse.ControlChannel(pulse_channel)]
        except KeyError:
            raise ValueError(f"Coupling {qubits} not in coupling map.")

    def make_qobj(self, experiments: object, /, **kwargs) -> PulseQobj:
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
        # Ensure that the target is recompiled for the latest calibration data
        self._refresh_target()

        if type(experiments) is not list:
            experiments = [experiments]

        # convert all non-schedules to schedules
        experiments = [
            (
                compiler.schedule(experiment, backend=self)
                if (type(experiment) is not pulse.ScheduleBlock)
                and (type(experiment) is not pulse.Schedule)
                else experiment
            )  # already a schedule, so don't convert
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

    def _refresh_device_properties(self):
        """Refreshes the device properties for this backend

        Internally, a fresh call to the calibrations endpoint is made to the REST API
        """
        if self.data.characterized:
            self._device_properties = api_client.get_latest_calibration(
                self.provider.account, backend_name=self.name
            )
            logging.info(f"Refreshed the device properties of '{self.name}' backend")

    def _refresh_target(self):
        """Recompiles the target for this backend

        Internally, a fresh call to the calibrations endpoint is made to the REST API
        """
        gmap = Target(num_qubits=self.data.number_of_qubits, dt=self.data.dt)
        if self.data.characterized:
            self._refresh_device_properties()

            device_compiler.add_instructions(
                backend=self,
                qubits=tuple(q for q in range(self.data.number_of_qubits)),
                coupled_qubit_idxs=self.data.coupled_qubit_idxs,
                target=gmap,
                device_properties=self.device_properties,
            )

        logging.info(f"Refreshed the target for '{self.name}' backend")
        self._target = gmap

    @property
    def meas_map(self) -> list:
        return self.data.meas_map

    @property
    def last_calibrated(self) -> Optional[str]:
        """The timestamp for when this backed was last calibrated"""
        try:
            return self.device_properties.last_calibrated
        except AttributeError:
            pass

    @functools.cached_property
    def coupling_map(self) -> CouplingMap:
        # It is required that nodes are contiguously indexed starting at 0.
        # Missed nodes will be added as isolated nodes in the coupling map.
        #
        # Also for some reason the graph has to be connected in Qiskit? Not sure why that is..
        edges = sorted(
            sorted(self.data.coupling_map, key=lambda i: i[1]), key=lambda i: i[0]
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
        obj["characterized"] = self.data.characterized
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


class OpenQASMBackend(TergiteBackend):
    open_pulse = False

    @functools.cached_property
    def target(self) -> Target:
        gmap = Target(num_qubits=self.data.number_of_qubits)

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
