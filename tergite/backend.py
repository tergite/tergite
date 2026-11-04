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
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional, Sequence, Tuple

from qiskit import QuantumCircuit, qasm3
from qiskit.providers import BackendV2, Options
from qiskit.transpiler import Target

from .api import mss
from .api.bcc_models import CircuitJobParams, JobFile, QasmCircuit
from .exc import TergiteError
from .job import Job
from .pulse import (
    MIGRATION_GUIDE_URL,
    add_calibrations,
    get_calibration_qasm,
    get_calibrations,
    get_frames,
    get_program_info,
    get_program_qasm,
)
from .results import CircuitHeader
from .target import get_target

if TYPE_CHECKING:
    import oqpy

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
        self._target_calibrated: Optional[str] = None
        self._device_properties: Optional["DeviceCalibration"] = None

    @property
    def target(self) -> Target:
        """The transpiler target of the device, from its latest calibration as of when it
        was first read or a job last run"""
        if self._target is None:
            self._compute_target()
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
    def frames(self) -> Dict[str, "oqpy.FrameVar"]:
        """The frames the device's pulse-level jobs may play on, as oqpy frames by name,
        e.g. q12_drive, from its latest calibration; none if it takes no pulse-level jobs.
        Needs the pulse extra"""
        return get_frames(self.device_properties)

    @property
    def calibrations(self) -> Dict[Tuple[str, Tuple[int, ...]], str]:
        """The defcals of the device's gates by gate and physical qubits, e.g. ("x", (0,)),
        from its latest calibration, which a job may run its gates with, as they are or
        changed; none if it takes no pulse-level jobs"""
        return get_calibrations(self.device_properties)

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
        run_input: Any,
        /,
        calibrations: Iterable[Any] = (),
        **options: Any,
    ) -> Job:
        """Runs the circuits, transpiled to the target, and pulse-level programs, as one job

        Args:
            run_input: a circuit or a pulse-level program, or a list of them: circuits
                transpiled to the target; programs as OpenQASM 3 text, or anything with
                to_qasm(), e.g. an oqpy Program, which the backend checks against the
                device's limits, named program_{index} in the result
            calibrations: defcals that each circuit and program runs its gates with, as
                text, e.g. of backend.calibrations, or anything with to_qasm(), e.g. an
                oqpy Program of defcals
            options: shots, meas_level (2 for counts, 1 for IQ points) or meas_return
                (single or avg), for this job instead of the backend's options; a job
                with a program that does not measure runs at meas_level 1 unless given
                one

        Returns:
            the job, submitted

        Raises:
            TergiteError: an entry is neither a circuit nor a program, a circuit uses an
                instruction the target lacks, or a calibration is neither text nor has
                to_qasm()
            ApiError: MSS or the backend refused the job, e.g. a pulse-level job of a
                project without pulse access or beyond the device's limits
        """
        entries = _get_entry_list(run_input)
        defcals = [get_calibration_qasm(calibration) for calibration in calibrations]
        self._refresh_calibration()
        items = [
            self._get_job_item(entry, index) for index, entry in enumerate(entries)
        ]
        settings = {**self.options.__dict__, **options}
        if "meas_level" not in options and not all(item.is_measuring for item in items):
            settings["meas_level"] = 1
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
            headers=[item.header for item in items],
            shots=settings["shots"],
            meas_level=settings["meas_level"],
            meas_return=settings["meas_return"],
            upload_url=created.upload_url,
            access_token=created.access_token,
            calibration_date=self.last_calibrated,
        )
        job.submit(_get_job_file(created.job_id, items, defcals, settings))
        logging.info(f"Tergite: Job {job.job_id()} has been successfully submitted")
        return job

    def _get_job_item(self, entry: Any, index: int) -> "_JobItem":
        """Gets what a job runs of a circuit, checked against the target, or of a program

        Raises:
            TergiteError: the entry is neither a circuit nor a program, or the circuit
                uses an instruction the target lacks
        """
        if isinstance(entry, QuantumCircuit):
            self._check_supported(entry)
            header = CircuitHeader.from_circuit(entry)
            return _JobItem(header=header, qasm=qasm3.dumps(entry), is_measuring=True)
        qasm = get_program_qasm(entry)
        info = get_program_info(qasm)
        header = CircuitHeader(
            name=f"program_{index}",
            creg_sizes=info.creg_sizes,
            memory_slots=info.num_clbits,
        )
        return _JobItem(header=header, qasm=qasm, is_measuring=info.is_measuring)

    def _refresh_calibration(self) -> None:
        """Fetches the latest calibration, and rebuilds a target built from another"""
        self._device_properties = None
        if self._target is not None and self.last_calibrated != self._target_calibrated:
            self._compute_target()

    def _compute_target(self) -> None:
        """Computes the target from the latest calibration fetched"""
        self._target = get_target(self.data, self.device_properties)
        self._target_calibrated = self.last_calibrated
        logging.info(f"Computed the target of the '{self.name}' backend")

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
            "OpenPulseBackend is deprecated: use TergiteBackend, and write pulses in "
            f"OpenPulse: {MIGRATION_GUIDE_URL}",
            DeprecationWarning,
        )
        super().__init__(data=data, provider=provider, base_url=base_url)


class OpenQASMBackend(TergiteBackend):
    """Deprecated: TergiteBackend, which every device now is"""

    def __init__(self, /, *, data: "Device", provider: "Provider", base_url: str):
        warnings.warn(
            "OpenQASMBackend is deprecated: use TergiteBackend", DeprecationWarning
        )
        super().__init__(data=data, provider=provider, base_url=base_url)


@dataclass(frozen=True)
class _JobItem:
    """What a job runs of a circuit or a program: its header, its OpenQASM 3 and whether it
    measures"""

    header: CircuitHeader
    qasm: str
    is_measuring: bool


def _get_entry_list(run_input: Any) -> List[Any]:
    """Gets the circuits and programs of what run() was given: one of them, or a list; one
    that is neither, for the refusal of an entry"""
    is_single = isinstance(run_input, (QuantumCircuit, str)) or hasattr(
        run_input, "to_qasm"
    )
    if is_single or not isinstance(run_input, Iterable):
        return [run_input]
    return list(run_input)


def _get_job_file(
    job_id: str, items: List[_JobItem], defcals: Sequence[str], settings: dict
) -> JobFile:
    return JobFile(
        job_id=job_id,
        params=CircuitJobParams(
            circuits=[
                QasmCircuit(
                    name=item.header.name,
                    qasm=add_calibrations(item.qasm, defcals),
                    num_clbits=item.header.memory_slots,
                    metadata=item.header.metadata,
                )
                for item in items
            ],
            shots=settings["shots"],
            meas_level=settings["meas_level"],
            meas_return=settings["meas_return"],
        ),
    )
