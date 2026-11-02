# This code is part of Tergite
#
# (C) Copyright Axel Andersson 2022
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
# Martin Ahindura, 2023
"""Handles the compilation of device properties into qiskit target"""
import warnings
from typing import TYPE_CHECKING, Dict, List, Tuple

import qiskit.circuit as circuit
from qiskit.transpiler import InstructionProperties, Target

from ...exc import UncalibratedCouplerError
from ..device_compiler import schedules as templates

if TYPE_CHECKING:
    from ...api.mss_models import DeviceCalibration
    from ...types.backend import TergiteBackend


def add_instructions(
    target: Target,
    backend: "TergiteBackend",
    qubits: tuple,
    device_properties: "DeviceCalibration",
) -> Target:
    """Adds Rx, Rz gates and Delay and Measure instructions for each qubit
    to the transpiler target provided.

    Implementations are backend dependent and are based on a specific calibration.

    Args:
        target: the target on which the instruction is to be added
        backend: the instance of
            :class:`~tergite.providers.tergite.backend:TergiteBackend`
            for which to add the instructions
        qubits: a tuple of qubits on which the instruction is to be run
        device_properties: the dynamic device parameters of the device
    """
    # TODO: Fetch error statistics of gates from database

    rx_theta = circuit.Parameter("theta")
    # changed lambda to lambda_param as it's not a valid name when it's used as a parameter further in transpilation
    rz_lambda = circuit.Parameter("lambda_param")
    delay_tau = circuit.Parameter("tau")

    # Reset qubits to ground state
    reset_props = {
        (q,): InstructionProperties(
            error=0.0,
            calibration=templates.delay(backend, (q,), 300 * 1000, delay_str="Reset"),
        )
        for q in qubits
    }
    target.add_instruction(circuit.library.Reset(), reset_props)

    # Rotation around X-axis on Bloch sphere
    rx_props = {
        (q,): InstructionProperties(
            error=0.0,
            calibration=templates.rx(
                backend, (q,), rx_theta, device_properties=device_properties
            ),
        )
        for q in qubits
    }
    target.add_instruction(circuit.library.standard_gates.RXGate(rx_theta), rx_props)

    # Rotation around Z-axis on Bloch sphere
    rz_props = {
        (q,): InstructionProperties(
            error=0.0, calibration=templates.rz(backend, (q,), rz_lambda)
        )
        for q in qubits
    }
    target.add_instruction(circuit.library.standard_gates.RZGate(rz_lambda), rz_props)

    # Delay instruction
    delay_props = {
        (q,): InstructionProperties(
            error=0.0, calibration=templates.delay(backend, (q,), delay_tau)
        )
        for q in qubits
    }
    target.add_instruction(circuit.Delay(delay_tau), delay_props)

    measure_instruction = circuit.measure.Measure()

    # Measurement

    # Add all the qubits that are going to be measured
    measure_props = {
        (q,): InstructionProperties(
            error=0.0,
            calibration=templates.measure(
                backend, [q], device_properties=device_properties
            ),
        )
        for q in qubits
    }
    target.add_instruction(measure_instruction, measure_props)

    # a qubit coupled to itself in coupling_map means the device has no couplers
    coupled_qubit_idxs = [
        pair for pair in backend.data.coupling_map if pair[0] != pair[1]
    ]
    cz_props = _get_cz_props(backend, coupled_qubit_idxs, device_properties)
    if cz_props:
        target.add_instruction(circuit.library.CZGate(), cz_props)

    return target


def _get_cz_props(
    backend: "TergiteBackend",
    coupled_qubit_idxs: List[Tuple[int, int]],
    device_properties: "DeviceCalibration",
) -> Dict[Tuple[int, int], InstructionProperties]:
    """Gets the CZ of each coupled pair whose coupler is calibrated, warning of the others

    Args:
        backend: the backend whose CZs they are
        coupled_qubit_idxs: the pairs of coupled qubit indexes
        device_properties: the calibration of the backend's device

    Returns:
        the CZ's instruction properties of each pair that has one
    """
    cz_props = {}
    uncalibrated_pairs = []
    for pair in coupled_qubit_idxs:
        try:
            schedule = templates.cz(
                backend,
                control_qubit_idxs=[pair[0]],
                target_qubit_idxs=[pair[1]],
                device_properties=device_properties,
            )
        except UncalibratedCouplerError:
            uncalibrated_pairs.append(pair)
            continue
        cz_props[pair] = InstructionProperties(error=0.0, calibration=schedule)

    if uncalibrated_pairs:
        warnings.warn(
            f"Backend '{backend.name}' has no CZ on {uncalibrated_pairs}, "
            "whose couplers are not calibrated"
        )
    return cz_props
