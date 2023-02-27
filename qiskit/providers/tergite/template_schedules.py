import numpy as np
import qiskit.circuit as circuit
import qiskit.pulse as pulse

#from .device_properties import qubit, readout_resonator

def rx(
    backend: object, qubits: set, rx_theta: circuit.Parameter
) -> pulse.ScheduleBlock:
    """Returns a backend-specific schedule which implements a
    rotation on a set of qubits around the x-axis on the Bloch sphere.
    The schedule is parameterised by θ [rad], which specifies the angle.
    """
    #print(f"creating rx instruction for the {backend.name=} .... ...")
    #print(f"{qubits=}")
    #print(f"{rx_theta=}")

    #ctq, _, _ = backend.calibration_tables
    #two_tone = ctq["spectroscopy"]
    #rabi = ctq["rabi_oscillations"]
    device_properties = backend.device_properties
    qubit = device_properties.get("qubit")
    
    sched = pulse.ScheduleBlock(name=f"RX(θ, {qubits})")
    for q in qubits:
        sched += pulse.SetFrequency(
            #two_tone[q].frequency, channel=backend.drive_channel(q)
            qubit[q]["frequency"], channel=backend.drive_channel(q)
        )
        #print(f"{q=}  {(qubit[q]['frequency'])=}")
        sched += pulse.Play(
            pulse.Gaussian(
                #duration=round(rabi[q].gauss_dur / backend.dt),
                duration=round(qubit[q].get("pi_pulse_duration") / backend.dt),
                #amp=rx_theta / (2 * np.pi * rabi[q].frequency),
                amp=rx_theta / (qubit[q].get("pi_pulse_amplitude")),
                #sigma=round(rabi[q].gauss_sig / backend.dt),
                sigma=round(qubit[q].get("pulse_sigma") / backend.dt),
                name=f"RX q{q}",
            ),
            channel=backend.drive_channel(q),
        )
        """ print(f"{q=}  {(round(qubit[q].get('gauss_dur') / backend.dt))=}")
        print(f"{q=}  {(rx_theta / (2 * np.pi * qubit[q].get('frequency')))=}")
        print(f"{q=}  {(round(qubit[q].get('gauss_sig') / backend.dt))=}") """

        #print(f"{q=}  {(qubit[q].get('pi_pulse_duration'))=}")
        #print(f"{q=}  {(rx_theta / (qubit[q].get('pi_pulse_amplitude')))=}")
        #print(f"{q=}  {(qubit[q].get('pulse_sigma'))=}")
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
    #_, ctr, _ = backend.calibration_tables
    #rspec = ctr["spectroscopy"]
    
    device_properties = backend.device_properties
    readout_resonator = device_properties.get("readout_resonator")
 
    sched = pulse.ScheduleBlock(name=f"Measure({qubits})")
    for q in qubits:
        sched += pulse.SetFrequency(
            #rspec[q].frequency, channel=backend.measure_channel(q)
            readout_resonator[q].get("frequency"), channel=backend.measure_channel(q)        
        )
        sched += pulse.Play(
            pulse.Constant(
                #amp=rspec[q].square_amp,
                amp=readout_resonator[q].get("pulse_amplitued"),
                #duration=round(rspec[q].square_dur / backend.dt),
                duration=round(readout_resonator[q].get("pulse_duration") / backend.dt),
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
            #duration=round(rspec[q].integration_time / backend.dt),
            duration=round(readout_resonator[q].get("acq_integration_time") / backend.dt),
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
