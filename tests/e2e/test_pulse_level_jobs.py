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
"""End-to-end tests of pulse-level jobs on Loke's dummy clusters, whose data mean nothing,
so these check what runs and what is refused, not physics"""
import os

import oqpy
import pytest
from qiskit import QuantumCircuit, transpile

from tergite import Provider, Tergite, TergiteBackend
from tergite.exc import ApiError
from tests.utils.jobs import wait_for_final_state

# the app token of tergite-frontend's ui/fixtures project that may send pulse-level jobs;
# API_TOKEN's project may not
PULSE_TOKEN = "ee13b8c6df6b55770e73b9887e9ffca8489864d290935503"
SHOTS = 100


@pytest.fixture
def pulse_backend() -> TergiteBackend:
    """Loke's backend, through a provider of a project that may send pulse-level jobs"""
    provider = Tergite.use_provider_account(
        service_name="pulse", url=os.environ["API_URL"], token=PULSE_TOKEN
    )
    return provider.get_backend("Loke")


def test_loke_publishes_its_frames_and_defcals(pulse_backend):
    frames = pulse_backend.frames
    calibrations = pulse_backend.calibrations

    assert {"q00_drive", "q00_readout", "q01_drive", "q01_readout"} <= set(frames)
    assert {("x", (0,)), ("sx", (0,)), ("rz", (0,)), ("x", (1,))} <= set(calibrations)


def test_a_circuit_runs_with_its_own_defcal(pulse_backend):
    drive = pulse_backend.frames["q00_drive"]
    defcals = oqpy.Program()
    gaussian = oqpy.declare_waveform_generator(
        "gaussian",
        [("amp", oqpy.complex128), ("d", oqpy.duration), ("sigma", oqpy.duration)],
    )
    with oqpy.defcal(defcals, oqpy.PhysicalQubits[0], "x"):
        defcals.play(drive, gaussian(0.2, 40e-9, 10e-9))

    job = pulse_backend.run(
        _get_x_circuit(pulse_backend), calibrations=[defcals], shots=SHOTS
    )

    counts = _get_counts(job)
    assert sum(counts.values()) == SHOTS


def test_a_circuit_runs_with_the_published_defcal(pulse_backend):
    defcal = pulse_backend.calibrations[("x", (0,))]

    job = pulse_backend.run(
        _get_x_circuit(pulse_backend), calibrations=[defcal], shots=SHOTS
    )

    assert sum(_get_counts(job).values()) == SHOTS


def test_a_cal_block_plays_and_captures_iq_points(pulse_backend):
    readout = pulse_backend.frames["q00_readout"]
    program = oqpy.Program()
    constant = oqpy.declare_waveform_generator(
        "constant", [("amp", oqpy.complex128), ("d", oqpy.duration)]
    )
    capture = oqpy.declare_extern(
        "capture_v1", [("frame", oqpy.frame), ("d", oqpy.duration)], oqpy.bit
    )
    clbits = oqpy.BitVar(name="c", size=1)
    with oqpy.Cal(program):
        program.play(readout, constant(0.1, 400e-9))
        program.set(clbits[0], capture(readout, 400e-9))

    job = pulse_backend.run(program, shots=SHOTS)

    wait_for_final_state(job)
    memory = job.result().get_memory()
    assert memory.shape == (SHOTS, 1)


def test_a_project_without_pulse_access_is_refused(backend_provider: Provider):
    backend = backend_provider.get_backend("Loke")

    with pytest.raises(ApiError, match="pulse"):
        backend.run(_get_amplitude_program(0.2), shots=SHOTS)


def test_a_pulse_beyond_the_devices_limits_is_refused(pulse_backend):
    with pytest.raises(ApiError, match="is beyond the device's limit of 0.8"):
        pulse_backend.run(_get_amplitude_program(0.9), shots=SHOTS)


def _get_x_circuit(backend: TergiteBackend) -> QuantumCircuit:
    """Gets an X on qubit 0, measured, transpiled to the backend"""
    circuit = QuantumCircuit(1, 1)
    circuit.x(0)
    circuit.measure(0, 0)
    return transpile(circuit, backend=backend, initial_layout=[0])


def _get_amplitude_program(amplitude: float) -> str:
    """Gets a program that plays a constant of the amplitude on qubit 0's drive, measured"""
    return f"""OPENQASM 3.0;
defcalgrammar "openpulse";
bit[1] c;
cal {{
    play(q00_drive, constant({amplitude}, 40ns));
}}
c[0] = measure $0;
"""


def _get_counts(job) -> dict:
    """Gets the job's counts, once it is final"""
    wait_for_final_state(job)
    return job.result().get_counts()
