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

if TYPE_CHECKING:
    from .backend import OpenPulseBackend


def rx(
    backend: "OpenPulseBackend", qubits: Iterable, rx_theta: circuit.Parameter
) -> pulse.ScheduleBlock:
    """Creates a rotation around the x-axis on the Bloch sphere for the list of qubits in the backend.

    It returns a backend-specific schedule which implements a
    rotation on a set of qubits around the x-axis on the Bloch sphere.
    The schedule is parameterised by θ [rad], which specifies the angle.

    Args:
        backend: the backend for which the schedule is to be created.
        qubits: the set of qubits to be affected.
        rx_theta: the theta parameter for the circuit

    Returns:
        qiskit.pulse.ScheduleBlock: the schedule implementing the rotation
    """
    device_properties = backend.device_properties
    qubit = device_properties.get("qubit")

    sched = pulse.ScheduleBlock(name=f"RX(θ, {qubits})")
    for q in qubits:
        sched += pulse.SetFrequency(
            qubit[q]["frequency"],
            channel=backend.drive_channel(q),
        )
        sched += pulse.Play(
            pulse.Gaussian(
                duration=round(qubit[q].get("pi_pulse_duration") / backend.dt),
                amp=rx_theta / np.pi * qubit[q].get("pi_pulse_amplitude"),
                sigma=round(qubit[q].get("pulse_sigma") / backend.dt),
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


def measure(backend: "OpenPulseBackend", qubits: Iterable) -> pulse.ScheduleBlock:
    """Creates a measurement on the list of qubits in the given backend.

    It returns a backend-specific schedule which implements
    a measurement on a set of qubits.

    Args:
        backend: the backend for which the schedule is to be created.
        qubits: the set of qubits to be affected.

    Returns:
        qiskit.pulse.ScheduleBlock: the schedule implementing the measurement
    """
    device_properties = backend.device_properties
    readout_resonator_props = device_properties.get("readout_resonator")

    sched = pulse.ScheduleBlock(name=f"Measure({qubits})")
    for q in qubits:
        readout_resonator = readout_resonator_props[q]
        sched += pulse.SetFrequency(
            readout_resonator.get("frequency"),
            channel=backend.measure_channel(q),
        )
        sched += pulse.Play(
            pulse.Constant(
                amp=readout_resonator.get("pulse_amplitude"),
                duration=round(readout_resonator.get("pulse_duration") / backend.dt),
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
            duration=round(readout_resonator.get("acq_integration_time") / backend.dt),
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
