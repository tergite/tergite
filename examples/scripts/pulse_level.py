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
"""A sample script running pulse-level jobs: a gate with pulses of its own, and pulses alone

It needs the `pulse` extra, `pip install "tergite[pulse]"`, a project an admin has allowed
pulse-level jobs in the dashboard, and a device that takes them. The account comes from the
environment variables TERGITE_API_URL and TERGITE_API_TOKEN.
"""
import oqpy
import qiskit.circuit as circuit
import qiskit.compiler as compiler

from tergite import Tergite

if __name__ == "__main__":
    # a device that takes pulse-level jobs, within the limits its operators set
    BACKEND_NAME = "Loke"
    # the timeout in seconds for how long to keep checking for results
    POLL_TIMEOUT = 100

    # the account of TERGITE_API_URL and TERGITE_API_TOKEN, which nothing saves to disk
    provider = Tergite.get_provider()
    backend = provider.get_backend(BACKEND_NAME)
    backend.set_options(shots=1024)

    # the frames the device publishes, as oqpy frames, and its gates' pulses as defcals
    frames = backend.frames
    print(sorted(frames))
    print(backend.calibrations[("x", (0,))])

    # an X on qubit 0 played as a gaussian of our own, for this job alone
    qc = circuit.QuantumCircuit(1, 1)
    qc.x(0)
    qc.measure(0, 0)
    defcals = oqpy.Program()
    gaussian = oqpy.declare_waveform_generator(
        "gaussian",
        [("amp", oqpy.complex128), ("d", oqpy.duration), ("sigma", oqpy.duration)],
    )
    with oqpy.defcal(defcals, oqpy.PhysicalQubits[0], "x"):
        defcals.play(frames["q00_drive"], gaussian(0.15, 40e-9, 10e-9))

    tc = compiler.transpile(qc, backend=backend, initial_layout=[0])
    job = backend.run(tc, calibrations=[defcals])
    job.wait_for_final_state(timeout=POLL_TIMEOUT)
    print(job.result().get_counts())

    # pulses alone: a readout pulse on qubit 0, its response captured as an IQ point
    program = oqpy.Program()
    constant = oqpy.declare_waveform_generator(
        "constant", [("amp", oqpy.complex128), ("d", oqpy.duration)]
    )
    capture = oqpy.declare_extern(
        "capture_v1", [("frame", oqpy.frame), ("d", oqpy.duration)], oqpy.bit
    )
    clbits = oqpy.BitVar(name="c", size=1)
    with oqpy.Cal(program):
        program.play(frames["q00_readout"], constant(0.1, 400e-9))
        program.set(clbits[0], capture(frames["q00_readout"], 400e-9))

    job = backend.run(program)
    job.wait_for_final_state(timeout=POLL_TIMEOUT)
    # a program that does not measure runs at meas_level 1: each shot's IQ point
    memory = job.result().get_memory()
    print(memory.shape, memory[:3])
