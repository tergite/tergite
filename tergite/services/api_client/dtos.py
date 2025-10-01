# This code is part of Tergite
#
# (C) Copyright Chalmers Next Labs 2025
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""Module containing the types for data transfer"""
from __future__ import annotations

import enum
import json
from typing import Any, Dict, List, Literal, Optional, Tuple, TypeAlias, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    SerializationInfo,
    field_serializer,
    field_validator,
)
from pydantic.main import IncEx

from tergite.compat.qiskit.qobj import PulseQobj
from tergite.compat.qiskit.qobj.encoder import IQXJsonEncoder

IQPoint: TypeAlias = Tuple[float, float]  # [re, im]  (len = 2)
IQMemory: TypeAlias = List[List[List[IQPoint]]]  # exp → shot → IQ points
HexMemory: TypeAlias = List[
    List[str]
]  # experiments x reps/shots x str(channels x bits)


class TergiteBackendConfig(BaseModel):
    """backend configuration got from the remote server"""

    model_config = ConfigDict(extra="allow")

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
    id: Optional[str] = None
    last_online: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    number_of_couplers: int = 0
    number_of_resonators: int = 0
    dt: Optional[float] = None
    dtm: Optional[float] = None
    coupling_dict: Dict[str, Tuple[str, str]] = {}
    coupled_qubit_idxs: Tuple[Tuple[int, int], ...] = []
    qubit_ids_coupler_dict: Dict[Tuple[int, int], int] = {}
    qubit_ids_coupler_map: List[Tuple[Tuple[int, int], int]] = []
    qubit_ids: List[str] = []
    meas_lo_freq: Optional[List[int]] = None
    qubit_lo_freq: Optional[List[int]] = None
    gates: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

    def model_post_init(self, _context: Any):
        """Run after initialization of the model"""
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


class CalibrationValue(BaseModel):
    """A calibration value"""

    model_config = ConfigDict(extra="allow")

    value: Union[float, str, int]
    date: Optional[str] = None
    unit: str = ""


class QubitCalibration(BaseModel):
    """Schema for the calibration data of the qubit"""

    model_config = ConfigDict(extra="allow")

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


class ResonatorCalibration(BaseModel):
    """Schema for the calibration data of the resonator"""

    model_config = ConfigDict(extra="allow")

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


class CouplersCalibration(BaseModel):
    """Schema for the calibration data of the coupler"""

    model_config = ConfigDict(extra="allow")

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
    control_rz_lambda: Optional[CalibrationValue] = None
    target_rz_lambda: Optional[CalibrationValue] = None
    pulse_type: Optional[CalibrationValue] = None
    id: Optional[int] = None


class DeviceCalibration(BaseModel):
    """Schema for the calibration data of a given device"""

    model_config = ConfigDict(extra="allow")

    name: str
    version: str
    qubits: List[QubitCalibration]
    resonators: Optional[List[ResonatorCalibration]] = None
    couplers: Optional[List[CouplersCalibration]] = None
    discriminators: Optional[Dict[str, Any]] = None
    last_calibrated: str


class CreatedJobResponse(BaseModel):
    """The response when a new job is created"""

    model_config = ConfigDict(
        extra="allow",
    )

    job_id: str
    upload_url: str
    access_token: str


class RemoteJobResult(BaseModel):
    """The results of the job"""

    model_config = ConfigDict(
        extra="allow",
    )

    memory: Union[HexMemory, IQMemory] = []


class RemoteJobStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESSFUL = "successful"
    FAILED = "failed"
    EXECUTING = "executing"
    CANCELLED = "cancelled"


class RemoteJob(BaseModel):
    """the job schema"""

    model_config = ConfigDict(
        extra="allow",
    )

    device: str
    calibration_date: str
    job_id: str
    project_id: Optional[str] = None
    user_id: Optional[str] = None
    status: RemoteJobStatus
    failure_reason: Optional[str] = None
    cancellation_reason: Optional[str] = None
    download_url: Optional[str] = None
    result: Optional[RemoteJobResult] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class JobFileParams(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        arbitrary_types_allowed=True,
    )

    qobj: PulseQobj

    @field_serializer("qobj")
    def serialize_qobj(self, qobj: PulseQobj, _info: SerializationInfo):
        """Converts qobj into a dict"""
        qobj_dict = qobj.to_dict()

        if _info.mode_is_json():
            return json.dumps(qobj_dict, cls=IQXJsonEncoder)
        return qobj_dict

    @field_validator("qobj", mode="before")
    @classmethod
    def parse_qobj(cls, v):
        """Parses the qobject from dict/str to Qobj"""
        if isinstance(v, PulseQobj):
            return v
        elif isinstance(v, dict):
            return PulseQobj.from_dict(v)
        elif isinstance(v, str):
            return PulseQobj.from_dict(json.loads(v))

        raise TypeError(f"Invalid type for PulseQobj: {type(v)}")


class JobFile(BaseModel):
    """The expected structure of the job file"""

    model_config = ConfigDict(extra="forbid")

    job_id: str
    params: JobFileParams
