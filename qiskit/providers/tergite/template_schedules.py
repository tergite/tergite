import numpy as np
import qiskit.circuit as circuit
import qiskit.pulse as pulse


def rx(
    backend: object, qubits: set, rx_theta: circuit.Parameter
) -> pulse.ScheduleBlock:
    """Returns a backend-specific schedule which implements a rotation on a set of qubits around the x-axis on the Bloch sphere. The schedule is parameterised by θ [rad], which specifies the angle."""
    table = backend.calibration_table
    sched = pulse.ScheduleBlock(name=f"RX(θ, {qubits})")
    for q in qubits:
        sched += pulse.SetFrequency(
            table["qubit_frequency"][q], channel=backend.drive_channel(q)
        )
        sched += pulse.Play(
            pulse.Gaussian(
                duration=round(table["rabi_dur_gauss"][q] / backend.dt),
                amp=rx_theta / (2 * np.pi * table["rabi_frequency"][q]),
                sigma=table["rabi_sig_gauss"][q] / backend.dt,
                name=f"RX q{q}",
            ),
            channel=backend.drive_channel(q),
        )
    return sched


def rz(
    backend: object, qubits: set, rz_lambda: circuit.Parameter
) -> pulse.ScheduleBlock:
    """Returns a backend-specific schedule which implements a rotation on a set of qubits around the z-axis on the Block sphere. The schedule is parameterised by λ [rad], which specifies the angle."""
    sched = pulse.ScheduleBlock(name=f"RZ(λ, {qubits})")
    for q in qubits:
        sched += pulse.ShiftPhase(
            rz_lambda, channel=backend.drive_channel(q), name=f"RZ q{q}"
        )
    return sched


def measure(backend: object, qubits: set) -> pulse.ScheduleBlock:
    """Returns a backend-specific schedule which implements a measurement on a set of qubits."""
    table = backend.calibration_table
    sched = pulse.ScheduleBlock(name=f"Measure({qubits})")

    def resonator_line(qubit: int):
        nonlocal table
        m = table["resonator_slope"][qubit]
        c = table["resonator_intercept"][qubit]
        x = table["ro_amp_square"][qubit]
        return m * x + c

    for q in qubits:
        sched += pulse.SetFrequency(
            resonator_line(q), channel=backend.measure_channel(q)
        )
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


def delay(
    backend: object, qubits: set, delay_tau: circuit.Parameter, delay_str: str = "Delay"
) -> pulse.ScheduleBlock:
    """Returns a backend-specific schedule which implements a delay operation on a set of qubits. The schedule is parameterised by τ [ns], which specifies the delay duration."""
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
