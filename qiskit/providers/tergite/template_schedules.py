import numpy as np
import qiskit.pulse as pulse


def rx(backend: object, qubits: set) -> pulse.ScheduleBlock:
    """Returns a backend-specific schedule which implements a rotation on a set of qubits around the x-axis on the Bloch sphere. The schedule is parameterised by θ [rad], which specifies the angle."""
    table = backend.calibration_table

    def empirical(θ: float, qubit: int):
        nonlocal table
        x90 = 1 / (2 * table["rabi_frequency"][qubit])
        A = table["rabi_amplitude"][qubit]
        p = table["rabi_phase"][qubit]
        c = table["rabi_offset"][qubit]
        return (np.arccos((θ - c) / A) - p) * x90 / np.pi

    sched = pulse.ScheduleBlock(name=f"RX(θ, {qubits})")
    for q in qubits:
        sched += pulse.Play(
            pulse.Gaussian(
                duration=round(table["rabi_dur_gauss"][q] / backend.dt),
                amp=empirical(Parameter("θ"), qubit),
                sigma=table["rabi_sig_gauss"][q] / backend.dt,
                name=f"RX q{q}",
            ),
            channel=backend.drive_channel(qubit),
        )
    return sched


def rz(backend: object, qubits: set) -> pulse.ScheduleBlock:
    """Returns a backend-specific schedule which implements a rotation on a set of qubits around the z-axis on the Block sphere. The schedule is parameterised by λ [rad], which specifies the angle."""
    sched = pulse.ScheduleBlock(name=f"RZ(λ, {qubits})")
    for q in qubits:
        sched += pulse.ShiftPhase(
            Parameter("λ"), channel=backend.drive_channel(q), name=f"RZ q{q}"
        )
    return sched


def measure(backend: object, qubits: set) -> pulse.ScheduleBlock:
    """Returns a backend-specific schedule which implements a measurement on a set of qubits."""
    table = backend.calibration_table
    sched = pulse.ScheduleBlock(name=f"Measure({qubits})")
    for q in qubits:
        sched += pulse.Play(
            pulse.Constant(
                amp=table["ro_amp_square"][q],
                duration=round(table["ro_dur_square"][q] / backend.dt),
                name=f"Readout q{q}",
            ),
            channel=backend.measure_channel(q),
        )
        sched += pulse.Delay(
            duration=round(table["ro_tof"][q] / backend.dt),
            channel=backend.acquire_channel(q),
            name=f"Time of flight q{q}",
        )
        sched += pulse.Acquire(
            duration=round(table["ro_integration_time"][q] / backend.dt),
            channel=backend.acquire_channel(q),
            mem_slot=backend.memory_slot(q),
            name=f"Integration window q{q}",
        )
    return sched


def delay(backend: object, qubits: set) -> pulse.ScheduleBlock:
    """Returns a backend-specific schedule which implements a delay operation on a set of qubits. The schedule is parameterised by τ [ns], which specifies the delay duration."""
    sched = pulse.ScheduleBlock(name=f"Delay({qubits}, τ)")
    for q in qubits:
        sched += pulse.Delay(
            duration=Parameter("τ"),
            channel=backend.drive_channel(q),
            name=f"Delay q{q}",
        )
        sched += pulse.Delay(
            duration=Parameter("τ"),
            channel=backend.measure_channel(q),
            name=f"Delay q{q}",
        )
        sched += pulse.Delay(
            duration=Parameter("τ"),
            channel=backend.acquire_channel(q),
            name=f"Delay q{q}",
        )
    return sched
