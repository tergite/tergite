import numpy as np
import qiskit.circuit as circuit
import qiskit.pulse as pulse


def rx(
    backend: object, qubits: set, rx_theta: circuit.Parameter
) -> pulse.ScheduleBlock:
    """Returns a backend-specific schedule which implements a
    rotation on a set of qubits around the x-axis on the Bloch sphere.
    The schedule is parameterised by θ [rad], which specifies the angle.
    """
    ctq, _, _ = backend.calibration_tables
    two_tone = ctq["spectroscopy"]
    rabi = ctq["rabi_oscillations"]

    sched = pulse.ScheduleBlock(name=f"RX(θ, {qubits})")
    for q in qubits:
        sched += pulse.SetFrequency(
            two_tone[q].frequency, channel=backend.drive_channel(q)
        )
        sched += pulse.Play(
            pulse.Gaussian(
                duration=round(rabi[q].gauss_dur / backend.dt),
                amp=rx_theta / (2 * np.pi * rabi[q].frequency),
                sigma=round(rabi[q].gauss_sig / backend.dt),
                name=f"RX q{q}",
            ),
            channel=backend.drive_channel(q),
        )
    return sched


def rz(
    backend: object, qubits: set, rz_lambda: circuit.Parameter
) -> pulse.ScheduleBlock:
    """Returns a backend-specific schedule which implements a rotation on a set
    of qubits around the z-axis on the Block sphere. The schedule is
    parameterised by λ [rad], which specifies the angle.
    """
    sched = pulse.ScheduleBlock(name=f"RZ(λ, {qubits})")
    for q in qubits:
        sched += pulse.ShiftPhase(
            rz_lambda, channel=backend.drive_channel(q), name=f"RZ q{q}"
        )
    return sched


def measure(backend: object, qubits: set) -> pulse.ScheduleBlock:
    """Returns a backend-specific schedule which implements a measurement on a set of qubits."""
    _, ctr, _ = backend.calibration_tables

    rspec = ctr["spectroscopy"]

    sched = pulse.ScheduleBlock(name=f"Measure({qubits})")
    for q in qubits:
        sched += pulse.SetFrequency(
            rspec[q].frequency, channel=backend.measure_channel(q)
        )
        sched += pulse.Play(
            pulse.Constant(
                amp=rspec[q].square_amp,
                duration=round(rspec[q].square_dur / backend.dt),
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
            duration=round(rspec[q].integration_time / backend.dt),
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
