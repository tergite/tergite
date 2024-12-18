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
# This code was refactored from the original on 22nd September, 2023 by Martin Ahindura
"""Handles the calibration of the devices of type OpenPulseBackend"""
from dataclasses import dataclass
from typing import TYPE_CHECKING

import qiskit.circuit as circuit
from qiskit.transpiler import InstructionProperties, Target

from . import template_schedules as templates

if TYPE_CHECKING:
    from .backend import DeviceCalibrationV2, OpenPulseBackend


# TODO: Replace with BCC graph node
@dataclass(frozen=True)
class Node:
    """Parsing node for job objects from the API

    Note: the keys in the job objects should be
    valid Python string identifiers

    This node transforms the keys in the job object
    into attributes

    Attributes:
        data: the data to instantiate the node with
    """

    data: dict

    def __post_init__(self):
        # subvert frozen restriction, create new frozen fields for key value pairs in data
        for k, v in self.data.items():
            object.__setattr__(self, k, v)

    def __repr__(self) -> str:
        return self.job_id


def add_instructions(
    *,
    backend: "OpenPulseBackend",
    qubits: tuple,
    coupled_qubit_idxs: tuple,
    target: Target,
    device_properties: "DeviceCalibrationV2"
):
    """Adds Rx, Rz gates and Delay and Measure instructions for each qubit
    to the transpiler target provided.

    Implementations are backend dependent and are based on a specific calibration.

    Args:
        backend: the instance of
            :class:`~tergite.providers.tergite.backend:TergiteBackend`
            for which to add the instructions
        qubits: a tuple of qubits on which the instruction is to be run
        coupled_qubit_idxs: a tuple of tuples of qubit indexes that are coupled
        target: the target on which the instruction is to be added
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

    if coupled_qubit_idxs:
        cz_props = {
            (control_qubit_idx, target_qubit_idx): InstructionProperties(
                error=0.0,
                calibration=templates.cz(
                    backend,
                    control_qubit_idxs=[control_qubit_idx],
                    target_qubit_idxs=[target_qubit_idx],
                    device_properties=device_properties,
                ),
            )
            for control_qubit_idx, target_qubit_idx in coupled_qubit_idxs
        }

        target.add_instruction(circuit.library.CZGate(), cz_props)
