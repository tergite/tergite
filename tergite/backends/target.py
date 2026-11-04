# This code is part of Tergite
#
# (C) Copyright Chalmers Next Labs 2026
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.
"""The transpiler target of a device: its gates, their durations and errors, its qubits"""

import warnings
from typing import Dict, List, Optional, Tuple

from qiskit.circuit import Delay, Measure, Parameter, Reset
from qiskit.circuit.library import CZGate, RXGate, RZGate, SXGate, XGate
from qiskit.providers import QubitProperties
from qiskit.transpiler import InstructionProperties, Target

from ..clients.mss import models as mss_models

# each calibration value is in SI units unless its unit says otherwise; many say none
SI_SCALES = {"ns": 1e-9, "us": 1e-6, "MHz": 1e6, "GHz": 1e9}


def get_target(
    device: mss_models.Device, calibration: Optional[mss_models.DeviceCalibration]
) -> Target:
    """Gets the target the transpiler compiles circuits for the device to

    The gates are those the backends compile, on every device: rz, sx, x and rx on each
    qubit, cz on each coupled pair whose coupler is calibrated, and measure, reset and
    delay. The device's basis_gates are not read, as they list its gate configs.

    Args:
        device: the device as MSS lists it
        calibration: its latest calibration, or None for a device not characterized

    Returns:
        the target, with the calibration's durations, errors and qubit properties
    """
    qubits = range(device.number_of_qubits)
    target = Target(
        num_qubits=device.number_of_qubits,
        dt=device.dt,
        qubit_properties=_get_qubit_properties(calibration, qubits),
    )
    single_qubit_props = {
        (q,): InstructionProperties(duration=_get_pi_pulse_duration(calibration, q))
        for q in qubits
    }
    # rz is a phase shift of the drive's frame, which takes no time and adds no error
    rz_props = {(q,): InstructionProperties(duration=0.0, error=0.0) for q in qubits}
    target.add_instruction(RZGate(Parameter("λ")), rz_props)
    target.add_instruction(SXGate(), single_qubit_props)
    target.add_instruction(XGate(), single_qubit_props)
    target.add_instruction(RXGate(Parameter("θ")), single_qubit_props)
    target.add_instruction(Measure(), _get_measure_props(calibration, qubits))
    target.add_instruction(Reset(), {(q,): None for q in qubits})
    target.add_instruction(Delay(Parameter("τ")), {(q,): None for q in qubits})
    cz_props = _get_cz_props(device, calibration)
    if cz_props:
        target.add_instruction(CZGate(), cz_props)
    return target


def _get_qubit_properties(
    calibration: Optional[mss_models.DeviceCalibration], qubits: range
) -> Optional[List[QubitProperties]]:
    if calibration is None:
        return None
    return [
        QubitProperties(
            t1=_get_si_value(calibration.qubits[q].t1_decoherence),
            t2=_get_si_value(calibration.qubits[q].t2_decoherence),
            frequency=_get_si_value(calibration.qubits[q].frequency),
        )
        for q in qubits
    ]


def _get_pi_pulse_duration(
    calibration: Optional[mss_models.DeviceCalibration], qubit: int
) -> Optional[float]:
    if calibration is None:
        return None
    return _get_si_value(calibration.qubits[qubit].pi_pulse_duration)


def _get_measure_props(
    calibration: Optional[mss_models.DeviceCalibration], qubits: range
) -> Dict[Tuple[int], Optional[InstructionProperties]]:
    if calibration is None or not calibration.resonators:
        return {(q,): None for q in qubits}
    return {
        (q,): InstructionProperties(
            duration=_get_si_value(calibration.resonators[q].pulse_duration),
            error=_get_si_value(calibration.qubits[q].readout_assignment_error),
        )
        for q in qubits
    }


def _get_cz_props(
    device: mss_models.Device, calibration: Optional[mss_models.DeviceCalibration]
) -> Dict[Tuple[int, int], InstructionProperties]:
    """The CZ of each coupled pair whose coupler the calibration has, timed as the backend
    plays it: a wait, the rising and constant pulse, and the wait again"""
    if calibration is None:
        return {}
    couplers = {coupler.id: coupler for coupler in calibration.couplers or []}
    coupler_ids = {
        tuple(sorted(pair)): index for pair, index in device.qubit_ids_coupler_map or []
    }
    cz_props = {}
    uncalibrated_pairs = []
    for control, target in device.coupling_map:
        if control == target:
            continue
        qubit_ids = (calibration.qubits[control].id, calibration.qubits[target].id)
        coupler = couplers.get(coupler_ids.get(tuple(sorted(qubit_ids))))
        if coupler is None:
            uncalibrated_pairs.append((control, target))
            continue
        cz_props[(control, target)] = InstructionProperties(
            duration=_get_cz_duration(coupler)
        )

    if uncalibrated_pairs:
        warnings.warn(
            f"Backend '{device.name}' has no CZ on {uncalibrated_pairs}, "
            "whose couplers are not calibrated"
        )
    return cz_props


def _get_cz_duration(coupler: mss_models.CouplersCalibration) -> Optional[float]:
    parts = (
        coupler.cz_pulse_duration_before,
        coupler.cz_pulse_duration_rise,
        coupler.cz_pulse_duration_constant,
        coupler.cz_pulse_duration_before,
    )
    durations = [_get_si_value(part) for part in parts]
    return None if None in durations else sum(durations)


def _get_si_value(
    calibration_value: Optional[mss_models.CalibrationValue],
) -> Optional[float]:
    if calibration_value is None or isinstance(calibration_value.value, str):
        return None
    return float(calibration_value.value) * SI_SCALES.get(
        calibration_value.unit.value, 1.0
    )
