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
# This code was modified from the original by:
#
# - Martin Ahindura 2023
# - Stefan Hill 2023
"""Handles the creation of schedules for the devices of type OpenPulseBackend"""
from typing import TYPE_CHECKING, Iterable

import numpy as np
import qiskit.circuit as circuit
import qiskit.pulse as pulse
from qiskit.pulse.library import SymbolicPulse
from sympy import symbols

from .functions import delta_t_function_sympy

if TYPE_CHECKING:
    from .backend import DeviceCalibrationV2, OpenPulseBackend


def rx(
    backend: "OpenPulseBackend",
    qubits: Iterable,
    rx_theta: circuit.Parameter,
    device_properties: "DeviceCalibrationV2",
) -> pulse.ScheduleBlock:
    """Creates a rotation around the x-axis on the Bloch sphere for the list of qubits in the backend.

    It returns a backend-specific schedule which implements a
    rotation on a set of qubits around the x-axis on the Bloch sphere.
    The schedule is parameterised by θ [rad], which specifies the angle.

    Args:
        backend: the backend for which the schedule is to be created.
        qubits: the set of qubits to be affected.
        rx_theta: the theta parameter for the circuit
        device_properties: the device parameters of the backend

    Returns:
        qiskit.pulse.ScheduleBlock: the schedule implementing the rotation
    """
    qubit = device_properties.qubits

    sched = pulse.ScheduleBlock(name=f"RX(θ, {qubits})")
    for q in qubits:
        sched += pulse.SetFrequency(
            qubit[q].frequency.value,
            channel=backend.drive_channel(q),
        )
        sched += pulse.Play(
            pulse.Gaussian(
                duration=round(qubit[q].pi_pulse_duration.value / backend.dt),
                amp=rx_theta / np.pi * qubit[q].pi_pulse_amplitude.value,
                sigma=round(qubit[q].pulse_sigma.value / backend.dt),
                name=f"RX q{q}",
            ),
            channel=backend.drive_channel(q),
        )

    return sched


def rz(
    backend: "OpenPulseBackend", qubits: Iterable, rz_lambda: circuit.Parameter
) -> pulse.ScheduleBlock:
    """Creates a rotation around the z-axis on the Bloch sphere for the list of qubits in the backend.

    It returns a backend-specific schedule which implements a rotation on a set
    of qubits around the z-axis on the Block sphere. The schedule is
    parameterised by λ [rad], which specifies the angle.

    Args:
        backend: the backend for which the schedule is to be created.
        qubits: the set of qubits to be affected.
        rz_lambda: the lambda parameter for the circuit

    Returns:
        qiskit.pulse.ScheduleBlock: the schedule implementing the rotation
    """
    sched = pulse.ScheduleBlock(name=f"RZ(λ, {qubits})")
    for q in qubits:
        sched += pulse.ShiftPhase(
            rz_lambda, channel=backend.drive_channel(q), name=f"RZ q{q}"
        )
    return sched


def wacqt_cz_gate(duration, name, numerical_args):
    # define the time variable
    t = symbols("t", real=True)

    # define symbolic variables (can also be passed as parameters)
    symbolic_args = {
        "t_w": symbols("t_w", real=True),
        "t_rf": symbols("t_rf", real=True),
        "t_p": symbols("t_p", real=True),
        "delta_0": symbols("delta_0", real=True),
    }

    # create the symbolic expression
    envelope_expr = delta_t_function_sympy(t, symbolic_args)

    # substitute numerical values into the symbolic expression
    if numerical_args:
        envelope_expr = envelope_expr.subs(numerical_args)

    numerical_args["amp"] = [numerical_args["amp"], 0]
    # create the SymbolicPulse instance
    instance = SymbolicPulse(
        pulse_type="Wacqt_cz_gate_pulse",
        duration=duration,
        parameters=numerical_args,
        envelope=envelope_expr,
        name=name,
    )

    return instance


