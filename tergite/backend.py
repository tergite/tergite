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
# Chalmers Next Labs, 2026
"""The Qiskit backend of a Tergite device, which runs circuits"""
import logging
import warnings
from typing import TYPE_CHECKING, Any, Iterable, List, Optional, Union

from qiskit import QuantumCircuit, qasm3
from qiskit.providers import BackendV2, Options
from qiskit.transpiler import Target

from .api import mss
from .api.job_file import CircuitPayload, JobFile, JobParams
from .exc import TergiteError
from .job import Job
from .results import CircuitHeader
from .target import get_target

if TYPE_CHECKING:
    from .api.mss_models import Device, DeviceCalibration
    from .types.provider import Provider


class TergiteBackend(BackendV2):
    """The backend of a Tergite device, which runs circuits transpiled to its target"""

    def __init__(self, /, *, data: "Device", provider: "Provider", base_url: str):
        """Initializes the backend of the device

        Args:
            data: the device as MSS lists it
            provider: the provider the backend is got through
            base_url: the URL of the MSS the provider uses
        """
        super().__init__(
            provider=provider, name=data.name, backend_version=data.version
        )
        self.base_url = base_url
        self.data = data
        self._target: Optional[Target] = None
        self._device_properties: Optional["DeviceCalibration"] = None

    @property
    def target(self) -> Target:
        """The transpiler target of the device, from its latest calibration"""
        if self._target is None:
            self._refresh_target()
        return self._target

    @property
    def max_circuits(self) -> None:
        """None, as a job may hold any number of circuits"""
        return None

    @property
    def device_properties(self) -> Optional["DeviceCalibration"]:
        """The latest calibration of the device, or None if it is not characterized"""
        if self._device_properties is None and self.data.characterized:
            self._device_properties = mss.get_calibration(
                self.provider.mss_client, backend_name=self.name
            )
        return self._device_properties

    @property
    def last_calibrated(self) -> Optional[str]:
        """When the device was last calibrated, or None if it is not characterized"""
        calibration = self.device_properties
        return None if calibration is None else calibration.last_calibrated

    @property
    def meas_map(self) -> List[List[int]]:
        """The qubits the device measures together"""
        return self.data.meas_map

    @classmethod
    def _default_options(cls) -> Options:
        options = Options(shots=2000, meas_level=2, meas_return="single")
        options.set_validator("shots", (1, float("inf")))
        options.set_validator("meas_level", [0, 1, 2])
        options.set_validator("meas_return", ["single", "avg"])
        return options

    def run(
        self,
        run_input: Union[QuantumCircuit, Iterable[QuantumCircuit]],
        /,
        **options: Any,
    ) -> Job:
        """Runs the circuits, transpiled to the target, as one job

        Args:
            run_input: a circuit or circuits, transpiled to the target
            options: shots, meas_level (2 for counts, 1 for IQ points) or meas_return
                (single or avg), for this job instead of the backend's options

        Returns:
            the job, submitted

        Raises:
            TergiteError: a circuit is not a QuantumCircuit, or uses an instruction the
                target lacks
            ApiError: MSS or the backend refused the job
        """
        circuits = _get_circuit_list(run_input)
        self._refresh_target()
        for circuit in circuits:
            self._check_supported(circuit)
        settings = {**self.options.__dict__, **options}
        # Qiskit defines meas_return for levels 0 and 1 alone; at level 2 the backend
        # averages what it is sent, so each shot's bits are asked for, whatever was passed
        if settings["meas_level"] == 2:
            settings["meas_return"] = "single"

        created = mss.create_job(
            self.provider.mss_client,
            backend_name=self.name,
            calibration_date=self.last_calibrated,
        )
        job = Job(
            backend=self,
            job_id=created.job_id,
            headers=[CircuitHeader.from_circuit(c) for c in circuits],
            shots=settings["shots"],
            meas_level=settings["meas_level"],
            meas_return=settings["meas_return"],
            upload_url=created.upload_url,
            access_token=created.access_token,
            calibration_date=self.last_calibrated,
        )
        job.submit(_get_job_file(created.job_id, circuits, settings))
        logging.info(f"Tergite: Job {job.job_id()} has been successfully submitted")
        return job

    def _refresh_target(self) -> None:
        """Rebuilds the target from a fresh calibration"""
        self._device_properties = None
        self._target = get_target(self.data, self.device_properties)
        logging.info(f"Refreshed the target for '{self.name}' backend")

    def _check_supported(self, circuit: QuantumCircuit) -> None:
        """Raises if the circuit uses an instruction the target lacks"""
        for instruction in circuit.data:
            name = instruction.operation.name
            if name == "barrier":
                continue
            qargs = tuple(circuit.find_bit(q).index for q in instruction.qubits)
            if not self.target.instruction_supported(name, qargs):
                raise TergiteError(
                    f"Backend '{self.name}' has no {name} on qubits {qargs}: transpile "
                    f"the circuit '{circuit.name}' to the backend first"
                )

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, TergiteBackend):
            return False
        return (self.name, self.backend_version, self.data) == (
            other.name,
            other.backend_version,
            other.data,
        )

    def __hash__(self) -> int:
        # only fields __eq__ compares, so that equal backends hash alike
        return hash((self.name, self.backend_version))

    def __repr__(self) -> str:
        return f"<TergiteBackend {self.name} {self.backend_version} at {self.base_url}>"


class OpenPulseBackend(TergiteBackend):
    """Deprecated: TergiteBackend, which every device now is"""

    def __init__(self, /, *, data: "Device", provider: "Provider", base_url: str):
        warnings.warn(
            "OpenPulseBackend is deprecated: use TergiteBackend", DeprecationWarning
        )
        super().__init__(data=data, provider=provider, base_url=base_url)


class OpenQASMBackend(TergiteBackend):
    """Deprecated: TergiteBackend, which every device now is"""

    def __init__(self, /, *, data: "Device", provider: "Provider", base_url: str):
        warnings.warn(
            "OpenQASMBackend is deprecated: use TergiteBackend", DeprecationWarning
        )
        super().__init__(data=data, provider=provider, base_url=base_url)


def _get_circuit_list(
    run_input: Union[QuantumCircuit, Iterable[QuantumCircuit]],
) -> List[QuantumCircuit]:
    circuits = [run_input] if isinstance(run_input, QuantumCircuit) else list(run_input)
    for circuit in circuits:
        if not isinstance(circuit, QuantumCircuit):
            raise TergiteError(
                f"Tergite backends run circuits, not {type(circuit).__name__}: "
                "pulse schedules went with Qiskit's qiskit.pulse"
            )
    return circuits


def _get_job_file(
    job_id: str, circuits: List[QuantumCircuit], settings: dict
) -> JobFile:
    return JobFile(
        job_id=job_id,
        params=JobParams(
            circuits=[
                CircuitPayload(
                    name=circuit.name,
                    qasm=qasm3.dumps(circuit),
                    num_clbits=circuit.num_clbits,
                    metadata=dict(circuit.metadata or {}),
                )
                for circuit in circuits
            ],
            shots=settings["shots"],
            meas_level=settings["meas_level"],
            meas_return=settings["meas_return"],
        ),
    )