def cz(
    backend: "OpenPulseBackend",
    control_qubit_idxs: Iterable,
    target_qubit_idxs: Iterable,
    device_properties: "DeviceCalibrationV2",
) -> pulse.ScheduleBlock:
    """Two qubit CNOT gate building block. TODO: Add doc comment."""
    # FIXME: Why choose to pass control_qubits and target_qubits as Iterables yet
    #    when being called, only as single value is passed
    sched = pulse.ScheduleBlock(
        name=f"CZ(θ, control={control_qubit_idxs}, target={target_qubit_idxs})"
    )

    for control_qubit_idx, target_qubit_idx in zip(
        control_qubit_idxs, target_qubit_idxs
    ):
        control_qubit = device_properties.qubits[control_qubit_idx]
        target_qubit = device_properties.qubits[target_qubit_idx]

        # Get control channels between control and target qubits

        control_channels = backend.control_channel((control_qubit.id, target_qubit.id))

        c_props = [
            x for x in device_properties.couplers if x.id == control_channels[0].index
        ]
        c_props = c_props[0] if c_props else None

        # TODO: raise error if c_props is none

        f1 = min(target_qubit.frequency.value, control_qubit.frequency.value)
        f0 = max(target_qubit.frequency.value, control_qubit.frequency.value)

        alpha0 = c_props.anharmonicity.value

        f2 = c_props.frequency.value  # Coupler frequency
        detuning = c_props.frequency_detuning.value  # detuning in radial frequency

        args = {
            "delta_0": c_props.cz_pulse_amplitude.value,  # Maximum delta value
            "Theta": c_props.cz_pulse_dc_bias.value,  # DC bias term
            "omega_c0": 2 * np.pi * f2,  # Maximum frequency in Hz
            "omega_Phi": detuning
            + 2 * np.pi * (f1 - f0 - alpha0),  # Transition frequency in Hz
            "phi": c_props.cz_pulse_phase_offset.value,  # Phase offset
            "t_w": c_props.cz_pulse_duration_before.value,  # s, duration before pulse
            "t_rf": c_props.cz_pulse_duration_rise.value,  # s, rise time
            "t_p": c_props.cz_pulse_duration_constant.value,  # s, constant pulse duration
        }

        t_gate = args["t_rf"] + args["t_p"] + 2 * args["t_w"]
        # required param for pulse, for display purposes delta_0 is equivalent to max_amplitude
        amp = args["delta_0"]
        # this is for display purposes, as we overriding frequency modulation in backend
        freq = int(f2)

        args["amp"] = amp
        args["freq"] = freq

        cz_gate = wacqt_cz_gate(
            duration=round(t_gate / backend.dt), name="cz_pulse", numerical_args=args
        )
        sched += pulse.Play(cz_gate, control_channels[0])

    return sched


def measure(
    backend: "OpenPulseBackend",
    qubits: Iterable,
    device_properties: "DeviceCalibrationV2",
) -> pulse.ScheduleBlock:
    """Creates a measurement on the list of qubits in the given backend.

    It returns a backend-specific schedule which implements
    a measurement on a set of qubits.

    Args:
        backend: the backend for which the schedule is to be created.
        qubits: the set of qubits to be affected.
        device_properties: the device parameters of the backend

    Returns:
        qiskit.pulse.ScheduleBlock: the schedule implementing the measurement
    """
    readout_resonator_props = device_properties.resonators

    sched = pulse.ScheduleBlock(name=f"Measure({qubits})")
    for q in qubits:
        readout_resonator = readout_resonator_props[q]
        sched += pulse.SetFrequency(
            readout_resonator.frequency.value,
            channel=backend.measure_channel(q),
        )
        sched += pulse.Play(
            pulse.Constant(
                amp=readout_resonator.pulse_amplitude.value,
                duration=round(readout_resonator.pulse_duration.value / backend.dt),
                name=f"Readout q{q}",
            ),
            channel=backend.measure_channel(q),
        )
        sched += pulse.Delay(
            duration=300,
            channel=backend.acquire_channel(q),
            name=f"Time of flight q{q}",
        )
        sched += pulse.Acquire(
            duration=round(readout_resonator.acq_integration_time.value / backend.dt),
            channel=backend.acquire_channel(q),
            mem_slot=backend.memory_slot(q),
            name=f"Integration window q{q}",
        )
    return sched


def delay(
    backend: "OpenPulseBackend",
    qubits: Iterable,
    delay_tau: circuit.Parameter,
    delay_str: str = "Delay",
) -> pulse.ScheduleBlock:
    """Creates a delay on the set of qubits in the backend.

    It returns a backend-specific schedule which implements a delay
    operation on a set of qubits.
    The schedule is parameterised by τ [ns], which specifies the delay duration.

    Args:
        backend: the backend for which the schedule is to be created.
        qubits: the set of qubits to be affected.
        delay_tau: the tau parameter for the circuit
        delay_str: the delay string for the instruction set

    Returns:
        qiskit.pulse.ScheduleBlock: the schedule implementing the delay
    """
    sched = pulse.ScheduleBlock(name=f"{delay_str}({qubits}, τ)")
    for q in qubits:
        sched += pulse.Delay(
            duration=delay_tau,
            channel=backend.drive_channel(q),
            name=f"{delay_str} q{q}",
        )
        sched += pulse.Delay(
            duration=delay_tau,
            channel=backend.measure_channel(q),
            name=f"{delay_str} q{q}",
        )
        sched += pulse.Delay(
            duration=delay_tau,
            channel=backend.acquire_channel(q),
            name=f"{delay_str} q{q}",
        )
    return sched
